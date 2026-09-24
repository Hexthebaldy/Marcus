# 接口与数据格式

> 以下是拟实施接口，不是已经运行的服务。第一版没有Agent、聊天、个性化偏好或AI研究接口。

## 1. 这份文档描述什么

手机应用或编辑后台向服务器发送请求时，需要约定传哪些字段，以及服务器返回哪些字段。本文把这一约定称为接口数据格式，也就是Schema。它与数据库表不是同一个东西：例如数据库里有邮箱地址密文，返回用户资料时不会把密文发给客户端。

后端用Pydantic定义这些字段并检查输入。FastAPI导出接口说明，前端据此生成TypeScript类型和调用代码。数据库中的Python数据模型则由SQLAlchemy定义；它负责读写MySQL，不直接作为对外返回值。

## 2. 所有接口共同遵守的规则

| 项目 | 约定与原因 |
|---|---|
| 路径 | 所有产品接口以 `/v1` 开头，下文省略这个共同前缀。 |
| 登录 | 申请login用途验证码和验证登录不要求已有登录。申请delete_account用途验证码必须登录。/auth/refresh通过续期凭证认证，不要求尚未过期的access_token；其他产品接口使用有效访问凭证，服务器从已验证凭证确定用户身份。 |
| 编号 | 对外使用字符串编号，与数据库的36字符编号一致。 |
| 时间 | 返回带时区的时间字符串，例如 `2026-09-24T12:00:00Z`。Z表示UTC，客户端转成上海时间显示。 |
| 未传字段 | 修改请求没有传某个字段，表示不修改它。只有允许为空的字段，才能通过传null清空。 |
| 未知字段 | 后端拒绝未定义的字段，避免客户端误以为某个值已经保存。 |
| 成功状态 | 200表示读取或修改成功，201表示对象已创建，202表示工作已接受但还在处理，204表示成功且没有响应正文。 |
| 失败状态 | 401表示需要登录，403表示没有操作权限，404表示对象不存在或不可见，409表示冲突，422表示字段格式不对。 |
| 列表 | 返回items数组和next_cursor。没有下一页时next_cursor为null，每次最多50条。 |
| 重复请求 | 创建草稿、申请上传和提交发布需要Idempotency-Key请求头。它是客户端为同一次操作生成的编号；重试复用该编号，服务器返回原结果。 |
| 同时编辑 | 保存时携带读到的版本号。服务器发现版本已经变化就返回409，不直接覆盖别人刚保存的内容。 |

错误响应包含error.code、error.message、error.details和request_id。code用于前端判断错误类型，message用于显示，details只返回安全的字段提示，request_id用于定位后台日志。后端不会把内部堆栈、邮箱地址密文或验证码返回给用户。

## 3. 邮箱验证码注册、登录和基础资料

第一版只提供邮箱验证码这一种注册与登录方式，不要求用户设置密码。首次验证成功创建账户，之后验证同一邮箱即可登录；仅申请发送验证码不会创建用户。移动应用与Editor后台共用这一方式，后台操作权限另行检查。

### 接口列表

| 方法 | 路径 | 作用 |
|---|---|---|
| POST | `/auth/challenges` | 创建一次验证码验证记录，并请求发送邮件。 |
| POST | `/auth/verify` | 核对登录验证码。首次登录时创建账户。 |
| POST | `/auth/refresh` | 换取新的访问凭证和续期凭证。 |
| POST | `/auth/logout` | 撤销当前设备的登录。 |
| GET | `/me` | 返回当前用户的基础资料。 |
| PATCH | `/me` | 修改昵称、简介、头像或城市。 |
| DELETE | `/me` | 验证注销验证码后停用账户并启动数据清理。 |

### 获取验证码时发送什么

| 字段 | 数据格式 | 是否必须发送 | 用途 |
|---|---|---|---|
| email | 字符串 | 是 | 用户的邮箱地址，后端校验格式并使用统一的邮箱规范化规则。 |
| purpose | login或delete_account | 是 | 说明这次验证码用于登录还是注销。 |
| terms_version | 字符串 | 登录时必须 | 当前登录页展示的产品协议版本。 |

邮箱规范化规则是：去掉两端空白，将@后的域名转成小写，保留@前的文字，不删除点号或加号后缀。后端用规范化后的同一地址进行查找、发送和核验。

