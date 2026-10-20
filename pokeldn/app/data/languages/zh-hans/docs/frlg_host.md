---
title: 主机端实现
parent: FireRed and LeafGreen
nav_order: 7
---

# 主机端实现

`bin/frlg_trade_host.py` 是《火红／叶绿》直接联机角的领队：Switch 加入主机端的 LDN 网络，Pia 建立对等会话，Reliable 承载模拟的 RFU 父端链路，最终接入领队侧的交换状态机。 `bin/frlg_mg_host.py` 复用活动层以下的所有组件。

## 组件与归属

| 组件 | 负责内容 |
| --- | --- |
| `TradeRunConfig` | 不可变的运行配置：`TrainerProfile`, `TradePlan`, `LdnConfig`, `HostOptions` 或 `JoinerOptions` |
| `HostApplication` | 资源操作顺序：验证、启动传输、注入信标、事件循环、中断、清理；活动钩子提供消息和持久化功能，因此交换和神秘礼物共用此循环 |
| `HostTransport` | LDN AP、虚拟接口、参与者事件、UDP :12345；不解析 Pia |
| `HostPeerProtocol` | 一个对等端的 Pia 状态：Net、Session 接受、RTT、数据包 ID、nonce 选择、加密、成帧、Reliable 批处理；输出 `OutboundDatagram` |
| `HostSession` | Reliable + `RFULeader` + 活动引擎（`engine=` 选择交换或神秘礼物）；不使用套接字，也是离线端到端测试采用的边界 |
| `HostTradeEngine` | 领队入室、队伍与卡片交换、选择、确认、动画与保存同步屏障、取消、离室、关闭宽限期；`HostTradeTiming` 为各帧数命名 |
| `BeaconInjector` | 其原始监控套接字和工作线程 |

数据报依次流经 Switch、`HostTransport`, `HostPeerProtocol`, `HostSession`, `RFULeader`, `HostTradeEngine`（子端命令行输入、父端命令行输出），然后原路返回。定时器截止时间由对等端协议提供，因此 Net／Session 重试、RTT 探测、重传和约 59.727 Hz 的时钟步进均不依赖轮询延迟。

## 启动与会话建立

1.
2.
3.
4.

格式错误的 Pia、错误的填充、身份验证失败、Reliable 分块覆盖不完整以及 Session 身份不匹配都会被记录并忽略。只有当 Session 请求的常量 ID、Pia 变量、源 IP 和加密头部均与当前 LDN 对等端一致时，才会接受该请求。

## 交换与离室生命周期

```mermaid
stateDiagram-v2
    [*] --> PlayerExchange
    PlayerExchange --> RoomEntry: LinkPlayer and trainer card
    RoomEntry --> PartyExchange: seat route and entry barriers
    PartyExchange --> Selection: party, mail, ribbons
    Selection --> Confirmation: Switch selects; leader offers configured slot
    Confirmation --> Animation: both confirm
    Animation --> Save: trade committed
    Save --> PartyExchange: another configured trade
    Save --> MenuExit: final party refresh
    MenuExit --> RoomExit: both cancel; five-second field wait
    RoomExit --> CloseGrace: Switch confirms room exit
    CloseGrace --> Disconnect: fifteen seconds of peer traffic
    Disconnect --> [*]
```

最后一次交换结束后，主机端等待 Switch 显示交换菜单；玩家选择“取消”并确认“是”，主机端立即回复 `BOTH_CANCEL_TRADE`。主机端完成待机同步屏障，等待五秒后离室，除非 Switch 先行离开；Switch 确认关闭后（`READY_CLOSE_LINK`），主机端继续保持正常对等通信十五秒，然后将 RFU 断开连接加入队列。它使用类型 4 回复主机的 Session 离开请求（[frlg_link.md](frlg_link.md)，离开 Pia 会话）。发生 LDN 离开事件时，立即停止向对等端输出。

## 关闭与清理

断开连接后：如有接收到的宝可梦则保存，停止信标工作线程并等待其结束，关闭套接字和网络，清理 LDN 虚拟接口。正常完成、`KeyboardInterrupt`、部分资源分配后启动失败以及信标工作线程失败时，都会执行相同的清理。保存接收到的宝可梦与抓包日志相互独立。

无论交换、对战还是神秘礼物，所有主机端都会在主机离开 LDN 时停止（`HostApplication.run`）：未确认关闭时立即停止；已确认关闭时则等待 2 秒稳定期（`HOST_CLOSE_SETTLE_SECONDS`）后停止。`--end-on-success` 会在成功投递后的断开连接消息发出时停止神秘礼物主机端，无需等待主机离开；其 `--idle-timeout` 会在连续这么多秒未收到 Switch 通信后将其停止。

## 训练家资料的传递

`pokeldn.config.DEFAULT_TRAINER` 是默认身份。每个 CLI 都会为单次运行生成不可变的 `TrainerProfile` (`--ot`, `--version`、十进制 `--id TID[:SID]`），验证第三世代名称和数值范围，并据此生成所有表示形式：

| 表示形式 | 携带内容 |
| --- | --- |
| LDN 发现 | 名称和公开 TID |
| Pia Session | UTF-8 参与者名称 |
| LinkPlayer | `SID << 16 \| TID`、版本、语言、性别和进度标志；第三世代名称 |
| 训练家卡片 | 第三世代名称；主机端使用以下值填充：`0xFF`，加入端保留原生的 `0x00` |

## 故障处理

-
-
-
-
-
-

## 扩展主机端

应在能够理解某项行为的最低层添加它：设置放在运行配置中，操作系统与网络相关行为放在应用或传输层中，Pia 放在 `HostPeerProtocol` 中，RFU 放在 `RFULeader` 中，直接联机角决策放在 `HostTradeEngine` 中。通过各边界输出的数据报、载荷、帧或命令行测试该边界。

主机端服务一台 Switch。要支持更多对等端，每个对等端都需要自己的 `HostPeerProtocol`（各自的 Pia 变量、nonce、数据包 ID），还需要游戏层面的 RFU 策略；仅提高 LDN 参与者上限并不够。

## 源码索引

| 源码 | 职责 |
| --- | --- |
| `bin/frlg_trade_host.py` | CLI、配置、入口点 |
| `pokeldn/frlg/host_cli.py` | 共用的主机端 CLI 选项 |
| `pokeldn/frlg/link/host_app.py` | `HostApplication` |
| `pokeldn/frlg/config.py` | 训练家、交换计划、神秘礼物载荷、LDN、角色和运行配置 |
| `pokeldn/frlg/link/trade_runtime.py` | CLI 日志、队伍加载、槽位解析、输出保存 |
| `pokeldn/frlg/link/host_beacon.py` | 捕获的交换信标、发现数据修改、`BeaconInjector` |
| `pokeldn/host_support.py` | 面向操作系统的支持（兼顾 sudo 的密钥路径解析） |
| `pokeldn/ldn/transport.py` | `HostTransport` |
| `pokeldn/ldn/host_pia.py` | Pia 成帧、`HostPeerProtocol` |
| `pokeldn/frlg/link/host_session.py` | `HostSession` |
| `pokeldn/ldn/reliable.py` | Reliable |
| `pokeldn/gba/rfu_leader.py` | `RFULeader`：父端成帧、NI／UNI 握手、回显表 |
| `pokeldn/frlg/link/host_trade.py` | `HostTradeEngine`, `HostTradeTiming` |
| `pokeldn/frlg/link/linkplayer.py` | LinkPlayer 与训练家卡片编码器 |
| `pokeldn/ldn/ldntrace.py` | 可选 JSONL 诊断信息 |
