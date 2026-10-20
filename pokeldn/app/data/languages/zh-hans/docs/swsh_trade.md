---
title: 与零售版《剑／盾》交换
parent: Sword and Shield
nav_order: 3
---

# 与零售版《剑／盾》交换

《剑／盾》连接交换从交换快照到存档的完整过程。帧结构、内容注册和 PK8 见 [同步框架](swsh_protocol.md).

## 流程

```
1  the console broadcasts its 3456-byte snapshot on protocol 0x84, port 0
2  the client acknowledges the fragments (0x21) and the transfer (0x19 / 0x28)
3  the client sends its own snapshot on 0x84 port 1 and reports it complete
4  the trade screen opens
5  the console sends the 40030 RPC pair on 0x7C port 1, several times a second
6  the client answers the pair and sends `imReady` on 20030
7  the console offers a Pokemon on 20030; the client offers one on 10050
8  the player accepts (box command 4)
9  the confirmation ladder runs on content 40
10 the console writes its save
```

作为主机端的主机不会确认加入端在端口 0 上发送的快照；加入端快照应发送到端口 1。在其 0x84 得到响应之前，主机不发送其他内容，并无限重传。`pokeldn/ldn/broadcast4.py` 实现全部四种类型。

存档后的流程见 [托管交换](#hosting-a-trade) 和 [主机端迁移](#host-migration).

## 交换 RPC

ping、块消息和交换提议使用端口 0，40030 配对使用端口 1；发到错误端口的响应不会被读取。

```
id 40030 = 40000 + 30
  1  offset      30
  2  base        10000, and 20000 in the other member
  3  station id  the sender's, equal to the host_constant of the seat record
  4  clock       a counter advancing between messages
  5  bytes(4)    00000000 for the 10000 member, 000018fc for the 20000 one
```

`000018fc` 是哨兵值 `0xfc18` ([步骤消息体](#the-step-body)）。主机消息可以从解析字段逐字节重建（`pokeldn/swsh/trade.py`). `3e4e000012020801` 是携带 `imReady{isReady:true}` 的 20030。加入的客户端会发送它；作为主机端的主机随后显示提议的宝可梦供确认。尚未观察到主机端主机发送它。

-
-

## 主机端迁移

作为主机端的《剑》离开会话时，会在协议 0x18 的端口 1 上请求主机端迁移（`nn::pia::mesh::LeaveWithHostMigrationJob`):

```
0f 00 00 03 00 01 00 01   44 00 01
^ version 4's reliable header, sequence 1     ^ the mesh message
```

`44` 是 MIGRATION_START，`[0x44, host index 0, new host index 1]`：主机将客户端指定为下一主机端（`nn::pia::mesh::LeaveWithHostMigrationJob`）。被指定的客户端必须在网状网络端口 1 的可靠窗口上广播 `MIGRATION_FINISH`（[Pia 层](pia.md#host-migration)).

使用 `--answer-migration --update-mesh` 时，客户端发送完成消息，并以新的主机端索引发布网状网络更新。移交后是否能够保留会话尚未验证。

零售版《剑》主机端在以下两种情况下发送一次 MIGRATION_START：

| 时间 | 条件 |
| --- | --- |
| 其盒子命令 3 之后 0.8 s | 交换完成后 |
| 玩家接受后几秒，在主机使用以下消息拆除会话之前：`2-ALZAA-0016` | 确认阶梯开始前失败的交换，加入端未发送任何确认命令 |

`bin/swsh_host.py --migrate` 使用盒子命令 3 和 MIGRATION_START 结束其托管的交换；模拟《盾》加入端随后在保存后显示通信中断消息。默认情况下，主机端保留会话。

## 托管交换

`bin/swsh_host.py` 负责托管，`pokeldn/swsh/host_trade.py` 像《剑》主机端一样引导流程。零售版法语《剑》1.3.2 和模拟《盾》1.3.2 都能加入并交换。以下细节来自两个模拟《盾》1.3.2 之间的交换。

主机端以新的网络 id、设备 id 和账户 uid 构建站点广播。在 0x84 上，它确认加入端的三个快照分片，使用自身训练家身份和 `--offer-file` PK8 重写该实时快照，然后在端口 0 上发送结果。主机端将主机提议的 PK8 写入 `--received`. `--advert FILE` 和 `--snapshot FILE` 保留已保存记录路径，以便比较。

主机端一侧的站点握手：

```
joiner -> host   connection request, [1] a random byte per request
host   -> joiner ack (05 000000 and the request's trailing id)
host   -> joiner its own request, the joiner's [1] at [0x10]
joiner -> host   ack, then its connection response
host   -> joiner ack, then its response
```

如果没有确认，加入端会重复请求，且从不响应主机端的请求；不匹配的 [0x10] 会被忽略。加入网状网络后，加入端每两秒发送 Sync Clock（0x1C），并发送一次 Clone Clock（0x77）；主机端分别回复请求中的 tick 与毫秒单位的网状网络时钟，以及 01、请求字节 1 至 9 和毫秒单位的克隆时钟。

应用层，在双向完成 [ping 握手](swsh_session.md) 之后：

```
0x84  each side's snapshot on the port of its station index, the joiner's on port 1 and the
      host's on port 0, each acked on the same port; `host_trade.py`
      builds its own from the joiner's and sends it second, a retail host sends first
110   the joiner pings first once its trade screen is up; the host answers with its own ping
      and the reply (a host ping before that screen is acked and dropped)
30    the host opens content 30; each side offers on 20030 and sends box command 1; each
      acceptance is box command 4
130   the joiner pings first
50    the host publishes its Pokemon as element 0 and relays the joiner's 10050 as element 1
120   the host pings first
40    the ladder: host commands as element 0, the joiner's 10040 as element 1, phases 0 to 4
```

## 交换动画

主机在最后一条 syncCommand 40（`3`）后播放交换动画，期间没有交换消息。加入 `bin/swsh_host.py` 的零售版《剑》在该 syncCommand 后 1.2 s 开始动画，约 24 s 时将控制权交还玩家。在玩家退出盒子之前（盒子命令 3），它不发送任何应用消息。

## 同一会话中的连续交换

一个会话可以接连进行交换。交换状态 9 发送事件 7（成功）或 8（失败），并向 `0x010ca360` 写入状态 0，玩家随后返回盒子。内容 30 和 ping 110 在整个会话期间存活（由会话设置函数 `0x010c9280` 一次性构建）；内容 50、40 及其 ping 则在每次交换时重建：

| 对象 | 生命周期 | 代码 |
| --- | --- | --- |
| 内容 30，ping 110 | 整个会话 | `0x010c9280` -> `0x010cca10` |
| 内容 50，ping 130 | 一次交换 | 交换状态 1 -> `0x010d5440` -> 初始化 `0x010d4d90`（新内容，旧内容释放），在阶段 0 生成元素 `0x010d53fc`；在状态 3 中由以下函数拆除：`0x010d54b0` |
| 内容 40，ping 120 | 一次交换 | 状态 6 -> `0x010dabc0` -> 初始化 `0x010da470`；在状态 8 中由以下函数释放：`0x010dac90` |
| 内容的 SyncPing | 对应元素的生命周期 | 生成函数 `0x006d44e0` 构建新的 SyncPing，id 为 offset + 0x50（`0x006d46d0`），同时销毁前一个（`0x006cd940`) |

达到 synced 的 SyncPing 从不会原地重置，因此在主机没有内容 50 时发送 ping 130，不会到达任何持有器。

盒子界面的步骤状态机（`0x00aa5160`，表 `0x2059218`）读取监听器 `0x00c8d900` 设置的伙伴盒子命令标志。在步骤 3，收到伙伴标志 1（其提议）后，它同时清除标志 1 和 4（`0x00aa5688..0x00aa569c`）；步骤 7 等待标志 4（`0x00aa5628`），只有步骤 10 才发出行动 6，启动交换状态 1。因此，与提议同一批发送的盒子命令 4 会被清除，主机停在步骤 7，显示“En attente d’une réponse”（等待回应）。伙伴的命令 4 必须在主机处理提议之后到达：`pokeldn.swsh.host_trade` 仅在收到加入端的命令 4 后才发送自身的命令 4；加入端启动器则响应主机端的命令 4 发送自身的命令 4。

玩家按 B 也会结束步骤 7；没有计时器会结束它。该步骤状态机的 UI 是位于 `[this+0x80]` (`0x00aa4e78` 的 View_Model，虚表 `0x25376d8`）。其输入处理函数 `0x00aab0b0`（槽位 16，由以下位置的 UI 分派器调用：`0x00efad28`）在 `ui+0x5cc = 1` 条件下设置 `ui+0x5d0` 已启用且本帧按下掩码携带位 49；重映射表 `0x02062928` 仅从 B 键生成该位。步骤 2 和 6 在提议和接受后启用它（`0x00aa5434`）；每次 tick 都将其清除（`0x00aa5608`）。在步骤 7 中，按键会清除伙伴标志，发送盒子命令 5（撤回接受）并退出流程（`0x00aa57d0`）；在步骤 3 中则发送盒子命令 2。

伙伴在该盒子命令 5 之前发送的提议和盒子命令 1 会随标志一起清除；主机下一次提议会停在步骤 3，直到它们再次到达。`pokeldn.swsh.host_trade` 和 `bin/swsh_connect.py` 都会在盒子命令 5 之后重新发送提议和盒子命令 1。零售版《剑》无论担任何种角色，在提议、接受、按 B、重新提议后，交换均能完成；若不进行第二次发送，主机会一直停在“En attente d’une réponse”（等待回应）。

此后每次交换都会重复交换自身的部分：双方的提议和盒子命令 1、按上述顺序发送的两个盒子命令 4、ping 130（加入端先 ping）、阶段 0 的新内容 50、ping 120，以及从阶段 0 到 4 的新内容 40。两次交换之间没有 0x84 快照、ping 97 或 110、盒子命令 3 或内容 30 发布。`bin/swsh_host.py` 和 `bin/swsh_connect.py` 使用重复的 `--offer-file`，分别与零售版《剑》加入端和主机端在同一会话中按每次一条的方式交换排队记录；主机端在主机离开时关闭。

`bin/swsh_connect.py` 使用重复的 `--offer-file`，将确认阶梯完成后（40040 上阶段 4）主机的提议视为下一次交换。它用下一条记录响应该提议，此时主机的盒子流程已经在步骤 3 持有自身提议；随后它清除每次交换的状态：已响应的 40050 和 40040 配对及消息体、确认命令队列、选择提议锁存标志。40030 配对和 ping 响应则延续保留。`bin/swsh_host.py --accept-first --lead SECONDS` 扮演主机端主机的玩家（先接受，交换后从盒子中提议下一条排队记录），两个启动器在模拟开发板上的同一会话中，双向各交换两条记录（`tests/test_esp32.py`).

零售版加入端玩家在盒子中按 B 时，主机发送盒子命令 2、3 和网状网络的 `0401`，随后取消认证，不出现错误；下一次搜索可以再次加入同一托管网络（网络 id 相同）。搜索中的主机会加入任何通过 [匹配规则](swsh_session.md#how-a-searching-sword-finds-a-partner).

## 盒子状态机

内容 30 携带从交换界面到提议的所有内容。`onBoxSyncStateCommand` `0x010ce180`，是位于 `session+0x120` 的 0x50 字节包装对象的槽位 1（虚表组 `0x2625808`):

1.
2.
3.

字段 1，即 `boxSendPokemon`，以事件 0 传给槽位 0 `0x010ce080`。分派器接受 0..6；发送者发出 1..5。

监听器 `0x00c8d900` 设置 `[owner + 0x218 + code] = 1`；代码 2 先清除代码 1 的标志（`+0x219`），代码 5 先清除代码 4 的标志（`+0x21c`）。1 表示提议，2 表示撤回提议；4 表示确认，5 表示撤回接受

1.

发送函数 `0x010cda70(content, command)` 位于包装函数 `0x010cde90` .. `0x010cded0` 之后（命令 1 至 5），由场景跳转表 `0x00a96d10` 根据其行动值 `+0x78`:

```
action 1  ->  command 3
action 2  ->  the Pokemon (0x010ca430), then command 1
action 3  ->  command 2
action 4  ->  command 5
action 5  ->  command 4
action 6  ->  0x010ca640, which stores its Pokemon and sets the trade state to 1
```

发送受两项静默条件限制：

```
[content+0x48] a pending command; a different one arriving sets the error byte [content+0x4d]
               and sends nothing
[content+0x4c] channel ready, set by 0x010ce040 on result 0; while clear the command waits in
               +0x48 and never goes out
```

命令 3 用于开启流程。逐帧更新函数 `0x010c9bb0` 在其状态分支之前执行：

```
if ([session+0x418]) { if (![session+0x419]) send command 3; [session+0x418] = 0; }
```

设置函数 `0x010c9280` 设置 `+0x418 = 1`, `+0x419 = 0x00dceea0() & 1`（来自玩家列表）：恰好只有一方发送命令 3。`--box-open` 在收到 0x84 确认时发送盒子命令。

## 交换状态机

`[session+0x140]`，范围 1..10，表 `0x2067b68`:

```
1  0x010c9c78  -> 0x010ca0a0: start content 50 and send its Pokemon; true -> 2, false -> 9
2  wait        5  wait        7  wait
3  0x010c9f60  the Pokemon exchange (0x010d54b0 on content 50), then 4, or 9 on error
4  0x010c9c9c  0x01109320 decides; false -> 6
6  0x010c9f84  -> 0x010ca1ac: install four delegates and start content 40
8  0x010c9fa8  0x010dac90(content40, session+0x170, session+0x210): unhook from
               [content+0x20]+0x60, [content+0x28]+0x60, release 0x010daac0; -> 9
9  0x010c9ef4  terminal: [+0x144] set means failure; listeners get event 8
10 0x010ca838
```

盒子回调 `0x010ca800` 在状态不为 0 时丢弃事件。状态 2 最终进入委托 `0x010cc380` (`session+0x2e0`）：伙伴宝可梦写入 `session+0x70`，一个 0x60 字节记录（`0x010f5cc0`），然后进入状态 3。中止可从状态 1 开始：当内容 50 的初始化 `0x010d4d90` (`mov w2, #0x32`）失败时，其发送函数 `0x010d5440` 不执行任何操作，调用方设置 `[session+0x144] = 1`，进入状态 9：通信中断消息。

## 确认阶梯

内容 40 是一个屏障，每条命令推进一级。

### 阶段到状态的映射

状态为 `delegate+0x5c`，只由初始化（0）、状态机 `0x010dae70` 中的四个位置，以及 `0x010dbf40` 写入。状态机将 `state - 1` 分派到含 14 个条目的表 `0x2067ed0`；状态 2、4、7、9（发送操作留下的状态）进入默认的 `0x010db38c`，即收尾部分，并仅通过 `0x010dbf40` 离开；后者忽略大于 4 的 u16，否则索引表 `0x2067f4c`:

```
phase 0  -> state 1              -> send(0), announcing 1     0x010db308
phase 1  -> state 3              -> send(1), announcing 2     0x010db0b0
phase 2  -> state 5 -> 6 or 8    -> send(2), announcing 3     0x010db0dc / 0x010db104
phase 3  -> state 10 or 11 -> 12 -> send(3), announcing 4     0x010db16c
phase 4  -> state 13 -> 14       -> 0x010db970 tears down, content+0x84 = 0xfc18; no send
```

`[delegate+0x58]` (`0x110e620(...) & 1`）表示角色：状态 7 立即发送 2，状态 9 在倒计时 `[delegate+0x60]` 后发送，其值由 xorshift 在 2..302 中随机抽取。

虚表组 `0x257fe90`：主虚表 `0x257fea0`（槽位 0 为 SyncCommand 接收函数 `0x010dbc90`，槽位 3 为 `0x010dbf40`），offset-to-top −8 位于 `0x257fec8`，次虚表 `0x257fed8` 的槽位 0 `0x010dbfd0` 是同一段代码，作用于 `+0x50`/`+0x54`（表 `0x02067f60`，偏移 `0x70 0x38 0x40 0x48 0x6c`），槽位 4 `0x010dc070` 尾调用 `0x010f8e30`，其余为 `ret`。初始化同时安装两者：

```
0x010da6bc   add x9, x19, #8       ->  [content+0x2c0] = delegate + 8     the second interface
0x010da6d0   str x19, [x8, #0x168] ->  the 10040 holder's listener        the first
```

### 同步泵

`0x010db3e0` 由内容 40 的 tick 在状态机之前运行，是基于 `[content+0x80]` 的 17 状态状态机，带有共享尾部：

```
w1 = [content+0x17c]                    the content's PHASE
if (w1 != [content+0x84] && w1 != [content+0x86])                     0x010db758..0x010db778
    { 0x010de310(content, w1); B->slot7(w1); }                        slot 7 is a ret
w1 = [content+0x17c]
if (w1 != [content+0x84] && w1 == [content+0x86])                     0x010db794..0x010db7b4
    { 0x010de310(content, w1); B->slot0(w1); }   <- the state setter
0x010ddf40(content)                     the queued jobs                0x010db7d4
0x006d4b80(content+0xd0)                the element update, last       0x010db7e8
```

`B` 是 `[content+0x2c0]` (`delegate+8`）。先执行状态分支；状态 0（`0x010db740`）跳过尾部，状态 16（`0x010db730`）在 `0x006d4b30` 为 false 时提前返回。一个既未提交也未通告的阶段会被静默提交（清除标志和任务，同步泵状态为 2）。

| 字段 | 含义 | 写入方 |
| --- | --- | --- |
| `+0x84` | 已提交阶段 | `0x010de310`，它还会丢弃待处理消息体并清空任务队列 `content+0x310` (`0x010de348..0x010de3a0`）；仅从尾部（`0x010db778`, `0x010db7b4`）和状态 14（`0x010db6ac`）调用，条件为 phase != `+0x84` |
| `+0x86` | 随上一条命令通告的阶段 | 仅由 `0x010dbab0`, `data + 1` 在全部五个发送点写入 |
| `+0x17c` | 阶段，`element+0xac` | 构造函数 `0x006d3ff8`，生成函数 `0x006d4500`，采纳函数 `0x006d4ccc` |

阶段达到 `+0x86` 时，阶梯向上推进。构造函数设置 `+0x84 = 0xfc18` (`0x010dc228`, `0x010dc260`), `+0x86 = 0` (`0x010dc25c`）；注册器将 `+0x84` 设置为 0（`0x010da810`, `0x010daa78`），使用 0 生成元素（`0x010daa7c`），并保留 `[content+0x80] = 1`；随后同步泵状态 1 在门控之外调用状态设置函数：命令 0，通告 1。

同步泵状态（表 `0x2067f08`; `[+0x1c0]` 是元素的 `+0xf0` 通道，`[+0x2a0]` 是以下对象的命令标志：[命令](#the-command)):

```
1   0x010db418  element ready (0x006d4e70) -> 2; delegate slot 1, then slot 0 with the phase
2   0x010db47c  a pending body at +0x88 -> 3
3   0x010db48c  0x006d4f10 (all ready, every pair's low half == phase): send the body
                (0x010de080) to station [[0x2616a30]+0xf8] -> 4
4   0x010db4dc  0x006d3690([+0x1c0], [+0x86]) publishes the high half, must return 1;
                then 0x018407f0 ? 8 : 7                                      cinc 0x010db514
5   0x010db51c  the same through [+0x2b8] (0x008b7300) with [+0xa8] -> 6; dead in content 40
8   0x010db594  0x006a2840([+0x2a0]): every station has sent a command -> 9
9   0x010db5b4  0x006d4fb0 == 0: no resend byte set -> 10
10  0x010db5d4  0x006d4da0 && 0x006d3060([+0x1c0], [+0x86]) (every high half == announced)
                && 0x006d4f50; then 0x006d33b0 writes shared value = announced -> 7
11  0x010db62c  0x006a2760([+0x2a0]) clears every flag; [+0x374] ? 12 : 2
6, 7, 12        the default, the shared tail at 0x010db758
14  0x010db68c  the gated commit (13, 15, 16 unread)
```

状态 8 至 10 只在主控端运行（`0x018407f0`）；其他站点经过 4 至 7 并遵循共享值。`0x010d9000..0x010df000` 中没有任何代码向 `[content+0x80]` 存入 5，或向 `[content+0xa8]` 存入非零值（仅清除，`0x010db9ec`, `0x010dc530`, `0x010de3a4`）。其他写入方，目标为 `[content+0x80]`:

| 位置 | 函数 | 状态 |
| --- | --- | --- |
| `0x010dc234` | 构造函数 | 0 |
| `0x010daa9c` | 注册器 | 1 |
| `0x010dbc70` | `0x010dbab0`，命令发送（要求状态 2；写入 `+0x86`) | 3 |
| `0x010de3c4` | `0x010de310`，提交；清除以下位置的每个标志：`0x010de344` | 2 |
| `0x010dc7a0` | `0x010dc720`（槽位 `0x257ff70`），站点离开：若 `[+0x374]`，通知委托槽位 4，否则从元素（`0x006d50e0`）和标志中移除它（`0x006a2140`) | 11 |
| `0x010dc6f4` | `0x010dc6c0`（槽位 `0x257ff68`），要求 `[+0x374]` 和 `0x006a2a80([+0x2a0])` | 13 |
| `0x010dccec` | 槽位 `0x257ff90` | 2 |
| `0x010dcee8` | `0x010dce70`，CancelAccepted（`x19 = content+0x68`），除非为 16 | 2 |
| `0x010db998` | `0x010db970`，拆除 | 16 |

内容 40 的注册器将 `w2 = 1` (`0x010da6a8`）存到 `[+0x374]` (`0x010da800`）：站点离开时经过 11、12 并结束阶梯。

### 阶段是元素的字段

在 `0x010c0000..0x010e0000` 中没有任何代码写入 `content+0x17c`。注册器在 `content+0xd0` (`0x010daa4c`）构建 40040 元素，添加子元素（`0x006d4ff0`），并使用 `0x006d44e0(element, w20)` 生成它，后者打开 `str wzr,[x0,#0xa8]; strh w1,[x0,#0xac]`：阶段为 `element+0xac` (`0xd0 + 0xac = 0x17c`），初始值来自初始化的 `wzr`.

它只在以下函数中推进：`0x006d4ca0`:

```
w0  = 0x006d3260([element+0xf0])        the shared value; 0xfc18 when none
if (w0 == [element+0xac]) done
if (0x006d3980([element+0xf0], w0)) {   publish it as its own; on success
    [element+0xac] = w0                 the phase moves
    [element+0xa0]->vtable[0]()         and the content is told
}
```

这是元素更新函数 `0x006d4b80` 的尾部（每个同步泵最后都调用它；内容 40 的调用位置为 `0x010db7e8`），当 `0x006ce5a0([element+0xb0])` 返回 1 时运行。在所有站点就绪之前：

```
if (!0x006d2e20(shared) && !0x006da180(hash channel)) {
    if (0x018407f0([[0x2616a30]]))  0x006d33b0(shared, [element+0xac])
    0x006da3d0(hash channel, element+0xa8); 0x006d3980(shared, [element+0xac])
    return
}
```

`0x018407f0` 在托管 Pia 网状网络的主机上为 true（[会话](swsh_session.md#the-pia-session-object)；后端调用 `+0xe0`，作用于 `[x0 + 0x168 + [x0+0x162]*8]`）。只有它能初始化共享值，即 `+0xf0` 通道的 16 位子元素（[子元素种类](swsh_protocol.md#sub-element-kinds)）；每个站点都采纳该值：

```
0x006d3260  read            ready [sub+0x61] ? [sub+0x88] : 0xfc18
0x006d33b0  write(v)        0x006d3570 when not ready or body != v
0x006d3570  publish         body [sub+0x88] = v; clock from 0x01766740 (-1: error 0x2c27);
                            [sub+0x80]->vtable[0] with (sub+0x88, 2, clock, [sub+0x62], [sub+0x68])
                            when [sub+0x80]->vtable[1]() or [sub+0x70] allows, resend byte
                            [sub+0x60] = !sent; else [sub+0x60] = 1
0x006d2e20  all ready       the shared value and every pair
0x006d2c20  all low == v    all ready, every pair's [sub+0x88] == v
0x006d3060  all high == v   all ready, every pair's [sub+0x8a] == v
```

写入操作不改变就绪字节（只有接收函数 `0x006d6a08` 写入 `+0x60`；写入函数为 `0x006d35b8 strh w8,[x20,#0x88]!`），因此在消息到达之前，读取会返回 `0xfc18`；在主控端，这条消息来自自身。发布操作到达元素的槽位 0（`0x006d5730`），后者按站点对消息体排队。在一次完成的交换中，40040 上的 149 条客户端消息都携带四字节消息体；该内容的其他形式见 [下文](#shapes-the-confirmation-content-also-sends).

### 步骤消息体

内容 40 的 elementId 20000 上的四字节消息体，低半部分为阶段，高半部分为上次通告值：

```
0x006d3980(channel, v)   body = <u16 v><u16 [sub+0x8a]>    low; from the element update
0x006d3690(channel, v)   body = <u16 [sub+0x88]><u16 v>    high; from pump state 4, [content+0x86]
```

两者都在通道的 `[[0x2616a30]]+0xf0` 中查找自身 id（`{ownerId, entry}`）表，取得 `[entry+0x60] - 0x50`，并调用 `0x006d3860` (`0x010dbe20`，再下一层）；`[content+0x1c0]` 是 `[element+0xf0]`。观察到的一次阶梯：

```
000018fc   phase 0, announced 0xfc18   the birth sentinel
00000100   phase 0, announced 1        the cue; command 0 already sent
01000100   phase 1, announced 1        caught up, committed
01000200   phase 1, announced 2        state 3 sent command 1
02000200   phase 2, announced 2        caught up
02000300   phase 2, announced 3        committed, sent command 2
04000400   phase 4                     the teardown rung
```

`trade.parse_sync_step`, `SYNC_LADDER` 和 `sync_announced_phase` 将其解码。

### 命令

`SyncSaveDataHolder{syncCommand{data:N}}`，在 10040、可靠端口 0 上。处理函数 `0x010dbc90` 丢弃 `0x006b5850` 无法解析的发送者（`0xfd`），读取 `[arg1+0x14]` 处的 int32，按站点索引选择 `+0x38` 处的订阅者，将 int32 传给中继 `0x010dbe20` 和订阅者的 `+0x18`，随后始终执行：

```
0x010dbdf8  ldr  x8, [x20, #0x18]
0x010dbdfc  ldr  x0, [x8, #0x2a0]
0x010dbe00  mov  w2, #1          <- a constant
0x010dbe04  mov  x1, x19         <- keyed by the sender
0x010dbe08  bl   #0x6a24a0
```

该值只到达中继（elementId-1 消息体 `00000000` 回显 `syncCommand{data:0}`）；状态只通过 `0x010dbf40` 推进，由同步泵传入自身阶段调用。任何命令都会推进一级。`[content+0x2a0]` 是逐站点的标志对象（`0x006a24a0` 有 44 个调用点）：

```
0x006a24a0(obj, id, flag)   map[id] = flag & 1; map at obj+0x1c0, find-or-insert
                            (0x006a24d0 hashes by udiv/msub on the bucket count at +0x10)
0x006a2840(obj)             1 when every station listed at obj+0x100 (count +0x108) is set
0x006a2760(obj)             clear(): frees nodes, zeroes buckets and the size at +0x270
0x006a2480(obj)             obj+0xc0, the station list the registrar walks
```

状态 8 等待 `0x006a2840`；提交和状态 11 清空映射。标志在同步泵之外的网络更新取尽操作中设置：`0x006a9a20` 调用 Pia 的分派函数 `0x006a8380` (`0x006a9a54`），然后调用取尽函数 `0x006db3b0` (`0x006a9a90`, [路由](swsh_protocol.md#the-routing-path)）。在其调用方 `0x00ef4a9c`, `0x01109250`, `0x01109308` 中，逐帧函数 `0x00f1df30` 围绕游戏更新运行两次：

```
0x00f1df30  bl 0x01109240     network update: 0x01109250 bl 0x006a9a20, the drain
            bl 0x00fa09a0
            bl 0x00f1cc60     the game update
            bl 0x00793ec0
            bl 0x011092f0     0x01109304 bl 0x01111db0, 0x01109308 bl 0x006a9a20, the drain again
```

内容 40 的命令 tick `0x010dae70` 在交换场景任务中运行：`0x00c8c6b0` 调用 `0x010c9bb0`，位置为 `0x00c8c6d8`，后者在 `0x010c9c34` 处调用该 tick。任务分派器通过 `0x00f19770` 和 `0x00f19080` 到达它。模拟器跟踪显示，此 tick 先于 `0x01109250`，然后是 `0x00f1cc60`，然后是 `0x01109308`。在那里取出的命令可以被随后一次场景 tick 消费。

RequestCancel 和 RequestCancelAll 也读取该映射（[下文](#the-cancel-and-proceed-messages)).

每一级需要在前一次提交之后到达主控端的一条命令。第 0 级任意命令都计入，包括响应提示 `00000100` 的命令；此后，响应提示（`01000200`, `02000300`, `03000400`）的命令在提交前到达并被清除，而响应已追平消息体（`01000100`, `02000200`, `03000300`）的命令才计入：

| 命令，每个新消息体一条 | 最后的消息体 |
| --- | --- |
| 1，响应 `00000100` | `01000200`：第 0 级 |
| 4, `000018fc` 至 `01000200` | `02000300`：第 0 和第 1 级 |
| 9, `000018fc` 至 `04000400` | `04000400`：完成交换 |

`--confirm-commands 0,1,2,3,0,1,2,3,0,1,2,3` 每个新消息体弹出一条，包括 `000018fc`；队列不得耗尽。`answer_rpc` 回显消息体，不推进任何半部分；`--confirm-phase N` 写入低半部分。

### 取消与继续消息

30040，即 `SequenceDataHolder` ([协议页面](swsh_protocol.md#the-30000-holder)），保存于 `[content+0x2b8]` (`0x010da9b8`），监听器为 `content+0x68` (`0x010da9b4`, `0x010da9bc`；虚表 `0x02580030`, `0x010dc238`):

| 分支 | 消息 | 处理函数 |
| --- | --- | --- |
| 1 | CancelAccepted | `0x010dce70` |
| 2 | RequestCancel | `0x010dc920`，经由 thunk `0x010dcf20` |
| 3 | RequestCancelAll | `0x010dcaa0`，经由 `0x010dcf30` |
| 4 | RequestForcedProceed | `0x010dc7b0`，经由 `0x010dcf40` |

每种消息仅在 `currentSeqNo` 等于已提交阶段 `(s16)[content+0x84]`:

-
-
-
-

`RequestForcedProceed` 可在没有 `syncCommand` 的情况下推进共享阶段（模拟《盾》）。它不能替代确认命令：如果阶梯后续命令改用这些请求，则会在存档前停在“正在通信”。

任务队列 `content+0x310`（条目 `+0x350`，数量 `+0x358`）在 `0x010ddf40` 中由同步泵运行（`0x010db7d4`）；返回 true 的任务被移除。提交会清空队列。

### 确认内容还会发送的形式

不带 ownerId、且消息体不是四字节的 40040 封装：

```
elementId 20000, no owner, 2 bytes   0000   then   0100
elementId 1,     no owner, 4 bytes   00000000        after a syncCommand{data:0}
no elementId,    no owner, 4 bytes   00000000  then  01000000
```

配对的接收函数 `0x006d6490` 丢弃两字节形式（`cmp x2,#4`）；它们是共享值（[阶段是元素的字段](#the-phase-is-the-elements-field)).

## 联盟卡

交换后，每台主机都会询问是否保存伙伴的联盟卡，即其快照 0x924 处的 TrainerCard（[协议](swsh_protocol.md#the-party-payload-on-protocol-0x84)）；作答不会发送任何内容。

选择“Oui”（是）会将其原样保存在存档块 `0x28e707f5` 中：从 `album+0x230` 开始有 300 个 0x1d0 大小的槽位，作为一个 `0x21fc0` 字节块加载（`0x013fad4c`），当 `+0x1c8` 非零时表示空闲。`0x013fbab0` 填充第一个空槽位：0x1c4 字节，`+0x1c8`/`+0x1c9` 清零，年份 `+0x1ca` (`tm_year + 0x76c`）、月份 + 1 `+0x1cc`、日期 `+0x1cd`, `+0x1ce`/`+0x1cf`，来自参数（`00 00 ea 07 09 1a 02 00`：年份 0x07ea，月份 9，日期 0x1a）。`0x013fbc00` 在 300 个槽位全部占用时返回 1。

`0x013fbc40(album, card)`（调用方 `0x00aa6414`, `0x0106612c`, `0x015253f0`, `0x01543868`）在已使用槽位与卡片 0x1C 处的 u32（`0x013fbc4c`）和 0x1A8 处的八个字节（`0x013fbc5c`，一次 64 位比较）匹配时跳过询问；清空该槽位会恢复询问。0x1C 是 PKHeX 的 `TrainerCard8.TrainerID`, `(SID << 16 | TID) mod 10**6`（56909/48474 对应 848973）；0x1A8 是 `TimestampPrinted`，一个 Unix 时间（`9bc62a5e00000000`，2020-01-24，来自零售版卡片）；游戏比较全部八个字节，而 `pokeldn.swsh.league_card` 映射一个 u32。`trade_payload.rewrite` 设置训练家 id。面对已持有主机端卡片的模拟《盾》时：

| 主机端的卡片 | 是否询问 |
| --- | --- |
| 不变 | 否 |
| 训练家 id 848973 -> 111111 | 是；保存在第一个槽位旁的新槽位中 |
| 图鉴数量 400 -> 401 | 否 |
| 名字增加一个字母 | 否 |
| timestamp_printed，仅更改字节 0x1A8 | 是 |

零售版《剑》绘制接收日期，左上角显示 `game` 的标志（0x24，0 为《剑》），左下角显示 0x39 处的三个 ASCII 字节，`dex_complete`（0x30）对应洛托姆图鉴皇冠，此外还绘制星星。视图函数 `0x01592e70` 将卡片复制到 `view+0x3c0`; `0x015a52f0(view, count)` 点亮七个面板中的 `count + 1` 个（`view+0x618..+0x648`；验证器将数量上限设为 6）：

```
count = card[0x177] + (card[0x1b6] != 0) + (card[0x1b7] != 0)      0x015930bc..0x015930dc
```

它还将 `card[0x24]` 传给 `0x015a5260`，并将 `card[0x1b3] != 0` 传给 `0x015a50d0`。构建器 `0x0158eef0`（调用方 `0x00c77830`, `0x014be578`, `0x0156167c`, `0x01561b0c`, `0x01568f4c`, `0x015691bc`）根据存档填充：

| 字节 | 值 | 位置 |
| --- | --- | --- |
| 0x177 | `DesignLevel`：满足 `FSYS_GAME_CLEAR` (`0x7d0b1ced4dbe8a87`）时为 4，否则徽章数 > 6、> 3、> 0、0 时分别为 3、2、1、0 | `0x0158f084`, `0x0158f484..0x0158f4dc`, `0x0158f0c4` |
| 0x1B1 | `FSYS_SEED_CHALLENGE` (`0xbd07c2b80232e9b0`) | `0x0158f564..0x0158f5a0` |
| 0x1B3 | `FSYS_INPUT_SHIRT_NUMBER` (`0xe44b16771524b07e`) | `0x0158f0fc` |
| 0x1B6 | `FSYS_R1_GAME_CLEAR` (`0x8f1a133dff5c0ecf`），一颗星 | `0x0158f11c` |
| 0x1B7 | `FSYS_R2_GAME_CLEAR` (`0xd450875d834cfc30`），一颗星 | `0x0158f12c` |

标志键是名称的 FNV-1a 64（[协议](swsh_protocol.md#the-player-profile)），由 `0x01410f30` 读取；徽章数由 `0x01438fb0` 给出，即对以下值统计置位位数：`[status+0x60]`. `DesignLevel` 是由 `capture_data.prmb` 列（哈希 `0x3bc4598485d2a2ef`，字符串 `0x01c2a2e9`）通过以下函数存储的值：`0x0158ead4..0x0158eb30`; `GlossIndex` 是 0x178。

`0x0158f5e0` 返回 1 表示拒绝卡片，随后以默认卡片替换。在 unicorn 中，它接受 pokeldn 发送的卡片（0x177 = 4、0x1B3 = 1、语言 3），也接受 0x1B6 或 0x1B7 置位；它拒绝 DesignLevel 5、语言 6、GlossIndex 9。`bin/swsh_host.py --card-set FIELD=VALUE` 编辑所发送的卡片（`pokeldn.swsh.league_card` 字段）；新的 `trainer_id` 会让主机再次询问。

## 提议的记录

将构建的皮卡丘交换给零售版《剑》再交换回来，所有指定的提议选项均保留。返回的 PK8 校验和有效，并通过 PKHeX 合法性检查；PID、初训家 id、个体值和基础点数与发出的提议一致。

| 指定字段 | 返回记录 |
| --- | --- |
| 等级 | 30 |
| 性格与能力值性格 | 固执，3 |
| 特性 | 避雷针，31 |
| 性别 | 雌性，1 |
| 精灵球 | 高级球，2 |
| 携带道具 | 电气球，236 |
| 指定的个体值 | HP 31，攻击 0，速度 31 |
| 基础点数 | HP 252，速度 4，其他所有能力值为 0 |

在 `0x011e3458` 读取的加密常量与同行队伍索引一起进入宝可梦露营模型键 `[model+0x368]`，用于露营同步；它不会到达交换或盒子代码。

20030 上的提议是快照中同行队伍槽位 `--offer-slot`，采用原地编辑，因此显示的同行队伍与提议一致；先执行身份重写，且 `party_matches_trainer` 成立。`pokeldn.swsh.pokemon.build_from` 重写校验和，在新加密常量下重新打乱，并保留所有未指定字节（奖章、回忆、相遇数据、当前训练家记录）。

法语《剑》1.3.2 在四次交换中接受了其存档已持有的记录（相同 PID 和 EC），并将其继续交换出去。在《盾》1.3.2 已读取的路径上没有重复检查：PID getter（`0x0076bc20`，块 A + 0x14）仅由异色检查调用；加密常量 getter（`0x0077ec90`）在 12 处被读取，没有一处遍历盒子；盒子代码（`obj+0x60 + box*0x2850 + slot*0x158`）仅读取种类和蛋标志；没有任何访问器触及 PK8 字节 0x52，而《晶灿钻石》将其非法标志保存在该处（[BDSP 交换页面](bdsp_trade.md#duplicate-detection)). `bin/swsh_host.py --fresh-pid` 和 `bin/swsh_connect.py --fresh-pid` 抽取新的加密常量和 PID；在《剑》中，这是预防措施。

对 `memcmp` 桩函数 `0x018fe460` 的 375 次带计算长度的调用，没有任何一次将两个宝可梦相互比较：其中 374 次比较字符串或库数据（sol2、protobuf、NEX、Lua、Pia、SDK 图形、名称词典、对战数据持有器、FlatBuffers 虚表），而 `0x014514ac` 将位于 `obj+0x60` 的 0x158 字节槽位与全零比较。从交换接收路径（`0x010d81d0` 至 `0x010f5cc0`）或盒子路径（`0x010ce180`, `0x00c8d900`）均没有直接调用到这些比较；交换代码只到达 protobuf 的描述符注册（`0x006e26f0`），其操作数为 rodata 中的名称。未跟踪通过虚表进行的调用。

```
--offer-slot 1 --offer-nickname POKELDN --offer-ivs 31,31,31,31,31,31
```

| 标志 | 效果 |
| --- | --- |
| `--offer-nickname`, `--offer-ot` | 26 字节 UTF-16 字段，最多 12 个字符；提供昵称会设置已取昵称标志，否则显示种类名称 |
| `--offer-species` | 仅修改种类字；其余内容保持模板的值 |
| `--offer-ability ID`, `--offer-moves A,B,C,D` | 这两个字段；PP 和回忆招式保持不变 |
| `--offer-level N` | 0x148 处的等级字节 |
| `--offer-experience N` | 0x10 处的经验值字 |
| `--offer-ivs` | 六项个体值 |
| `--offer-file FILE` | 一个 `.pk8`，支持四种格式（存储或同行队伍、加密或 PKHeX 解密导出，通过头部校验和区分）；初训家名字和 id 改为快照中的训练家 |
| `--offer-file-as-is` | 保留文件的初训家 |
| `--save-offer FILE` | 在使用无线通信之前写出构建好的记录 |

法语《剑》1.3.2 对编辑记录的处理：

| 发送的记录 | 结果 |
| --- | --- |
| 模板、昵称、个体值 31 | 接受；未指定字段保持模板的值 |
| 种类 93，配上耿鬼的特性 130 和招式 | 显示为鬼斯通，并通过交换进化：不检查特性和招式 |
| 种类 25 | 根据个体值、基础点数、性格和 0x126 处的极限特训重建能力值；丢弃 0x14A 处的能力值字节 |
| 等级字节 0x148 = 50，经验值达到等级 100 | 等级 100：等级由经验值（0x10）决定；同行队伍尾部被重建 |
| 初训家改为 12345/54321 | 显示 ID 993401，`(SID << 16 \| TID) mod 1000000` |
| 外来 MyStatus 下使用接收者自身的初训家 | 按玩家自己捕获的宝可梦接受：不将初训家 id 与 MyStatus 比较 |
| PID 高半部分 = `low ^ TID ^ SID` | 异色 |
| 种类 152（不存在） | 已存储：皮卡丘模型、名称字段、黑色精灵球图标、成长组 0 和全零种族值；只有当前 HP（0x8A）和当前训练家块（0xA8、0xC2、0xC3、0xC8、0xCB-0xCC）变化 |

未测量：其他不存在种类会显示什么，以及名称究竟来自名称字段还是查找失败。

## 完成一次交换的命令行

`swsh_connect.py --preset trade` 携带交换所需的标志；在其后指定的标志会覆盖预设。让主机搜索本地连接交换（YY 通讯、连接交换、本地、两条消息均按 A），然后运行：

```
POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/swsh_connect.py --keys PROD_KEYS \
    --preset trade --save-offered offered.pk8 --capture trade.jsonl
```

返回发送的快照来自主机在同一会话中的自身快照（`--send-snapshot live`，预设默认值）：三个 0x84 分片在到达时重新组装，训练家名字、TID 和 SID 被重写为 `--snapshot-name/-tid/-sid`，主机快照重组完成后就发送，因此无需较早抓取的会话。`--send-snapshot FILE` 改为发送已保存的 3456 字节负载（`--preset capture`，然后 `tools/switch/swsh_snapshot.py`，可写出一份）。

`--offer-file FILE` 将一个 `.pk8` 放入提议的同行队伍槽位，其初训家改为快照训练家。重复指定时，在会话中按每次交换一条记录排队；最后一条用于后续所有交换，使用 `--fresh-pid` 生成新 PID，且第 N 次交换写入 `--save-offered`，使用 `-N`。主机已发出提议、但阶梯尚未完成的交换，可使会话在 `--grace` 之后额外保持最多相应秒数（300）：`--hold`。没有同行队伍能力值的存储格式记录也可交换；主机根据经验值计算等级。

## 惩罚与干净结束运行

链路仍保持连接时交换超时，视为交换失败，并禁止主机进行交换（`msg_ui_live_comm_app_alert_00`，位于 `/bin/message/French/common/live_comm.dat` 的第 331 行）。文本没有说明持续时间，且标签不在 `main.bin` 中；锁定时长尚未读明。在 `04000400` 后 15 s、存档过程中切断链路，会显示通信错误 `2-ALZAA-0016`，但不会触发交换锁定，且可以立即开始新的本地搜索。

`bin/swsh_connect.py --abort-on-stall SECONDS` 在阶梯已开始且经过 SECONDS 秒没有新消息体时断开链路。达到阶段 4，即静默拆除级别（`stall_abort()`, `final_phase_seen`, `LADDER_FINAL_PHASE`）时，它会停止该行为，因此绝不会在存档期间切断链路。

## 验证交换完成

收到的宝可梦在 0xC4 处携带 `CurrentHandler` 值 1，并在 `HandlingTrainerName` 的 0xA8 处携带接收者名字，同时保留发送者的初训家。`--offer-echo` 会将主机自身的记录交还，所以只有种类不同才能证明发生了传输。