获取注销验证码必须已登录，且规范化后的邮箱地址与当前账户绑定的邮箱一致。返回challenge_id、expires_in_seconds和resend_after_seconds，分别表示验证记录编号、有效时长、多少秒后可以重发。不通过响应区分这个邮箱地址是否注册过。

发送服务先检查邮箱地址的发送间隔，再创建验证记录和邮件任务。初始设置为60秒内不可重发、5分钟内有效、最多5次验证尝试。重复申请生成新验证码，并使该邮箱旧的同用途验证码立即失效。后台发送前也检查该记录仍有效，避免发送已经过期或被替换的验证码。验证码发送完成后清除发送用的密文。供应商返回未知发送结果时不反复盲发，允许用户等待后重新获取。

### 验证登录时发送什么

| 字段 | 数据格式 | 是否必须发送 | 用途 |
|---|---|---|---|
| challenge_id | 编号字符串 | 是 | 对应刚才收到的验证记录。 |
| code | 六位数字字符串 | 是 | 用户输入的验证码，使用字符串保留开头的0。 |
| device_label | 最多100字符的字符串 | 是 | 当前设备的显示名称。 |
| client_type | mobile或editor_web | 是 | 当前是手机应用还是编辑后台。 |

登录接口只接受login用途的验证码。后端在同一事务中消费验证码、创建或找到用户、记录首次email_verified_at、创建登录记录。邮箱地址查找值的唯一限制保证并发首次登录也只生成一个账户。

邮件服务商接受发送请求不等于用户已收件。页面显示已提交发送、目标邮箱的部分隐藏形式、重发倒计时，并提示检查垃圾邮件；具体邮箱地址不写入普通日志。

成功响应包含access_token、expires_in、session_id和user。access_token是短期访问凭证，初始有效期15分钟。手机端还收到refresh_token，用来续期，存放在设备安全存储中。编辑后台的续期凭证写入浏览器受保护Cookie，不交给页面脚本读取；后台变更请求检查来源并防止跨站请求伪造。

访问凭证采用带签名的JSON Web Token，简称JWT。后端验证签名和期限后，还要检查所属登录没有被撤销。凭证只包含用户与登录编号等必要信息，不放邮箱地址。后端不能把“签名有效”直接等同于“账户仍可用”。

### 用户资料响应

| 字段 | 数据格式 | 用途 |
|---|---|---|
| id | 编号字符串 | 用户编号。 |
| display_name | 字符串 | 展示昵称。 |
| bio | 字符串 | 简介。 |
| avatar | 图片信息或null | 已设置的头像。 |
| city | 城市信息或null | 用户选择的城市。 |
| roles | 字符串数组 | 当前用户的后台权限，仅用于界面展示，后端仍独立检查权限。 |

修改资料只允许display_name、bio、avatar_asset_id和city_id。第一版不允许在这个接口修改绑定邮箱，也没有设置密码、密码登录或找回密码接口。没有personalization_enabled字段，也没有兴趣画像接口。注销请求提交challenge_id和code，且验证码用途必须是delete_account；验证成功后立即撤销所有登录，再执行清理任务。

## 4. 城市、地点与活动

| 方法 | 路径 | 作用 |
|---|---|---|
| GET | `/cities` | 返回已开放城市，第一版只有上海。 |
| GET | `/cities/{id}/districts` | 返回该城市下的区域。 |
| GET | `/tags` | 返回允许新内容选择的标签。 |
| GET | `/places/{id}` | 返回公开地点详情。 |
| GET | `/events/{id}` | 返回活动信息，以及已确认的地点；地点尚未确定时返回null。 |
| GET | `/events/{id}/sessions` | 分页返回活动场次。 |
| PUT | `/events/{id}/participation` | 保存当前用户的想去或去过状态。 |
| DELETE | `/events/{id}/participation` | 取消当前用户的参与标记。 |

城市信息包含id、code、name和timezone。区域信息包含id、city_id和name。标签信息包含id、slug、name和category。这些对象的id都是字符串。

地点详情的返回结构如下。除用于修改冲突检查的version外，不返回后台审核备注和上传者的私有信息。

