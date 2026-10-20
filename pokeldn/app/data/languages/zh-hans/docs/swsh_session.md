---
title: 卡带、密钥与入座
parent: Sword and Shield
nav_order: 1
---

# 卡带、密钥与入座

`main` 静态链接了整个 Pia（252 个 `nn::pia` 类、2036 个虚方法），并导入 `nn::ldn`。在 Pia 之上，游戏使用 protocol buffers：`main` 为 78 组 P2P 消息集中的每一组携带一个 `FileDescriptorProto`（`gflnet.p2p.framework.pb`, `.block.pb`, `.sync.pb`，每个内容一个包：交换、对战、露营、团体战）。

## LDN 口令

```
W3GoSMEn7RIIUQ89rzqBHGhGferRNb7K18ZBq2aNuj8Us9RO9Q9JYyGOZlLy8MYL
```

原始 64 字节（两份副本，`0x203ff04` 和 `0x203ff45`）；与 NintendoClients wiki 的《朱／紫》条目相同，与《传说 阿尔宙斯》相差一个字符（`HGhG` 为此处的字符，`HGHG` 为另一处的字符）。

```
0x006c3eb4  adrp x1, #0x203f000 ; add x1, x1, #0xf04    the literal
0x006c3ec0  add  x0, sp, #0x10                          the LdnCreateSessionSetting
0x006c3ec4  mov  w2, #0x40                              64, not a NUL-terminated length
0x006c3ec8  bl   #0x1790450                             its passphrase setter
```

