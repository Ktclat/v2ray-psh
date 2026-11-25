# v2ray-psh

[v2rayN](https://github.com/2dust/v2rayN) 的非官方下游。Windows 托盘右键菜单现在有两个入口：

- **复制 CMD 代理命令**：沿用原版的 `set` 命令。
- **复制 PowerShell 代理命令**：生成 `$env:HTTP_PROXY = 'http://127.0.0.1:…'` 等命令。

地址和端口继续取自 v2rayN 当前的本地代理配置。命令只复制到剪贴板，不自动运行；粘贴到对应终端后，只影响该终端和它启动的进程。Linux/macOS 保留原有 `export` 项。

## 下载与源码

- [Releases](https://github.com/Ktclat/v2ray-psh/releases)：Windows x64 WPF 便携预发布包，包含 .NET 运行时，不捆绑 Xray、sing-box 等上游代理核心。使用应用的核心更新入口，或将受信任的原版核心文件补到新包的相应 `bin` 位置。解压到新目录，不覆盖现有配置。
- [patched 源码分支](https://github.com/Ktclat/v2ray-psh/tree/patched)：每个发布版对应的完整 v2rayN 下游源代码，保留上游许可与作者，不包含上游自己的发布工作流。Release 标签绑定到实际构建的下游源码快照。
- 本仓库默认分支存放[补丁](patches/terminal-commands.patch)、测试和同步配置。如果应用内更新指向 2dust，安装官方版本会覆盖本项目的改动。

## 自动同步

[同步流水线](https://github.com/Ktclat/v2ray-psh/actions/workflows/sync-upstream.yml) 每 6 小时检查上游 `master`，也可手动运行。没有变化时跳过；有变化时会：

1. 检出明确的上游提交并应用补丁。冲突就停止，不发布未应用补丁的包。
2. 实际运行生成的 CMD 和 PowerShell 命令，并构建 Windows WPF 和 Avalonia 界面；当前发布资产仅为 Windows x64 WPF。
3. 更新 `patched` 源码分支并创建预发布版，包含 SHA-256 校验文件。预发布跟随上游开发分支，不冒充官方稳定版本。

如果补丁冲突，先用上游的新提交重新调整 `patches/terminal-commands.patch`，再推送到默认分支复测。不会自动猜测或覆盖上游对相关功能的修改。

上游作者：2dust 与 v2rayN 贡献者。代码沿用 [GPL-3.0](LICENSE)。