| 字段 | 数据格式 | 用途 |
|---|---|---|
| id | 编号字符串 | 地点编号。 |
| name | 字符串 | 地点名称，在推广卡片与详情显著展示。 |
| city | 城市对象 | 地点所在城市。 |
| district | 区域对象 | 地点所在区域。 |
| address | 字符串 | 完整地址。 |
| coordinates | 包含latitude、longitude的对象或null | 地点坐标，没有可靠坐标时不伪造。 |
| summary | 字符串 | 地点介绍。 |
| opening_hours_text | 字符串 | 可直接阅读的营业时间。 |
| transport_notes | 字符串 | 交通和入口说明。 |
| cover | 图片对象或null | 可选的地点封面。没有封面时返回null。 |
| gallery | 图片对象数组 | 按顺序展示的地点图片，没有照片时返回空数组。 |
| status | active或closed | 告知用户该地点是否仍正常开放。 |
| verified_at | 时间字符串或null | 最近核实资料的时间。 |

活动详情包含id、city、title、description、organizer、place、price、booking_url、status、verified_at和upcoming_sessions。city必须存在；place是一个地点对象或null，不是数组。地点尚未确认时返回null并显示“场地待确认”，不能为此编造地点记录；upcoming_sessions最多返回5场，更多场次另行分页读取。活动取消、结束或地点关闭时仍可显示历史资料，但必须有状态提示。

price对象包含status、min_fen、max_fen、currency。unknown状态时金额为空，免费时明确为0。前端把分换算成元展示，不能把未知价格显示为免费。场次对象包含id、event_id、starts_at、ends_at、entry_note和status。

参与请求包含state、session_id和attended_at。state只能是interested或attended；attended需要填写不晚于当前时间的参与时间；session_id可空，但填写时必须属于这个活动。

## 5. 图片与视频上传

文件保存在对象存储，MySQL的media_assets表保存文件位置、用途、类型、处理状态和尺寸等资料。以下上传接口共用，但Notes只能引用图片，Editor正文可以引用图片和视频。

| 方法 | 路径 | 作用 |
|---|---|---|
| POST | `/media/uploads` | 创建媒体记录并返回临时上传地址。 |
| POST | `/media/{id}/complete` | 核查上传结果并安排文件处理。 |
| GET | `/media/{id}` | 查询状态；获得授权后才返回可读取地址。 |
| DELETE | `/media/{id}` | 删除没有被任何有效内容引用的文件。 |

申请时传kind、purpose、file_name、mime_type、size_bytes。kind为image或video；purpose为note_image、editorial_media、place_image或avatar。只有editorial_media允许video，且需要编辑权限。普通用户只能给Notes使用本人上传的note_image图片；头像只能使用本人avatar图片。具有editor或admin权限的人员可复用团队editorial_media和place_image素材，但不能读取普通用户的私有Note图片；文章封面必须是图片。返回asset_id、upload_url、method、required_headers和expires_at，客户端不能自行指定存储位置。

图片初始支持JPEG、PNG、WebP，单图上限20MB；手机HEIC先转换，后端仍检查实际文件内容。视频初始接受MP4、MOV容器，单文件上限200MB和5分钟，后台探测真实格式后转换成供客户端播放的MP4（H.264视频、AAC音频）。这些数值是第一版工程默认，需经移动网络和设备测试调整，并非已经确定的产品要求。

图片响应包含id、kind、status、width、height、variants、error_code。variants包含thumb、feed、detail等展示文件及宽高。视频另返回duration_ms、playback和poster；playback描述处理后的播放文件，poster描述生成的视频预览图片。视频预览图不是文章封面，也不要求文章设置cover_asset_id。私有地址附带expires_at。

审核人员的读取权限有明确范围：moderator或admin只能通过有权访问的固定note_submission、editorial_review或举报详情响应，取得该次审核或举报涉及媒体的短期读取地址。该例外不允许通过/media/{id}任意浏览其他用户的私有素材和草稿，也不授予媒体转用权限。

status依次可能为pending、processing、ready；不合格文件为rejected，清理后为deleted。上传完成不代表ready。媒体仍在处理或已被拒绝时，不允许把它提交到公开内容；草稿可以保留引用并显示处理进度。

## 6. Notes：简单文字与有序图片

Notes不使用Editor正文格式。手机编辑页只提供可选标题、正文输入、相册选图和图片排序，以及可选地点或活动。正文保留换行；第一版不提供段落样式、正文内插图、视频上传或自由排版。正文中的网址只是文字，不保存可自定义的超链接样式。

