# 接口与 Schema 契约

> 本文定义拟实现的接口，不代表已有可调用服务。请求/响应由后端 Pydantic 模型实现，数据库映射模型另由 SQLAlchemy 实现。两者不能混用：数据库中的手机号密文、审核信息和内部状态不应因为“直接序列化表对象”而被返回客户端。

## 1. 通用规则

为了让前端知道每次请求应传什么、失败后如何恢复，所有接口均定义独立输入和输出模型。下面的 `Create`、`Patch`、`Read` 分别表示创建请求、修改请求和读取响应的字段结构；它们是设计模型名，不是仓库已有类。

| 规则 | 约定 |
|---|---|
| 路径与认证 | `/v1`；除验证码、登录和健康检查外均要求 Bearer 访问凭证；首版不提供游客私有会话 |
| 标识符 | UUID 字符串；身份始终来自服务端已验证会话，普通写接口不接收 author_id/user_id |
| 时间 | 带时区的 ISO 8601 字符串；请求若给无时区时间返回 422 |
| 钱 | 整数分，币种 CNY；预算指“每人总预算”，不默认包含交通/餐饮 |
| 未知字段 | Pydantic 配置 extra=forbid；PATCH 区分未传与明确 null |
| 成功 | GET/PATCH/PUT 常用 200，创建 201，入队 202，删除 204；不包无意义的 success=true |
| 分页 | `{items: T[], next_cursor: string|null}`，limit 默认 20，最大 50 |
| 错误 | `{error:{code,message,details},request_id}`；details 仅白名单字段，不泄露内部堆栈 |
| 并发编辑 | `expected_version`；条件更新未命中返回 409 VERSION_CONFLICT 与当前版本号 |
| 重试去重 | 指定创建/提交接口携带 Idempotency-Key；同 key 不同 body 返回 409 |
| 异步操作 | 返回 job_id 或 turn_id 与状态；客户端轮询恢复，不依赖进程内后台任务 |

错误码至少覆盖 AUTH_REQUIRED、SESSION_EXPIRED、FORBIDDEN、NOT_FOUND、VERSION_CONFLICT、IDEMPOTENCY_MISMATCH、MEDIA_NOT_READY、CONTENT_REJECTED、STALE_OPTIONS、RATE_LIMITED、UPSTREAM_UNAVAILABLE、NO_MATCHES。私有对象越权读取返回 404；已认证但没有后台角色返回 403；无效字段返回 422。

