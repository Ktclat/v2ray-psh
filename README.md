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

[同步流水线](https://github.com/Ktclat/v2ray-psh/actions/workflows/sync-upstream.yml) 支持事件唤醒；没有接入上游通知时，每小时第 23 分钟（UTC）低频兜底检查 GitHub 的「最新正式 Release」，也可手动运行。GitHub 的定时执行可能延迟。普通提交、仅推标签、预发布和草稿不会触发 Windows 构建；相同上游版本和补丁只发布一次。检测到新版本后：

1. 从正式 Release 标签解析出明确的提交并应用补丁。冲突就停止，不发布未应用补丁的包。
2. 实际运行生成的 CMD 和 PowerShell 命令，并构建 Windows WPF 和 Avalonia 界面；当前发布资产仅为 Windows x64 WPF。
3. 更新 `patched` 源码分支并创建预发布版，包含 SHA-256 校验文件。虽然源码基于上游正式版，下游包仍标记为预发布，以区别于官方发行包。

如果补丁冲突，按 WPF 项目目录调整 `patches/` 中对应的补丁，在 `test/event-release-sync` 分支验证后再合并。测试分支不会更新 `patched` 或创建 Release。不会自动猜测或覆盖上游对相关功能的修改。

### 事件唤醒与失败恢复

- 本仓库已支持 `repository_dispatch`，事件类型为 `upstream-stable-release`，`client_payload.repository` 必须为 `2dust/v2rayN`。该信号只唤醒 Action，Action 会独立从 GitHub 验证最新正式版和其实际提交，不信任传入的 tag。现未安装外部通知中继；真正由上游发布立即触发，需要上游维护者配置 Release webhook，或由有授权的通知服务发出此信号。
- 发布遇到 API 错误时，先回查写入是否已生效，不覆盖或删除现有附件。下次检查发现有效草稿时，只继续发布；如果缺附件，只使用原 Actions 构建产物补齐，不重新构建。对没有可核验记录、校验不符、过期产物或未完成附件，任务停止并保留草稿供检查。

上游作者：2dust 与 v2rayN 贡献者。代码沿用 [GPL-3.0](LICENSE)。