| 方法 | 路径 | 作用 |
|---|---|---|
| POST | `/notes` | 传city_id，创建Note及空草稿。 |
| GET | `/notes/{id}` | 只读取当前公开帖子，不返回正在编辑的草稿。 |
| GET | `/notes/{id}/draft` | 作者读取草稿。 |
| PATCH | `/notes/{id}/draft` | 作者保存文字、图片顺序和关联对象。 |
| POST | `/notes/{id}/publish` | 提交指定草稿保存版本。 |
| GET | `/notes/{id}/publication` | 查询最新提交是否通过、是否成为当前公开内容。 |
| DELETE | `/notes/{id}` | 作者传expected_version删除帖子。 |
| GET | `/me/notes` | 分页读取我的公开Notes。 |
| GET | `/me/note-drafts` | 分页读取我的Notes草稿。 |
| GET | `/me/bookmarks` | 返回带content_type的收藏条目，note和editorial各自使用独立卡片结构。 |

保存草稿使用下列字段，后端拒绝document、cover_asset_id和其他未定义字段。

| 字段 | 数据格式 | 规则 |
|---|---|---|
| expected_version | 正整数 | 必须发送，与读取草稿时的edit_version一致。 |
| title | 字符串 | 可不传；可用空字符串清空，最多100字。 |
| body_text | 字符串 | 可不传；保留换行，最多5000字。 |
| image_ids | 编号字符串数组 | 可不传；传入后整体替换图片顺序，最多9张，不允许重复；空数组清空图片。 |
| place_id | 编号字符串或null | 可选地点。 |
| event_id | 编号字符串或null | 可选活动。 |

返回note_id、上述工作字段、edit_version、updated_at及latest_submission。标题、正文、图片数量限制是首版工程默认。标题可空，发布时正文去除空白后必须非空，或者至少有一张就绪图片；只有标题不构成一篇可发布帖子。

place_id和event_id可以均为空。选择活动时无需重复提供地点，已知场地由后端补齐；若同时提供地点，必须与活动已确认的place_id一致。活动场地未知时不能另外为它声明地点。引用对象必须公开且与Note城市一致。保存关联字段时，后端校验修改后整份草稿，不能只检查请求中的单个字段。

提交请求只含expected_edit_version，返回202与note_id、submission_id、review_status、job_id。每次提交复制固定的文字、图片顺序和关联对象到note_submissions，供审核读取；它不是富文本文章版本，也不提供历史版本编辑功能。查询publication返回submission_id、review_status、is_current_published、reason_code。review_status为pending、approved或rejected；审核通过和当前公开是两件事。

公开详情包含id、kind（note）、title、body_text、images、cover、place、event、author、city、first_published_at、published_at、published_submission_id、version和reactions。images按用户顺序返回；cover从第一张图片派生，无图时为null，没有独立封面设置。公开文字直接读取notes，公开图片读取note_images。详情接口必须用单次查询或同一个一致性读取事务取得文字和图片，不能让两个独立查询跨过一次公开更新而拼出不同提交的数据。新提交待审或被拒绝时，不改变这两张表中的公开内容。

## 7. Editor：专业文章、明确重心和独立正文

Editor文章由网页后台创建，手机只负责阅读。它与Notes使用不同的输入格式、保存服务和数据库表，不使用一个content表加kind字段混存。

| 方法 | 路径 | 作用 |
|---|---|---|
| GET | `/editorials/{id}` | 读取当前公开文章。 |
| GET、POST | `/admin/editorials` | 管理列表；传city_id和可选district_id创建文章身份和草稿。 |
| GET、PATCH | `/admin/editorials/{id}/draft` | 读取或保存专用文章草稿。 |
| POST | `/admin/editorials/{id}/publish` | 提交expected_edit_version指定的草稿。 |
| GET | `/admin/editorials/{id}/publication` | 查询最新提交和当前公开版本。 |

### 文章草稿字段

| 字段 | 数据格式 | 规则 |
|---|---|---|
| expected_version | 正整数 | 保存必填，检查草稿是否已被别人修改。 |
| title | 最多150字的字符串 | 提交时必须非空。 |
| subtitle | 最多200字的字符串 | 可选副标题，空字符串表示没有。 |
| summary | 最多500字的字符串 | 编辑可填写的卡片摘要；草稿可空，提交未填写时由后端从正文文字生成不超过500字的摘要。 |
| focus_type | place、event或null | 地点或活动重心；null仅用于未完成草稿。 |
| primary_place_id | 编号字符串或null | 地点重心的唯一主要地点。 |
| primary_event_id | 编号字符串或null | 活动重心的唯一主要活动。 |
| document | 正文对象 | 专用有序内容块，格式见下文。 |
| document_schema_version | 正整数 | 第一版为1，明确正文格式版本。 |
| cover_asset_id | 图片编号或null | 可选封面，无图也能发布。 |
| tag_ids | 编号字符串数组 | 整体替换标签，最多10个，供未来搜索和合集聚合。 |