Pydantic 用于将输入解析并校验为明确的数据类型；外键存在性和用户权限仍由业务服务检查，不能把“字段校验通过”当成“有权使用该对象”。[Pydantic 模型文档](https://docs.pydantic.dev/latest/concepts/models/)

## 2. 登录、账户与权限

| 方法与路径 | 请求 Schema | 返回与权限 |
|---|---|---|
| POST `/auth/challenges` | ChallengeCreate | 202 ChallengeRead；限流，未登录可用 |
| POST `/auth/verify` | LoginVerify | TokenPair + UserRead；一次消费验证码，首次自动创建账户 |
| POST `/auth/refresh` | RefreshRequest；网页改用 Cookie | 新 TokenPair；轮换续期凭证 |
| POST `/auth/logout` | 无 | 204；撤销当前 session，重复调用可成功 |
| GET `/me` | 无 | UserRead |
| PATCH `/me` | ProfilePatch | UserRead |
| DELETE `/me` | recent_challenge_id、code | 202；二次验证后启动注销，立即撤销会话 |
| GET `/me/interests` | 无 | InterestRead[] |
| PUT `/me/interests` | InterestReplace | 显式偏好列表，替换操作 |
| GET `/me/contents` | kind、status、cursor | 本人已发布内容 |
| GET `/me/drafts` | cursor | 本人草稿摘要 |
| GET `/me/bookmarks` | cursor | 当前可见的收藏内容；已下架项可显示不可用占位 |

`ChallengeCreate` 字段：phone 为规范化手机号字符串，默认支持大陆 +86；purpose 固定 login 或 delete_account；登录用途包含 terms_version；删除用途必须先登录且手机号等于本人号码。服务端限制号码/IP/设备请求频率，例如重发间隔 60 秒、验证码 5 分钟有效、最多 5 次尝试，这些是可配置初值。

`ChallengeRead`：challenge_id、expires_in_seconds、resend_after_seconds。响应不透露号码是否已注册。发送任务受幂等键约束；验证码随机生成后只保留校验 HMAC 和仅供发送任务读取的短时密文，发送成功即清除密文。调用短信商遇到未知结果时使用供应商请求去重号；供应商不支持去重时不盲目重发同一挑战，标记待用户重新获取。

`LoginVerify`：challenge_id、code（6 位数字字符串）、device_label（<=100 字符）、client_type（mobile/editor_web）。只接受 purpose=login 的挑战；delete_account 挑战只能由 DELETE /me 消费。首次登录的账户创建、挑战消费、session 和 refresh token 行写入在同一事务完成；并发首次登录由 phone_lookup_hash 唯一键保证仅一个账户。`TokenPair`：access_token、token_type="bearer"、expires_in=900、refresh_token（仅移动端响应）、session_id。网页响应只把 refresh_token 写入受保护 Cookie；移动端存设备安全存储，不写日志。

`UserRead`：id、display_name、bio、avatar（MediaRead|null）、city（CityRead|null）、personalization_enabled、roles。ProfilePatch 只允许 display_name、bio、avatar_asset_id、city_id、personalization_enabled；不能改手机号、角色或状态。改绑号码放后续版本。

`InterestReplace`：items 数组最多 30 项，每项 `{tag_id, preference: like|dislike}`；服务端分别映射 explicit weight 1/0，删除未包含的 explicit 项。inferred 项不可由该接口写入。

JWT 的签名用于验证令牌未被修改，不提供载荷加密；因此不放手机号等个人信息。FastAPI 提供安全请求处理工具，本设计的短信认证、轮换和会话撤销仍需自行实现。[FastAPI 安全文档](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)

## 3. 城市、活动与地点

| 方法与路径 | 请求 | 响应 |
|---|---|---|
| GET `/cities` | enabled=true | CityRead[]；首发只有上海启用 |
| GET `/cities/{id}/districts` | 无 | DistrictRead[] |
| GET `/tags` | category? | TagRead[] |
| GET `/events/{id}` | 无 | EventRead；只能读取 published/ended/cancelled 公开资料 |
| GET `/events/{id}/sessions` | from、to、cursor | EventSessionRead[] |
| GET `/places/{id}` | 无 | PlaceRead；draft 不可公开读 |
| PUT `/events/{id}/participation` | ParticipationUpsert | ParticipationRead |
| DELETE `/events/{id}/participation` | 无 | 204 |

`CityRead`：id、code、name、timezone。`DistrictRead`：id、city_id、code、name。`TagRead`：id、slug、name、category。

`Price`：status=free|known|unknown、min_fen:int|null、max_fen:int|null、currency="CNY"、basis=per_person|reference。free 对应 0/0；unknown 对应 null/null。每人预算筛选只接受可比的 per_person 价格，reference 仅展示，并要求用户确认是否接受预算不确定项。

数据库 places/events/event_sessions 中持久化 `price_basis text(per_person/reference)`，不能只在响应时凭空推断。跨活动价格高低范围不等于实际可购票档位；没有票务连接时不保证库存。

`PlaceRead`：id、name、city_id、district_id|null、address、category、coordinates|null、opening_hours、price、status、verified_at|null。coordinates={latitude,longitude}；不是客户端实时位置。

`OpeningHours`：schema_version=1、timezone、weekly（每项 weekday:1..7 和 intervals:[{opens:"HH:mm",closes:"HH:mm",closes_next_day:bool}]）、exceptions（date、closed、intervals）、notes。服务器按例外日期优先、周规则其次判断是否营业；空 weekly 表示未知而非 24 小时开放，跨午夜必须显式标识。

`EventRead`：id、title、description、city_id、category、place:PlaceRead|null、organizer|null、attendance_mode、status、price、booking_url|null、verified_at|null、upcoming_sessions（最多 5 场）、participation:ParticipationRead|null。

`EventSessionRead`：id、event_id、starts_at、ends_at、last_entry_at|null、timezone、status、price、booking_url|null、verified_at|null。`ParticipationUpsert`：state=interested|attended、session_id|null、attended_at|null、origin_agent_result_id|null。后端重验结果归属与引用关系。

## 4. 图片上传

| 方法与路径 | 请求 | 响应 |
|---|---|---|
| POST `/media/uploads` | MediaUploadCreate；Idempotency-Key | 201 UploadTicket |
| POST `/media/{id}/complete` | 无 | 202 MediaRead；只改变 processing 状态并入队 |
| GET `/media/{id}` | 无 | MediaRead；权限判断后生成可访问变体 URL |
| DELETE `/media/{id}` | 无 | 204 或 409 ASSET_IN_USE |

`MediaUploadCreate`：purpose、file_name（仅用于显示，不作为 storage_key）、mime_type、size_bytes。首版 JPEG/PNG/WebP，单图<=20MB，单篇最多20图，最长边限制由服务端图片解码验证；iOS HEIC 在本机转换后上传。头像另有较小限制。

`UploadTicket`：asset_id、method=PUT、upload_url、required_headers、expires_at、max_bytes。服务端生成随机且限定到当前用户的存储 key。上传签名仅允许该 key；若存储供应商支持策略限长则同时使用，否则完成校验时拒绝超大文件，文件不会因此自动公开。

`MediaRead`：id、status、width|null、height|null、variants（thumb/feed/detail，各含 url,width,height,expires_at|null）、error_code|null。客户端上传成功不等于图片 ready；complete 接口核验存储对象存在后入队，worker 解码、检查并生成变体。正文只保存 asset_id，不能保存 upload_url 或任意外部图片 URL。

## 5. Notes 与通用正文格式

### 内容接口

| 方法与路径 | 请求 | 返回 |
|---|---|---|
| POST `/notes` | NoteCreate；Idempotency-Key | 201 DraftRead；创建空草稿也允许 |
| GET `/notes/{id}` | 无 | NoteDetail；只返回公开版本，本人编辑走 draft 接口 |
| GET `/notes/{id}/draft` | 无 | DraftRead；仅作者 |
| PATCH `/notes/{id}/draft` | DraftPatch | DraftRead；仅作者，检查 edit_version |
| POST `/notes/{id}/publish` | PublishRequest；Idempotency-Key | 202 PublishReceipt |
| GET `/notes/{id}/publication` | 无 | PublicationRead；本人可读审核结果 |
| DELETE `/notes/{id}` | expected_version | 204；隐藏并取消未完成发布资格 |
| GET `/editorials/{id}` | 无 | EditorialDetail；公开版本 |
| PUT `/contents/{id}/reactions/{kind}` | kind=like/bookmark | ReactionRead |
| DELETE `/contents/{id}/reactions/{kind}` | 无 | 204 |
| POST `/contents/{id}/reports` | ReportCreate | 201 ReportRead |
| PUT/DELETE `/users/{id}/block` | 无 | 204 |

`NoteCreate`：city_id，其他字段初始为空；kind=note、author_id 从服务端确定。`DraftPatch`：expected_version 必填；title、document、cover_asset_id、tag_ids、link_refs 可选。字段出现表示更新，null 只适用于允许清空的字段。采用整个正文快照而非字符级合并；自动保存建议停止输入 1 秒后触发，本地每次编辑先落盘。

`DraftRead`：content_id、kind、title、document、cover_asset_id、tag_ids、link_refs、edit_version、updated_at、published_revision_id|null、latest_submission:PublicationRead|null。它不混入公开版本正文。

`PublishRequest`：expected_edit_version。`PublishReceipt`：content_id、revision_id、review_status=pending、job_id。`PublicationRead`：revision_id、review_status、is_current_published、reason_code|null、updated_at。审核 approved 不必然说明该版本当前公开，必须检查 is_current_published；例如该版本比另一提交旧。

`NoteDetail`：id、kind="note"、author（id、display_name、avatar）、city、revision_id、title、document、cover、tags、linked_entities、first_published_at、updated_at、reactions、viewer_permissions。`EditorialDetail` 另含 editor_byline、authoring_mode、sources（可展示的事实来源）。阅读详情永远使用公开快照，不能自动把本人草稿混进去。

### 富文本结构

为了同时支持原生阅读和网页编辑，服务器只接受一个受限文档格式。Tiptap 编辑器通过转换器产生这种格式；不接受任意 HTML、任意脚本或全部 Tiptap 扩展节点。Tiptap 支持 JSON 文档持久化，但本项目的约束与转换规则需要自己实现。[Tiptap 持久化文档](https://tiptap.dev/docs/editor/core-concepts/persistence)

`RichDocumentV1`：`schema_version:1`、`type:"doc"`、`content:Block[]`。这是接口正文对象；数据库外部 schema_version 必须与内部一致。

| 节点类型 | 字段 | 支持的排版 |
|---|---|---|
| paragraph | type、content:Inline[]、attrs.align:left/center/right | 正文段落 |
| heading | type、attrs.level:2/3、content:Inline[] | 小标题；文章主标题独立存 title |
| blockquote | type、content:Paragraph[] | 引用 |
| bulletList / orderedList | type、content:ListItem[] | 无序/有序列表；禁止无限嵌套 |
| listItem | type、content:Paragraph[] | 列表项 |
| image | type、attrs.asset_id、attrs.alt、attrs.caption? | 图片节点，不含外部 src |
| horizontalRule | type | 分隔线 |
| text（Inline） | type、text、marks?:Mark[] | 行内文本 |
| hardBreak（Inline） | type | 段内换行 |

`Mark` 是行内样式结构：bold、italic、strike，或 link（attrs.href 仅 http/https，<=2048 字符）。段落、标题的行内节点不能嵌入图片或块节点；image 作为独立块。允许明文无图片笔记；标题发布时 1..100 字符；正文文本最多 20,000 字符，至少有非空文字或1张图片；节点总数<=2,000、树深<=6、请求正文<=512KB、图片<=20、标签<=5、活动/地点引用<=10。Editor 文章也使用同一格式，后续长专题可另调限额。

下面是**接口数据示例，不是仓库实现代码**。`asset_id` 位置在真实请求中填写上传流程返回的媒体 UUID；为保持示例最小，这里仅展示正文和链接，无媒体变量。paragraph 是正文段，text 是其中的文字。

```json
{
  "schema_version": 1,
  "type": "doc",
  "content": [
    {"type":"heading","attrs":{"level":2},"content":[{"type":"text","text":"看完演出，沿着街区散步"}]},
    {"type":"paragraph","attrs":{"align":"left"},"content":[
      {"type":"text","text":"先确认当天的"},
      {"type":"text","text":"开放信息","marks":[{"type":"link","attrs":{"href":"https://example.com/venue"}}]}
    ]}
  ]
}
```

此例的重点是正文保存结构化节点，原生详情渲染器逐节点显示；链接只是可点击引用，服务器不会因保存正文而自动访问该 URL。`example.com` 为示意地址，不是活动资料来源。

### 草稿并发与发布事务

客户端发 PATCH 时携带读取到的 edit_version。后端执行带版本条件的更新并将版本加一；另一台设备提交旧版本收到 409。前端保留本地副本，提示选择远端或保存本地副本为新草稿，不进行无声的“最后写入覆盖”。

publish 服务锁草稿与内容行，校验作者、expected_edit_version、正文、图片和引用，创建 revision、关系行、pending review 和 job，最后提交事务。唯一键 `(content_id,based_on_edit_version)` 保证同一版本重试不会生成两篇帖子；提交成功不等于已经公开。重新编辑并提交会得到新的 revision_no。

## 6. Discover 与行为上报

| 方法与路径 | 请求 | 响应 |
|---|---|---|
| GET `/discover/editorials` | city_id、limit、cursor? | FeedPage<EditorialCard> |
| GET `/discover/notes` | city_id、limit、cursor? | FeedPage<NoteCard> |
| POST `/behavior/events` | BehaviorBatch | accepted_count、duplicate_count、rejected[] |

`FeedPage`：items、next_cursor、feed_snapshot_id、context_token、expires_at。`BaseCard`：id、kind、revision_id、title、excerpt、cover:MediaRead|null、author、tags、first_published_at、viewer_reaction。`EditorialCard` 增加 layout=hero/feature/compact、kicker、linked_entity_summaries；`NoteCard` 包含 image_count、preview_text，不用客户端解析整个正文来计算卡片。

首屏服务器筛选当前城市、公开状态、屏蔽关系和内容类型，再计算最多 200 条有序编号，存 Redis 15 分钟快照。活动排序优先编辑权重和时效；Notes 首版按新鲜度与有限标签匹配排序，同作者连续露出设上限。权重先用可解释配置，不宣称已具备机器学习推荐能力。

分页 cursor 是签名后的快照编号与偏移，绑定用户、城市、Tab 和排序版本；不能只传可篡改 offset。下一页读同一排序，过滤已不可见项后继续向后补足；到200条需显式刷新开启新快照。快照过期或 Redis 丢失返回 410 FEED_EXPIRED，前端保留当前位置提示刷新，不假装无缝延续另一份排序。

context_token 证明某些编号来自服务器给当前用户的 Feed，但不证明用户确实看过。当前视口最多传10条，API验证所属快照与最新可见性。返回媒体/正文之前再次检查隐藏与屏蔽，快照不能覆盖实时权限。

`BehaviorBatch`：events 最多50项；每项 client_event_id、type、occurred_at、content_id?、agent_session_id?、agent_result_id?、feed_snapshot_id?、dwell_ms?、metadata（仅 screen、entry_point、direction_id 等白名单）。时间允许客户端时钟有限偏移，但聚合窗口以 received_at 为准；超限/无权目标逐项拒绝。重复上报通过唯一键去重。

## 7. Agent 请求与界面响应

| 方法与路径 | 请求 | 返回 |
|---|---|---|
| POST `/agent/sessions` | AgentOpen | 201 AgentSessionRead，含恰好3个方向 |
| GET `/agent/sessions/{id}` | 无 | 当前状态、最近输出、active_turn_id |
| POST `/agent/sessions/{id}/turns` | AgentTurnCreate | 202 TurnRead，或幂等重放原 turn |
| GET `/agent/sessions/{id}/turns/{turn_id}` | 无 | TurnRead；轮询直到终态 |
| GET `/agent/results/{id}` | 无 | RecommendationArticleRead；仅本人 |
| PUT/DELETE `/agent/results/{id}/saved` | 无 | 保存/取消保存，仅本人 |
| GET `/me/agent-results` | saved_only、cursor | 本人结果摘要 |
| DELETE `/agent/sessions/{id}` | 无 | 202；停止新生成并异步清理 |

`AgentOpen`：client_session_id:uuid（映射唯一键，用于请求重试）、city_id、surface=editorials|notes、feed_snapshot_id?、context_token?、visible_content_ids（<=10）。无有效 Feed 上下文时也可创建，使用城市+显式兴趣冷启动方向；无权编号丢弃而非进入提示词。服务端从数据库补齐历史，不接收客户端声称的“已收藏/已参加”列表。

`AgentSessionRead`：id、mode、stage、state_version、output:AgentOutput、active_turn_id|null、expires_at。首个 directions 输出由后端规则评分生成，无需等待大模型；可同时利用当前视口、城市和真实用户偏好。一次会话的 direction_id 与输出版本绑定，不能在用户正点击时被后台静默替换。

`AgentTurnCreate`：client_turn_id:uuid、expected_state_version:int、input:TurnInput。input 由 type 区分：

| type | 必填内容 | 含义 |
|---|---|---|
| choose_direction | direction_id | 选择本会话已经提供的方向 |
| answer | question_id、option_ids:string[] | 回答上轮给出的选项，不接受任意选项编号 |
| text | text（1..4000 字符） | 任意阶段转自由输入；进入 chat 模式 |
| retry | failed_turn_id | 用失败输入再次尝试，不重新创建会话 |

每会话仅一个 turn 可 queued/running；此时第二个不同输入返回 409 TURN_IN_PROGRESS。用户仍可切换到输入框编辑文字，但发送按钮等待当前轮完成；首版不实现生成中抢占。相同 client_turn_id 返回已有结果，不重复计费。更新 state_version 与创建 turn/job 在同一事务完成，worker 完成前再次校验 session 未删除且 active_turn_id 一致。

`AgentOutput` 是由 type 决定字段的联合结构，前端不能解析自然语言来判断显示按钮还是文章：

| type | 字段与约束 |
|---|---|
| directions | items:Direction[3]；每项 id、label<=30、description<=80、intent_key、prefilled_slots |
| clarification | question_id、prompt、fields:QuestionField[1..3]、round:1/2；每字段 key、label、options[{id,label,value}]、allow_multiple |
| article | result_id、preview:{title,dek}、assumptions；全文从 result 接口获取 |
| message | text、citations:SourceRef[]、suggested_actions[]；用于普通问答 |
| no_matches | explanation、relax_options[]；不能编造不存在的候选 |
| failure | code、message、retryable、failed_turn_id |

`TurnRead`：id、session_id、status、progress=queued/retrieving/writing/validating/done、output|null、error|null、updated_at。轮询间隔1秒逐步退避到3秒，切后台停止轮询，重进先读取当前状态；超过30秒进入明确失败或后台恢复状态，不无限动画。队列等待和供应商执行分别记录耗时。

`AgentSlots`：time_window:{start,end,timezone}|null；budget:{max_total_per_person_fen,currency}|null；district_ids:uuid[]；companions=solo/couple/friends/family/unspecified；interest_tag_ids:uuid[]；每个字段附 origin=explicit/profile/inferred/default 与 confidence:0..1。用户本轮明确文本覆盖旧默认值；模型抽取到不确定时间应追问或在 assumptions 明示，不能默默硬筛选。

`RecommendationArticleRead`：id、title、dek、sections（1..6 个，每节 heading、paragraphs）、items（1..5）、assumptions、warnings、generated_at、valid_until、saved_at|null、freshness=current/stale。items 每项引用 AgentResultItem 的 id、event/place、可选场次、why_for_you、practical_notes、source_refs。SourceRef={source_id,url,title,verified_at|null}；标题、地址、票价等事实由后端按实体渲染，模型只写有证据支撑的叙述，不允许仅凭自由文本生成售票链接。

## 8. Editor 与审核后台

| 方法与路径 | 模型与动作 | 权限 |
|---|---|---|
| POST/PATCH `/admin/places[/{id}]` | PlaceWrite，PATCH含expected_version | editor/admin |
| POST/PATCH `/admin/events[/{id}]` | EventWrite，PATCH含expected_version | editor/admin |
| POST/PATCH `/admin/events/{id}/sessions[/{session_id}]` | EventSessionWrite | editor/admin |
| GET `/admin/catalog` | city、kind、status、cursor；管理列表 | editor/admin |
| POST `/admin/sources` | SourceCreate；URL、excerpt、候选facts | editor/admin |
| POST `/admin/catalog-sources` | CatalogSourceConfirm；source_id、目标、field_name | editor/admin |
| POST `/admin/editorials` | EditorialCreate；city_id | editor/admin |
| GET/PATCH `/admin/editorials/{id}/draft` | DraftRead / DraftPatch | editor/admin；记录编辑人 |
| POST `/admin/editorials/{id}/publish` | PublishRequest；实际为提交人工审核 | editor/admin |
| GET `/admin/reviews` | status、cursor；ReviewRead[] | moderator/admin |
| POST `/admin/reviews/{id}/decision` | ReviewDecision | moderator/admin |
| POST `/admin/contents/{id}/hide` | reason、expected_version | moderator/admin |
| POST `/admin/contents/{id}/restore` | reason、expected_version | moderator/admin；重新校验批准版本 |
| POST `/admin/editorial-runs` | EditorialResearchCreate；Idempotency-Key | editor/admin |
| GET `/admin/editorial-runs/{id}` | EditorialRunRead | editor/admin |
| GET/PATCH `/admin/reports[/{id}]` | ReportRead / ReportResolve | moderator/admin |
| PUT/DELETE `/admin/users/{id}/roles/{role}` | 授予/撤销角色 | admin |
| POST `/admin/users/{id}/suspend` | reason | admin；撤销全部session |

上表方括号是文档中的路径缩写，不是 FastAPI 路径语法；实现为独立的列表/详情、创建/更新接口。

`PlaceWrite`/`EventWrite`/`EventSessionWrite` 对应数据库业务字段，排除 id、created_at、updated_at、verified_at；核验时间由 CatalogSourceConfirm 设置。PATCH 不允许改变会造成跨城市关联失效的 city_id，迁移城市作为独立人工操作。场次变更要使相关缓存与推荐结果到期。

`SourceCreate`：url、title、publisher?、excerpt、facts_json；服务端分配 trust_level=unverified，人工确认时可更新正式事实关联但不修改已保存的来源快照。`CatalogSourceConfirm`：source_id、target:{type:event|place,id}、field_name、confirmed_value、expected_version；事务更新对应资料、确认关联及 verified_at，并留审计。

`ReviewDecision`：decision=approve|reject、reason_code?、note?、expected_review_version。对应数据库 content_reviews.version；拒绝时必须 reason_code。并发审核只有一个成功。Note 自动审核也走同一审核/发布服务，避免两套发布逻辑。

`EditorialResearchCreate`：city_id、brief（1..4000字符）、allowed_source_domains?、target_content_id?。若目标非空，必须是本人或团队可编辑的 editorial，并记录启动时 draft edit_version；生成完成发现草稿已被人改动时，保存建议稿而非覆盖。`EditorialRunRead`：id、status、sources、proposed_facts、suggested_draft、draft_content_id|null、error_code|null。

## 9. 契约验证要求

FastAPI 导出的 OpenAPI、正文 JSON Schema、TypeScript 客户端在持续集成中重新生成并检查差异。正文需要双向 round-trip 样本：编辑器文档 → API 正文 → 编辑器文档，确保链接、中文、列表、图片标题不丢失；原生阅读器覆盖相同样本。

数据库集成验证重点是唯一键、外键、事务与状态，不能只测“mock 返回成功”。至少覆盖发布重试、刷新重放、旧审核迟到、私有图片越权、Agent 并发输入与下架内容过滤。所有网络供应商提供测试适配器，离线契约测试不调用收费模型。
