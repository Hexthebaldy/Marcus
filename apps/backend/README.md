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

## 编辑器提示找不到 Python 包

使用 VS Code 时，请打开整个 `Marcus` 仓库目录。根目录的 `.vscode/settings.json` 将后端的 `apps/backend/.venv` 设为默认 Python 环境；`pyrightconfig.json` 告诉代码检查工具从 `apps/backend/src` 查找项目源码，并为独立运行的 Pyright 指定后端虚拟环境。这些配置不会安装依赖，也不会关闭找不到包的检查。

如果虚拟环境尚未创建，从仓库根目录执行：

```bash
(cd apps/backend && uv sync --dev)
```

如果仍提示 `Import ... could not be resolved`，在 VS Code 命令面板执行 `Python: Select Interpreter`，选择 `apps/backend/.venv` 中的 Python。macOS/Linux 的程序路径是 `apps/backend/.venv/bin/python`，Windows 是 `apps/backend/.venv/Scripts/python.exe`。**已经手动选过的解释器不会因修改默认配置而自动切换**；Pylance 使用编辑器选中的解释器，而不是 `pyrightconfig.json` 中的虚拟环境设置。选好后可执行 `Developer: Reload Window` 重新载入编辑器。

配置行为参考 [VS Code Python 设置说明](https://code.visualstudio.com/docs/python/settings-reference)和 [Pyright 配置说明](https://github.com/microsoft/pyright/blob/main/docs/configuration.md)。
