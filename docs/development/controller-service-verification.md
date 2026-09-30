# 后端分层与目录重构验证

## 实测结果

- 后端测试：**83 项通过，0 项失败，0 项跳过**，本次完整运行耗时 4.77 秒。
- `pnpm typecheck:backend`：0 错误、0 警告。
- `apps/backend/.venv/bin/ruff check apps/backend`：通过。
- `git diff --check`：通过。
- 重构前后 OpenAPI 完全一致。
- 重构前后 33 张表、326 列的模型结构完全一致。比较范围包含 MySQL 建表语句、索引、约束、列类型、可空性、主键、默认值、更新默认值和自增设置。

模型和 OpenAPI 基线在本轮目录修改前保存。模型拆分后，24 处 Python 默认值函数的所属模块名随文件移动改变；逐一映射新旧模块名后，完整模型比较一致。另逐类比较了 35 个模型类及 31 个请求类的语法结构，字段、默认值和校验器定义未变。

本轮将接口集中到 `controllers/`、业务集中到 `services/`，新增 4 个实际执行数据库查询和关联写入的 `repositories/*_repository.py`。表模型与请求字段分别拆到 `models/`、`schemas/`；旧业务目录及兼容路径已经移除。11 个迁移模块的 95 个顶层函数在移动前后保持相同的参数、装饰器和执行代码；数据库访问提取另行审阅并由集成测试覆盖。

## 新增验证

`apps/backend/tests/test_layer_boundaries.py` 增加以下检查：

1. 业务 service、公共业务工具、鉴权逻辑和 worker 不导入 FastAPI、Starlette、HTTP controller 或请求依赖模块。
2. 定义路由的 controller 不导入 SQLAlchemy 或数据库模型，也不直接执行查询、写入、提交等数据库操作。
3. worker 通过 Notes、Editor 和审核业务 service 执行相关工作。
4. 在真实 MySQL 事务内，直接调用 Note service 创建笔记、用相同请求标识重试、保存正文并拒绝过期版本。业务调用不构造 Request 或 Response，最终检查数据库只新增一篇笔记，正文保存正确。

5. 要求 controller、service、repository、model、schema 和 job 目录存在，旧业务包不再保留 Python 源文件。
6. 数据库访问文件不导入 HTTP 框架、controller 或 service，也不自行提交或回滚事务。

除第四项外均为源码边界检查；第四项是直接调用业务层的运行测试。它们与已有 HTTP 集成测试互补，不将静态检查当作全部业务正确性的证明。

## 命令入口

- `uv run python -m marcus.scripts.seed --help` 成功，只验证参数入口，未执行初始化写入。
- `marcus.jobs.worker` 可导入，未启动常驻循环。
- 专用测试库运行 `alembic check`，没有待生成的数据库结构变更。
- `pnpm db:seed` 及 README 已改用 `marcus.scripts.seed`。服务启动命令和 worker 命令保持不变。
- 保留了用户在 `core/common.py` 中对 `enqueue` 的注释修改。

## 原有测试的调整

媒体存储和限流测试改为替换对应 service 中的对象；鉴权测试直接调用 `services.authentication_service.authenticate`。业务失败断言使用 `ServiceError`，保留原来的状态码、错误内容和异常传播要求。没有保留旧 controller 的兼容导出，也没有删除或放宽已有行为断言。

## 测试环境与复跑

完整测试使用专用 MySQL `marcus_test` 数据库和本机 S3 兼容服务中的 `marcus-directory-test` 桶。数据库测试夹具会清理这个测试库的数据；没有对开发数据库执行清理。媒体测试通过本机 HTTP 服务上传、处理和下载文件；邮件测试使用测试夹具创建的本机 SMTP 接收器，未发送外部邮件。

在已有独立测试库和本机 S3 服务的环境中，设置 `MARCUS_TEST_DATABASE_URL`、`MARCUS_TEST_S3_ENABLED=1`、以 `-test` 结尾的 `MARCUS_S3_BUCKET` 及相应 S3 地址和测试凭证，再从根目录执行：

```bash
bash scripts/test-backend.sh -q
pnpm typecheck:backend
apps/backend/.venv/bin/ruff check apps/backend
```

`scripts/test-backend.sh` 会先验证数据库名以 `_test` 结尾，再执行数据库迁移和测试。此报告没有保存或展示数据库密码及存储凭证。