除expected_version外，未传字段不修改。focus_type、primary_place_id、primary_event_id必须一起发送和整体替换，防止改为地点重心后遗留活动编号。草稿可暂不选择主要对象，但不能同时保留两个主要对象，也不能存下与已选重心矛盾的编号。保存返回所有草稿字段、article_id、edit_version、last_edited_by、updated_at、published_revision_id、latest_submission。

提交时有且只有一种关系成立：focus_type为place时primary_place_id必填、primary_event_id必须null；focus_type为event时primary_event_id必填、primary_place_id必须null。活动文章的场地从events.place_id读取，若场地未知则公开响应place为null。餐厅、公园文章无需创建虚构活动。一篇仍只选择一个主要对象，不支持在关联字段中保存多活动合集。

主要对象必须公开且与文章city_id一致；已知活动场地也必须属于同一城市、可公开读取且处于active状态。新提交使用的地点需active，活动需published。草稿与版本保存重心，editor_articles主记录不保存重心；所以修改选择不改变旧公开文章。

editor_articles另保存district_id，表示文章所属区。创建时若选择了区，后端检查它属于city_id指定的城市。地点文章公开时使用主要地点的区，活动文章使用已确认举办地的区；提交时由后端根据本次主要对象核定，不直接沿用创建时或旧公开版本的区。没有已确认举办地的活动，所属区可以为null。公开版本切换时同步更新区，草稿修改不提前改变公开列表归类。

提交返回202与article_id、revision_id、review_status、job_id。后端写入editor_revisions、editor_revision_tags、editor_revision_assets和editor_reviews。查询publication返回revision_id、review_status、is_current_published、reason_code。

### 正文格式与排版

正文是一个type为doc、content为有序块数组的JSON对象。数组顺序就是阅读顺序；编辑人员可以把图片或视频放到两个指定段落之间，而不是只能放在顶部相册。格式版本由外层document_schema_version指定。

| 块或文字类型 | 保存内容 | 展示行为 |
|---|---|---|
| paragraph | content、attrs.align | 普通段落；align为left、center或right。 |
| heading | content、attrs.level | 二级或三级小标题；主标题独立保存。 |
| blockquote | 段落数组 | 引用文字。 |
| bulletList、orderedList | listItem数组 | 项目列表或编号列表；每项只包含段落。 |
| image | attrs内的asset_id、alt、caption、credit、width | 在指定位置展示图片、替代说明、图注及图片署名。 |
| video | attrs内的asset_id、caption、credit、width | 在指定位置展示原生播放器和说明，不接受外部iframe。 |
| gallery | attrs内的items、layout、width | items是有序图片对象数组，每项含asset_id、alt、caption、credit；layout只允许single或two_column，分别为单列和桌面两列；手机均按相同顺序堆叠。 |
| callout | attrs内的tone，以及块级content | content只包含paragraph对象；tone只允许info或warning，用固定样式突出提示。 |
| divider | type | 一条分隔线。 |
| text | text、marks | 文字及bold、italic、strike、link样式。 |
| hardBreak | type | 段落内换行。 |

图片、视频及图片组的width只能为content、wide、full，分别表示正文宽度、较宽和占满可用阅读区。手机根据屏幕宽度调整，不允许任意像素坐标、绝对定位或自由CSS。文章署名先使用作者资料。link包含attrs.href，只允许http或https，href最多2048字符；保存时不会自动访问链接。引用块和提示块只包含paragraph，列表项也只包含paragraph，不允许列表、提示或引用块相互无限嵌套。

后端限制正文最多20,000字、2,000节点、6层结构、512KB JSON；每篇最多20张不同图片及5段视频。这些是待实测的工程默认。正文必须包含非空文字，所有媒体引用必须有使用权限且ready。后台Tiptap编辑器通过明确转换规则输出该格式；后端不接收任意HTML、脚本、iframe或未经支持的编辑器节点。

