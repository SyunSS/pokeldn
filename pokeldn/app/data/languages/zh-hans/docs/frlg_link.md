---
title: GBA 链路及其承载的功能
parent: FireRed and LeafGreen
nav_order: 1
---

# GBA 链路及其承载的功能

在零售版硬件上测得，或从以下项目读取：[pret/pokefirered](https://github.com/pret/pokefirered).

# RFU 链路层

## 父端每次轮询仅接收一个子端槽位

`RfuMain2_Parent` 在每次轮询中仅将一个子端槽位保留到 `gRfu.childRecvBuffer[i]`，并检查其滚动的 `childSendCmdId` 标签是否为上次保留的 `+1 mod 8` [link_rfu_2.c:876-892]。错误标签会递增 `numChildRecvErrors[i]`; `> 4` 调用 `RfuSetErrorParams` 并终止链路；正确标签会将其重置，因此需要连续五次错误轮询才会断开。一次轮询内的第二个槽位相当于丢失一个标签。在零售版《火红》走入交换房间时，按不同发送速率实测：

| 子端发送方式 | 主机停止轮询的时间 |
| --- | --- |
| 自由运行（约 57 次／秒，对方约 55 次／秒） | 开始行走后 0.10 秒 |
| 每次轮询 2 个槽位 | 开始行走后 0.28 秒 |
| 每次轮询 1 个槽位 | 开始行走后 5.8 秒 |

每次轮询一个槽位时，所有标签均按顺序，`numChildRecvErrors` 从不递增；该速率下行走可以到达座位，因此 5.8 秒处的停止并非由标签检查引起。

没有任何例外，包括走向座位的过程。

## 父端表的第 1 行是主机自身命令的镜像回传

在任何活动中，主机发送期间的所有停滞都受此规则支配。

`MGL_Send` 按 252 字节分块，并在每个分块之前及传输结束时等待 `MGL_HasReceived(link->sendPlayerId)` [mystery_gift_link.c:176,205]。`sendPlayerId` 是主机自身的 ID 1 [mystery_gift_client.c:33]，因此它会一直等待，直到自身数据块通过父端 `gRecvCmds` 的第 1 行完整返回，也就是主机端镜像回传的副本。`RfuHandleReceiveCommand` 会为每位玩家重组数据块，包括子端自身 [link_rfu_2.c:1125]，而 `RfuMain1_Child` 将 `gRecvCmds` 从父端表填入，其中也包括自身所在行 [:970]。

RFU 数据块发送方等待同一个镜像：`HandleBlockSend` 保持 INIT，直至看到其镜像，`SendLastBlock` 重复最后一个片段直到收到镜像，随后将镜像位掩码中缺失的每个片段重新入队 [HandleSendFailure, link_rfu_2.c:1366-1416]。主机无法指定缺失片段；它会重发全部内容。

`rfu_leader.ChildEcho` 遵循两条规则：

-
-

子端每收到一个父端帧便发送一条命令（`childSendCount` 仅在 `recv.newDataFlag` 时递增 [link_rfu_2.c:600]），因此镜像队列不会自行增长。

## 移动一格恰好需要 16 次链路更新

`FacingHandler_DpadMovement` 设置 `objEvent->directionSequenceIndex = 16`; `MovementStatusHandler_TryAdvanceScript` 在忽略按键期间，每次链路更新将其减一（`MOVEMENT_MODE_FROZEN`）[overworld.c:3432-3470]。连续 N 次方向键会消耗最后一步中的 `N mod 16`，因此脚本化行走的间隔只需要 `16 - (N mod 16)` 次更新；超出的更新每次只会多耗一个槽位，没有其他代价。

## 玩家输入并非总会被传输

`UpdateHeldKeyCode` 会将 EMPTY、四种 DPAD 代码、START 和 A 改写为 `LINK_KEY_CODE_NULL`，条件为 `GetLinkSendQueueLength() > 1` [overworld.c:2786-2810]，而 `SendKeysToRfu` 不发送任何内容：受到队列压力的行走玩家看起来像停在原地。`LINK_KEY_CODE_READY`（0x16）不受影响，因此应以 0x16 为门控，绝不能以未出现 DPAD 代码为依据。

## 座位是双向同步屏障

`Task_EnterCableClubSeat` 显示“请稍候”，调用 `SetInCableClubSeat()`（下一次持续按键发送会变成 `LINK_KEY_CODE_READY`），然后循环等待 `GetCableClubPartnersReady()` [cable_club.c:827-869]，后者只有在 `AreAllPlayersInLinkState(PLAYER_LINK_STATE_READY)` 时才成功 [overworld.c:2988-2999]。随后 `Task_StartWirelessTrade` 运行 `SetLinkStandbyCallback()` [cable_club.c:910-943]，这就是就座后待机轮次的来源。必须等双方玩家都为 READY 才驱动这些轮次；对仍处于 `CABLE_SEAT_WAITING` 的主机驱动这些轮次，会使其座位状态机出错。

## 真实子端从头到尾发送的内容

一台零售版法语《火红》作为子端连接主机端。顺序由协议固定；IDLE 次数取自一次交换：

```
IDLE x8
SEND_BLOCK_INIT w1=0x0011 x4   + 17 fragments      (LinkPlayer, 0x11 = 17)
IDLE x31
SEND_BLOCK_INIT w1=0x0009 x4   + 9 fragments       (trainer card)
IDLE x262   READY_EXIT_STANDBY w1=0x0000 x1
IDLE x72    READY_EXIT_STANDBY w1=0x0001 x1
IDLE x45    <room: SEND_HELD_KEYS 0x1b x24, EMPTY, 0x1a once, the walk, READY, then EMPTY x13>
IDLE x22    READY_EXIT_STANDBY w1=0x0002 x1
IDLE x28    READY_EXIT_STANDBY w1=0x0003 x1
IDLE x75    -> the host pulls the party
```

-
-
-

## 双方只有收到对等端消息后才会推进

`CB1_UpdateLinkState` 运行 `UpdateAllLinkPlayers`，条件为 `!IsRfuRecvQueueEmpty()`；若任一 `gRecvCmds` 条目非零，该检查返回 FALSE [link_rfu_2.c:787-800]。`MoveSendCmdToRecv` 将父端自身的 `gSendCmd` 复制到 `gRecvCmds[0]`，因此父端可以自行维持循环；实际运行中，循环会稳定为每个往返一次交换。

主机端 `SEND_HELD_KEYS` 的高字节为 `heldKeyCount`，每准备一条命令递增一次，因此最后的值可计出其交换房间存续期间的链路更新次数。

## 就座后的待机门控与走出房间

双方就座后，主机在镜像回传主机端消息之后，会以 mpId 0 广播自身的 `READY_EXIT_STANDBY` count=2（某次记录的交换中晚了 130 毫秒）。它仅在子端计数与自身计数相等时才接受（`Rfu_LinkStandby` 接收门控，link_rfu_2.c:1577-1591），因此在主机端 count=2 的镜像返回时发送 count=3 会被忽略；镜像只证明父端看到了该槽位。应以主机端自身的 mp0 count=2 为条件启用 count=3，并持续重新触发，间隔需超过主机端在 `BufferTradeParties` (`HostTradeTiming.entry_final_standby_quiet_frames` 之前的静默窗口，即 75 个槽位，长于子端对 `READY_EXIT_STANDBY` 的 60 帧重发周期 [link_rfu_2.c:1529]）。

走出房间：主机端发出 `LINK_KEY_CODE_EXIT_ROOM`（0x17），并阻塞在 `KeyInterCB_WaitForPlayersToExit`，直至 `AreAllPlayersInLinkState(EXITING_ROOM)` [overworld.c:2962-2981]。子端必须通过持续按键流回复自身的 0x17；全零槽位不是按键。

## 离开房间

玩家在就座前或对战后走出交换中心时，主机会发送持续按键 `0x17`（EXITING_ROOM），并停在“请稍候”，直到每位玩家都发出该按键 [KeyInterCB_WaitForPlayersToExit, overworld.c:2977]。主机端会在 `0x17` 中以及 `H_ENTRY_SEAT`, `H_RETURN_FIELD` 和对战状态中（`host_trade._child_send_held_keys`）回复自身的按键。一台零售版《火红》在主机端仍走向椅子时离室，会一直停在“请稍候”，直到 `H_ENTRY_SEAT` 也回复。

### 静默门控

当主机已有 `QUIET_GATE_SECONDS`（0.25 秒）未发送任何内容时，主机端丢弃自身重传，但每隔 `QUIET_RETRANSMIT_SECONDS`（1 秒）仍发送一次，因此等待某帧的主机仍能收到它，即使该帧被主机端的缺口防护（`HOST_OUTSTANDING_MAX`）暂扣（`tests/test_host_quiet_gate.py`).

## 交换后取消

`BufferTradeParties` 在礼物奖章交换后清除已接收数据块标志 [trade.c:1549]，此时尚未由 `Leader_ReadLinkBuffer` 读取菜单命令 [1593-1633]。在该交换期间完成的取消请求，可能尚未设置伙伴选择便被清除。领队自身的 `REQUEST_CANCEL` (`0xEEAA`）证明它正在处理取消输入 [2049]。`bin/frlg_trade_join.py` 在完成配置的交换并选择取消后，会在领队的请求到达时再次发送自己的 `REQUEST_CANCEL`（`pokeldn/frlg/link/trade.py`, `_on_linkcmd`). `BOTH_CANCEL_TRADE` 在退出待机轮次之前清除所有待处理请求。

跟随端在实时菜单中确认“是”后发送 `REQUEST_CANCEL`，显示“正在等待朋友”，然后空闲等待 `BOTH_CANCEL_TRADE` [trade.c:2049, 1643]；玩家已选择取消的领队在读取该消息时应答 [1715-1722]。主机端会立即回复主机在最终菜单中的 `REQUEST_CANCEL`。

## 单方取消会使双方返回菜单

`PLAYER_CANCEL_TRADE` / `PARTNER_CANCEL_TRADE` 经过 `CB_HandleTradeCanceled` → `CB_MAIN_MENU` [trade.c:2094-2113]；只有 `BOTH_CANCEL_TRADE` 才会结束会话 [1715-1722]。加入端重新进入 S4_PARTY，60 帧后再次选择。回复 `REQUEST_CANCEL` 时使用 `PARTNER_CANCEL_TRADE` 会使主机反复显示“你的朋友想交换宝可梦”；`bin/frlg_trade_host.py` 会用 `BOTH_CANCEL_TRADE` 回复第一条消息，进入退出路径。领队自身的选择不发送任何内容（`SetReadyToTrade` [trade.c:1811-1828]）；它的取消会以 `REQUEST_CANCEL` 发送给每位玩家 [trade.c:2049]。一个先发送 `READY_TO_TRADE` 的加入端，在领队第一次取消时会显示 `PLAYER_CANCEL_TRADE`；`bin/frlg_trade_join.py` 随后在菜单中取消，因此领队第二次取消会结束会话。

## 链路中的版本与语言

`IsTryingToTradeAcrossVersionTooSoon` [union_room.c:1499] 仅在伙伴既不是《火红》也不是《叶绿》时触发，并只打印消息而不丢弃链路；FR↔LG 交换已在硬件上验证可用。`ConvertInternationalString` 对日语名称做特殊处理；法语《火红》可以接收英语神奇卡片。联盟交谊厅的 `Task_SearchForChildOrParent` 会跳过日语候选项 [union_room.c:3726]。神秘礼物使用 `Task_ListenForCompatiblePartners`，其兼容玩家检查依赖序列号与广播名称标志，不包含该语言过滤。日语卡带接受不同的神奇卡片和神奇新闻活动编号（[日语版布局](frlg_rom_map.md#japanese-layout)).

玩家在神秘礼物朋友列表选择 pokeldn 后，主机在 GameData 中发送其 ROM 游戏代码。主机端会在投递之前选择该卡带的地址和卡片布局。GUI 在“基本”页面的版本旁显示自动检测的语言。

## 模拟器可自行关闭链路

`HandleLinkConnection` 仅在 Switch 构建中运行 `svc_51` [link.c:1654]：

```
#if REVISION >= 0xA
    if (svc_51())
    {
        ...
        CloseLink();
    }
#endif
```

`svc_51` (`swi 0x51`）由模拟器应答 [sloopsvc.c:120]。非零表示 `CloseLink()`，然后在 `RfuSoftReset()` 下执行 `Task_MysteryGift`，否则 `RfuReloadSave()` [link.c:1674]：Switch 错误 2318-0006。如果主机端 RFU 层正常却仍断开，则问题指向 LDN／Pia。

| SVC | 调用位置 | 作用 |
| --- | --- | --- |
| `swi 0x45` | librfu_rfu.c:667,749 | 向模拟器传递 `gRfuLinkStatus` |
| `swi 0x49` | AgbRfu_LinkManager.c:657 | 非零时，在 SEARCH_CHILD 期间保持 `connect_period` 开启 |
| `swi 0x4a` | AgbRfu_LinkManager.c:720 | 同上，但发生在 SEARCH_PARENT 期间 |
| `swi 0x4b` | link_rfu_2.c:2114, union_room_player_avatar.c:518 | `SVC4B_EXIT_EARLY` 从 SpawnGroupLeader 提前退出；`SVC4B_RESEED_RNG` 根据主机端训练家 ID 重新播种 |
| `swi 0x51` | link.c:1654 | 立即关闭链路（神秘礼物中软复位） |
| `swi 0x53` | wireless_communication_status_screen.c:328 | 由模拟器驱动退出状态画面 |

# 本游戏实际使用的无线层

## 广播的速率集

如果关联响应中没有 6、9 和 12 Mbit/s，无论处于哪个链路阶段，主机都会在关联后 2.9 至 3.9 秒、Pia 会话已完成建立之后离开 LDN 网络：76 次此类首次关联中有 42 次离开，而包含这些速率的 284 次中无一离开。缺少 Pia 类型 2 Join Response 也会在相同时间导致离开（[主机作为 Pia 子端](#the-console-as-a-pia-child)）。以下来自 360 次主机端托管《火红》和《叶绿》会话的空口抓包，统计每次运行的首次关联，以及主机是否在 6 秒内离开：

| 关联响应 | 信标 | 主机关联请求 | 约 3 秒时离开 | 保持连接 |
| --- | --- | --- | --- | --- |
| 含 6、9、12 | 包含 | 包含 | 0 | 139 |
| 含 6、9、12 | 包含 | 不含 | 0 | 84 |
| 含 6、9、12 | 不含 | 包含 | 0 | 26 |
| 含 6、9、12 | 不含 | 不含 | 0 | 35 |
| 不含 | 不含 | 不含 | 42 | 34 |

只交替改变响应的速率集：含这些速率时 20 次中 0 次离开，不含时 8 次中 4 次离开。失败的速率集为 `1B 2B 5.5B 11B 18 24 36 54`（无 6、9、12、48）；主机究竟需要其中哪一种尚不清楚。ESP32 softAP 的关联响应携带全部十二种速率（[hardware_esp32.md](hardware_esp32.md)，接入点的帧）。

主机端广播 Switch 速率集（1B 2B 5.5B 11B 6 9 12 18，扩展速率为 24 36 48 54）。Switch 的其他信息元素（DTIM 2、ERP、能力值 0x411、任天堂厂商元素、HT／HE、WMM）均非必需。主机根据信标构造关联请求中的速率，因此信标头携带元素 0（SSID）、1（支持速率）和 3（DS 参数），共 41 字节的子集。含 WMM 的信标会让主机发送 QoS 数据帧（子类型 8），主机端必须解码；随项目提供的 LDN 解码器将 TID 纳入 CCMP nonce 和 AAD。`host_pia` 单播类型 5 Update Session。若探测响应设置隐私能力却不含 RSN，主机的关联请求将得不到应答。

## 主机作为 Pia 子端

-
-

托管神秘礼物的主机向接收客户端发送的序列，从其 Net 0x11 开始：

```
0.000  Net 0x11 (once)
0.006  client: Net 0x12 + Session join
0.252  RTT request, then every 316ms (6 probes, nothing else)
2.038  Session type 5, no type 2 ever
2.040  client: type 6 (finalize); 2.159 reliable open
2.318  host 'A' frame
4.63   host's own NI (join status = the player's YES on the console)
6.82   SEND_PLAYER_IDS, 6.87 BLOCK_REQ (2.2s after the YES)
8.15   Net 0x50 property update every ~0.5s, acked 0x51
```

## 离开 Pia 会话

主机子端在其 RFU `D` 帧后分三步离开：暂停、发送 Session 类型 3 离开请求，然后进行 LDN 取消身份验证（原因 3）。在未回复类型 4 的 33 次主机端托管交换和神秘礼物抓包中实测：

| 间隔 | 实测值 |
| --- | --- |
| `D` 到首次类型 3 | 1.97–2.02 秒 |
| 类型 3 之间，共发送四次 | 0.48–0.54 秒 |
| 首次类型 3 到离开 LDN | 2.03–2.08 秒 |
| `D` 到离开 LDN | 4.02–4.08 秒 |

```
type 3, 22 bytes:  03 | random u32 | constant id (8) | variable id (2) | kind 0 | IPv4 | port
type 4, 15 bytes:  04 | random u32 | the request's constant id and variable id
```

偏移位于 GBA 应用的 `main` 中，相对于镜像起点。`LeaveMeshJob` 在 `0xcacf4` 发送请求，截止时间为 500 毫秒，而 `WaitLeaveResponse` (`0xcaf38`）会在任务响应标志 `+0x99` 置位时结束，否则每到截止时间，只要其计数不超过 2 就重发（`0xcb06c`.. `0xcb08c`）：总共四次发送，然后任务完成，站点离开网络。Session 分发器的类型 4 分支（`0xba028`，表 `0x180fc9`）会对一条 15 字节消息设置该标志，前提是偏移 5 处的常量 ID 和偏移 13 处的变量 ID 都属于站点自身。主机端的类型 3 处理函数（`0xbf2d4`）接受 22 或 34 字节（种类 1 携带 18 字节地址，`0xbf3ac`），并回复 15 字节：类型 4、一个新随机字，以及请求的第 5 至 14 字节（`0xbf454`..`0xbf4e4`）。主机端以该格式回复每个类型 3（`pokeldn.ldn.host_pia.HostPeerProtocol`），采用单播，头部为 `(console variable, 0x00C6)`，使用向该主机发送其他单播数据包的同一计数器编号。在同一站点的单播数据包编号已达到 6203 后，零售版《火红》忽略了编号 560 至 573 的四个类型 4（四个类型 3 全部发出，并在首个类型 3 后 2.05 秒离开）。改用单播计数器编号后，第一个类型 4 就被接受（只发送一个类型 3，0.07 秒后离开 LDN）。主机自身的数据包对每个目的地各有一个计数器（发往主机端变量和变量 1）。

首个类型 3 之前的暂停，是 GBA 应用网络管理器中固定的 120 tick 倒计时，与主机端无关。管理器每秒计 60 tick（其超时将 tick 计数器 `+0x2774` 与秒数乘 60 比较，`0x4ff64`）。子端的 `TryDisconnectRfu` 在其 `swi 0x44` 之前发出 `rfu_REQ_disconnect` 发送 `D` [link_rfu_2.c:1446-1455, 983-985]；`LinkRfu_Shutdown` 也会发出它 [link_rfu_2.c:625]。其处理函数 `0x58b0c` 通过管理器槽位 `0x68` (`0x53d98` -> `0x4f0ec`、字段 `+0x730`）提交断开请求 1。逐 tick 更新 `0x4ee34` 将请求 1 转为倒计时 `+0x734 = 0x78` (`0x4ef00`），每 tick 减一，归零时调用管理器槽位 `0x78` (`0x4ef60`；子类 `0x53328` 通过 `0x4f0b4`）将状态设为 1。下一次更新（`0x5392c` -> `0x536f0`）调用 `Session::LeaveAsync` (`0xb1060`，位于 `0x537e0`），离开任务的第一步发送类型 3（[pia.md](pia.md)，离开会话）。

从网络收到的任何内容都不会缩短倒计时。只有断开请求 2 或 3（`swi 0x42`，或 `swi 0x43` 且 PID 为零），或 Pia 错误、超时已经设置断开原因 `+0x277c` 时，倒计时才会提前结束（首先在 `0x4ee64` 中检查；通过 `0x4f020` 设置，来源为 `0x5110c`, `0x52470` 和 `0x53440`）。倒计时代码不检查角色。

## 802.11 行为

-
-

## Pia 头部 nonce 是主机强制检查的计数器

主机为每个通道保留上次接受的 8 字节头部 nonce（大端序），丢弃所有不严格大于该值的数据报，因此随机 nonce 约有一半能通过：

```
random nonce:   ~1.1 duplicate outgoing reliable deliveries per unique frame, ~0.3 inbound
counter nonce:  0.34 outgoing, 0.00 inbound
```

`Sim._next_nonce` 和主机端都使用计数方式。

## 前向携带

每个可靠帧会在后续 4 个数据报中重复携带，在首次发送后约 17 毫秒得到确认。空口丢失率为 1–2%，且呈突发性（主机自身每帧重传率为 0.01–0.02）；Pia 按顺序交付，缺口会阻塞所有后续槽位，直到缺失帧重传，然后将它们一并交付，溢出主机深度为 8 的 RFU 接收队列。carry 为 0 时，一个父端槽位丢失并在 68 毫秒后重传，使十个槽位同时进入主机，300 毫秒后主机断开。主机端按序号去重。

## 主机确认延迟遵循 512 毫秒节拍

主机累计确认位于 CTRL 帧载荷中（`parse_bulk_ack`）；可靠头部的 `ack` 字段是发送方自身尚未确认的最低序号。

主机每次停滞 50–70 毫秒：入站流量暂停 35–70 毫秒，而基线为 15 毫秒；它重传自己的最后几个帧，随后累计确认跨越数帧：

```
26.553 in   D1849 D1850 ACK next=919
26.587 OUT  D919 D920 ACK next=1851
26.617 in   D1849* D1850*        (retransmits, no ack)
26.653 in   ACK next=924         (catches up five frames at once)
```

在两款卡带、三种活动的 42 个间隔中，每个周期都是 512 毫秒时隙的整数倍，误差在 16 毫秒（一帧）内。观察到的周期为 16 和 17 个时隙，另有一次 18 和一次 33，表明跳过了一个 tick。该时间网格与加入 LDN 的时刻锁相：103 秒内十二次停滞的相位跨度仅 18 毫秒。空闲聊天链路上，未确认数量达到 5 也无妨；神秘礼物或交换负载下，停滞会落在已满的发送窗口上。ROM 中没有 512 毫秒 tick，因此该定时器属于模拟器或 Pia／LDN 层；其具体用途仍未知。

## ident-25 停滞：缺口叠加无界积压

主机可能在最后一个投递脚本块（ident 25，`MG_LINKID_RAM_SCRIPT`）后进入空闲，始终不发送 ident 20（READY_END），然后离开。父端数据块从不被镜像回传，因此丢失片段在抓包中不可见。

无界积压前面的缺口补齐后，主机会一次性将所有积存帧交给游戏，深度为 8 的 RFU 队列会丢弃 ident-25 片段，画面停在“传输中……”，但链路仍连通。一次实测停滞中，连续两帧丢失，累计确认停滞 1.75 秒；期间主机端每个数据报都重发这两帧（约 100 份副本），并向每个数据报添加五个新帧，最终 97 个帧在一个数据报中抵达游戏，主机在“传输中……”停留了 150 秒。99% 的确认中，正常确认延迟为 0–1 帧。

`HostSession` 在有 `HOST_OUTSTANDING_MAX`（6）帧未确认时暂缓新帧，持续重传缺口，待确认追上后恢复，因此补齐缺口后最多释放 6 帧。`--ram-script-block-repeat 3` 将 ident-25 数据块发送三次：5 次会话全部投递成功。使用 `--block-repeat 1` 时，唯一一次实测《叶绿》会话在 ident 25 停滞。片段究竟丢于空口，还是主机从 RFU 向游戏交付的环节，尚不清楚。

## 收到卡片后在传输阶段断开

先出现 250 毫秒至 3 秒的发送停滞，随后无确认，再随后每个 tick 重发所有未确认帧，最终使卡片之后的会话断开：主机端 UDP 输出峰值每 0.25 秒达 52–519 个数据报，而完成的会话为 23–36 个。主机端的以下防护默认全部启用：

-
-
-

## 数据报滞留在套接字与空口之间

主机端数据报在发到空口前滞留 0.1–1.1 秒（一次实测对战中，71 帧在 200 毫秒内作为一个突发释放），足以使游戏进入链路丢失路径并显示“连接错误，请靠近一些”[link_rfu_2.c:2312 → CB2_PrintErrorMessage, link.c:1521]。在 ESP32 板上，四次《火红》交换中，从套接字到确认的最长等待为 265 毫秒，发生于板载发送队列（[ESP32 无线设备](hardware_esp32.md)，TX_DONE）。

# 联盟交谊厅

## 出现在列表中：广播活动字节

搜索中的主机，仅当候选项广播的活动位于所搜联机组的接受列表中时才保留它 [`IsPartnerActivityAcceptable`，union_room.c:1590；`sAcceptedActivityIds`，src/data/union_room.h:398-456]；大多数列表仅有一个 ID。联盟交谊厅中的主机广播 `ACTIVITY_SEARCH`（12），并搜索 `LINK_GROUP_UNION_ROOM_INIT`，列表为 `{ACTIVITY_SEARCH, 0xFF}` [src/data/union_room.h:419]，因此交换主机端（`ACTIVITY_TRADE`，4）或神秘礼物主机端（`ACTIVITY_WONDER_CARD`，21）仅凭该字节就会被过滤。房间内的搜索为 `LINK_GROUP_UNION_ROOM_RESUME` [union_room.c:2664]：`IN_UNION_ROOM | activity`, `IN_UNION_ROOM = 1 << 6` [include/constants/union_room.h:49]。

记录的字节 16 是活动：21 会让主机端出现在神奇卡片画面，22 则出现在神奇新闻画面，主机会加入并完成会话。

## 连接：必须恰好且仅为 IN_UNION_ROOM

`IsPartnerActivityIncompatible` [src/link_rfu_2.c:2925] 检查

```
else if (partner->activity != IN_UNION_ROOM)   // [link_rfu_2.c:2933]
    return TRUE;
```

是否严格相等。`IN_UNION_ROOM | ACTIVITY_TRADE`（0x44）会生成角色，但与其交谈时显示“正在与 POKELDN 通信”，然后是“训练家正忙”，空口上没有任何数据包：连接在 `Task_TryConnectToUnionRoomParent` [link_rfu_2.c:2963] 内被拒绝。交换意图位于 `sPlayerCurrActivity` 中，在链路建立之后协商。单独的 `IN_UNION_ROOM`（0x40）可以连接。角色实时跟随信标：主机端重启时，它会走出去再走进来。

## 没有父端 NI，以及五帧规则

联盟交谊厅子端不期待父端加入状态 NI：其名称 NI 一旦成功 [AgbRfu_LinkManager.c:1203]，`LinkManagerCB_UnionRoom` [link_rfu_2.c:2526] 就设置 TYPE_UNI 接收缓冲区，绝不设置 TYPE_NI，而 `Task_UnionRoomListen` [link_rfu_2.c:533] 将 `Task_PlayerExchange` 作为 MODE_CHILD 启动。只有交换中心回调 [link_rfu_2.c:2364] 会添加 TYPE_NI 缓冲区。

NI 正文会导致致命错误。`rfu_STC_NI_receive` 在没有游戏缓冲区时也接受 LCOM_NI_START [librfu_rfu.c:2202]，但正文需要缓冲区：`rfu_STC_NI_initSlot_asRecvDataEntity` 以 ERR_RECV_BUFF_OVER 失败 [librfu_rfu.c:2300] → `recvErrorFlag` → REQ 错误 → `LMAN_MSG_REQ_API_ERROR` → `RfuSetErrorParams` → “连接错误，请靠近一些”[link_rfu_2.c:2585]。`RFULeader(skip_parent_ni=True)` 由 `--union-room` 启用后会跳过它。

主机会在第五个未应答的父端帧到来时断开（三次抓包一致）：

```
child NULL 28.361  host NI ts=8..12, K only   D 28.496   (NI_STARTs ts=6,7 were mirrored)
child NULL 34.069  host NI ts=8..12, K only   D 34.199
child NULL 36.527  host UNI ts=6..10, K only  D 36.628
```

从子端 NULL 起计：135／130／101 毫秒；第三次因少了两个镜像而提前两帧，与 `maxMFrame = 4` 一致 [link_rfu_2.c:128]。已完成的交换中心抓包中，未应答最多为两个。

`--union-room-keepalive N`（120 可用）在 UNI 之前将第一个父端 NI_START 重复呈现 N 个 VBlank，因此主机始终有确认可发送。随后它等待约八秒：`Task_UnionRoomListen` 每帧重试 `rfu_UNI_setSendData`，而有 NI_START 待处理时会以 ERR_SUBFRAME_SIZE 失败：接收控制占用了子端 16 个 LL 帧字节中的 2 个 [librfu_rfu.c:2262]，而 UNI 子帧需要 16 个 [librfu_rfu.c:1449]。挂起接收只能由 `NI_failCounter_limit` 释放，时间为最后一个 NI_START 之后 480 帧 [link_rfu_2.c:139, AgbRfu_LinkManager.c:1328]（实测：首个 UNI 帧在主机端最后一次发送后 482 帧）。没有任何机制会提前释放它。

## 连接后主机的行为

[src/union_room.c:2858-2879]

```
if (gReceivedRemoteLinkPlayers) {
    CreateTrainerCardInBuffer(gBlockSendBuffer, TRUE);
    CreateTask(Task_ExchangeCards, 5);
    uroom->state = UR_STATE_COMMUNICATING_WAIT_FOR_DATA;
}
... then, if sPlayerCurrActivity == (ACTIVITY_TRADE | IN_UNION_ROOM),
    UR_STATE_SEND_TRADE_REQUST
```

提示为“POKELDN：你好，\<name>，有什么事吗？”，选项为打招呼／对战／聊天／返回。每个选项发送一条 `SEND_PACKET` 并等待 [UR_STATE_HANDLE_ACTIVITY_REQUEST, union_room.c:3151]：

| 主机发送 | 活动 | 主机端回复 |
| --- | --- | --- |
| 0x48 | CARD（打招呼） | 0x51 ACCEPT（接受） |
| 0x44 | TRADE（交换公告板） | 0x51 ACCEPT（接受） |
| 0x41 | BATTLE（对战） | 0x51 ACCEPT（接受） |
| 0x45 | CHAT（聊天） | 0x51 ACCEPT（接受） |
| 0x40 | EXIT（返回） | 视为主机请求关闭 |

每项活动结束后，双方都会 `SetLinkStandbyCallback` [union_room.c:2995, :3012]，主机返回提示菜单。Switch 构建还会通过 `svc_CommsAllowedByParentalControls()` 对接受方施加门控 [union_room.c:3159, :3037, REVISION >= 0xA]，因此主机自身的家长控制可能将其请求转为 DECLINE。打招呼会显示主机端的训练家卡片，然后回到菜单；返回会先发送 0x40，再发送 READY_CLOSE_LINK，收到应答后主机正常断开并留在房间内，不显示错误。

## 交换公告板

公告板列出广播中携带 `tradeSpecies`, `tradeType` 和 `tradeLevel` 的伙伴 [union_room.c:3400]：记录字节 18（`type << 2`), 19 (`gameClear | level << 1`，包装层的打包方式参见：[广播记录](frlg_rom.md#the-advertisement-record)）及 22:24（小端序的 `tradeSpecies:10`，属于 `RfuGameData` [include/link_rfu.h:107]）。种类 277（木守宫；仅看低字节则为 21，烈雀）会列为“POKELDN／一般／木守宫／26”，由此测定了字节 23。

交换公告板每条链路只进行一次交换。`Task_StartUnionRoomTrade` 在 `gMain.savedCallback = CB2_ReturnToField` 之前设置 `CB2_LinkTrade` [union_room.c:1744]，而 `CB2_SaveAndEndTrade` 仅在保存的回调为交换中心的 `CB2_StartCreateTradeMenu` 时保留链路 [trade_scene.c:2722-2725]；其他回调均以 `SetCloseLinkCallback` 结束。顺序为：主机的宝可梦块（count 9）、主机端的对应块、主机的邮件块（count 19）、主机端的对应块、动画、主机的 READY_FINISH、主机端的 CONFIRM_FINISH、保存同步屏障、双向 READY_CLOSE_LINK，最后正常断开回到房间。下一次公告板交换需要新连接。交换中心则返回其交换菜单 [trade.c:2094-2113]。这里没有队伍交换、菜单或房间行走路线。

## 聊天

聊天使用 `SendBlock`，绕过 `Rfu_SendPacket`：每位成员主动调用 `SendBlock(0, sendMessageBuffer, 0x28)`，无需 `BLOCK_REQ` [`ChatEntryRoutine_Join`，union_room_chat.c:429；`ChatEntryRoutine_SendMessage`，:823]。0x28 字节数据块为 `count` 4.

```
[0]      command: 0 NULL, 1 CHAT, 2 JOIN, 3 LEAVE, 4 DROP, 5 DISBAND
[1..8]   player name, PLAYER_NAME_LENGTH + 1 bytes, EOS-terminated
[9]      multiplayer id            (JOIN / LEAVE / DROP / DISBAND)
[9..39]  message text, EOS-terminated (CHAT)
```

[`PrepareSendBuffer_*`，union_room_chat.c:1256-1281；`ProcessReceivedChatMessage`，:1283]。0x45 被 ACCEPT 后，主机进入 `Task_StartActivity` 的聊天分支 [union_room.c:1938]，它仅停止新连接（`rfu_LMAN_stopManager(FALSE)`），保留现有链路。双方进入时都立即发送 JOIN，不等待对方；主机端响应主机的 JOIN。

一行有 15 个条目（`MESSAGE_BUFFER_NCHAR` [union_room_chat.c:21]；31 字节缓冲区允许 0xF9 字节对 [string_util.c:560]）。接收方会把收到的所有内容 [:1308] 复制到一条不裁剪的行中，因此第 16 个及后续条目会超出屏幕；主机端会在启动时拒绝过长的 `--chat-message` 或 `--chat-file` 行（`uroom_chat.entry_count`).

收到 LEAVE 时领队必须关闭：离开者会等待父端断开链路 [`ChatEntryRoutine_AskQuitChatting` 分支 2／4／5，union_room_chat.c:596-660]，否则停在“退出聊天？”画面。主机端在 LEAVE 后 0.1 秒发送 DROP，并执行关闭链路握手。追加到 `--chat-file` 的行在写入后约 1.7 秒到达主机。

## 联机对战（UR_BATTLE 0x41）

`HasAtLeastTwoMonsOfLevel30OrLower` [union_room.c:4565] 要求队伍中有两只不高于 30 级、且不是蛋的宝可梦，在主机发起时 [union_room.c:2923] 和接受时 [union_room.c:3176，发送 DECLINE] 检查；双方只检查自己的 `gPlayerParty`，拒绝时在屏幕显示消息。

双方各选两只宝可梦后，各自发送一个 0x20 字节块，首字节为 `ACTIVITY_ACCEPT | 0x40` = 0x51（取消则为 0x52），其余为零 [union_room_battle.c，`CB2_UnionRoomBattle`]；其他任何值都会以“拒绝”关闭链路。Switch 路径随后有两次链路任务等待，中间夹一次待机（`#if REVISION >= 0xA` 分支 50／51／52）。

`SetUpPartiesAndStartBattle` 保留选中的两只宝可梦，将其他四只清零，然后调用 `StartUnionRoomBattle(BATTLE_TYPE_LINK | BATTLE_TYPE_TRAINER)` [union_room.c:1811]，设置 `gLinkPlayers[0].linkType = LINKTYPE_BATTLE`（0x2211）[link.h:92]，而 `TryReceiveLinkBattleData` 会严格检查该值 [battle_controllers.c:520]。然后 [`CB2_HandleStartBattle`，battle_main.c:934]：

```
state 1  SendBlock struct LinkBattlerHeader {versionSignatureLo, versionSignatureHi,
         vsScreenHealthFlagsLo, vsScreenHealthFlagsHi, struct BattleEnigmaBerry}
state 3  SendBlock gPlayerParty[0..1]   200 bytes      state 4  recv -> gEnemyParty
state 7  SendBlock gPlayerParty[2..3]   200 bytes      state 8  recv
state 11 SendBlock gPlayerParty[4..5]   200 bytes      state 12 recv
state 15 InitBattleControllers
```

队伍交换采用与交换功能相同的 3 × 200 字节传输（`mon.party_blocks`; `Rfu_InitBlockSend` 允许最多 252 字节）。

### 主控端选定

联机单打对战中，只有 `BATTLE_TYPE_IS_MASTER` 一侧设置 `gBattleMainFunc = BeginBattleIntro`；另一侧保留 `BeginBattleIntroDummy` [`InitLinkBtlControllers`，battle_controllers.c:141；`SetUpBattleVars`，:45]。非主控端不执行回合结算、伤害或随机数计算：它接收 BUFFER_A 控制器命令、显示结果并回复，因此非主控角色下的主机端就是一个对战控制器。

`LinkBattleComputeBattleTypeFlags` [battle_main.c:886]，来自多人 ID 为 1 的主机：若 `gBlockRecvBuffer[0][0] == 0x100` 或双方签名相同，则玩家 0 为主控端；否则选择版本号最高且索引最低的玩家。小于 0x201 且不为 0x100 的签名会让主机成为主控端；主机端发送 0x200。

### 链路缓冲区协议

每条控制器命令都是一个带 8 字节头部的 SendBlock [battle_controllers.c:401-435]：`LINK_BUFF_BUFFER_ID, ACTIVE_BATTLER, ATTACKER, TARGET, SIZE_LO, SIZE_HI, ABSENT_BATTLER_FLAGS, EFFECT_BATTLER`，后跟载荷，存储为 `alignedSize = size - size % 4 + 4`（4 字节载荷占用 8 字节）。`bufferId` 0 = BUFFER_A（命令），1 = BUFFER_B（回复），2 = 清除执行标志，其单字节内容为发送方的多人 ID [Task_HandleCopyReceivedLinkBuffersData:566-594]。对战者 0 是主控端的宝可梦，对战者 1 是主机端的宝可梦。

同步规则 [battle_util.c:185-201]：`MarkBattlerForControllerExec` 设置位 `28+battler`；当命令数据块返回时，`MarkBattlerReceivedLinkData` 为每位玩家 i 设置 `gBitTable[battler] << (i*4)`，并清除位 28+battler；每位玩家用 bufferId 2 清除自己的半字节。主控端仅在 `gBattleControllerExecFlags == 0` 时推进，因此每条命令都必须为双方对战者进行确认。

56 条玩家缓冲区命令 [battle_controller_player.c:110] 中，以下命令除了确认还需要其他内容：

```
CONTROLLER_GETMONDATA    -> EmitDataTransfer(BUFFER_B, size, data)   [player.c:1515]
CONTROLLER_CHOOSEACTION  -> EmitTwoReturnValues(1, B_ACTION_*, 0)    [player.c:232-241]
CONTROLLER_CHOOSEMOVE    -> EmitTwoReturnValues(1, 10, move | target << 8) [player.c:342]
CONTROLLER_CHOOSEPOKEMON -> EmitChosenMonReturnValue(1, partyId, order)    [player.c:1316]
CONTROLLER_OPENBAG       -> EmitOneReturnValue(1, itemId)            [player.c:1340]
CONTROLLER_EXPUPDATE     -> EmitTwoReturnValues(1, RET_VALUE_LEVELED_UP, exp) [player.c:1051]
CONTROLLER_ENDLINKBATTLE -> gBattleOutcome = payload[1], then ack     [player.c:2876]
```

`B_ACTION_USE_MOVE` 0, `USE_ITEM` 1, `SWITCH` 2, `RUN` 3 [battle.h:34]。

第一条命令是 `GETMONDATA` `REQUEST_ALL_BATTLE` [battle_main.c:2519]，回复一个 0x58 字节的 `struct BattlePokemon` [pokemon.h:170]，构造方式与 `CopyPlayerMonData` 相同 [player.c:1519]；`statStages`, `ability`, `type1`, `type2`, `status2` 和 `unknown` 会重新计算，因此填零即可。对战者 0 的 BUFFER_B 回复可省略：主机会从 `gEnemyParty` 回复自身的 GETMONDATA [link_opponent.c:444]。

联机对战者可以逃跑 [battle_main.c:3239]，且处于最高行动顺序 [:3548-3560]，因此对首条 `CHOOSEACTION` 回复 `B_ACTION_RUN`，即可测试完整路径并结束对战。

### 反编译源码中看不到的两条规则

数据块大小不决定其处理路径。每个确认和短命令（包括第一个 `GETMONDATA`）都是 16 字节、两片段的记录，因此对战中应根据状态路由数据块，绝不能根据大小。

确认绝不能抢在所确认数据块的回显之前。主机仅在自身数据块返回时设置执行标志位 [`MarkBattlerReceivedLinkData`，battle_util.c:193]，而主机端的确认会清除此位 [battle_controllers.c:585]；两片段确认可能超越七片段回显：

```
104.268 console bufferA battler 0 PRINTSTRING (72 B)
104.366 host    ack battler 0                     <-- host's ack first
104.383 echo    bufferA battler 0 PRINTSTRING
```

随后回显又设置该位，主机将永远等待 `gBattleControllerExecFlags == 0`，而它对 `Cmd_waitmessage` 施加门控 [battle_script_commands.c:2041]，导致画面冻结在对战结束消息，链路仍连通。`HostTradeEngine._echo_owed` 会在任一子端命令仍等待镜像时暂缓新数据块。

确认还必须等待回显的每个片段。`rfu_leader.echo_blocks` 为每个已回显的 `SEND_BLOCK_INIT` 保存已发片段索引集合，确认等待 0..count-1 全部出现。等待回显队列完全为空会慢 24 倍；仅计数回显或只观察最后一个片段，都可能使重发片段的回显与确认处于同一帧。没有任何后续消息能解救等待 `gBattleControllerExecFlags` 的主机；结束主机端只能使它经错误画面返回房间。

### 节奏由 RFU VBlank 预算决定

与主机端进行联机对战时，双向每步均约需一秒。数据报周转时间中位数为 5.8 毫秒（8204 次回复的 p99 为 16.6 毫秒；主机自身中位数 8.1 毫秒）。连续的 `bufferA` 命令间隔中位数为 800 毫秒；主机数据块在 19 毫秒内得到回显，主机端的应答块再过 355 毫秒发送。`HostSession.tick` 每次调用发送一个 RFU 槽位，周期为 `HOST_VBLANK_SECONDS = 1/59.727` = 16.74 毫秒（实测 17 毫秒 × 5035 次、16 毫秒 × 413 次）；一个命令块跨越约二十帧，即约 340 毫秒，一个步骤还需加上返回方向耗时。硬件链路不会每个 VBlank 发送超过一个槽位。

## 两台真实主机的空口流量

对两台真实主机间的交换进行被动抓包（《火红》通过第三个 NPC 托管，《叶绿》加入）。监控捕获的帧数只是下限；802.11 序号计数器可得出监控漏掉的帧。同一台《火红》主机，按序号修正后的帧速率：

| 站点 | 与主机端通信 | 与真实主机通信 |
| --- | --- | --- |
| 火红主机 | 161.8／秒 | 25.5／秒 |
| 其对等端 | 58.9／秒，主机端每个 VBlank 一个槽位 | 6.1／秒，叶绿主机 |

25.5／秒这一数值来自捕获质量最弱的一次抓包。

通过直接联机角托管的《火红》主机会在 `application_data` 的偏移 0x11 处以明文 ASCII 携带 Switch 用户资料名称；广播中不包含游戏内训练家名称。

## 主机端步进速率与主机输出速率

`--tick-hz` 设置主机端每秒 RFU 槽位数（默认每个 VBlank 一个）。同一主机在每种速率下各进行一次交换：

|  | 59.727 Hz（默认） | 20 Hz |
| --- | --- | --- |
| 主机端发出的数据报 | 79.3／秒 | 39.3／秒 |
| 从主机收到的数据报 | 61.8／秒 | 51.8／秒 |
| 交换时长 | 92 秒 | 197 秒 |
| 整个会话的主机数据报数 | 5663 | 10218 |

20 Hz 时，主机速率降低六分之一，交换耗时从 92 秒增至 197 秒，主机发送的数据报反而增加 80%。默认值为每个 VBlank 一个槽位。

# 联机俱乐部竞技场

`frlg_trade_host.py --colosseum` 托管以下路径：宝可梦中心 2F → 第三个 NPC（无线俱乐部）→ 竞技场 → 单打对战 → 加入。只有 `CB2_ReturnFromCableClubBattle` 会递增神奇卡片的 `battlesWon` [src/cable_club.c:792]；联盟交谊厅对战通过 `CB2_ReturnToField`.

`Task_StartActivity` 对 `ACTIVITY_BATTLE_SINGLE` 的处理与 `ACTIVITY_TRADE` 相同 [union_room.c:1903]，区别仅在地图（`MAP_BATTLE_COLOSSEUM_2P`，坐标 (6, 8)，而非 `MAP_TRADE_CENTER`，坐标 (5, 8)）及一个 `HealPlayerParty()`，因此训练家卡片交换与 `--card-flag-id` 无需改动即可工作。有四处变化：

1.
2.
3.
4.

从 `CB2_InitBattle` 开始，与联盟交谊厅对战相同，包括签名 0x200，但不包含 0x20 字节的 0x51 选择块（`CB2_UnionRoomBattle` 独有）。

座位只需要 READY 按键：即使没有发送移动，主机也会进入 `Task_StartWirelessCableClubBattle` (`GetCableClubPartnersReady` 仅检查链路状态 [overworld.c:2989]）。没有就座后的待机轮次；等待这些轮次的主机端会死锁，而主机停在分支 3，发送 `SEND_BLOCK_INIT` count 3 和 `04 40 00 80 65 df | bb c8 ff 00 11 00 | 01 00 03 00 00 00`（版本 0x4004 火红、`lp_field_2` 0x8000、其训练家 ID）。该块到达便完成入场。

对战结束后，主机端同样必须发送退出按键：门口会在 `PLAYER_LINK_STATE_EXITING_ROOM` 等待所有玩家 [overworld.c:2977]，否则主机停在 *“正在引导离开房间，请稍候”*，直到链路报错。

## 竞技场对战是否计数的决定因素

弃权视为主机获胜：`HandleAction_Run` 为未逃跑的一方设置 `B_OUTCOME_WON`，并与 `B_OUTCOME_LINK_BATTLE_RAN`（1 « 7）做或运算 [battle_main.c:4300]；`HandleEndTurn_BattleWon` 在 `CB2_ReturnFromCableClubBattle` 据此执行分支前将该位清除 [battle_main.c:3734]。记录的 ID 为 `gLinkPlayers[GetMultiplayerId() ^ 1].trainerId` [cable_club.c:794]，来自 28 字节记录，每个 ID 仅计一次（每项统计记住五个）[mystery_gift.c:630]。对三个不同的 `--id` 值各弃权一次，可将 `battlesWon` 增至 3，对战计数卡便会奖励伤药。一次之后：

```
save 0x3434:  0100 0000 0000 2300    battlesWon 1, lost 0, trades 0, icon 35 CARD_TYPE_LINK_STAT
game data:    "1 battles won"
```

# 主机端的两项约束

关闭路径依赖缺口防护：`done` 来自断开路径，受 `disconnect_requested` 门控，该值由 `_tick_close_link` 在 `activity.tick()` 内设置，而 `HostSession.tick` 会在缺口防护生效时跳过它。主机停止确认会使防护锁定，因此关闭定时器停滞；确认退出后，一旦主机离开 LDN，运行时便停止。

全零的 `easyChatProfile` 会在训练家卡片上打印“??? ???”：词 0 是 `EC_GROUP_POKEMON_2` 的索引 0（`SPECIES_NONE`），它会被 `IsECWordInvalid` 拒绝，再由 `CopyEasyChatWord` 替换为 `gText_ThreeQuestionMarks` [easy_chat.c:166-171]。一个词的格式为 `(group & 0x7F) << 9 | (index & 0x1FF)` [easy_chat.h:1089]，每张卡片四个词 [trainer_card.h:28]；短语不足时用 `EC_WORD_UNDEFINED`（0xFFFF）填充，它不显示任何内容。
