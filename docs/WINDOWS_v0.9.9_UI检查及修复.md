# Windows Codex：v0.9.9 界面检查和发布

请使用 SSGclassify 项目的 v0.9.9 源码，在 Windows x64 上构建并检查桌面应用，重点检查下述三项。Windows GUI 与 Mac 共用 `ssg_enumeration/desktop.py`；请在实际 Windows 程序中验证，发现问题后直接修复源码并重新打包。

1. **矩阵根号**：寻找包含 `sqrt(3)/2` 和 `-sqrt(3)/2` 的群元，确认根号及根号上横线清楚可见，分子分母和正负号不重叠；同时检查 Spin operation 中的根式以及不同缩放比例。测试截图要包含实际矩阵，而非只测试字符串。
2. **检索结果列**：结果表只展示 Q 和 K 两个群像列，隐藏 H 和 ker；Q 在 K 前，标题分别为编译的数学式 `Q=ϱ_P(P)` 和 `K=ϱ(G)`。确认调整列宽、分页、Details 按钮、点击和导出功能不受影响。隐藏展示列不应删除群结构数据。
3. **树状目录**：No. 列应较窄（当前目标宽度 42 个 Qt 逻辑像素），No. 和 Count 的数字应与分类文字字体风格、字号协调；检查编号 1–230、不同层级、计数的显示，确认箭头、缩进、数字无裁切。

## 数据与构建

- 使用 v0.9.9 标签对应的源码及其发布的 Mac ZIP 所含的 `Contents/Resources/SSGclassify.sqlite`，该数据库的 SHA-256 为 `075a65d8b1e4bbde3ce535e308d78ddbbc58528bcd5efd661cec1242011a8b56`。请核对内嵌数据库确实与此一致，并包含 67,475 个分类和 230 个母群。
- 在 Windows x64 的 Python 3.12 环境安装项目和 `PySide6-Essentials==6.8.3`、`pyinstaller==6.16.0`，使用 `python scripts/build_windows.py --database <正确的SSGclassify.sqlite路径>` 构建。
- `python scripts/verify_windows.py` 会核对数据库摘要、从含空格和中文的目录启动打包程序，测试查询及 ZIP 完整性；其输出包含运行报告。运行前确认脚本里的摘要与上面一致。保留整个应用目录，包括 `_internal`。
- 可使用仓库的 `Windows desktop` GitHub Actions 工作流；它会从 v0.9.9 Mac 发布包提取同一个数据库并生成 Windows 构建产物。自动检查不能替代 Windows 实机视觉检查。

## 回报内容

对三项分别给出通过、失败或未验证；附实际运行截图，注明 Windows 版本和显示缩放；列出任何修改、测试结果、打包路径及 ZIP SHA-256。将经过检查的 Windows ZIP 附到 v0.9.9 Release。不要把未运行的检查标为通过。
