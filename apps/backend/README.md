# 后端代码导航

接收请求的函数在 `controllers/`，处理业务的函数在 `services/`。文件名分别以 `_controller.py`、`_service.py` 结尾；在编辑器只看文件名也能分清职责。

```text
src/marcus/
├── controllers/
│   ├── auth_controller.py          # 邮箱登录、续期、退出与个人资料
│   ├── catalog_controller.py       # 城市、区、地点、活动、场次和标签
│   ├── note_controller.py          # 用户笔记
│   ├── editorial_controller.py     # 编辑文章
│   ├── media_controller.py         # 媒体上传和访问
│   ├── moderation_controller.py    # 内容审核和账号管理
│   ├── discovery_controller.py     # Discover 列表
│   ├── engagement_controller.py    # 点赞、收藏、参与和举报
│   └── dependencies.py             # 读取请求凭证和来源，取得当前用户
├── services/
│   ├── auth_service.py             # 验证码、登录及个人资料业务
│   ├── authentication_service.py   # 验证访问凭证、登录记录和角色
│   ├── catalog_service.py          # 地点活动资料的检查、修改和关联处理
│   ├── note_service.py             # 笔记草稿、提交和公开内容
│   ├── editorial_service.py        # 编辑文章、版本和发布
│   ├── media_service.py            # 上传资格、媒体状态和文件访问
│   ├── moderation_service.py       # 审核决定、上下架和角色修改
│   ├── discovery_service.py        # 内容筛选、排序和分页
│   ├── engagement_service.py       # 点赞、收藏、参与和举报业务
│   ├── content_service.py          # 两类内容共用的作者、地点和互动信息
│   └── editorial_document.py       # 编辑文章正文格式检查
├── repositories/
│   ├── auth_repository.py          # 邮箱、验证码和登录相关查询与批量更新
│   ├── catalog_repository.py       # 地点、活动及关联资料的查询和写入
│   ├── note_repository.py          # 笔记图片、投稿和版本查询
│   └── editorial_repository.py     # 文章版本、审核和关联资料查询
├── models/                         # 按业务拆开的数据库表类
│   ├── base.py                     # 所有表共用的基类
│   ├── constraints.py              # 跨表约束和补充索引
│   └── *_model.py                  # 每类业务的数据库字段
├── schemas/                        # 按业务拆开的请求字段、校验与响应定义
│   ├── *_schema.py                 # 各业务的请求字段
│   └── responses.py                # 返回给客户端的字段
├── jobs/worker.py                  # 领取并执行邮件、媒体和清理任务
├── scripts/seed.py                 # 初始化上海资料与可选管理员
├── core/                           # 配置、数据库连接、加密和共用函数
└── main.py                         # 接入路由，将异常转换为 HTTP 响应
```

## 修改功能时去哪里

用户保存笔记时，`note_controller.py` 取得请求里的正文、图片编号和当前用户，再调用 `note_service.py`。业务函数检查归属、版本和图片状态，安排保存，最后把结果交回接口函数。

- 改请求路径、参数来源、Cookie 或响应状态码：改 `controllers/` 中对应的文件。
- 改操作是否允许、状态如何变化、需要安排哪些后台任务：改 `services/` 中对应的文件。
- 改已经抽出的成组查询、加锁查询或关联表写入：改 `repositories/` 中对应的文件。数据库访问函数不自行提交事务，也不调用接口或业务函数。
- 改数据库表字段：改 `models/` 中对应的文件，并在 `migrations/` 增加迁移。`models/__init__.py` 统一导出表类，确保迁移和接口加载同一套完整模型。
- 改请求和响应的字段、类型或格式要求：改 `schemas/`，再检查生成的接口说明与前端类型。

本轮从登录、笔记、编辑文章和地点活动业务中提取了数据库访问函数。其他服务中的直接查询，以及服务对数据库对象的字段赋值和 `flush()`，仍然保留；不是每一次数据库调用都新增一层转发。

业务函数不接收 FastAPI 的 `Request`、`Response`，不读取 Cookie。需要审计编号时，接口只传入编号字符串。服务之间和后台任务直接调用业务函数，不从 controller 导入代码。服务通过 `ServiceError` 报告失败；`main.py` 将它转换为 HTTP 错误响应。

## 数据库提交由谁负责

HTTP 请求通过 `core/db.py` 的 `get_session()` 取得数据库操作对象。接口把它传给业务函数，业务函数再把同一个对象传给数据库访问函数。因此创建笔记、登记审核任务等改动可以一起提交或回滚。普通业务操作不自行结束事务；接口正常完成后，`get_session()` 提交，发生异常则回滚，成功响应在提交完成后发送。

登录中有两个明确例外：验证码输入错误次数、旧续期凭证被重复使用后的撤销结果，必须在返回失败响应后仍然保存，因此业务服务保留原先的显式提交。worker 自己开启并管理其数据库事务。

测试或后台程序可以直接调用业务函数；调用者负责传入数据库操作对象和所需数据，并负责结束事务。独立调用不经过 controller 的登录与角色检查，调用者必须先确认操作权限。

数据库迁移位于 `migrations/`，测试位于 `tests/`。目录调整不需要重建数据库；接口路径和表结构保持不变。

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
uv run python -m marcus.scripts.seed --admin-email editor@example.com
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
