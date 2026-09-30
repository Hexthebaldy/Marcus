# Marcus

面向城市年轻用户的文娱生活发现社区，首发上海。代码包含手机端、网页编辑后台和 Python 后端，统一放在这个仓库中。

手机端提供邮箱验证码注册与登录、Discover 的“活动”和 Notes、内容详情、简单图文笔记创作、收藏及个人资料。搜索保留基础入口。编辑后台提供地点与活动资料管理、专业文章编辑、预览、提交和审核。Editor 文章与 Notes 使用不同的数据模型；文章由编辑选择以地点或活动为重心，并包含城市与区。封面和图片均可选。

界面以卡其色为主、深绿色为辅。Mars 是城市生活内容的视觉参考，当前实现没有经过与指定版本逐页对照，不声称一比一复刻。第一版不包含 Agent、个性化推荐、手机登录或 Electron 桌面端。

## 项目结构

| 路径 | 内容 |
|---|---|
| `apps/mobile` | TypeScript、React Native、Expo 手机应用。 |
| `apps/editor` | React、Vite 网页编辑与审核后台。 |
| `apps/backend` | FastAPI 接口、MySQL 数据模型与迁移、独立后台工作进程、后端测试。见[后端代码导航](apps/backend/README.md)。 |
| `packages/api-client` | 两端共用的请求、登录续期和接口类型。 |
| `packages/design-tokens` | 手机端使用的卡其色与深绿色等配色值。网页采用同一套主要配色。 |
| `packages/editorial-schema` | 专业文章的内容块和校验。 |
| `packages/editorial-editor` | 基于 Tiptap 的专业文章编辑器。 |
| `infra` | 本地 MySQL、Redis、对象存储和邮件接收服务配置。 |
| `contracts/openapi.json` | 从后端代码生成的接口说明。 |

后端按 controllers、services、repositories、models、schemas 分目录，第一版不拆微服务。接口进程将邮件、图片和视频处理工作写入 MySQL 的任务表，由另一个 Python 进程领取并完成。Redis 用于请求频率限制，不承担消息队列。图片和视频文件保存在兼容 S3 接口的对象存储，MySQL 保存文件资料和引用。

## 本地启动

需要 Node.js 22.13 或更高版本、pnpm 11.18.0、Python 3.12 或更高版本、uv，以及提供 `ffmpeg` 和 `ffprobe` 命令的视频处理工具。使用下面的容器方案还需要 Docker Compose。依赖版本分别记录在 `pnpm-lock.yaml` 和 `apps/backend/uv.lock`。

从仓库根目录安装前端依赖，启动基础服务并准备本地配置：

```bash
pnpm install --frozen-lockfile
pnpm infra:up
cp -n apps/backend/.env.example apps/backend/.env
cp -n apps/mobile/.env.example apps/mobile/.env
cp -n apps/editor/.env.example apps/editor/.env
cd apps/backend
uv sync --frozen
cd ../..
pnpm db:migrate
pnpm db:seed
pnpm storage:init
```

等待 MySQL 的健康检查通过后再运行迁移。如果已有 `.env`，上面的命令会保留它；请检查其中端口是否对应当前基础服务。样例使用 MySQL 3307、Redis 6380、对象存储 9000、邮件服务 1025。仓库中的示例密码只用于本地开发。

为第一个编辑人员授予管理员、编辑和审核权限。下面的地址只适合本地开发；实际环境改为运营人员的邮箱：

```bash
cd apps/backend
uv run python -m marcus.scripts.seed --admin-email editor@example.com
cd ../..
```

分别在四个终端启动：

```bash
pnpm backend
pnpm worker
pnpm editor
pnpm mobile
```

| 入口 | 地址或用途 |
|---|---|
| 后端接口说明 | http://localhost:8000/docs |
| 网页编辑后台 | http://localhost:5173 |
| 本地验证码邮件 | http://localhost:8025 |
| 手机应用 | 按 Expo 终端提示打开开发客户端。 |

本地邮件服务 Mailpit 只接收邮件，不向真实邮箱投递。登录时输入 `editor@example.com`，在 Mailpit 中查看验证码。普通用户可以用其他邮箱注册。必须保持工作进程运行，否则验证码发送和媒体处理任务不会完成。

初始数据只有上海、16 个区以及可选管理员，没有虚构的活动或用户帖子。先在后台创建公开地点或活动，再创建文章并提交审核。默认所有 Notes 和文章都要通过审核，手机端会显示提交进度；审核通过后才进入 Discover。

真机访问时，手机与开发电脑应处于同一网络。将手机 `.env` 的 `EXPO_PUBLIC_API_URL` 改为电脑局域网地址，例如 `http://192.168.1.20:8000/v1`，并把后端 `MARCUS_S3_PUBLIC_ENDPOINT_URL` 改为同一台电脑可访问的 9000 端口。否则登录可能成功，上传和图片仍会因手机无法访问电脑的 localhost 而失败。修改后重启对应进程；以上示例地址需要按自己的电脑替换。

## 后端验证

测试会清理独立测试数据库内的业务数据，只允许名称以 `_test` 结尾的 MySQL 数据库。容器首次初始化时会创建 `marcus_test`；已有数据卷不会重复执行初始化 SQL，需自行创建独立测试库并授权。禁止使用开发库或生产库运行测试。

在仓库根目录执行：

```bash
export MARCUS_TEST_DATABASE_URL='mysql+asyncmy://marcus:marcus-local-only@127.0.0.1:3307/marcus_test'
export MARCUS_TEST_S3_ENABLED=1
export MARCUS_S3_BUCKET=marcus-test
bash scripts/test-backend.sh -q
```

测试媒体文件只放入名称以 `-test` 结尾的独立桶。需要本地对象存储、FFmpeg 和 ffprobe。未启用媒体测试时，相关测试会跳过，不能据此声称媒体链路已通过。运行结果及本轮实际验证边界见[验证记录](docs/development/verification.md)。

前端可分别运行 `pnpm --filter @marcus/mobile typecheck` 和 `pnpm --filter @marcus/editor build`。这些命令只检查类型及构建，不代表已经完成页面操作或设备体验测试。

后端接口变更后，从仓库根目录更新共享类型：

```bash
pnpm contracts
pnpm contracts:types
```

## 设计与交付范围

- [总体架构与实施方案](docs/architecture/01-system-design.md)
- [数据库表与字段说明](docs/architecture/02-data-model.md)
- [接口与数据格式](docs/architecture/03-api-contracts.md)
- [内容编辑、发布与后台任务](docs/architecture/04-content-publishing.md)
- [开发上下文与分工](docs/development/implementation-context.md)
- [实际验证记录](docs/development/verification.md)
- [过度防御性代码审查与消融记录](docs/development/ablation-review.md)

当前交付是可继续开发和本地运行的第一版代码，没有部署公开服务或签发上架安装包。正式上线还需要接入真实邮件服务和文件存储，配置域名、HTTPS、独立签名及加密密钥，并完成设备体验验证。`MARCUS_ENVIRONMENT=production` 会拒绝示例签名密钥和非 HTTPS 网页来源；其他上线配置仍需按部署环境完成。
