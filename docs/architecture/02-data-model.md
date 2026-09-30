# 数据库表与字段说明

> 本文记录MySQL 8.4的数据设计。对应实现位于 `apps/backend/src/marcus/models/`，初始迁移位于 `apps/backend/migrations/versions`；已经在独立 MySQL 环境运行迁移与测试。所有业务数据放在名为 `marcus` 的数据库中。第一版包含邮箱登录、可选地点或活动重心的Editor专业文章、简单Notes和必要后台管理，不包含Agent。

## 1. 先理解两种不同的内容

Editor文章是编辑部制作的专业文章。编辑可以选择介绍一个地点，也可以选择介绍一项活动。例如，餐厅文章围绕餐厅本身展开，不需要虚构一个“去餐厅活动”；演出文章围绕演出、演员、场次和票价展开，场馆只是辅助信息。

因此，Editor文章保存“本篇以什么为重心”以及一个主要对象。以地点为重心时，只填写主要地点；以活动为重心时，只填写主要活动，举办地从活动资料中读取。活动不再是每篇文章必须具备的数据。当前仍以每篇一个主要对象为范围，合集留待以后设计。

Notes是普通用户的简单图文帖子，保存文字、可选标题和有序图片。Notes没有专业正文排版结构，也不用Editor文章的版本和媒体块模型。两个模块分别建表、分别定义接口，不能用一张contents表加一个类型字段代替这次拆分。

共享的只有用户、地点、活动、文件存储和标签基础设施。Editor文章可以选标签，便于以后按主题整理合集；Notes第一版不要求维护编辑部标签。地点、文章和Notes都可以没有封面或照片。

## 2. 怎样阅读下面的字段表

每张数据库表都可以理解成一张有固定列的表格。表中的一行代表一个对象，例如一个用户或一个地点。下文的每一行字段说明，解释的都是这张表中的一列。

**记录编号。** `id` 是一条记录的编号。后端创建记录时生成一个不重复的编号，保存为36个字符的字符串，例如 `7ce0d692-0f0c-49c5-bf26-119cde97d5bd`。数据库类型写作 `CHAR(36)`。用来唯一识别一行的字段称为主键。某些对应关系表用两个或三个字段一起识别一行，会在该表后面明确说明。

**一张表如何指向另一张表。** 例如，活动表中的 `place_id` 保存某个地点的 `id`。数据库可以检查这个地点是否真实存在，这种检查叫外键。每张表后面会用完整句子写出它关联哪张表，不使用箭头替代解释。

**是否可以为空。** “是”表示目前可以没有这个信息。例如用户尚未设置头像时，头像编号为空，数据库中称为 `NULL`。“否”表示必须有值。数字0表示确实为零，不表示未知；空字符串表示有一个字符串但没有文字，也不同于没有值。

**文本与数字。** `VARCHAR(100)` 表示最多100个字符的文本，`TEXT` 表示较长文字，`INT` 表示整数。`BOOLEAN` 表示是或否；在 MySQL 中用0和1保存，并限制只能使用这两个值。`JSON` 表示有字段和层次的结构化数据，本方案主要用它保存富文本正文，不用它替代地点编号和标签关系。

**创建和修改时间。** `created_at` 记录后端第一次保存这行的时间；`updated_at` 记录最后修改时间。它们在每张需要的表中明确列出。只追加、以后不改正文的记录不会有修改时间。

