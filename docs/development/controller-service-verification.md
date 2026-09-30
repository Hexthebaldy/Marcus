# Controller / Service 拆分验证

## 实测结果

- 后端测试：**81 项通过，0 项失败，0 项跳过**，本次完整运行耗时 5.72 秒。
- `pnpm typecheck:backend`：0 错误、0 警告。
- `apps/backend/.venv/bin/ruff check apps/backend`：通过。
- `git diff --check`：通过。
- 重构前后 OpenAPI 完全一致。
- 重构前后 33 张表、326 列的模型结构完全一致。比较范围包含 MySQL 建表语句、索引、约束、列类型、可空性、主键、默认值、更新默认值和自增设置。

模型和 OpenAPI 基线在本轮源码修改前保存。尝试运行原有 77 项测试时，其他 agent 已开始修改接口，出现临时缺少 `core.dependencies` 的导入错误，因此不把该次运行记为成功基线。所有模块完成后，原有测试与新增 4 项测试一起运行，得到上面的 81 项通过结果。

## 新增验证

`apps/backend/tests/test_layer_boundaries.py` 增加以下检查：

1. 业务 service、公共业务工具、鉴权逻辑和 worker 不导入 FastAPI、Starlette、HTTP controller 或请求依赖模块。
2. 定义路由的 controller 不导入 SQLAlchemy 或数据库模型，也不直接执行查询、写入、提交等数据库操作。
3. worker 通过 Notes、Editor 和审核业务 service 执行相关工作。
4. 在真实 MySQL 事务内，直接调用 Note service 创建笔记、用相同请求标识重试、保存正文并拒绝过期版本。业务调用不构造 Request 或 Response，最终检查数据库只新增一篇笔记，正文保存正确。

前三项是源码层边界检查；第四项是直接调用业务层的运行测试。它们与已有 HTTP 集成测试互补，不将静态检查当作全部业务正确性的证明。

## 原有测试的调整

媒体存储和限流测试改为替换对应 service 中的对象；鉴权测试直接调用 `core.auth.authenticate`。业务失败断言使用 `ServiceError`，保留原来的状态码、错误内容和异常传播要求。没有保留旧 controller 的兼容导出，也没有删除或放宽已有行为断言。

## 测试环境与复跑

完整测试使用专用 MySQL `marcus_test` 数据库和本机 S3 兼容服务中的 `marcus-layer-test` 桶。数据库测试夹具会清理这个测试库的数据；没有对开发数据库执行清理。媒体测试通过本机 HTTP 服务上传、处理和下载文件；邮件测试使用测试夹具创建的本机 SMTP 接收器，未发送外部邮件。

在已有独立测试库和本机 S3 服务的环境中，设置 `MARCUS_TEST_DATABASE_URL`、`MARCUS_TEST_S3_ENABLED=1`、以 `-test` 结尾的 `MARCUS_S3_BUCKET` 及相应 S3 地址和测试凭证，再从根目录执行：

```bash
bash scripts/test-backend.sh -q
pnpm typecheck:backend
apps/backend/.venv/bin/ruff check apps/backend
```

`scripts/test-backend.sh` 会先验证数据库名以 `_test` 结尾，再执行数据库迁移和测试。此报告没有保存或展示数据库密码及存储凭证。
