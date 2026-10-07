# 城市笔记 RN 教学 demo

教程入口：打开同目录的 `guide.html`。新版按 Net Ninja 的 Complete React Native 29 课顺序组织，一次显示一课；教程中的本地文件按钮可展开源码。

在 Marcus 仓库根目录运行：

```bash
pnpm install --frozen-lockfile
pnpm --filter @marcus/rn-city-notes ios
```

首页选择“从第一个屏幕开始”，依次体验文字、样式和图片三个练习。列表、详情与发布保留在原 demo 中，数据只存内存，重新加载后恢复初始内容。

教程的主题、账号与 Appwrite 数据库章节是独立教学示例，没有接入本地 demo，也没有改动 Marcus 正式应用的登录方式。

检查命令：

```bash
pnpm --filter @marcus/rn-city-notes typecheck
pnpm --filter @marcus/rn-city-notes export
```

原 demo 验证记录见 `VERIFICATION.md`，新版教程与基础练习验证见 `COURSE-VERIFICATION.md`。课程来源记录在 `course-outline.json`。
