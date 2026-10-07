# 验证记录

2026-10-01，独立测试 agent 验证。以下分别说明检查范围，不把编译成功当作完整交互测试。

| 检查 | 结果 |
| --- | --- |
| `pnpm --filter @marcus/rn-city-notes typecheck` | 通过，最终 Scene 配置修复后重新执行，退出码 0 |
| `pnpm --filter @marcus/rn-city-notes export` | coding agent 执行通过；独立检查 `dist/metadata.json` 确认包含 iOS 和 Android 的 Hermes 包 |
| iOS 原生编译 | 通过，0 errors / 0 warnings |
| iOS 模拟器启动、首页显示 | 通过，iPhone 18 Pro / iOS 27.0 实际显示标题、发布入口和两张笔记卡片，截图已检查 |
| 详情、发布、返回、空内容拦截、键盘避让 | 已检查对应源码；未完成实际点击和输入验证 |
| Android 原生运行 | 未验证；双平台导出不能代替 Android 原生运行 |

首次原生编译成功，但启动日志报 `UIScene life cycle is required`，应用未能显示页面。已在 `app.json` 启用 `expo-build-properties` 的 `enableSceneSupport`，重新生成工程并编译后，实际首页正常显示。

本次首次运行命令：

```bash
pnpm --filter @marcus/rn-city-notes ios --device 14035296-F75A-4D8F-8CCA-82E93BB04BA6 --port 8087
```

修复配置后保留上述 Metro 进程，重新编译：

```bash
RCT_METRO_PORT=8087 pnpm --filter @marcus/rn-city-notes ios --device 14035296-F75A-4D8F-8CCA-82E93BB04BA6 --no-bundler
```

工具无法连接 Simulator 窗口（名称、bundle ID、完整路径均返回 `Invalid app`）。尝试 `simctl openurl` 打开详情时出现系统“Open in 城市笔记 Demo?”确认框，未绕过工具限制模拟点击。因此不声称发布流程已通过端到端测试。模拟器当前保留此确认框，可手动点 Cancel 回到首页，或 Open 打开详情。

本机临时证据：首页截图 `/tmp/rn-city-notes-home.png`；首次启动错误日志 `/tmp/rn-city-notes-first-launch.log`。这些临时文件不随仓库分发。