`nn::pia::local::LdnCreateNetworkJob` 在 +0xC4 保存口令，在 +0x104 保存其长度，在 +0xB8（本地通信 id）和 +0xC0 保存 `NetworkConfig` 意图参数；它将口令复制到 `SecurityConfig+4` (`0x01797280..0x01797284`），紧接着调用 `nn::ldn::CreateNetwork` (`0x017972bc`). `LdnBackgroundProcessJob` 要求长度为 16..64。

## Pia 游戏密钥

```
p1frXqxmeCZWFv0X
```

位于 `0x01c3dc87` 的十六个 ASCII 字节，被三个调用点原样使用（wiki 的《剑／盾》条目）：

```
0x006ca914  mov  w8, #1 ; str w8, [sp, #0x18]     crypto enabled
0x006ca91c  adrp x8, #0x1c3d000 ; add x8, x8, #0xc87
0x006ca924  ldp  x9, x8, [x8]                     the 16 bytes
0x006ca938  stur x9, [sp, #0x1c]                  -> the setting's key field
0x006ca93c  bl   #0x183fd10                       create/join
```

## 读取卡带

```
./.venv/bin/python tools/switch/xci_read.py <the.xci> --keys prod.keys --type Program
./.venv/bin/python tools/switch/xci_read.py <the.xci> --nca 87e41bc8 --exefs 0 --extract main
./.venv/bin/python tools/switch/nso_read.py main
./.venv/bin/python tools/switch/rtti_names.py main.bin 0x1900fc0 --rodata 0x1901000:0x24da168
```

`xci_read.py` 原地读取 XCI；`main` 的 text 范围为 0..0x1900fc0，rodata 延伸至 0x24da168，data 延伸至 0x2635f38。方法：[逆向分析 Switch 游戏](switch_re.md).

`/bin/message//common/*.dat` 使用第 6／7／8 世代的消息容器：第 *n* 行的密钥初始值为 `0x7C89 + n * 0x2983`，每个字符后循环左移 3 位（每行均以 `0x0000` 结尾）。`.tbl` 是一个 `AHTB` 索引，条目 *i* 对应行 *i*.

## Pia 4

Pia 头部携带版本 4，其结构不同于 [Pia 层](pia.md) 上的两个版本区间；其下为 5.27 的 LDN 系列（密钥、IV、帧结构相同，另加一个字段）。`pokeldn/ldn/pia4.py` 实现该结构。`pokeldn.swsh.session_keys` 使用 BDSP 的派生方法，但不替换版本：

```
session key   = ldn_session_key(GAME_KEY, application_data[12:16] little-endian)
IV            = crc32(application_data[0:4] || the sender's MAC)[0:3] || source id || nonce
tag           = sixteen bytes, checked in full
```

484 个零售版数据包中，484 个全部通过认证，每个源 id 均为 0。会话参数和网络 id 随会话变化。另一条路径 `0x0179bff0` -> `0x01774f40` 使用该会话的两个 64 位值初始化 AES-GCM；本地交换只需要广播数据。

## 入座

```
POKELDN_RADIO=esp32:auto ./.venv/bin/python bin/swsh_join.py --keys PROD_KEYS --scan-only
```

扫描处于主机端状态的界面，并将每条广播写入 `scratchpad/swsh_net_facts.json`; `--pw-mode raw` 是默认值。

| 界面 | 本地通信 id | 版本 | 场景 | 应用版本 |
| --- | --- | --- | --- | --- |
| 连接交换 | `0x0100ABF008968000`（《剑》的） | 4 | 60001 | 7 |
| 神秘礼物本地无线 | 相同 | 4 | 65535 |  |

《盾》使用《剑》的 id：它使用 `0x0100ABF008968000` 构建 `mov`/`movk`，位置为 `0x011083e0..0x011083f0`，写入 `sp+0x88` (`0x01108404`；通向 LDN 意图参数的路径尚未跟踪），且其 `control.nacp` 列出 `LocalCommunicationId[0] = 0x0100ABF008968000`, `[1..7] = 0x01008DB008C2C000`.

384 字节的应用数据：

```
0x00  4  network id, random per session
0x04  4  CRC32 of the Link Code's ASCII digits, LE; 0 with no code (12345678 -> 0x9AE0DAAF)
0x08  1  system communication version, 5
0x09  1  header size, 0x18
0x0A  2  padding
0x0C  4  session param, random per session
0x10  8  zero
0x18  2  CRC16 over 0x1A..0x180 (`0x0065dcb0`, `pokeldn.swsh.beacon.crc16`)
0x1A  2  network version word, 12 bits, 0x0D70 (`0x006c17c0` from `0x02068848`)
0x1C  1  bit 0 from `0x006b5c10`; set is refused
0x1D  1  payload type, 0 for station info
0x1E  1  page byte, 1 and 2 in turn every third publish (`0x0111aac0`)
0x1F 266 the player profile, as in the trade snapshot at 0xAEC but sampled at another moment
         ([the protocol page](/pokeldn/swsh_protocol.html#the-player-profile)); zero to the end
```

`Connect failed with status code 1` 表示关联遭到拒绝；在同一次搜索中再次尝试则可能关联成功。搜索中的《剑》在同一个通信 id 下广播两个网络：场景 65535 的 YY 通讯信标网络，以及越过第二条消息后出现的场景 60001 匹配网络。在信标网络上的站点，16 次加入中有 0 次到达交换盒子（网状网络加入以原因 1 拒绝，或者广播在其连接期间变化）；`bin/swsh_connect.py` 仅加入场景 60001，并不断重新扫描直到它出现。关联后，主机向 `169.254.x.255:12345` 广播 Pia（每秒约十个数据包）；界面没有任何显示。已加入的站点离开后，什么机制结束主机广播尚未读明。

## 搜索中的《剑》如何寻找伙伴

在 YY 通讯界面，每台主机都托管一个场景 65535 的信标网络，并以每秒约一次的频率浏览（`0x006c3630`：托管函数 `0x006c3840`，浏览函数 `0x006c3770`，筛选条件来自 `0x006c4550`, `0x0183fac0`，仅按通信 id 和网络类型筛选）。通过 CRC 和版本检查的记录（`0x006c1be0`）进入附近玩家注册表（`0x0110f270`），该表丢弃自身记录（设备 id 位于广播 0x1F，账户 uid 位于 0x2F，`0x0111b160`），以及任何没有网络 id 与场景配对的记录（`0x0110f2d4`）。此处不执行任何加入操作。

选择连接交换，再选择普通交换，会显示两条消息，每条都等待按 A。第二条消息（“你可以取消搜索……”）之后，`0x00fba940` 调用 `SetMode(comm, 2)` (`0x01096d10`); `0x01095f10` 在一秒内依次经过状态 0、5、3、4、6，状态 6 调用 `StartRandomMatching` (`0x010fcff0`），传入场景 60001（`0x01096730`）。野外场景显示“Recherche…”（搜索中……）。停在第一条消息的主机从不调用 `SetMode(comm, 2)`，也绝不会匹配。

匹配层通过以下条件加入网络（`0x006c9e70`, `0x006cb8e0`，加入函数 `0x006ca1c0`）：

```
scene 60001, equal to its own
node count 1, below its maximum of 2; network type 2; node count maximum 8 or less
advertise 0x04 zero: a search without a link code refuses a password
advertise 0x00, a u32, greater than the searcher's own
advertise 0x00 not among ids whose join failed this search (0x80 entries)
```

连接密语只更改 0x04。`bin/swsh_connect.py`（不设置密语）可加入设密语的主机并交换；`bin/swsh_host.py --code 12345678` 会被使用相应密语的搜索加入，不带密语则绝不加入。id 较大者担任主机端，因此两台搜索中的主机只会按一个方向配对；主机端广播接近 0xFFFFFFFF 的 id。

## 主机最先发送的内容

Pia 本地协议 0x24，与 BDSP 相同（`pokeldn.ldn.local_protocol`）：版本 1、类型 0x11、0x30 个固定字节、八个九字节座位，以及主机迁移字节。`allow_participating` 为 true，因此主机在加入端发出 Pia 消息之前就将其列入表中。

```
a9fe0e01 3039 ... 00      169.254.14.1:12345   station 0, the console, ranking 0
a9fe0e02 3039 ... 01      169.254.14.2:12345   station 1, the seat, ranking 1
```

主机端不断重复会话更新，直到每个站点都确认（0x21）。携带相同序号 id 的确认会停止重广播（13 ms 内）；使用其他序号 id 的确认不会（`bin/swsh_connect.py --seq-delta`）。头部字节 0x05 和 IV 的源 id 均为 0，与主机自身相同（`--station-sweep` 遍历其他站点）。

## Pia 会话对象

`[[0x02616a30]]`（也为 `[0x02630f40]`）是交换代码读取站点 id 的位置，即 Pia 会话对象：0x270 字节，无虚表，由 `0x0183ddb0` (`0x0183dfd4`）从 `0x006a8644` 一次性分配。后端来自网络工厂（`[x20+0x60]`, `0x006a8600`): `+0x178` 槽位 `0x240/8`, `+0x188` 槽位 `0x290/8`, `+0x168` 槽位 `0x248/8` (`0x0183e074`), `+0x170` 槽位 `0x248/8`，条件是槽位 `0x1b8/8` 为 true；由字节 `+0x162` 选择。在 LDN 中，工厂是 `LdnNetworkFactory`，其槽位 73（`0x01791080`）构建一个 0x7220 字节的 `LdnMatchmakeSession`（虚表来自 GOT `0x0262fbd0`).

| 字段 | 写入方 | 值 |
| --- | --- | --- |
| `+0xf0` | `0x018418a0` (`0x01841918`) | 本主机自身的站点 id |
| `+0xf8` | `0x018418a0` (`0x01841990`) | 网状网络主机端索引对应站点的 id，该索引字节为 `[[0x0262f7b0]]+0xab` (`0x017bbfe0`）；在以下条件下跳过：`[obj+0xd4] == 4` |

`0x018418a0` 在 `0x018410e0` 之后运行，分别发生于创建（`0x018394d8`）和加入（`0x0183d9b0`）。网状网络主机端索引 `+0xab`（自身索引 `+0xac`）由以下操作写入：创建（`0x017b092c`，等于 `+0xac`）、加入响应（`0x017b4e4c`）、重置为 `0xfe` (`0x017bb820`）以及重置为 `0xfd`，同时设置 `+0xac` (`0x017b99a0`），还有主机迁移：`0x017ca454`（来自 `LanProcessHostMigrationJob`, `LocalProcessHostMigrationJobNew`，Nex）和 `0x017caf48`.

`MeshEventListener` 槽位 2，`0x01843580`（根据 `[x1]` 分支，表 `0x02083fe8`），还会写入 `+0xf8`:

| 事件 | 存储操作 |
| --- | --- |
| 1 | 后端的槽位 30（`0x01844bc4`），然后执行 `0x018412a0(obj, 2, id)`（值发生变化时） |
| 2 | 由 `0x017d6080` 返回的 id（`0x01844a74`）；后端的槽位 30（`0x01844edc`); `0x01844f60` |
| 3 | 零，同时设置 `+0x100` (`0x0184415c`, `stp xzr,xzr`），条件为 `[obj+0xd4] != 3` |

对 `+0xd4` 的写入，发生于 `0x01837000..0x01850000`:

| 值 | 位置 |
| --- | --- |
| 0 | `0x018399c8` |
| 1 | `0x01837c1c`, `0x018396ac`, `0x0183dbbc` |
| 2 | `0x01837a8c`, `0x01839474`, `0x0183cda8`, `0x0183d94c` |
| 3 | `0x01839f7c`，位于 `0x01839cc0`，其调用方为 `0x0177d8a0`, `0x0180afe0` 和 `0x0180bd0c` |
| 4，否则为 2 | `0x0183a2cc`，位于 `0x0183a040`：满足以下条件时为 4：`w8 - 6 < 3` (`0x0183a2b8..0x0183a2c8`）；调用方 `0x0177e8a8` 和 `0x01818b68` |

以下函数的调用方：`0x01839cc0` 属于 `LanMatchJointSessionJob` (`0x0177d8a0`）和 `NexMatchJointSessionJob` (`0x0180afe0`, `0x0180bd0c`）。而 `0x0183a040` 的调用方属于相同的两个任务（`0x0177e8a8`, `0x01818b68`）。普通 LDN 创建和加入将模式 `+0xd4` 设为 2。

仅当 `0x01841350` 和 `0x01769ec0([obj+0x38])` 均为 false，且无符号值 `[obj+0xd8] - 2` 至少为 6（`0x01843980..0x018439a4`）时，事件 2 才能到达任一主机端 id 存储操作。模式 2 从 `0x017d6080` 中选择新站点的常量 id；模式 4 选择包含槽位 30 存储操作的联合会话分支。因此，事件 2 的槽位 30 存储要求联合会话模式 4。

事件 1 的槽位 30 存储要求离开站点的 id 匹配 `+0xf8` 且不同于 `+0x100`, `0x01840b90(obj)`，并要求其为 true，状态为 `+0xd8 == 1`，而且 `[mesh+0x64] == 0` (`0x01844614..0x01844638`, `0x01844654..0x01844664`). `0x0184a4b0` 必须找到一个映射，其输出字非零且不同于以下位置的字：`obj+0x180+4*[obj+0x162]`。如果网状网络控制器的字节 `+0x84` 已置位，其字节 `+0xc0` 也必须置位（`0x01844b54..0x01844b9c`）。新的槽位 30 值必须不同于 `+0xf8` 才会被存储。在 LDN 中，`0x01840b90` 通过虚槽位检查本地网状网络控制器的 `+0x281` 和 `+0x234`，所用虚槽位为 `+0xb0` 和 `+0xa8`。本地控制器成功构建后，会将这两个字节均设为 1（`0x017a06ac`, `0x0183c228`）；事件 1 的其他条件仍然适用。仅凭后端类型不能排除此分支。

`LdnMatchmakeSession` 的槽位 30（`0x017a23d0`）返回 `0xff`，条件为 `[this+0x18]` 为空；否则返回 `0x017672d0`，其输入为以下位置的 16 字节地址：`[[this+0x18]+0x18]+0x2c0+8`：全零时为 0，最后十二字节为零时取前四字节，否则返回错误 `0x10c07`。槽位 28（`0x017a23b0`）就是以下函数发起的虚调用：`0x018407f0`。

`0x018407f0` 在 `+0xf0` 非零、等于 `+0xf8` 且后端槽位 28 的结果一致时为 true：根据创建和加入时的值，此条件在托管 Pia 网状网络的主机上成立。托管交换的主机会根据命令逐级推进确认阶梯；加入 pokeldn 主机端的主机则遵循共享值（[同步泵](swsh_trade.md#the-pump)).

## 到达游戏层

游戏以下的每一层均可双向工作（[Pia 层](pia.md)）：本地协议 0x24、站点握手 0x14、网状网络加入 0x18、RTT 0x58，以及可靠窗口 0x7C 和 0x80。

加入端的 0x14 连接响应必须采用《剑》发送的 840 字节格式（`host4.build_host_response`：账户 id 位于 0x11，玩家名字位于 0x88，尾部位于 0xB1，令牌位于 0xBC）。模拟《盾》1.3.2 主机端接受过 56 字节响应（在 `[0x37]` 处为 1，其后全零），将站点加入网状网络，但从未发送游戏消息；提供 840 字节格式后，它在加入响应后 0.03 s 发送第一个 ping，以加入端名字打开交换盒子并完成交换。零售版《剑》也曾在 17 字节响应后完成交换，此时 0x11 之后的字段实际从缓冲区旧字节中读取（[Pia 层](pia.md#what-a-connection-response-must-satisfy-to-be-read)). `bin/swsh_connect.py --respond` 发送 840 字节格式。

如果不作响应，主机会重复发送 `61 00 00 00 0a 00`，即 ping（每秒约四次）；0x80 每秒请求一次确认 id 1，0x7C 则保持静默。`bin/swsh_connect.py --send-data HEX --send-protocol 0x7c` 发送应用数据（`reliable4.build_data_message`，与主机自身数据逐字节一致；五项静默接收检查：[版本 4](pia.md#version-4)）。通过信号：0x80 确认 id 不再停留在 1；0x7C 开始发出确认。

## ping 握手

负载由一个四字节小端序消息 id 和一个 protobuf 消息体组成。握手仅携带以下五种消息，没有其他消息（右列是在一次抓包中各消息的数量）：

```
0x7C  61000000 0a00      97 SyncPingDataHolder, field 1 ping {}           x20
0x7C  61000000 1200      97, field 2 pingReply {}                          x2
0x7C  61000000 1a00      97, field 3 pingSynced {}                         x3
0x7C  60ea0000 0a00      60000 BlockDataHolder, field 1 result {}          x2
                         (Result { bool isBlocking })
0x80  60ea0000 12020801  60000, field 2 imReady { isReady: true }          x2
```

(`gflnet.p2p.sync.ping.pb`, `gflnet.p2p.block.pb`。）响应会分五步推进游戏：

```
1  answer the ping continuously   --send-data 610000000a00 --send-mirror --send-count N
2  ack every reliable window      0x7C, 0x18 port 1, 0x80; one unacked window kills the mesh
3  answer `result{}` on 0x7C      the mirror is per protocol
4  answer imReady on 0x80         --send2-data 60ea000012020801
5  the console sends its party on 0x84
```

-
-
-
-

`bin/swsh_connect.py --sync-answers` 在已有规则时响应 `trade.SYNC_ANSWERS`，其余情况按协议回显，并打印每个没有规则的负载（显示在它所触发的响应之后；请查看 ownerId）。

## 离开

《剑》离开交换会话时发送盒子命令 3，约 0.77 s 后开始执行对应角色的 Pia 离开流程。每一步都等待回复，无回复时在超时后继续下一步。

已加入主机端的《剑》离开时：

| 步骤 | 《剑》发送 | 主机端应回复 | 无响应时 |
| --- | --- | --- | --- |
| 离开网状网络 | LEAVE_REQUEST `04 `，0x18 端口 1，可靠，发送一次 | LEAVE_RESPONSE `08 ` | 5.0 s |
| 站点断开连接 | `03`，在 0x14 上，每 0.5 s 一次 | `04` | 8 个请求，3.6 s |
| LDN | 离开网络 |  |  |

两者均无响应时，《剑》（零售版，或模拟《盾》）在 LEAVE_REQUEST 后 9.0 至 9.1 s 离开 LDN 网络。如果 `08 00` 发送两次，并且 `04` 得到响应，零售版《剑》会在 LEAVE_REQUEST 后 0.04 s 发送一次 `03`，并在该请求后 0.14 s 离开。

-
-

`pokeldn/ldn/host4.py` 对两者均作响应。

作为主机端的《剑》离开其客户端时（它是 LDN 接入点）：

| 步骤 | 《剑》发送 | 客户端应回复 | 无响应时 |
| --- | --- | --- | --- |
| 网状网络迁移 | MIGRATION_START `44 00 01` ([主机端迁移](swsh_trade.md#host-migration)) | 由指定站点发送 MIGRATION_FINISH，以及将自身指定为主机端的 UPDATE_MESH | 5.0 s |
| 本地会话 | 主机迁移字节为 1、带新序号 id 的会话更新（0x24 类型 0x11），约每 0.11 s 一次 | 针对该序号 id 的 0x21 确认 | 10.0 s |
| 销毁网络 | START_HOST_MIGRATION `01 13 00..`（16 字节），每 0.33 s 一次 | 离开 LDN 网络 | 10.0 s |

在零售版《剑》上测量，从 MIGRATION_START 到其最后一个数据包：

| 客户端响应内容 | 网状网络步骤结束 | 最后一个数据包 |
| --- | --- | --- |
| 无（5 次抓包） | 5.0 s | 25.0 s |
| MIGRATION_FINISH 和将自身指定为主机端的 UPDATE_MESH，重复发送 | 0.1 s | 20.1 s |
| MIGRATION_FINISH（已确认）、确认、离开 | 5.0 s | 5.07 s |
| MIGRATION_FINISH、将自身指定为主机端的 UPDATE_MESH、确认、离开 | 0.07 s | 0.17 s |

仅完成消息得到确认时，主机会持续确认客户端数据 4.8 s；加入 UPDATE_MESH 后，它在开始后 0.07 s 就停止发声。

-
-
-

`bin/swsh_connect.py --answer-migration --update-mesh --leave-with-host`（位于 `--preset trade`）发送完成消息和将自身指定为主机端的 UPDATE_MESH，确认主机迁移会话更新，并在收到 START_HOST_MIGRATION 时离开网络。

## 操作说明

-
-
-
