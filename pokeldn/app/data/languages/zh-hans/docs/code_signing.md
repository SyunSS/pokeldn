---
title: 代码签名政策
nav_order: 12
---

# 代码签名政策

免费代码签名由[SignPath.io](https://about.signpath.io)提供，证书由[SignPath Foundation](https://signpath.org)

桌面应用的 Windows 发行版，即`pokeldn-windows-x64.zip`（位于[发行版](https://github.com/Decryptu/pokeldn/releases)页面），会对本仓库源码构建的二进制文件附加 Authenticode 签名：`pokeldn.exe`、PKHeX 辅助程序`pokeldn-pkhex.exe`以及 Unicorn 库`unicorn.dll`。GitHub Actions 从本仓库的`v*`标签构建它们（[release.yml](https://github.com/Decryptu/pokeldn/blob/main/.github/workflows/release.yml)）；SignPath 仅签署该次构建产生的文件，不签署在其他地方构建的内容。构建产物配置位于[.github/signpath/artifact-configuration.xml](https://github.com/Decryptu/pokeldn/blob/main/.github/signpath/artifact-configuration.xml)。未经修改而随包附带的第三方文件保留其发布者自己的签名，或保持无签名状态。

## 团队角色

| 角色 | 成员 |
| --- | --- |
| 提交者和审查者 | [Decryptu](https://github.com/Decryptu) |
| 批准者 | [Decryptu](https://github.com/Decryptu) |

每个发行版签名请求都由人工批准。其他人的贡献只能通过提交者审查过的拉取请求进入仓库。

## 隐私政策

除非用户或安装、操作本程序的人明确要求，否则本程序不会向其他联网系统传输任何信息。它会发出的请求如下：

| 何时 | 目标 | 发送内容 |
| --- | --- | --- |
| 启动时，且“设置”中的“更新”处于开启状态（默认开启） | GitHub API 及每个已安装插件的更新地址 | 请求最新发行版；不包含玩家或其游戏的任何信息 |
| 玩家下载无线固件或活动团体战数据时 | GitHub | 下载请求 |
| 玩家使用“交换（在线）”或 GTS 时 | 公共 Nostr 中继（[在线交换](online.md)) | 加密的交换事件，包括提供用于交换的宝可梦 |
| 玩家安装或更新插件，或浏览插件来源时 | 该插件或来源的地址 | 下载请求 |

发往 GitHub 的请求受 GitHub 隐私声明约束。每个中继由其运营者自身的政策约束。应用不发送分析统计数据，也不发送崩溃报告。
