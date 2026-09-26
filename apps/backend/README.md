# 后端代码导航

后端代码仍属于一个 `marcus` Python 包，内部按业务建立子包。HTTP 服务从 `main.py` 启动；寻找某个功能时，先进入对应业务目录。

```text
src/marcus/
├── main.py                 # 创建 HTTP 服务，接入各业务接口
├── identity/api.py         # 邮箱登录、登录续期、用户资料与账户删除
├── catalog/
│   ├── api.py              # 城市、区、地点、活动、场次和标签
│   └── seed.py             # 初始化上海资料与可选管理员
├── notes/api.py            # 用户笔记、草稿、提交和公开内容
├── editorials/
│   ├── api.py              # Editor 文章、草稿、版本和发布
│   └── document.py         # 专业文章正文格式检查
├── media/api.py            # 图片视频上传、访问权限及删除
├── moderation/api.py       # 内容审核、上下架、角色和账户管理
├── community/
│   ├── discovery.py        # Discover 的两个内容列表
│   ├── engagement.py       # 点赞、收藏、屏蔽、参与记录及举报
│   └── content_common.py   # 两类内容共用的作者、地点和互动信息
├── jobs/worker.py          # 执行邮件、媒体处理、审核检查及清理任务
├── core/
│   ├── config.py           # 读取运行环境配置
│   ├── db.py               # 数据库连接与请求事务
│   ├── security.py         # 凭证、加密、摘要等基础函数
│   └── common.py           # 多个业务共用的权限、分页和请求处理函数
├── database/models.py      # 数据库表模型、约束和索引
└── contracts/
    ├── schemas.py          # 客户端可以发送哪些请求字段
    └── responses.py        # 后端对外返回哪些字段
```

每个目录中的 `__init__.py` 仅标记和说明 Python 包，不转发旧模块的函数。跨目录引用使用完整包路径，例如从 `marcus.core.db` 读取数据库连接，从 `marcus.media.api` 引用媒体处理函数。

`api.py` 目前包含该业务的接口和处理逻辑。这次整理不强行给每个业务增加空的服务层或数据访问层。数据库表模型与请求、响应定义分别集中在 `database`、`contracts`，没有在移动文件时改写表结构。

数据库迁移仍放在 `migrations/`，测试仍放在 `tests/`。它们与 `src/` 并列。

## 启动命令

从仓库根目录执行的命令保持不变：

```bash
pnpm backend
pnpm worker
pnpm db:seed
pnpm db:migrate
```

如果在 `apps/backend` 中直接运行 Python，新的模块路径是：

```bash
uv run uvicorn marcus.main:app --reload
uv run python -m marcus.jobs.worker
uv run python -m marcus.catalog.seed --admin-email editor@example.com
```

完整安装与服务配置见[根目录 README](../../README.md)。