下面是**接口数据示例，不是仓库实现代码**。它只表达“普通段落后插入一段视频”；asset_id使用一个示意UUID；实际请求必须替换成上传接口返回、已处理成功且有使用权限的真实媒体编号。

```json
{
  "document_schema_version": 1,
  "document": {
    "type": "doc",
    "content": [
      {"type": "paragraph", "content": [{"type": "text", "text": "这段演出片段展示本次作品的舞台设计。"}]},
      {"type": "video", "attrs": {"asset_id": "123e4567-e89b-42d3-a456-426614174000", "caption": "演出片段", "credit": "主办方提供", "width": "content"}}
    ]
  }
}
```

阅读页按content数组顺序显示段落和视频。文件本身不在这个JSON里，后端另返回授权媒体资料，手机受限块渲染器用原生播放器播放视频。

### 公开文章响应

| 字段 | 数据格式 | 用途 |
|---|---|---|
| id、revision_id | 编号字符串 | 文章身份及当前公开版本。 |
| kind | 固定为editorial | 前端选择文章阅读布局。 |
| title、subtitle、summary | 字符串 | 标题、副标题及摘要。 |
| focus_type | place或event | 决定主要信息卡和页面展示重心。 |
| document、document_schema_version | 正文对象及整数 | 经校验的专业正文。 |
| media | 媒体对象数组 | 当前正文引用的图片和视频展示资料。 |
| cover | 图片对象或null | 文章可选封面。 |
| place | 地点对象或null | 地点重心的主要对象，或活动重心的已知场地。 |
| event | 活动摘要或null | 地点重心为空；活动重心必须存在。 |
| tags | 标签对象数组 | 当前公开版本标签。 |
| editor、city | 作者摘要及城市对象 | 文章署名和所属城市。 |
| district | 区域对象或null | 文章所属区，包含id、city_id、name；活动所在区尚未确认时为空。 |
| first_published_at、published_at | 时间字符串 | 首次公开及当前版本公开时间。 |
| reactions | 数量和本人状态对象 | 点赞、收藏。 |

## 8. Discover、互动与举报

| 方法 | 路径 | 作用 |
|---|---|---|
| GET | `/discover/editorials` | 当前城市已公开Editor文章。 |
| GET | `/discover/notes` | 当前城市已公开简单帖子。 |
| PUT、DELETE | `/notes/{id}/reactions/{kind}` | 添加或取消Note的like、bookmark。 |
| PUT、DELETE | `/editorials/{id}/reactions/{kind}` | 添加或取消文章的like、bookmark。 |
| POST | `/notes/{id}/reports` | 举报当前公开的Note提交，传submission_id、reason和description。 |
| POST | `/editorials/{id}/reports` | 举报文章版本，传revision_id、reason和description。 |
| PUT、DELETE | `/users/{id}/block` | 添加或取消用户屏蔽。 |

两个列表均接收city_id、limit、cursor。Editor卡片返回title、summary、cover、focus_type、tags以及主要对象摘要；活动重心突出活动名称、日期与票价，地点重心突出地点名称、区域与到访信息。第一Tab暂保留“活动”这个既定名称；是否改成“精选”留待产品确定，不在本轮自动改导航。

Editor公开列表和后台文章列表另外接受可选district_id，并在文章卡片中返回district。后端检查筛选的区属于请求城市；不传district_id表示查看全市，传入时只返回明确归属于该区的文章。所属区为空的文章不混入指定区结果。分页cursor绑定城市和区，切换筛选条件后必须从第一页重新查询。

Notes卡片返回title、body_text的摘要、author、cover及reactions，cover取第一张公开图片。所有无图内容都使用文字卡片，封面为null时不返回虚构尺寸，详情不渲染空的图片区域。

Editor按editorial_rank降序、first_published_at降序及id稳定排序；Notes按first_published_at降序及id排序。cursor包含带签名的上一页排序值，不能代替权限检查。Editor排名变化可能产生少量重复或跳过，客户端按编号去重并支持下拉刷新。编辑内容不重置首次发布时间。

点赞收藏分别写入note_reactions和editor_article_reactions；举报分别写入note_reports和editor_article_reports，不使用无法声明真实外键的通用content_id。举报版本必须属于目标对象且当前可见。用户屏蔽写入user_blocks，活动参与记录继续使用event_participations，不因为文章重心改变而迁移到文章表。