**时间如何保存。** 时间字段使用 `DATETIME(6)`，括号中的6表示可以保留到微秒。这个 MySQL 类型不会替我们保存时区，所以后端统一转换为协调世界时，也就是 UTC，再写入数据库。手机展示时再转换为上海时间。例如，上海晚上20点对应同一天UTC中午12点。城市表保存 `Asia/Shanghai`，让后端知道展示和解析时间时用哪个时区。[MySQL 时间类型说明](https://dev.mysql.com/doc/refman/8.4/en/datetime.html)

**金额如何保存。** 费用用整数保存“分”。例如8800表示88元。免费明确写0；价格未知则为空，并把价格状态写为 unknown。这样不会把未知价格显示成免费。

**如何防止重复和加快查询。** 唯一限制会拒绝重复记录，例如同一个用户不能给同一篇内容收藏两次。索引是数据库为了加快特定查询而维护的查找结构，例如给邮箱地址查找值建立索引能加快登录。下面分别解释哪些字段不能重复、哪些查询需要索引。

**如何一起保存多个改动。** 某些操作需要修改多张表，例如提交笔记时同时保存正文版本和审核记录。后端会要求这些改动全部成功后才生效，任何一步失败就全部取消，这称为数据库事务。涉及两个人同时修改时，后端还会暂时锁住相关记录，让这些修改按顺序完成。

MySQL 表使用 InnoDB，以支持上述事务和外键检查。文字采用 `utf8mb4` 字符集，以保存中文和表情。编号、验证码查找值等需要精确比较的列使用 ASCII 字符集和区分大小写的比较规则；用户文本使用 `utf8mb4_0900_ai_ci`。数据库支持对字段值设置检查规则，例如结束时间必须晚于开始时间。[MySQL 建表说明](https://dev.mysql.com/doc/refman/8.4/en/create-table.html)

## 3. 用户与登录
### users：用户账户

用户首次正确输入邮箱验证码后，后端才在这里创建一条记录；仅请求发送邮件不会创建账户。登录、显示作者信息和检查账户是否可用，都要读取这张表。

| 字段名 | MySQL 中保存的数据类型 | 是否可以为空 | 具体用途 |
|---|---|---|---|
| id | CHAR(36) | 否 | 用户编号，是本表的主键。 |
| email_lookup_hash | CHAR(64) | 是 | 后端根据邮箱地址和服务器密钥计算的固定查找值，用于识别同一邮箱地址；注销后清空。 |
| email_ciphertext | TEXT | 是 | 经过加密的邮箱地址。发送邮件时后端可以解密，数据库中不保存可直接阅读的邮箱地址。 |
| email_verified_at | DATETIME(6) | 是 | 首次成功验证该邮箱的时间，正常账户必须填写，注销后清空。 |
| display_name | VARCHAR(40) | 否 | 页面展示的昵称，注册时后端可以生成默认昵称。 |
| bio | VARCHAR(300) | 否 | 个人简介，未填写时保存空字符串。 |
| avatar_asset_id | CHAR(36) | 是 | 头像图片的编号，未设置头像时为空。 |
| city_id | CHAR(36) | 是 | 用户选择的城市编号，首发只开放上海。 |
| status | VARCHAR(20) | 否 | active表示正常，suspended表示被停用，deleted表示已经注销。 |
| terms_version | VARCHAR(40) | 否 | 注册时同意的产品协议版本。 |
| terms_accepted_at | DATETIME(6) | 否 | 同意协议的时间。 |
| deleted_at | DATETIME(6) | 是 | 注销账户的时间，未注销时为空。 |
| created_at | DATETIME(6) | 否 | 后端创建这条记录的时间。 |
| updated_at | DATETIME(6) | 否 | 后端最后修改这条记录的时间。 |

email_lookup_hash 不能重复。只有已经注销的账户才允许两个邮箱字段和email_verified_at为空，而且三个字段必须一起清空。正常或停用账户必须保留这三项信息。avatar_asset_id 关联 media_assets 的 id，city_id 关联 cities 的 id。创建表时先允许头像为空，等媒体表建立后再添加头像的外键检查。

邮箱保存前会去掉两端空白，将@后面的域名转成小写，保留@前面的文字大小写。后端不删除地址中的点号或加号后面的内容，避免把不同地址错误地合并。邮箱查找值的计算、发送目标和验证码核对全部使用同一个规范化结果。第一版不支持修改绑定邮箱，后续需要单独设计验证流程。

本表不保存密码。注册和后续登录都通过邮箱验证码完成。

本表不包含 personalization_enabled。这个字段原本用于决定能否拿用户历史行为做个性化推荐；第一版没有这种功能，所以不保留没有使用方的开关。

### user_roles：用户的后台权限

普通用户无需在这里添加记录。某个用户需要编辑内容、审核或管理账户时，管理员才给他添加对应权限。一个人可以拥有多种权限。

| 字段名 | MySQL 中保存的数据类型 | 是否可以为空 | 具体用途 |
|---|---|---|---|
| user_id | CHAR(36) | 否 | 获得权限的用户编号。 |
| role | VARCHAR(20) | 否 | editor表示编辑，moderator表示审核人员，admin表示管理员。 |
| granted_by | CHAR(36) | 是 | 给这个用户授权的管理员编号。第一次用部署命令创建管理员时可以为空。 |
| created_at | DATETIME(6) | 否 | 后端创建这条记录的时间。 |
| updated_at | DATETIME(6) | 否 | 后端最后修改这条记录的时间。 |

user_id 和 role 两个字段一起识别一条授权记录，这一组合不能重复。user_id 和 granted_by 都关联 users 的 id。后端收到后台请求时读取这些记录，不接受客户端自行声明的权限。第一次管理员初始化以外的授权必须填写 granted_by。

### auth_send_limits：同一邮箱地址的验证码发送限制

这张表帮助后端把同一邮箱地址的验证码发送按顺序处理。即使两个请求同时到达，也不能同时绕过重发间隔。

| 字段名 | MySQL 中保存的数据类型 | 是否可以为空 | 具体用途 |
|---|---|---|---|
| email_lookup_hash | CHAR(64) | 否 | 邮箱地址的固定查找值，与用户表使用相同的计算方法。 |
| purpose | VARCHAR(30) | 否 | login表示登录，delete_account表示确认注销账户。 |
| next_allowed_at | DATETIME(6) | 否 | 这个邮箱地址和用途下一次可以发送验证码的时间。 |
| created_at | DATETIME(6) | 否 | 后端创建这条记录的时间。 |
| updated_at | DATETIME(6) | 否 | 后端最后修改这条记录的时间。 |

email_lookup_hash 和 purpose 共同作为主键。发送服务先创建或找到这行，再在事务中锁住它，检查时间并更新 next_allowed_at。新验证码记录和这次限制更新一起保存。Redis 额外限制IP和设备频率，但不是唯一的重发间隔保护。

### auth_challenges：一次验证码验证记录

用户点击“获取验证码”后，后端创建一条记录，保存这次验证码何时失效、已经输错几次以及是否被用过。这里的 challenge 只是一次验证记录的名字。

| 字段名 | MySQL 中保存的数据类型 | 是否可以为空 | 具体用途 |
|---|---|---|---|
| id | CHAR(36) | 否 | 本次验证记录的编号，客户端提交验证码时一起发送。 |
| email_lookup_hash | CHAR(64) | 否 | 本次接收验证码的邮箱地址查找值。 |
| email_ciphertext | TEXT | 否 | 加密后的接收邮箱地址，仅发送服务解密使用。 |
| purpose | VARCHAR(30) | 否 | login表示登录，delete_account表示确认注销。 |
| code_hmac | CHAR(64) | 否 | 后端用密钥计算出的验证码校验值，不能直接读出验证码。 |
| delivery_code_ciphertext | TEXT | 是 | 暂存用于发送邮件的加密验证码，发送成功后清空。 |
| expires_at | DATETIME(6) | 否 | 验证码失效时间，初始设置为创建后5分钟。 |
| attempts | SMALLINT UNSIGNED | 否 | 已经尝试验证的次数，初始为0。 |
| max_attempts | SMALLINT UNSIGNED | 否 | 允许的最多尝试次数，初始为5。 |
| consumed_at | DATETIME(6) | 是 | 验证码成功使用的时间，未使用时为空。 |
| delivery_status | VARCHAR(20) | 否 | pending表示待发送，sent表示邮件服务商已接受发送请求，不代表收件箱已经收到；failed表示已确认发送失败。 |
| terms_version | VARCHAR(40) | 是 | 登录注册时使用的协议版本；注销验证不需要填写。 |
| created_at | DATETIME(6) | 否 | 后端创建这条记录的时间。 |
| updated_at | DATETIME(6) | 否 | 后端最后修改这条记录的时间。 |

id 是主键。为 email_lookup_hash、purpose、created_at 建立组合索引，以查找同一邮箱地址最近的验证记录。新验证记录创建时让旧的同用途验证码失效。邮箱规范化规则与users表一致；邮箱地址使用同一个结果生成查找值和发送邮件。校验时锁住这一行，检查用途、期限、次数与 consumed_at；成功后设置 consumed_at。输错时也要保存 attempts 的增加，不能因返回错误而把计数回滚。

code_hmac 中的 HMAC 全称是 Hash-based Message Authentication Code，是一种使用服务器密钥计算校验值的方法。这里它将邮箱地址、验证码和本次记录编号一起参与计算，避免数据库泄漏后仅靠枚举六位数字找回验证码。

### auth_sessions：一台设备的登录状态

每次用户成功登录，后端记录这次登录属于谁、在哪类客户端发生以及何时失效。退出登录时，后端撤销对应记录。

| 字段名 | MySQL 中保存的数据类型 | 是否可以为空 | 具体用途 |
|---|---|---|---|
| id | CHAR(36) | 否 | 本次登录的编号。 |
| user_id | CHAR(36) | 否 | 登录用户的编号。 |
| client_type | VARCHAR(20) | 否 | mobile表示手机应用，editor_web表示编辑后台网页。 |
| device_label | VARCHAR(100) | 否 | 便于识别设备的名称，不作为权限证明。 |
| last_seen_at | DATETIME(6) | 否 | 这次登录最近一次被使用的时间。 |
| absolute_expires_at | DATETIME(6) | 否 | 最迟何时要求重新登录，初始为登录后30天。 |
| revoked_at | DATETIME(6) | 是 | 主动退出或被管理员撤销的时间。 |
| created_at | DATETIME(6) | 否 | 后端创建这条记录的时间。 |
| updated_at | DATETIME(6) | 否 | 后端最后修改这条记录的时间。 |

id 是主键，user_id 关联 users 的 id。为 user_id、revoked_at 建立组合索引。后端处理需要登录的请求时检查这条记录没有过期或撤销，并检查用户状态正常。

### refresh_tokens：用于延长登录的凭证

手机的短期访问凭证过期后，可以用续期凭证换取新凭证，避免频繁要求用户输入验证码。每次续期都会换一份新的续期凭证。

| 字段名 | MySQL 中保存的数据类型 | 是否可以为空 | 具体用途 |
|---|---|---|---|
| id | CHAR(36) | 否 | 这份续期凭证的记录编号。 |
| session_id | CHAR(36) | 否 | 它属于哪次登录。 |
| token_hash | CHAR(64) | 否 | 随机续期凭证的摘要，用于查找；不保存原始凭证。 |
| parent_id | CHAR(36) | 是 | 本凭证由哪份旧凭证续期得到；首次登录时为空。 |
| expires_at | DATETIME(6) | 否 | 本凭证何时过期，不得晚于所属登录的最迟失效时间。 |
| used_at | DATETIME(6) | 是 | 已被用于续期的时间。 |
| revoked_at | DATETIME(6) | 是 | 被撤销的时间。 |
| created_at | DATETIME(6) | 否 | 后端创建这条记录的时间。 |
| updated_at | DATETIME(6) | 否 | 后端最后修改这条记录的时间。 |

id 是主键，token_hash 不重复，parent_id 的非空值也不重复，所以一个旧凭证只能生成一个新凭证。session_id 关联 auth_sessions 的 id，parent_id 关联本表 id。后端锁定旧记录后标记已使用，再插入新记录。再次使用旧凭证会撤销这次登录。客户端只允许一个续期请求同时发送；若成功响应丢失，首版要求重新登录。

## 4. 地点、活动与标签

### cities：开放的城市

移动端展示可选城市，后端也使用它判断哪些城市已有运营内容。首发只启用上海。

| 字段名 | MySQL 中保存的数据类型 | 是否可以为空 | 具体用途 |
|---|---|---|---|
| id | CHAR(36) | 否 | 城市编号。 |
| code | VARCHAR(32) | 否 | 稳定的内部名称，上海使用shanghai。 |
| name | VARCHAR(80) | 否 | 展示名称，例如上海。 |
| country_code | CHAR(2) | 否 | 国家代码，中国使用CN。 |
| timezone | VARCHAR(64) | 否 | 该城市使用的时区，上海为Asia/Shanghai。 |
| enabled | BOOLEAN | 否 | 是否已向用户开放。 |
| created_at | DATETIME(6) | 否 | 后端创建这条记录的时间。 |
| updated_at | DATETIME(6) | 否 | 后端最后修改这条记录的时间。 |

id 是主键，code 不重复。后端初始化上海记录；以后开放其他城市时增加记录，不修改原有编号。

### districts：城市下的区域

地点需要显示属于哪个区，因此将区域保存在单独的表中，避免编辑每次自由输入。

| 字段名 | MySQL 中保存的数据类型 | 是否可以为空 | 具体用途 |
|---|---|---|---|
| id | CHAR(36) | 否 | 区域编号。 |
| city_id | CHAR(36) | 否 | 所属城市的编号。 |
| code | VARCHAR(32) | 否 | 该城市内稳定的区域代码。 |
| name | VARCHAR(80) | 否 | 区域名称，例如静安区。 |
| created_at | DATETIME(6) | 否 | 后端创建这条记录的时间。 |
| updated_at | DATETIME(6) | 否 | 后端最后修改这条记录的时间。 |

id 是主键，city_id 关联 cities 的 id。同一 city_id 下 code 不重复。另为 id、city_id 两列建立唯一限制，供地点表同时检查区域与城市是否匹配。

### places：地点资料

团队维护地点名称、可选照片、区域、地址和到访说明。餐厅、公园等地点可以独立存在，不需要创建活动记录；以活动为重心的文章只把地点作为举办地资料。

| 字段名 | MySQL 中保存的数据类型 | 是否可以为空 | 具体用途 |
|---|---|---|---|
| id | CHAR(36) | 否 | 地点编号。 |
| city_id | CHAR(36) | 否 | 地点所在城市。 |
| district_id | CHAR(36) | 否 | 地点所在区域。 |
| name | VARCHAR(200) | 否 | 地点展示名称，例如某家书店或展览空间。 |
| address | VARCHAR(500) | 否 | 完整地址，发布前必须填写。 |
| latitude | DECIMAL(9,6) | 是 | 纬度，没有可靠坐标时为空。 |
| longitude | DECIMAL(9,6) | 是 | 经度，与纬度一起填写或一起留空。 |
| summary | VARCHAR(500) | 否 | 地点简短介绍，未完成时可暂存空字符串。 |
| opening_hours_text | VARCHAR(1000) | 否 | 供人阅读的营业时间说明，例如周二至周日10点到18点。 |
| transport_notes | VARCHAR(1000) | 否 | 交通、入口或停车说明，未填写时为空字符串。 |
| cover_asset_id | CHAR(36) | 是 | 地点封面图片编号。草稿和公开状态都可以为空，不要求地点有照片。 |
| source_url | VARCHAR(2048) | 是 | 编辑核对地点信息时使用的来源链接。 |
| verified_at | DATETIME(6) | 是 | 编辑最近确认地点资料的时间。 |
| status | VARCHAR(20) | 否 | draft表示未公开，active表示可公开展示，closed表示已关闭。 |
| version | INT UNSIGNED | 否 | 每次修改加1，用来发现两个人同时修改的冲突。 |
| created_at | DATETIME(6) | 否 | 后端创建这条记录的时间。 |
| updated_at | DATETIME(6) | 否 | 后端最后修改这条记录的时间。 |

id 是主键。另为id、city_id建立唯一限制，供活动检查地点城市。city_id 关联 cities，cover_asset_id 关联 media_assets。district_id、city_id 两个值一起关联 districts 的 id、city_id，防止城市和区域不匹配。经纬度限制在合法范围内。为 city_id、district_id、status 建立组合索引。地点已有活动引用后，不直接修改城市归属；变更须由后台专门处理。

### place_assets：地点的展示图片

地点可以有多张环境照片，也可以没有照片。本表记录每张图片属于哪个地点，以及在详情中按什么顺序展示；没有照片的地点无需在本表添加记录。

| 字段名 | MySQL 中保存的数据类型 | 是否可以为空 | 具体用途 |
|---|---|---|---|
| place_id | CHAR(36) | 否 | 地点编号。 |
| asset_id | CHAR(36) | 否 | 已经上传并通过检查的图片编号。 |
| position | INT UNSIGNED | 否 | 显示顺序，从0开始。 |
| created_at | DATETIME(6) | 否 | 后端创建这条记录的时间。 |

place_id 和 asset_id 共同作为主键，分别关联 places 和 media_assets。place_id 和 position 的组合也不重复，避免两个图片占用同一展示位置。

### events：独立的活动资料

活动保存演出、展览等确实存在的活动信息。活动本身可以是Editor文章的主要对象；餐厅、公园不需要为了发文章而创建一条活动。活动所在城市必须明确，场地尚未公布时地点可以暂时为空。

| 字段名 | MySQL 中保存的数据类型 | 是否可以为空 | 具体用途 |
|---|---|---|---|
| id | CHAR(36) | 否 | 活动编号。 |
| city_id | CHAR(36) | 否 | 活动所在城市，不依赖是否已经确定场地。 |
| place_id | CHAR(36) | 是 | 一个举办地点的编号，尚未公布时为空，不能为了填满字段虚构地点。 |
| title | VARCHAR(200) | 否 | 活动名称。 |
| description | TEXT | 否 | 活动事实介绍，不代替推广正文。 |
| organizer | VARCHAR(200) | 是 | 主办方名称。 |
| booking_url | VARCHAR(2048) | 是 | 报名或购票链接，没有时为空。 |
| price_status | VARCHAR(20) | 否 | free表示免费，known表示费用已知，unknown表示费用未知。 |
| price_min_fen | INT UNSIGNED | 是 | 最低每人费用，单位为分。 |
| price_max_fen | INT UNSIGNED | 是 | 最高每人费用，单位为分。 |
| currency | CHAR(3) | 否 | 人民币写CNY。 |
| source_url | VARCHAR(2048) | 是 | 编辑核对活动事实的来源链接。 |
| verified_at | DATETIME(6) | 是 | 编辑最近确认活动信息的时间。 |
| status | VARCHAR(20) | 否 | draft表示未公开，published表示公开，cancelled表示取消，ended表示结束。 |
| version | INT UNSIGNED | 否 | 每次修改加1，避免覆盖其他编辑的修改。 |
| created_at | DATETIME(6) | 否 | 后端创建这条记录的时间。 |
| updated_at | DATETIME(6) | 否 | 后端最后修改这条记录的时间。 |

id是主键，city_id关联cities。place_id、city_id一起关联places的id、city_id，填写地点时数据库检查城市一致。为city_id、status建立索引，为place_id、status建立另一索引。后台可以更正活动举办地，更新version并记录审计；文章地点信息读取最新活动资料，不另外保存一份可能过期的主地点。一个活动首版最多一个举办地，跨场地活动的建模以后另行设计。

free时两个金额都必须为0；known时两个金额都必须填写，且最低值不大于最高值；unknown时两个金额都为空。这些条件在数据库和后端同时检查。费用只是公开资料，不承诺实时票务库存。

### event_sessions：活动的日期和场次

一个活动可以在多个日期举办。每个可以单独说明的时间段保存一行，方便详情页展示。

| 字段名 | MySQL 中保存的数据类型 | 是否可以为空 | 具体用途 |
|---|---|---|---|
| id | CHAR(36) | 否 | 场次编号。 |
| event_id | CHAR(36) | 否 | 所属活动编号。 |
| starts_at | DATETIME(6) | 否 | 开始时间，保存前转换为UTC。 |
| ends_at | DATETIME(6) | 否 | 结束时间，必须晚于开始时间。 |
| entry_note | VARCHAR(500) | 否 | 入场说明，例如19点开始或闭馆前半小时停止入场。 |
| status | VARCHAR(20) | 否 | scheduled表示正常，cancelled表示取消，sold_out表示已知售罄。 |
| version | INT UNSIGNED | 否 | 修改版本号。 |
| created_at | DATETIME(6) | 否 | 后端创建这条记录的时间。 |
| updated_at | DATETIME(6) | 否 | 后端最后修改这条记录的时间。 |

id 是主键，event_id 关联 events。同一个活动的相同开始、结束时间不能重复。另为 id、event_id 建立唯一限制，供参与记录检查场次归属。为 event_id、status、starts_at 建立组合索引。没有确定日期时不创建伪造场次，在活动页面明确显示时间待确认。

### tags：可以给内容使用的标签

团队先维护统一标签，Editor再给专业文章选择这些标签。后续搜索和合集按标签编号查找内容，不依赖正文中恰好出现某个词。

| 字段名 | MySQL 中保存的数据类型 | 是否可以为空 | 具体用途 |
|---|---|---|---|
| id | CHAR(36) | 否 | 标签编号。 |
| slug | VARCHAR(64) | 否 | 稳定的内部标识，例如exhibition。 |
| name | VARCHAR(40) | 否 | 展示名称，例如展览。 |
| category | VARCHAR(30) | 否 | activity_type表示活动类型，theme表示主题，audience表示适合人群。 |
| enabled | BOOLEAN | 否 | 是否允许继续给新内容选择此标签。 |
| created_at | DATETIME(6) | 否 | 后端创建这条记录的时间。 |
| updated_at | DATETIME(6) | 否 | 后端最后修改这条记录的时间。 |

id 是主键，slug 不重复。编辑修改标签显示名称时不改变编号。已经被使用的标签优先停用，不直接删除；历史内容可以继续显示停用标签。

## 5. 共用的媒体文件

### media_assets：图片或视频文件

文件保存在对象存储服务，MySQL保存它属于谁、是什么媒体、是否处理完成以及文件位置。Notes与Editor可以共用上传设施，但这不表示它们共用正文模型。

| 字段名 | MySQL 中保存的数据类型 | 是否可以为空 | 具体用途 |
|---|---|---|---|
| id | CHAR(36) | 否 | 媒体编号。 |
| owner_id | CHAR(36) | 否 | 上传者的用户编号。 |
| kind | VARCHAR(20) | 否 | image表示图片，video表示视频。 |
| purpose | VARCHAR(30) | 否 | note_image表示笔记图片，editorial_media表示文章图片或视频，place_image表示地点照片，avatar表示头像。 |
| storage_key | VARCHAR(255) | 否 | 原始文件位置，由后端生成。 |
| verified_mime | VARCHAR(80) | 是 | 后端检查得到的真实文件格式。 |
| size_bytes | BIGINT UNSIGNED | 是 | 原文件大小，单位字节。 |
| width | INT UNSIGNED | 是 | 图片或视频画面宽度。 |
| height | INT UNSIGNED | 是 | 图片或视频画面高度。 |
| duration_ms | BIGINT UNSIGNED | 是 | 视频时长，单位毫秒；图片始终为空。 |
| status | VARCHAR(20) | 否 | pending表示待上传，processing表示处理中，ready表示可用，rejected表示拒绝，deleted表示删除。 |
| visibility | VARCHAR(20) | 否 | private表示只有授权后可访问，public表示被公开资料引用。 |
| variants | JSON | 否 | 图片各尺寸文件，或视频播放文件和预览图的位置及必要参数。 |
| rejection_code | VARCHAR(80) | 是 | 无法使用的原因，例如视频格式无法解码。 |
| upload_expires_at | DATETIME(6) | 否 | 上传许可的失效时间。 |
| deleted_at | DATETIME(6) | 是 | 文件被删除的时间。 |
| created_at | DATETIME(6) | 否 | 后端创建这条记录的时间。 |
| updated_at | DATETIME(6) | 否 | 后端最后修改这条记录的时间。 |

id是主键，storage_key不重复，owner_id关联users。为owner_id、status、created_at建立索引。数据库要求video只能用于editorial_media；note_image、place_image和avatar只能是image。只有ready媒体才能用于正式提交；有图但无权使用仍会被拒绝。

普通用户的Note只能使用本人上传的note_image。具备editor或admin权限的团队成员可以复用editorial_media和place_image团队素材，但这项权限不允许读取普通用户的私有Note图片。封面和地点照片只能使用图片；头像只能使用本人上传的avatar。后端在上传、保存引用、提交和返回访问地址时分别检查这些规则。

审核是另一种有明确范围的读取权限。moderator或admin打开有权处理的固定提交或举报时，后端仅给该提交或举报所引用的媒体签发短期读取地址，用于检查内容。这不允许他们枚举其他用户的私人素材或未提交草稿，也不授予把这些文件用于Editor文章的权限。后台检查任务同样只读取任务目标实际引用的媒体，不因知道一个文件编号就获得任意读取权。

图片variants保存thumb、feed、detail文件信息。视频variants保存playback的文件位置、格式、编解码信息和poster预览图位置；文件访问时生成地址，不把过期签名URL永久保存。视频ready必须有有效时长、可播放文件和生成的poster。poster是播放器预览，不要求Editor给文章选择cover_asset_id，也不自动把它设置成文章封面。

## 6. Editor专业文章

编辑文章有独立的工作草稿和提交版本。每个提交版本保留当时的正文块顺序、媒体位置、主题选择与标签。段落之间的图片、视频和链接属于文章正文，不属于一个放在文末的附件列表。

### editor_articles：编辑文章的固定身份

无论正文修改多少次，文章保留同一个编号。此表记录作者、所属城市与区、展示顺序和当前公开版本，不存Notes。

| 字段名 | MySQL 中保存的数据类型 | 是否可以为空 | 具体用途 |
|---|---|---|---|
| id | CHAR(36) | 否 | 文章编号。 |
| author_id | CHAR(36) | 否 | 负责文章的Editor用户编号。 |
| city_id | CHAR(36) | 否 | 文章所属城市。 |
| district_id | CHAR(36) | 是 | 文章所属区，关联districts。例如上海市静安区。活动所在区尚未确认时可以为空，不能随意指定。 |
| status | VARCHAR(20) | 否 | draft表示未公开，published表示公开，hidden表示下架，deleted表示删除。 |
| published_revision_id | CHAR(36) | 是 | 当前公开的文章版本，尚未公开时为空。 |
| first_published_at | DATETIME(6) | 是 | 文章首次公开时间。 |
| published_at | DATETIME(6) | 是 | 当前文章版本公开时间。 |
| editorial_rank | INT | 否 | 编辑人工排列文章时使用的数值，默认0。 |
| version | INT UNSIGNED | 否 | 文章状态修改版本号，初始1。 |
| deleted_at | DATETIME(6) | 是 | 文章删除时间。 |
| created_at | DATETIME(6) | 否 | 后端创建这条记录的时间。 |
| updated_at | DATETIME(6) | 否 | 后端最后修改这条记录的时间。 |

id是主键，author_id关联users，city_id关联cities。published_revision_id和本行id一起关联editor_revisions的id、article_id，保证公开版本属于该文章。建表时先允许公开版本为空，版本表创建后再加这个外键。published状态必须有公开版本和发布时间。为city_id、status、editorial_rank、first_published_at、id建立列表索引；为author_id、created_at建立管理查询索引。作者创建文章时必须有editor或admin权限。

district_id和city_id一起关联districts的id、city_id，确保选择的区属于文章城市。另为city_id、district_id、status、editorial_rank、first_published_at、id建立按区筛选的索引。地点主题的区取自主要地点；活动主题的区取自已确认举办地，没有已确认举办地时可以暂为空。创建时可先选择区；提交时由后端根据本次主要对象核定实际所属区，正式公开时再与公开版本一起更新。旧公开文章的区不作为新稿更换主要对象的限制，草稿更换主要对象也不会提前改变公开文章的区。

地点或活动举办地资料变更后，后端按当前公开文章关联的主要对象重新核对并同步所属区，不能从尚未公开的草稿读取区域。区尚未确定的文章仍可出现在城市列表，但不会被归入某个指定区的筛选结果。

### editor_drafts：编辑人员的文章工作稿

工作稿支持副标题、导语、分节、图文视频穿插和版式选择。修改主题和排版只影响工作稿，不改变当前公开文章。

| 字段名 | MySQL 中保存的数据类型 | 是否可以为空 | 具体用途 |
|---|---|---|---|
| article_id | CHAR(36) | 否 | 所属文章编号，也是本表主键。 |
| title | VARCHAR(150) | 否 | 主标题，草稿未完成时可为空字符串。 |
| subtitle | VARCHAR(200) | 否 | 副标题，可为空字符串。 |
| summary | VARCHAR(500) | 否 | 文章导语或摘要，可为空字符串。 |
| focus_type | VARCHAR(20) | 是 | place表示围绕地点，event表示围绕活动，草稿开始时可暂不选择。 |
| primary_place_id | CHAR(36) | 是 | 选择地点重心时的主要地点。 |
| primary_event_id | CHAR(36) | 是 | 选择活动重心时的主要活动。 |
| document | JSON | 否 | 专业正文结构，保存内容块的顺序和每块排版设置。 |
| document_schema_version | SMALLINT UNSIGNED | 否 | 正文格式版本，初始1。 |
| cover_asset_id | CHAR(36) | 是 | 可选文章封面，只能是图片，没有封面也可公开。 |
| tag_ids | JSON | 否 | 正在选择的标签编号数组，最多10个。 |
| edit_version | INT UNSIGNED | 否 | 每次保存工作稿加1。 |
| last_edited_by | CHAR(36) | 否 | 最近保存工作稿的编辑人员编号。 |
| created_at | DATETIME(6) | 否 | 后端创建这条记录的时间。 |
| updated_at | DATETIME(6) | 否 | 后端最后修改这条记录的时间。 |

article_id关联editor_articles；primary_place_id关联places，primary_event_id关联events，cover_asset_id关联media_assets，last_edited_by关联users。草稿可暂不选择主要对象，但不能同时保留两个主要对象。focus_type为空时两种编号都为空；place时primary_event_id必须为空；event时primary_place_id必须为空。

切换重心时客户端发送完整的focus_type、primary_place_id、primary_event_id三字段，后端一次更新并清除旧选择。提交时要求选定类型对应的唯一主要对象存在、城市一致且允许公开。tag_ids只是未提交的工作数据，正式标签在提交时写入editor_revision_tags。

### editor_revisions：文章的一次完整提交

编辑提交发布时，将工作稿复制到此表。正文与选择的主要对象都固定下来；之后再修改会产生新版本。

| 字段名 | MySQL 中保存的数据类型 | 是否可以为空 | 具体用途 |
|---|---|---|---|
| id | CHAR(36) | 否 | 文章提交版本编号。 |
| article_id | CHAR(36) | 否 | 所属文章编号。 |
| revision_no | INT UNSIGNED | 否 | 本文章第几次提交，从1开始。 |
| based_on_edit_version | INT UNSIGNED | 否 | 来自哪次草稿保存。 |
| title | VARCHAR(150) | 否 | 非空主标题。 |
| subtitle | VARCHAR(200) | 否 | 副标题，没有则为空字符串。 |
| summary | VARCHAR(500) | 否 | 导语或摘要；编辑未填时由后端从正文派生摘要。 |
| focus_type | VARCHAR(20) | 否 | 只允许place或event。 |
| primary_place_id | CHAR(36) | 是 | 地点主题的主要地点，活动主题时为空。 |
| primary_event_id | CHAR(36) | 是 | 活动主题的主要活动，地点主题时为空。 |
| document | JSON | 否 | 有序正文及排版数据，格式见接口文档。 |
| document_schema_version | SMALLINT UNSIGNED | 否 | 正文格式版本。 |
| plain_text | MEDIUMTEXT | 否 | 后端从正文提取的文字，不包含HTML脚本。 |
| cover_asset_id | CHAR(36) | 是 | 可选文章封面图片编号。 |
| submitted_by | CHAR(36) | 否 | 提交发布的编辑编号。 |
| created_at | DATETIME(6) | 否 | 后端创建这条记录的时间。 |

id是主键；article_id与revision_no组合不重复，article_id与based_on_edit_version组合不重复，id与article_id组合也设置唯一限制。article_id关联editor_articles，两个主要对象字段各自关联places和events；封面关联media_assets，submitted_by关联users。

数据库明确检查：place类型必须填primary_place_id且primary_event_id为空；event类型必须填primary_event_id且primary_place_id为空。保存草稿可不完整，保存这里时不允许缺主要对象。提交与实际公开前由服务核对城市和对象状态。事件已知的场馆从events.place_id读取，不在文章中再存一份主地点。

### editor_revision_tags：文章版本的标签

文章有几个标签，就为这个提交版本保存几条对应记录。公开标签始终取当前公开版本，供后续搜索或合集查找。

| 字段名 | MySQL 中保存的数据类型 | 是否可以为空 | 具体用途 |
|---|---|---|---|
| revision_id | CHAR(36) | 否 | 文章版本编号。 |
| tag_id | CHAR(36) | 否 | 标签编号。 |
| created_at | DATETIME(6) | 否 | 后端创建这条记录的时间。 |

revision_id和tag_id共同作为主键，分别关联editor_revisions和tags。为tag_id、revision_id建立反向查询索引。后续按标签查文章时还要检查editor_articles.published_revision_id，不能把旧版本标签算作当前标签。

### editor_revision_assets：文章版本使用的媒体

这张表用于核对文件是否仍被文章使用。媒体实际插在正文哪个位置、有没有图注、宽度如何设置，都由document里的对应内容块表达。

| 字段名 | MySQL 中保存的数据类型 | 是否可以为空 | 具体用途 |
|---|---|---|---|
| revision_id | CHAR(36) | 否 | 文章版本编号。 |
| asset_id | CHAR(36) | 否 | 图片或视频编号。 |
| role | VARCHAR(20) | 否 | cover表示文章封面，inline表示正文媒体。 |
| created_at | DATETIME(6) | 否 | 后端创建这条记录的时间。 |

revision_id、asset_id、role共同作为主键，分别关联editor_revisions和media_assets。cover只允许image。后台从已经校验的正文提取完整媒体集合，连同cover生成此表；同一媒体出现多次只记一个同role引用，正文保留每次出现的位置和说明。

### editor_reviews：文章版本的审核结果

Editor专业文章必须经过人工确认后公开。审核处理的是固定提交版本，不直接修改工作稿。

| 字段名 | MySQL 中保存的数据类型 | 是否可以为空 | 具体用途 |
|---|---|---|---|
| id | CHAR(36) | 否 | 审核记录编号。 |
| revision_id | CHAR(36) | 否 | 文章提交版本编号。 |
| status | VARCHAR(20) | 否 | pending表示待审，approved表示通过，rejected表示拒绝。 |
| reviewer_id | CHAR(36) | 是 | 完成审核的人员，终态时必须填写。 |
| reason_code | VARCHAR(80) | 是 | 拒绝原因，拒绝时必填。 |
| reviewer_note | TEXT | 是 | 人工补充意见。 |
| automated_findings | JSON | 否 | 媒体或文字检查的结果摘要，初始为空对象。 |
| reviewed_at | DATETIME(6) | 是 | 审核完成时间。 |
| version | INT UNSIGNED | 否 | 审核记录的修改版本。 |
| created_at | DATETIME(6) | 否 | 后端创建这条记录的时间。 |
| updated_at | DATETIME(6) | 否 | 后端最后修改这条记录的时间。 |

id是主键，revision_id不重复并关联editor_revisions，reviewer_id关联users。为status、created_at建立待审查询索引。通过审核不代表必然成为当前版本：发布服务还要确认文章未被删除或下架，而且本提交仍为最新提交。

## 7. 用户Notes简单帖子

Notes只有普通文字和有序图片。为保留编辑中的草稿、避免未经审核的改动立刻公开，下面保留一个工作副本和一次提交的固定字段；它们不接受专业正文document，不提供编辑部排版或历史版本管理界面。

### notes：当前公开的帖子

这里直接保存读者看到的普通文字和可选标题。新创建的帖子先是draft状态；首次审核通过时才把已提交文字复制到这里并改成published。

| 字段名 | MySQL 中保存的数据类型 | 是否可以为空 | 具体用途 |
|---|---|---|---|
| id | CHAR(36) | 否 | 帖子编号。 |
| author_id | CHAR(36) | 否 | 作者编号，来自登录身份。 |
| city_id | CHAR(36) | 否 | 帖子所属城市。 |
| title | VARCHAR(100) | 否 | 可选标题，未填写时为空字符串。 |
| body_text | TEXT | 否 | 普通正文，保留换行，第一版最多5000字。 |
| place_id | CHAR(36) | 是 | 可选的关联地点。 |
| event_id | CHAR(36) | 是 | 可选的关联活动，不是发帖必填项。 |
| status | VARCHAR(20) | 否 | draft表示未公开，published表示公开，hidden表示下架，deleted表示删除。 |
| published_submission_id | CHAR(36) | 是 | 产生当前公开文字和图片的提交编号，用于审核追查。 |
| first_published_at | DATETIME(6) | 是 | 首次公开时间。 |
| published_at | DATETIME(6) | 是 | 最近一次替换公开文字或图片的时间。 |
| version | INT UNSIGNED | 否 | 帖子的状态版本，初始1。 |
| deleted_at | DATETIME(6) | 是 | 删除时间。 |
| created_at | DATETIME(6) | 否 | 后端创建这条记录的时间。 |
| updated_at | DATETIME(6) | 否 | 后端最后修改这条记录的时间。 |

id是主键，author_id关联users，city_id关联cities，place_id和event_id分别关联对应资料表。published_submission_id和id一起关联note_submissions的id、note_id，该循环外键在两表创建后添加。published状态必须有公开提交编号和发布时间。公开文字与note_images在一个事务内从已批准提交复制；后端不允许其他接口直接修改公开字段。

为city_id、status、first_published_at、id建立列表索引，为author_id、created_at建立个人帖子索引。图片并不在body_text中插入，列表封面取note_images第一张；没有图片时封面返回null，不额外要求cover_asset_id。

### note_images：公开帖子的有序图片

用户按顺序选择照片，读者看到图片轮播或图片组。本表没有图文交错的位置、视频节点或排版参数。

| 字段名 | MySQL 中保存的数据类型 | 是否可以为空 | 具体用途 |
|---|---|---|---|
| note_id | CHAR(36) | 否 | 帖子编号。 |
| asset_id | CHAR(36) | 否 | 一张图片编号。 |
| position | INT UNSIGNED | 否 | 图片顺序，0表示第一张。 |
| created_at | DATETIME(6) | 否 | 后端创建这条记录的时间。 |

note_id和asset_id共同作为主键，分别关联notes和media_assets。note_id和position组合不能重复。发布服务检查0到8的连续顺序和最多9张图片，检查kind=image且purpose=note_image并属于作者；空数组对应没有记录。

### note_drafts：尚未提交的简单图文

手机原生文字输入框和图片选择器直接读写这些固定字段，不需要运行网页富文本编辑器。

| 字段名 | MySQL 中保存的数据类型 | 是否可以为空 | 具体用途 |
|---|---|---|---|
| note_id | CHAR(36) | 否 | 所属帖子编号，也是主键。 |
| title | VARCHAR(100) | 否 | 可选标题，未填写时为空字符串。 |
| body_text | TEXT | 否 | 普通文字和换行，最多5000字。 |
| image_ids | JSON | 否 | 按选择顺序保存0至9个图片编号，不能保存视频或外部图片地址。 |
| place_id | CHAR(36) | 是 | 可选地点。 |
| event_id | CHAR(36) | 是 | 可选活动。 |
| edit_version | INT UNSIGNED | 否 | 每次保存加1。 |
| created_at | DATETIME(6) | 否 | 后端创建这条记录的时间。 |
| updated_at | DATETIME(6) | 否 | 后端最后修改这条记录的时间。 |

note_id关联notes，place_id和event_id各自关联资料表。后端根据所属notes.author_id检查权限。image_ids在草稿里保存工作列表，保存时检查图片存在且本人有权使用，提交时再检查ready状态。编辑时可暂时没有文字也没有图片，提交时必须有非空正文或至少一张图片。第一版只填标题不算有效帖子。

### note_submissions：用于审核的一次帖子提交

保存点击发布时的标题、文字和图片清单，以免审核期间又被草稿编辑改掉。它只服务审核、重复请求处理和举报追查，没有专业文章document，也不为用户提供历史版本编辑功能。

| 字段名 | MySQL 中保存的数据类型 | 是否可以为空 | 具体用途 |
|---|---|---|---|
| id | CHAR(36) | 否 | 本次提交编号。 |
| note_id | CHAR(36) | 否 | 所属帖子编号。 |
| submission_no | INT UNSIGNED | 否 | 该帖子的第几次提交，从1开始。 |
| based_on_edit_version | INT UNSIGNED | 否 | 来自哪次草稿保存。 |
| title | VARCHAR(100) | 否 | 提交时的可选标题。 |
| body_text | TEXT | 否 | 提交时的普通文字。 |
| image_ids | JSON | 否 | 提交时按顺序排列的图片编号，0到9张。 |
| place_id | CHAR(36) | 是 | 提交时选择的地点。 |
| event_id | CHAR(36) | 是 | 提交时选择的活动。 |
| status | VARCHAR(20) | 否 | pending表示待审，approved表示通过，rejected表示拒绝。 |
| reviewer_id | CHAR(36) | 是 | 人工审核者编号，自动检查通过时可为空。 |
| reason_code | VARCHAR(80) | 是 | 拒绝原因，拒绝时必填。 |
| reviewer_note | TEXT | 是 | 人工审核意见。 |
| automated_findings | JSON | 否 | 自动检查结果，初始为空对象。 |
| reviewed_at | DATETIME(6) | 是 | 完成审核的时间，终态必填。 |
| review_version | INT UNSIGNED | 否 | 审核状态的修改版本，初始1。 |
| created_at | DATETIME(6) | 否 | 后端创建这条记录的时间。 |
| updated_at | DATETIME(6) | 否 | 后端最后修改这条记录的时间。 |

id是主键，note_id关联notes；id、note_id组合设置唯一限制，note_id、submission_no和note_id、based_on_edit_version分别设置唯一限制。place_id、event_id分别关联资料表，reviewer_id关联users。为status、created_at建立待审索引。提交的文字和图片清单不再改写，只有审核相关字段可修改。

image_ids是有严格长度与编号格式的JSON数组，数据库外键不能逐项检查它。提交服务验证每张图并与媒体删除服务采用一致的行锁顺序，保留任务也检查所有未清理的提交清单，防止待审核图片提前删除。审核通过时重新核验图片，从该清单重建note_images并复制文字到notes，所有写入在一个事务完成。若需要更复杂的媒体查询，再增加提交图片关系表，不让Notes继承Editor版本结构。

## 8. 分开的互动和举报

两种内容不再共用一张内容主表，互动和举报也使用各自真正的外键。权限检查、请求去重等辅助代码可以复用，但不能把note_id当作文章id写入另一种表。

### note_reactions：点赞和收藏

记录用户对这一类内容的点赞或收藏，取消时删除对应记录。

| 字段名 | MySQL 中保存的数据类型 | 是否可以为空 | 具体用途 |
|---|---|---|---|
| user_id | CHAR(36) | 否 | 操作用户编号。 |
| note_id | CHAR(36) | 否 | 被操作的帖子编号。 |
| kind | VARCHAR(20) | 否 | like表示点赞，bookmark表示收藏。 |
| created_at | DATETIME(6) | 否 | 后端创建这条记录的时间。 |

user_id、note_id、kind共同作为主键；user_id关联users，note_id关联notes。为user_id、kind、created_at建立我的收藏索引，为note_id、kind建立计数索引。重复操作不插入第二行。

### editor_article_reactions：点赞和收藏

记录用户对这一类内容的点赞或收藏，取消时删除对应记录。

| 字段名 | MySQL 中保存的数据类型 | 是否可以为空 | 具体用途 |
|---|---|---|---|
| user_id | CHAR(36) | 否 | 操作用户编号。 |
| article_id | CHAR(36) | 否 | 被操作的文章编号。 |
| kind | VARCHAR(20) | 否 | like表示点赞，bookmark表示收藏。 |
| created_at | DATETIME(6) | 否 | 后端创建这条记录的时间。 |

user_id、article_id、kind共同作为主键；user_id关联users，article_id关联editor_articles。为user_id、kind、created_at建立我的收藏索引，为article_id、kind建立计数索引。重复操作不插入第二行。

### event_participations：用户标记的想去或去过

用户主动标记是否想参加活动，或是否已经去过。去过是用户自己的记录，不表示平台验证过购票或到场。

| 字段名 | MySQL 中保存的数据类型 | 是否可以为空 | 具体用途 |
|---|---|---|---|
| id | CHAR(36) | 否 | 参与记录编号。 |
| user_id | CHAR(36) | 否 | 用户编号。 |
| event_id | CHAR(36) | 否 | 活动编号。 |
| session_id | CHAR(36) | 是 | 用户选择的具体场次，未选择时为空。 |
| state | VARCHAR(20) | 否 | interested表示想去，attended表示去过。 |
| attended_at | DATETIME(6) | 是 | 用户记录的参与时间，去过时必须填写。 |
| created_at | DATETIME(6) | 否 | 后端创建这条记录的时间。 |
| updated_at | DATETIME(6) | 否 | 后端最后修改这条记录的时间。 |

id是主键，user_id与event_id的组合不能重复。user_id关联users，event_id关联events。session_id、event_id一起关联event_sessions的id、event_id，防止选择另一个活动的场次。后端检查attended_at不能晚于现在；想去状态下将它清空。

### user_blocks：用户屏蔽其他用户

用户屏蔽某位作者后，后端在列表和详情中排除该作者的内容。

| 字段名 | MySQL 中保存的数据类型 | 是否可以为空 | 具体用途 |
|---|---|---|---|
| user_id | CHAR(36) | 否 | 执行屏蔽的人。 |
| blocked_user_id | CHAR(36) | 否 | 被屏蔽的人。 |
| created_at | DATETIME(6) | 否 | 后端创建这条记录的时间。 |

两个字段共同作为主键，都关联users。两者不能相同。取消屏蔽时删除记录。该关系不作为公开资料返回。

### note_reports：举报记录

记录用户看到的具体公开内容及对应提交，以便修改之后仍能复核当时的问题。

| 字段名 | MySQL 中保存的数据类型 | 是否可以为空 | 具体用途 |
|---|---|---|---|
| id | CHAR(36) | 否 | 举报编号。 |
| reporter_id | CHAR(36) | 否 | 举报用户编号。 |
| note_id | CHAR(36) | 否 | 被举报的内容编号。 |
| submission_id | CHAR(36) | 否 | 被举报内容对应的具体提交编号。 |
| reason | VARCHAR(30) | 否 | spam表示垃圾内容，abuse表示攻击，inaccurate表示信息错误，other表示其他。 |
| description | VARCHAR(1000) | 否 | 补充说明，可为空字符串。 |
| status | VARCHAR(20) | 否 | open表示待处理，resolved表示已处理，dismissed表示未采纳。 |
| resolved_by | CHAR(36) | 是 | 处理人员编号。 |
| resolution_note | TEXT | 是 | 处理说明。 |
| created_at | DATETIME(6) | 否 | 后端创建这条记录的时间。 |
| updated_at | DATETIME(6) | 否 | 后端最后修改这条记录的时间。 |

id是主键，reporter_id和resolved_by关联users，note_id关联notes。submission_id、note_id一起关联note_submissions的id、note_id，保证举报指向同一篇内容的提交。服务确认用户看过的目标是当前可见公开提交，而非内部草稿。为status、created_at建立处理队列索引。

### editor_article_reports：举报记录

记录用户看到的具体公开内容及对应提交，以便修改之后仍能复核当时的问题。

| 字段名 | MySQL 中保存的数据类型 | 是否可以为空 | 具体用途 |
|---|---|---|---|
| id | CHAR(36) | 否 | 举报编号。 |
| reporter_id | CHAR(36) | 否 | 举报用户编号。 |
| article_id | CHAR(36) | 否 | 被举报的内容编号。 |
| revision_id | CHAR(36) | 否 | 被举报内容对应的具体提交编号。 |
| reason | VARCHAR(30) | 否 | spam表示垃圾内容，abuse表示攻击，inaccurate表示信息错误，other表示其他。 |
| description | VARCHAR(1000) | 否 | 补充说明，可为空字符串。 |
| status | VARCHAR(20) | 否 | open表示待处理，resolved表示已处理，dismissed表示未采纳。 |
| resolved_by | CHAR(36) | 是 | 处理人员编号。 |
| resolution_note | TEXT | 是 | 处理说明。 |
| created_at | DATETIME(6) | 否 | 后端创建这条记录的时间。 |
| updated_at | DATETIME(6) | 否 | 后端最后修改这条记录的时间。 |

id是主键，reporter_id和resolved_by关联users，article_id关联editor_articles。revision_id、article_id一起关联editor_revisions的id、article_id，保证举报指向同一篇内容的提交。服务确认用户看过的目标是当前可见公开提交，而非内部草稿。为status、created_at建立处理队列索引。

## 9. 后台任务与重复请求处理

### jobs：等待后台执行的工作

请求进程先把待做的工作写进这张表，后台进程再领取并执行。例如上传完成后需要生成缩略图，提交内容后需要做审核检查。

| 字段名 | MySQL 中保存的数据类型 | 是否可以为空 | 具体用途 |
|---|---|---|---|
| id | CHAR(36) | 否 | 任务编号。 |
| kind | VARCHAR(30) | 否 | send_verification_email表示发送邮箱验证码，process_media表示处理图片或视频，review_note表示检查帖子，review_editorial表示检查文章，cleanup表示清理数据。 |
| target_id | CHAR(36) | 否 | 本任务处理的对象编号，具体是哪张表由kind决定。 |
| dedupe_key | VARCHAR(191) | 否 | 业务服务生成的唯一任务名称，防止重复入队。 |
| payload | JSON | 否 | 执行所需的少量参数，不复制验证码明文或整个正文。 |
| status | VARCHAR(20) | 否 | queued表示等待，running表示执行中，succeeded表示成功，failed表示失败，cancelled表示取消。 |
| attempts | INT UNSIGNED | 否 | 已经执行的次数，初始为0。 |
| max_attempts | INT UNSIGNED | 否 | 最多允许执行次数，初始为3。 |
| available_at | DATETIME(6) | 否 | 任务最早可以被执行的时间。 |
| lease_owner | VARCHAR(100) | 是 | 当前领取任务的进程标识。 |
| lease_until | DATETIME(6) | 是 | 当前进程的领取资格有效到何时。 |
| last_error_code | VARCHAR(80) | 是 | 最近一次失败原因。 |
| finished_at | DATETIME(6) | 是 | 任务结束时间。 |
| created_at | DATETIME(6) | 否 | 后端创建这条记录的时间。 |
| updated_at | DATETIME(6) | 否 | 后端最后修改这条记录的时间。 |

id是主键，dedupe_key不能重复。为status、available_at、id建立组合索引；为status、lease_until建立另一索引。target_id可能指向不同表，所以不设置虚假的外键；每一种kind由专门处理代码检查目标是否存在。任务领取和失败恢复见内容发布文档。

### idempotency_records：记住已经接受的创建请求

用户网络断开后可能再次点击发布。客户端给同一次操作使用同一个请求编号，后端用本表识别重试，并返回原先创建的对象，避免重复创建。

| 字段名 | MySQL 中保存的数据类型 | 是否可以为空 | 具体用途 |
|---|---|---|---|
| id | CHAR(36) | 否 | 记录编号。 |
| user_id | CHAR(36) | 否 | 请求属于哪个用户。 |
| operation | VARCHAR(80) | 否 | 具体操作，例如create_note、publish_note或publish_editorial。不同类型使用不同操作名称。 |
| request_key | VARCHAR(100) | 否 | 客户端为同一次操作生成的请求编号。 |
| request_hash | CHAR(64) | 否 | 请求内容的摘要，用来检查重试有没有偷偷换参数。 |
| resource_id | CHAR(36) | 否 | 第一次请求已经创建的对象编号。 |
| response_status | SMALLINT UNSIGNED | 否 | 第一次请求应返回的网络状态码。 |
| expires_at | DATETIME(6) | 否 | 去重记录的保留期限，至少24小时。 |
| created_at | DATETIME(6) | 否 | 后端创建这条记录的时间。 |

id是主键，user_id关联users。user_id、operation、request_key组合不能重复。相同编号但参数不同的请求返回409错误。业务对象和这条记录在同一事务中保存；并发重试遇到唯一限制后读取已经成功的结果。resource_id根据operation指向不同表，不设置跨多表的外键。

### audit_logs：关键后台操作记录

后台人员授权、审核、下架和修改地点活动资料时，后端记录谁做了什么，便于以后追查。

| 字段名 | MySQL 中保存的数据类型 | 是否可以为空 | 具体用途 |
|---|---|---|---|
| id | CHAR(36) | 否 | 操作记录编号。 |
| actor_type | VARCHAR(20) | 否 | user表示由用户操作，system表示由后台程序操作。 |
| actor_id | CHAR(36) | 是 | 操作人的用户编号，程序执行时可为空。 |
| action | VARCHAR(80) | 否 | 操作名称，例如approve_note、approve_editorial或hide_editorial。 |
| target_type | VARCHAR(50) | 否 | 操作对象类型，例如note、editor_article、place或user。 |
| target_id | CHAR(36) | 否 | 操作对象编号。 |
| before_summary | JSON | 是 | 修改前的必要信息。 |
| after_summary | JSON | 是 | 修改后的必要信息。 |
| request_id | CHAR(36) | 否 | 发起本次操作的请求编号。 |
| reason | TEXT | 是 | 操作原因或补充说明。 |
| created_at | DATETIME(6) | 否 | 后端创建这条记录的时间。 |

id是主键，actor_id关联users。为target_type、target_id、created_at建立组合索引。审计记录与业务修改一起保存。摘要不记录验证码、登录凭证或解密后的邮箱地址。

## 10. 关系与发布规则

**地点文章无需活动。** focus_type为place时，primary_place_id必须指向这篇文章介绍的一个地点；primary_event_id必须为空。后端不创建用于填字段的虚构活动。新文章发布要求地点active，城市与文章一致；照片仍可为空。

**活动文章以活动为主。** focus_type为event时，primary_event_id必须指向一项活动；primary_place_id必须为空。新文章发布要求活动published、城市与文章一致。活动的place_id有值时，后端验证它是可公开读取且仍正常开放的地点；未知场馆允许为空并显示“地点待公布”。已发布后活动取消或地点关闭，动态信息卡显示最新状态，不自动重写文章正文。

**Notes的可选关联只是补充信息。** place_id和event_id都可以为空。选择活动后若活动已有举办地，Note同时选择的地点必须与其一致；若只传活动，后端保存时补齐已知举办地。活动举办地未知时，Note也不强制填地点。它们必须与帖子城市一致，且关联对象可公开读取。这些规则在保存提交和公开时再次检查，不让用户帖子引用后台未公开资料。之后活动搬迁时，以最新活动举办地为准显示动态活动卡，历史提交不改写。

**两种内容分别发布。** Editor通过published_revision_id选择一个固定文章版本；Notes审核通过后把固定字段和图片清单复制到notes、note_images，并记录published_submission_id。二者分别检查最新提交序号、删除/下架状态、媒体权限和资料状态。不能用另一套模块的提交编号执行公开操作。

**公开内容内部必须一致。** Editor正文、重心、媒体和标签来自同一公开版本。Notes文字和图片在同一事务内替换，不能先换文字、过一会才换图片。读取Note详情时，后端也在同一个一致的读取事务中取正文和图片，或用同一条查询取得，避免两次读取之间恰好发生更新。修改工作草稿不影响公开显示。

## 11. 清理与保留

| 数据 | 初始处理方式 |
|---|---|
| 验证码 | 5分钟后不能使用。发送成功清除发送密文；过期24小时内删除验证记录中的敏感材料。 |
| 未完成上传 | 超过24小时、且没有草稿、提交清单、正文、头像或地点引用时清理。 |
| 用户草稿 | 用户保留期间保存。退出账户后，本地草稿不能显示给下一位登录者。 |
| 已删除内容 | 立即停止对外展示，30天后清理正文与不再使用的图片、视频和派生文件。 |
| 去重记录 | 至少保留24小时。Notes提交和Editor提交分别受各自草稿版本唯一限制保护。 |
| 成功的后台任务 | 7天后可以清理；尚未结束的任务不能按此规则删除。 |

以上是初始工程保留策略。账户注销先撤销登录并隐藏内容，再清理邮箱地址、个人资料和私人草稿。其他记录仍需要引用用户编号时，只保留已注销状态的匿名账户记录。清理按关联顺序执行，不直接删除被其他表引用的用户行。

第一版没有为Agent预留会话表，也没有浏览画像、推断兴趣或模型调用记录。后续确实开发这些功能时，再依据新的产品设计增加表。

文件清理必须覆盖Editor工作稿和版本、Note工作稿和提交图片数组、公开note_images、地点相册及头像；有任一保留引用就不能物理删除。视频原文件、播放文件和poster作为同一媒体一起管理。下架立即停止新授权并清除公开缓存，但不承诺收回已经下载的副本。
