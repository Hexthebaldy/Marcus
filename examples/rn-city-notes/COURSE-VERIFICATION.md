# 29 课 HTML 指南验证

验证日期：2026-10-02。独立测试 agent 依据当前 `guide.html`、本地源码、作者公开课程目录及 GitHub 源码核对。

## 已通过

- 作者课程页面确有 29 课，指南顺序覆盖相应主题；没有把无法取得的视频字幕冒充译稿。
- GitHub 分支核对到 `lesson-1` 至 `lesson-25`、`lesson-27` 至 `lesson-29`，没有 `lesson-26`。指南明确第 26 课按后续分支中的实现核对。
- 最终源码固定提交为 `b014b91d9d24d87853fe0c0e9629ddb5ec9f021c`；`course-outline.json` 的 29 个源码路径在该提交均存在。
- 独立阅读登录、初始登录检查、页面保护、书籍共享数据、查询、创建、实时事件、删除和路由文件，并与指南核对。原课版本与本地版本、教学修正与课程原实现已区分。
- HTML 有 29 个连续编号的课程、唯一元素编号、有效内部锚点；11 个源码按钮均有对应快照。10 份嵌入源码与当前本地文件逐字一致。
- 提取实际 JavaScript 后运行 `node --check`，语法通过。
- 使用最小 DOM 替身执行实际指南脚本：逐课前进 1→29、后退 29→1、首末按钮边界、非法 hash 返回第 1 课、源码弹窗内容与关闭、浅深配色切换，全部通过。该检查验证脚本行为，不能证明浏览器排版或原生 RN 运行。

## 审查中发现并已修正

- 第 9 课不再引用第 7 课尚未创建的 dashboard 分组。
- 第 26 课明确原实现发起查询后立即订阅，并未等待查询完成才订阅。
- 第 29 课不再把原源码中不存在的删除确认步骤写成已实现功能。

## 未验证范围

当前浏览器控制工具返回 `Browser is not available: iab`，无法完成真实浏览器视觉检查。DOM 替身不覆盖实际布局、滚动、焦点、浏览器历史和屏幕阅读器行为。

指南中标为教学片段的账号、主题、Appwrite 云数据等代码没有接入本地 demo。它们经过来源和流程核对，不是一个已运行的完整 Appwrite 应用。原生运行范围请看 `VERIFICATION.md`；新增基础练习未完成原生点击验证。

## 来源

- [作者课程目录](https://netninja.dev/p/complete-react-native)
- [作者最终源码固定提交](https://github.com/iamshaunjp/Complete-React-Native-Tutorial/tree/b014b91d9d24d87853fe0c0e9629ddb5ec9f021c)
- [Expo 页面保护说明](https://docs.expo.dev/router/advanced/protected/)
- [Appwrite React Native 文档](https://appwrite.io/docs/quick-starts/react-native)

本机临时核验资料位于 `/tmp/netninja-rn-lesson29`、`/tmp/netninja-rn-early`；DOM 执行检查脚本为 `/tmp/rn-course-dom-test.cjs`。这些临时文件不随仓库分发。