## 9. 管理与审核

editor负责地点、活动、标签和文章草稿，moderator负责审核与下架，admin负责权限。后端每次独立检查权限，不相信前端按钮是否可见。

| 方法 | 路径 | 作用 |
|---|---|---|
| GET、POST | `/admin/places` | 地点列表和创建。 |
| GET、PATCH | `/admin/places/{id}` | 查看或修改；保存传expected_version。 |
| PUT | `/admin/places/{id}/images` | 传asset_ids及expected_version替换图片顺序。 |
| GET、POST | `/admin/events` | 活动列表和创建；city_id必填，place_id可空。 |
| GET、PATCH | `/admin/events/{id}` | 查看或修改；保存传expected_version。 |
| POST | `/admin/events/{id}/sessions` | 添加场次。 |
| PATCH | `/admin/events/{id}/sessions/{session_id}` | 修改场次并检查expected_version。 |
| GET、POST | `/admin/tags` | 查询或创建标签。 |
| PATCH | `/admin/tags/{id}` | 修改名称、类别或停用。 |
| GET | `/admin/note-submissions` | 待审Note提交列表。 |
| GET | `/admin/note-submissions/{id}` | 查看固定文字、图片顺序及关联对象。 |
| POST | `/admin/note-submissions/{id}/decision` | 审核指定提交。 |
| GET | `/admin/editorial-reviews` | 待审文章列表。 |
| GET | `/admin/editorial-reviews/{id}` | 查看确切文章版本及排版、媒体、标签。 |
| POST | `/admin/editorial-reviews/{id}/decision` | 审核指定文章版本。 |
| POST | `/admin/notes/{id}/hide`、`/admin/editorials/{id}/hide` | 填reason和expected_version下架。 |
| POST | `/admin/notes/{id}/restore`、`/admin/editorials/{id}/restore` | 重新检查已批准内容后恢复。 |
| GET | `/admin/note-reports`、`/admin/editorial-reports` | 分别读取举报。 |
| GET | `/admin/note-reports/{id}`、`/admin/editorial-reports/{id}` | 读取有权处理的具体举报及相关提交，返回该上下文允许查看的媒体短期地址。 |
| PATCH | `/admin/note-reports/{id}`、`/admin/editorial-reports/{id}` | 填status和resolution_note处理举报。 |
| PUT、DELETE | `/admin/users/{id}/roles/{role}` | 授予或撤销权限。 |
| POST | `/admin/users/{id}/suspend` | 填reason停用账户并撤销登录。 |

管理输入仅开放业务字段，不允许直接写id、created_at、updated_at或任意数据库列。confirm_verified为true时由后端记录当前verified_at。地点公开要求名称、区域、地址，照片可空；活动公开要求必要活动资料和city_id，场地未知可空，已知场地必须公开且城市一致。活动场地变更需重新核对资料，并提示复核引用文章，不能静默修改跨城市关系。

审核请求包含decision、expected_review_version、reason_code、note。decision为approve或reject，拒绝必须填写reason_code。Note检查note_submissions.review_version；文章检查editor_reviews的审核版本。迟到审核只能更新旧提交自己的处理结果，不能覆盖较新的提交。正文仍以审核时固定副本为准，不读正在修改的草稿。

## 10. 验证与错误边界

保存草稿冲突返回409且客户端保留本地内容；重试发布必须复用Idempotency-Key；提交成功只表示进入审核。删除、下架和停用作者后，迟到审核不能重新公开内容。

邮箱验证码测试保留：发送不注册、首次验证才注册、同邮箱并发只创建一账户、规范化一致、旧码失效、过期与尝试上限、拒绝手机号和密码字段。数据库并发测试使用MySQL。

Notes独立验证纯文字、纯图片、标题可空、9图顺序、拒绝富文本document、拒绝视频、待审期间旧公开内容不变。Editor独立验证无活动的地点文章、突出活动且场地待定的文章、整组切换重心、正文图片视频位置、链接、图注署名、桌面双图与手机顺序一致。未经支持的节点与不合格媒体必须拒绝。

两类发布分别验证重复提交、旧审核、同时审核、无图发布、私有媒体越权、公开关系与城市检查。Editor草稿标签不能影响公开标签；视频处理失败必须阻止引用它的文章提交。以上是后续实现的验收要求，不表示本轮已经执行应用测试。
