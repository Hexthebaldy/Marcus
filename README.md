# Marcus

面向城市年轻用户的文娱生活发现社区。首发中国大陆上海。

第一版仅使用邮箱验证码完成注册与登录，无需设置密码，不提供手机号注册或登录。Discover中的Editor文章由编辑选择以地点或活动为重心，支持专业图文视频排版；用户Notes是独立建模的简单文字与图片帖子。底部保留搜索和个人入口。Agent、个性化推荐和 AI 编辑工作流留待后续单独设计，第一版不实现。

客户端采用 TypeScript + React Native。服务端采用 Python + FastAPI，数据库使用 MySQL。

当前仓库保存的是技术方案，尚未实现应用代码。

- [总体架构与实施方案](docs/architecture/01-system-design.md)
- [数据库表与字段说明](docs/architecture/02-data-model.md)
- [接口与数据格式](docs/architecture/03-api-contracts.md)
- [内容编辑、发布与后台任务](docs/architecture/04-content-publishing.md)
