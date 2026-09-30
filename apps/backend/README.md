# 后端代码导航

用户发来请求后，`api.py` 取出请求参数，调用同模块的 `service.py`，再返回结果。业务规则、数据库查询与修改、后台任务登记都由 `service.py` 执行。

```text
src/marcus/
├── main.py                  # 接入路由，将业务失败转换为 HTTP 错误响应
├── identity/
│   ├── api.py               # 登录请求、请求头及 Cookie 的读取和写入
│   └── service.py           # 验证码、注册登录、续期、资料修改和注销
├── catalog/
│   ├── api.py               # 城市、区、地点、活动、场次和标签接口
│   ├── service.py           # 资料查询、规则检查、数据库保存和关联更新
│   └── seed.py              # 初始化上海资料与可选管理员
├── notes/
│   ├── api.py               # 笔记请求参数和响应
│   └── service.py           # 创建草稿、保存修改、提交审核和公开内容读取
├── editorials/
│   ├── api.py               # 编辑文章请求参数和响应
│   ├── service.py           # 专业文章草稿、版本、发布及媒体关联处理
│   └── document.py          # 专业文章正文格式检查
├── media/
│   ├── api.py               # 上传、确认上传和删除接口
│   └── service.py           # 文件访问、上传资格、媒体状态与处理任务登记
├── moderation/
│   ├── api.py               # 审核、上下架和账户管理接口
│   └── service.py           # 审核决定、恢复内容、角色及账户状态修改
├── community/
│   ├── discovery.py         # Discover 列表接口
│   ├── discovery_service.py # 列表筛选、排序和分页查询
│   ├── engagement.py        # 点赞、收藏、屏蔽、参与和举报接口
│   ├── engagement_service.py # 对应业务处理与数据库操作
│   └── content_common.py    # 两类内容共用的作者、地点和互动信息读取
├── jobs/worker.py           # 领取任务，调用业务函数，执行邮件和媒体处理
├── core/
│   ├── dependencies.py     # 从 HTTP 请求取得凭证，向路由提供当前用户
│   ├── auth.py             # 验证凭证、数据库登录记录和用户角色
│   ├── errors.py           # 保存业务失败原因，不创建 HTTP 响应
│   ├── common.py           # 数据查询、版本检查、审计、任务登记和分页辅助
│   ├── config.py           # 读取运行环境配置
│   ├── db.py               # 数据库连接及请求结束后的提交或回滚
│   └── security.py         # 签发凭证、摘要、加密与解密
├── database/models.py      # 数据库表模型、约束和索引
└── contracts/
    ├── schemas.py          # 输入字段、类型及格式约束
    └── responses.py        # 接口响应字段
```

## 修改功能时去哪里

- 改请求路径、参数来源、Cookie 或响应状态码：改该模块的 `api.py`。社区模块对应 `discovery.py` 和 `engagement.py`。
- 改“这次操作是否允许”“哪些数据要保存”“要安排什么后台工作”：改该模块的 `service.py`。
- 业务模块之间直接调用对方的服务函数，例如 `marcus.media.service.validate_assets`。后台 worker 和存储初始化脚本也直接使用服务，不再从路由文件取业务函数。
- 服务接收输入数据、数据库操作对象及需要的用户信息。服务不接收 FastAPI 的 `Request`、`Response`，不读取 Cookie；审计需要请求编号时，由接口把编号字符串传进去。
- 服务通过 `ServiceError` 报告失败原因。`main.py` 负责返回原有错误格式与状态码；后台任务可以直接处理同一种错误，不需要构造 HTTP 请求。

## 数据库提交由谁负责

HTTP 请求通过 `core/db.py` 的 `get_session()` 取得数据库操作对象。接口把它传给服务，服务之间继续传递同一个对象。因此创建笔记、登记审核任务等改动可以一起提交或回滚。普通服务操作不自行结束事务；接口正常完成后，`get_session()` 提交，发生异常则回滚，成功响应在提交完成后发送。

登录中有两个明确例外：验证码输入错误次数、旧续期凭证被重复使用后的撤销结果，必须在返回失败响应后仍然保存，因此业务服务保留原先的显式提交。worker 自己开启并管理其数据库事务。

服务也能在测试或后台程序中直接调用；调用者负责传入数据库操作对象和所需数据，并负责结束事务。独立业务调用不经过路由上的角色检查，调用者必须先确认操作权限。

数据库迁移位于 `migrations/`，测试位于 `tests/`；本次拆分不改变表结构或对外接口定义。

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

## Python 类型检查

在仓库根目录执行 `pnpm typecheck:backend`，可以检查后端源码、数据库迁移和测试中的 Python 类型问题。检查工具 Pyright 已列入后端开发依赖，先执行 `(cd apps/backend && uv sync --dev)` 即可安装锁定版本。也可以在后端目录直接执行 `uv run pyright --project ../../pyrightconfig.json`。

根目录 `pyrightconfig.json` 固定使用 `standard` 检查模式，并按项目支持的最低 Python 版本 3.12 检查语法。此检查不会启动服务或访问数据库；数据库行为仍由 `pnpm test:backend` 验证。

现有 `scripts/test-backend.sh` 也会在确认专用测试库名称后、执行迁移和测试前运行类型检查；任何类型错误都会让脚本停止。

## 编辑器提示找不到 Python 包

使用 VS Code 时，请打开整个 `Marcus` 仓库目录。根目录的 `.vscode/settings.json` 将后端的 `apps/backend/.venv` 设为默认 Python 环境；`pyrightconfig.json` 告诉代码检查工具从 `apps/backend/src` 查找项目源码，并为独立运行的 Pyright 指定后端虚拟环境。这些配置不会安装依赖，也不会关闭找不到包的检查。

如果虚拟环境尚未创建，从仓库根目录执行：

```bash
(cd apps/backend && uv sync --dev)
```

如果仍提示 `Import ... could not be resolved`，在 VS Code 命令面板执行 `Python: Select Interpreter`，选择 `apps/backend/.venv` 中的 Python。macOS/Linux 的程序路径是 `apps/backend/.venv/bin/python`，Windows 是 `apps/backend/.venv/Scripts/python.exe`。**已经手动选过的解释器不会因修改默认配置而自动切换**；Pylance 使用编辑器选中的解释器，而不是 `pyrightconfig.json` 中的虚拟环境设置。选好后可执行 `Developer: Reload Window` 重新载入编辑器。

配置行为参考 [VS Code Python 设置说明](https://code.visualstudio.com/docs/python/settings-reference)和 [Pyright 配置说明](https://github.com/microsoft/pyright/blob/main/docs/configuration.md)。
