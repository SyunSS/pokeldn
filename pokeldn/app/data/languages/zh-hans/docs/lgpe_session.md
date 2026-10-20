---
title: 卡带、密钥与会话
parent: Let's Go Pikachu and Eevee
nav_order: 1
---

# 卡带、密钥与会话

地址均为 Let's Go 皮卡丘 1.0.2 解压后的 `main` 中的偏移量，按 `tools/switch/nso_read.py` 的布局：text `0..0xd32ba8`，rodata 起于 `0xd33000`，data 起于 `0x1527000`.

## 游戏程序的组成

更新 NSP 包含 Program NCA `2b7730a9e56498bbafac2002d4908c6b`（游戏 ID `010003f003a34000`，rights id `010003f003a348000000000000000007`，密钥代数 6）。其 exefs 包含 `main`（压缩后 13.0 MB）、`rtld`, `sdk`, `subsdk0` 和 `subsdk1`；所有 `nn::pia` 和 `gflnet3` 引用均位于 `main`.

```
./.venv/bin/python tools/switch/xci_read.py "<the .nsp>" --keys prod.keys \
    --nca 2b7730a9e56498bbafac2002d4908c6b --exefs 0 --extract main
./.venv/bin/python tools/switch/nso_read.py main main.bin
./.venv/bin/python tools/switch/rtti_names.py main.bin 0xd32ba8
```

Pia 采用静态链接：269 个 `nn::pia` 类，2112 个具名虚方法。`nn::pia::local` 包含 `Ldn*` 和 `Local*` 系列（`LdnCreateNetworkJob`, `LdnCreateSessionSetting`, `LdnJoinSessionSetting`, `LocalProtocol`). `nn::ldn` 从 nnSdk 导入（`CreateNetwork`, `Connect`, `Scan`, `SetAdvertiseData`, `GetSecurityParameter`，以及 `*Private` 变体），GOT 槽位 `0x15fa1e0..0x15fa2a8`。在 Pia 之上，`gflnet3` 捆绑了 Protocol Buffers（`lib/gflnet3/external/include/google/protobuf/`).

## LDN 口令

```
W3GoSMEn7RIIUQ89rzqBHGhGferRNb7K18ZBq2aNuj8Us9RO9Q9JYyGOZlLy8MYL
```

位于 `0xf73a50` 的 64 字节，直接按原始字节使用，与《剑／盾》相同。两个调用点以字面长度 `0x40`:

```
0x004db6b4  adrp x1, #0xf73000 ; add x1, x1, #0xa50
0x004db6c4  mov  w2, #0x40
0x004db6c8  bl   #0x5c0fb0              LdnCreateSessionSetting passphrase setter

0x004dbba4  adrp x1, #0xf73000 ; add x1, x1, #0xa50
0x004dbbb0  mov  w2, #0x40
0x004dbbbc  bl   #0x5c1280              LdnJoinSessionSetting passphrase setter
```

`LdnCreateNetworkJob`（构造函数 `0x5ce640`，使用《剑》的偏移量）将口令保存在 +0xC4，将其长度保存在 +0x104，并据此构建 `nn::ldn::SecurityConfig`，然后调用 `nn::ldn::CreateNetwork` (`0x5ce988`，PLT 桩 `0xd31c78`).

## Pia 游戏密钥

```
p1frXqxmeCZWFv0X
```

位于 `0xefd659` 的十六个 ASCII 字节，即 wiki 为《剑／盾》《传说 阿尔宙斯》和《朱／紫》列出的字面密钥。一个调用点根据模式字段的值，有条件地将其存入加密设置：

```
0x0011a364  ldr  w9, [x19, #0x98]
0x0011a368  orr  w9, w9, #2 ; cmp w9, #2 ; b.ne   (mode 0 or 2 takes the key)
0x0011a374  adrp x9, #0xefd000 ; add x9, x9, #0x659
0x0011a380  ldp  x10, x9, [x9]
0x0011a384  stp  x10, x9, [x8]          x8 = setting + 0x24c
```

## Pia 头部

版本 3（wiki 中的 Pia 5.11-5.17）。初始化函数 `0xd122d4` 通过一次 64 位存储写入魔数和版本，`0x00000003_32AB9864`；验证函数 `0xd12400` 检查魔数及 `(byte & 0x7f) == 3`.

```
0x00  4  magic 0x32AB9864, big-endian
0x04  1  0x80 (encrypted) | version (0x7F) = 3
0x05  1  connection id
0x06  2  packet id
0x08  8  AES-GCM nonce
0x10  16 AES-GCM tag, not truncated
0x20     ciphertext
```

采用 wiki 中的 5.11-5.21 布局，除版本字节外与《剑》的版本 4 相同；`pokeldn/ldn/pia4.py`.

## 消息分帧

固定 22 字节的消息头部（Pia 5.11-5.12；5.18 及更高版本使用字段存在标志）。`ProtocolMessageAccessor::Header` 的反序列化函数 `0x5ae870` 拒绝少于 `0x16` 字节的数据；写入函数 `0x5aeb00` 在字节 1 处存入字面值 1。

```
0x00  1  message flags: 1 = destination is a bitmap, 2 = relay needed, 4 = relayed, 8 = unbundled
0x01  1  version, always 1
0x02  2  payload size, big-endian
0x04  1  protocol type
0x05  1  protocol port
0x06  8  destination, big-endian: a constant id, or a station bitmap when flag 1 is set
0x0E  8  source constant id, big-endian
0x16     payload, then padding to a multiple of 4
```

`pokeldn/ldn/pia3.py` 在 pia4 的头部基础上实现它。

## 会话密钥

`LocalProtocol` 的派生过程 `0x5cd560` 与《晶灿钻石／明亮珍珠》和《剑》相同：用一个 32 位值为 SEAD xorshift128 设种（`0x57cfc0`，递推代码位于 `0x6C078965` 附近），抽取四次得到十六字节，再使用位于 `LocalProtocol+0x49c` 的游戏密钥执行 AES-128-ECB（启用标志为 +0x498）。`pokeldn.ldn.pia5.ldn_session_key`.

广播通告的应用数据（Pia 5.9-5.18）以 24 字节头部开头：

```
0x00  4  network id, random per session
0x04  4  CRC32 of the user password
0x08  1  system communication version, 4 for 5.11-5.17
0x09  1  header size, 0x18
0x0A  2  padding
0x0C  4  session param
0x10  8  zero
0x18     the game's application data
```

种子是 +0x0C 处的会话参数。来自一台 Let's Go 皮卡丘主机端的 392 个数据报中，392 个均在 `ldn_session_key(game key, session param)` 下使用 pia4 IV 通过认证（`crc32(network id little-endian || host MAC)` 的三个字节、值为 0 的源 ID 字节，以及头部中的八字节 nonce）。

## 连接密码

连接密码就是 NetworkInfo 的 scene id；应用数据 +4 处的密码 CRC32 始终为 0，SSID 始终为 `01000000000000000000000000000000`。scene id 为 `1000a + 100b + 10c + 1`，每次选择取其在选择器中的索引（皮卡丘 0、伊布 1、妙蛙种子 2、小火龙 3、杰尼龟 4、波波 5、绿毛虫 6、小拉达 7、胖丁 8、地鼠 9）。

它在运行时构建：`0x891580` 将各次选择合并成 `100a + 10b + c`, `0x978080` 计算 `10 * number + mode`，模式 1 表示交换（模式 2 和 3 来自 `0x9765f4` 处的 switch，其功能尚未分析）。该值经由 `0x349010` 和 `0x4da710` 传给会话构造函数 `0x4db1e0` (`u16`，位置为 `+0x302`); `0x4db6ac` 将其放入 `LdnCreateSessionSetting+0x60`，Pia 则将其复制到 `NetworkConfig.intentId.sceneId`，然后调用 `nn::ldn::CreateNetwork` (`0x5ce988`).

同一个构造函数还选择搜索中的主机在作为主机端时使用的信道：`{1, 6, 11}[scene % 3]`，表 `0xf73a44`，索引位置为 `0x4db248..0x4db254`; `pokeldn.lgpe.search_channel(code)`.

| 主机搜索时使用的密码 | 通告的 scene id | 信道 |
| --- | --- | --- |
| 皮卡丘、皮卡丘、皮卡丘 | 1 | 6 |
| 妙蛙种子、小火龙、杰尼龟 | 2341 | 6 |
| 妙蛙种子、小火龙、妙蛙种子 | 2321 | 11 |
| 伊布、皮卡丘、地鼠 | 1091 | 11 |
| 皮卡丘、皮卡丘、妙蛙种子 | 21 | 1 |

搜索中的主机仅在另一个网络于本机所用信道上通告了与本机相同的 scene id 时，才会加入该网络。`bin/lgpe_host.py --code NAMES` 在密码对应的信道上作为主机端（`--channel auto` 则扫描主机的网络）；Let's Go 皮卡丘和 Let's Go 伊布都能加入。`bin/lgpe_join.py` 不发送密码，主机端主机也能与它交换。

## Local Protocol 的实测结果

会话状态通过 Pia 协议 0x24、端口 0 发出，与《晶灿钻石／明亮珍珠》和《剑》相同：采用 wiki 中 5.7-5.45 的 update-session 消息（`pokeldn.ldn.local_protocol.parse_update_session`）。它包含一个 12 字节本地头部（版本 1，类型 0x11）、序列 ID、本地网络 ID、主机端可变 ID、服务可变 ID 和常量 ID、一个允许参与字节，以及八个节点（IPv4 地址、端口、迁移排序）：主机端 `169.254.105.1` 排序为 0，加入端 `169.254.105.2` 排序为 1，其余为 255。

消息体以小端序携带主机端常量 ID（`000048f120229beb`, `station_protocol.ldn_constant_id`，基于 MAC `48:f1:eb:20:9b:22`）；Pia 消息头部以大端序将其作为源（`eb9b2220f1480000`），与《剑》相同。

## 用于加入网状网络的 Station Protocol

先在协议 0x14 上发出连接请求，再在 0x18 上加入网状网络。连接请求处理函数 `0x5b8800` 读取 wiki 中 5.10-5.18 的布局，即 Station Protocol 版本 9：

```
[0]     message type            1
[1]     connection id
[2]     version number          must be 9 (`cmp w8, #9` at 0x5b8848; 5.27-5.45 checks a platform)
[3]     is inverse connection request; rejected above 1
[4]     target constant id      big-endian u64, compared against the console's own at 0x5b6830
[0xC]   target variable id      big-endian u32, checked only when [3] is 1 (0x5b6840)
[0x10]  inverse connection id   compared against the station's own record at +0xA0
[0x11]  station location        the 5.11-5.45 layout, unchanged from Sword
[...]   ack id                  u32, the message size minus four
```

《剑》的版本 4 请求（[2] 处为平台字节，[3] 处为移位标志）和 5.29-5.45 的布局（[1] 处为协议列表），在这里都会使所有字段错位。目标常量 ID 是主机根据自身 MAC 得到的 ID；加入端的 location 携带其常量 ID、可变 ID 和服务可变 ID。

零售版 Let's Go 皮卡丘会执行完整的版本 9 序列，其中包含 5.27 移除的反向连接请求：

```
->  connection request (type 1, is_inverse 0, target the host constant id, own location)
<-  type-5 ack; inverse connection request (type 1, is_inverse 1) to the joiner's constant and
    variable ids, with the host's location and a trailing ack id
->  type-5 ack; connection response (type 2, result 0, host constant id at [5], variable id at
    [0xD], gate byte 1 at [0x37], padded to 0x38)
<-  connection response (type 2, result 0, 840 bytes, platform 4, the joiner's ids, a network
    id, one player info), repeated until acknowledged
->  type-5 ack
```

连接响应解析函数 `0x5b9270` 读取 `[1]` 处的结果，将 `[5]` 处的大端序 u64 和 `[0xD]` 处的大端序 u32 与自身 ID 比较，并读取 `[0x37]` 处的门控字节；当该字节大于等于 5 时，结果为 0 的路径会丢弃响应。

### 站点发送的连接响应

0x348 字节（解析函数接受 0x3C）：

```
0x00  1  message type 2
0x01  1  result
0x02  1  version 9
0x03  1  platform 4
0x05  8  the receiver's constant id, big-endian
0x0D  4  the receiver's variable id, big-endian
0x31  4  the network id, big-endian: the advertise data's first u32, read little-endian
0x35  2  01 01
0x37  0xC3  a PlayerInfo: the station name "username", then the Switch profile's nickname,
         then the language. Its first byte is the gate the parser drops when 5 or more
0x344 4  the ack id
```

PlayerInfo 是由 `station_protocol.player_info` 构建的 195 字节结构；零售版主机会在其中填写用户资料名称。`station9.build_connection_response(..., network_id=N, player_name=B)`; `bin/lgpe_join.py --player-name NAME` (`--short-response` 发送 0x3C 字节）。

连接请求中加入端的站点 location 为 36 字节：空的公网地址（端口为零），NAT 标志和 location 均为零，`station_location(..., public=False, nat_flags=0, nat_location=0)`.

## 加入网状网络

0x18 上的网状网络加入请求（`mesh_protocol.build_join_request`，类型 1，本地站点索引 253，末尾带确认 ID）会得到加入响应：类型 2，148 字节，两个站点，主机端索引 0，加入端索引 1，一个分片，两份包含双方 location 的站点信息，最大活动数 2，最大总数 8。主机端随后广播 update mesh（类型 0x20，524 字节，更新计数器为 1）。加入响应通过 0x14 上的类型 5 确认消息进行确认（`mesh_protocol.ack_for`）；加入端的站点索引为 1。

随后主机端持续发送 Local Protocol 的 update-session（0x24，以 0x21 确认）、RTT（0x58）、Sync Clock（0x1C）和 Clone（0x73）。加入端逐一应答，并从入座那一刻起发送自身的 RTT 和时钟同步请求。

## RTT Protocol（0x58），版本 3

十六字节：[0] 处为大端序 u32 类型值（《剑》中为一个字节），[8] 处为 u64，表示发送方 19.2 MHz 系统计时器的 tick。响应将类型设为 1，并原样复制 tick。每个站点约每秒请求一次。

```
00000000 00000000 0000000049845557     request
00000001 00000000 0000000049845557     the answer to it
```

`rtt_protocol.build_v3` 和 `response_for_v3`; `bin/lgpe_join.py --connect` 双向运行（`--no-rtt` 可将其关闭）。

## Sync Clock Protocol（0x1C）

由主机端控制的单调递增网状网络时钟（wiki 的 Sync-Clock-Protocol）。站点每两秒请求一次，并在主机端回复的值上加上往返时间的一半。

```
request, 16 bytes   [0] u64 the sender's system tick (19.2 MHz), [8] u64 zero
reply,   16 bytes   [0] u64 the tick copied back, [8] u64 the mesh clock in milliseconds
```

加入端在收到网状网络加入响应后立即发送第一次请求。Clone Protocol 使用的就是这一时钟；若主机端收到按加入端自身运行时间计时的克隆消息，它会释放克隆并离开。`pokeldn.ldn.sync_clock`; `bin/lgpe_join.py --connect` 运行该协议（`--no-sync-clock` 可停止）。

保活使用协议 0x08，无消息体，并以同类型消息应答。

## 承载游戏数据的 Reliable Protocol（0x7C）

Pia 5.11 的头部为 24 字节（5.29-5.43 中为 9 或 13 字节）；两个站点的 32 位序列 ID 均从 0xFFFFF82F 开始。

```
0x00  1  flags
0x01  1  stream id, 3 for the game's stream and 0 on an acknowledgement
0x02  2  payload size, big-endian
0x04  4  zero
0x08  4  sequence id, big-endian
0x0C  4  the next sequence id expected from the peer, big-endian
0x10  8  zero
0x18     the payload
```

确认消息只有头部，流和大小均为零。`pokeldn.ldn.reliable3`。载荷采用游戏自身的分帧格式（见下文“可靠协议上的游戏消息”）。

## Clone Protocol（0x73）

`nn::pia::clone::CloneProtocol`（GetProtocolId `0x158aab8`；SDK 字符串 `PiaCommon-5_11_4`）承载伙伴同步。类型字节 `0xAB`：高半字节表示结构，低半字节表示变体。每条消息都以版本 3、类型，以及大端序 u16 形式的发送方帧计数器开头（从发送方 Pia 会话开始计数，每秒约 60）。测量使用两个运行于 Ryujinx、通过 ldn_mitm 连接的 Let's Go 皮卡丘 1.0.2 端点；双方运行同一状态机。

### 时钟同步：最初两秒

双方以每秒约 5 次的频率发送时钟请求（类型 0x11，18 字节，序列化函数 `0x51f9b0`），并应答对方的请求（类型 0x21，22 字节，`0x51fab0`).

```
clock request                              clock reply
[0]   1  version 3                         [0]   1  version 3
[1]   1  type 0x11                         [1]   1  type 0x21
[2]   2  sender frame counter              [2]   2  sender frame counter
[4]   4  sender message count              [4]   4  sender message count
[8]   2  destination station bitmap       [8]   2  destination station bitmap
[0xA] 8  sender system tick                [0xA] 4  sender clone clock, ms
                                           [0xE] 8  the request's system tick, echoed
```

-
-
-
-

### 参与

十次请求得到应答后，加入端发送参与消息（类型 0x31，10 字节，序列化函数 `0x51fbd0`）：头部、消息计数、位图 0x0003。主机端以 0x33、位图 0x0002 应答，然后发送自身的参与消息；加入端以 0x33、0x0001 确认。从第一次参与消息起，时钟回复使用类型 0x22。

### 克隆元素

克隆由克隆类型（1 到 4）、所属站点（无所属站点时为 0xFD）和 32 位克隆 ID 共同标识。两个站点都会发布自身的副本。首次交换时，随着交换界面推进，主机端依次创建 ID 1、2、3；后续每次交换都会通告更多 ID。双方均参与后，克隆类型 3、ID 0 的克隆就会存在。

```
every command message   [0] version 3, [1] type, [2] u16 the sender's frame counter,
                        [4] u8 clone type, [5] u8 owning station, [6] u16 0,
                        [8] u32 clone id
types 0x81 to 0xc4      [0xC] u32 the sender's message count, [0x10] u16 destination bitmap,
                        then the structure's own fields
types 0xd1 to 0xf4      [0xC] the data, with no message count and no bitmap
```

低半字节为命令令牌加一：1 为通告（`SendClone::AnnounceCommandToken`, `0x522480`），2 为请求（`ReceiveClone::RequestCommandToken`, `0x520df0`），3 为结束（`SendClone::EndCommandToken`, `0x522490`），4 为锁定（`AtomicSharingClone::LockCommandToken`, `0x517820`）。高半字节表示结构；`0x51c110` 将其通过表分派，表为 `0xf769c4`:

| 类型 | 新增内容 | 消息、长度 | 接收分支 |
| --- | --- | --- | --- |
| 0x8N | 无 | 0x12 | `0x51c614` |
| 0x9N | [0x12] 处以毫秒计的 u32 时钟 | ClockCloneCommandMessage，0x16 | `0x51c62c` |
| 0xaN | 时钟、[0x16] 处的 u8 计数、一个 u8 和一个 u16 | ClockAndCount，0x1a | `0x51c64c` |
| 0xbN | 时钟、[0x16] 处的 u32 参与者位图 | ClockAndParticipant，0x1a | `0x51c66c` (`0x51c680`) |
| 0xcN | 时钟、计数、[0x1A] 处的位图 | ClockAndCountAndParticipant，0x1e | `0x51c68c` |
| 0xeN | [0xD] 处的 zlib 流 | 克隆状态，用于确认 |  |
| 0xfN | [0xD] 处的一个字节、[0xE] 处的 zlib 流 | 克隆状态及其数据 |  |

zlib 流解压后得到一条记录：标签 0x20、其长度、一个 u16 克隆 ID，以及副本为空时的值 1、填充后为 3：

```
0x20 0x06 u16 clone id  0x01  0x00
                                      a copy with nothing in it yet
0x20 len  u16 clone id  0x03  u8 the station the data belongs to  u16 0
          u16 participant bitmap  u32 clock  then the clone's data
0x20 0x0A u16 clone id  0x05  u8 the station being acknowledged   u32 clock
```

站点先发布六字节形式，随后发布填充后的形式；六字节形式表示正在重试的发布，稳定会话不再构建记录。deflate 过程为一次压缩、一次同步刷新和最后一个空块，压缩级别为 2 到 5；`clone.pack_record` 可以复现捕获到的每一条流。0xfN 头部 [0xC] 处的字节携带记录的参与者位图，0xeN 头部同一位置则携带其确认的站点。

| 交互 | 消息 |
| --- | --- |
| 所有者通告 | 0xa1，以及带参与者位图的 0xb1；对方在数据发出前以 0xa2 和 0xc1 应答 |
| 接管 | 对方以 0x91 应答 0xa1 |
| 数据 | 所有者发送 0xf3；对方发送携带相同时钟的 0xe3 |
| 释放 | 0x83；以 0x84 确认 |
| 离开克隆会话 | 0x32；0x41（14 字节，[0xA] 处为应答方位图）；未得到应答的 0x32 会持续重发，直到游戏放弃 |

0xa2 携带网状网络时钟和计数；克隆类型 4 的计数为 1，克隆类型 2 为 0。

`ClockAndCountCloneCommandMessage`（虚表 `0x158ac58`，序列化函数 `0x51f4c0`）以大端序写入：`+0x1c`（时钟）位于 [0x12]，`+0x20`（计数）位于 [0x16]，`+0x21` 位于 [0x17]，`+0x22`（u16）位于 [0x18]。计数来自克隆的 vfunc 16：SendClone 为 0（`0x519290`), `+0x112` 对应 ReceiveClone（`0x520de0`), `+0x188` 对应 AtomicSharingClone（`0x517800`）。字节 `0x17..0x19` 是栈残留，接收方均不读取：构建函数（`0x51b3b0`, `0x51cb64`, `0x51ccf0`, `0x51cd8c`）不写入计数之后的任何内容，而清扫函数 `0x51b380` 会复用缓冲区，其 0xbN 路径会在那里留下一个参与者字（`0x51b7a0`），因此 `01 2808ab`. `0x51c110` 原地解析；每份载荷均从接收循环 `0x51ad90` 或回环（`0x51e330`, `0x51e4c4`).

`0x51c110` 读取公共头部（`0x51c2c0`: `[8]`, `[4]`, `[5]`），对于 0x80..0xc0 组还会读取字节 0x10-0x11（`0x51ce80`，表 `0xf76e08` -> `0x51ced0`），然后读取上表中的字段，不再读取后续内容。克隆类型表 `0xf769e4`（索引 `[4] - 1`）将 0xa1 和 0xa2 路由至仅接收克隆、站点和时钟而不接收缓冲区的处理函数：

| 克隆类型 | 0xa1 | 0xa2 |
| --- | --- | --- |
| 1 | `0x51c714` -> `0x51cb38`, `0x522350(clone, station, clock)`；未知克隆会得到 0x91 | 忽略 |
| 2 | 忽略（`0x51c3b8`) | `0x51cafc`, `[5]` 必须是本地站点，`0x520ce0(clone, clock)` |
| 3 | `0x51c934` -> `0x51cc00`, `0x522a60` | `0x51c838`, `0x522b20(clone, station, clock)` |
| 4 | `0x51c8c0` -> `0x51cbc4`, `0x522a60` | `0x51c838` |

携带缓冲区的后续调用（`0x51c268`, `0x51c2fc`, `0x51c32c`, `0x51c784`, `mov x3,x22; b 0x51d450`）用于处理其他消息类型。

`0x522a60` 是克隆类型 3 和 4 的 0xa1 处理函数；当元素状态 `[x0+0x38]` 不为 1 时返回 1，当发送方对应位已在 `[[x0+0x30]+0xc0]` 中置位时返回 2，否则记录站点并返回 0。调用方对返回值 0 发送类型为 `0xfd04` (`0xfd03` 的 0xa2（克隆类型 3 使用 `0x51cd00`），对返回值 1 发送 0x91（`0x51cbe4`），对返回值 2 不应答。针对未知克隆的 0xa1 会直接得到 0x91（`0x51c494`). `0x51c110` 会在目标检查 `0x51ce80`、按发送方进行的计数过滤（`0x51c1e0`：位于 `proto+0x714+4*station` 的计数至少为消息中的 `[0xC]`），以及长度和类型范围检查处静默丢弃消息。

掩码 `+0xc0` 属于克隆协议对象，与其站点掩码 `+0x38` 和状态字 `+0x40`:

| 事件 | 对以下字段的影响：`+0xc0` | 地址 |
| --- | --- | --- |
| 状态变为 `0x22`（当 `[[proto+0x48]+0x24]` 为 2 到 4 时） | 设为 `+0x38` | `0x51b060..0x51b06c` |
| 状态变为 `0x42` | 设为 `+0x38` | `0x51b140..0x51b150` |
| 站点加入，当前状态为 `0x22` 或 `0x31` | 对应位置位 | `0x51bc64..0x51bc88` |
| 收到 10 字节的 0x33，当前状态为 `0x31` 或 `0x22` | 清除发送方对应位 | `0x51c354..0x51c3b4` |
| 收到 14 字节的 0x41，且 `[0xa..0xd]` 等于 `[proto+0x3c]`，状态为 `0x42` | 清除发送方对应位 | `0x51c380..0x51c3b4` |
| 站点离开 | 清除对应位 | `0x51bce0..0x51bce8` |
| 站点离开，当前状态为 `0x42` | 设为 `+0x38` | `0x51bd04..0x51bd18` |
| 其他路径 | 清零 | `0x519a1c`, `0x519ccc`, `0x51a2d4`, `0x51a7d0`, `0x51a9c0` |

在状态 `0x22` 中，协议等待掩码清空后才转至 `0x31` (`0x51b074..0x51b084`).

### 克隆 0 消息对

克隆类型 3 中克隆 0 的所有者通过一个 0xa1 和一个 0xb1 通告它；另一站点以 0xa2 和 0xc1 应答，之后所有者才发布。未得到应答的零售版主机端（`--withhold-clone0-answer` 用于 `bin/lgpe_join.py`，仅供测试）在首次 0xa1 后 114 ms 再次发送 0xb1 和 0xa1，又过 108 ms 单独发送 0xb1，并接受针对重发消息的应答。若主机端只发送一次消息对且应答丢失，主机会停留在“即将连接”界面，此后只有时钟流量。`bin/lgpe_host.py` 每 110 ms 重发一次消息对，最多 20 次，直到收到主机的 0xa2、0xc1 或 0x91。已经应答过第一组消息对的零售版主机（`--ignore-clone0-answer` 在启动器上忽略该应答，仅供测试）会以 0xa2 应答重发消息。

### 可靠协议上的游戏消息

在 `0x7c` 上，每条消息都由 16 字节头部和消息体组成：

```
+0x00  4  kind: the channel id, 1 to 4 in one trade
+0x04  4  body length: 0x168 for kind 1, 0xe8 for kinds 2 and 4, 4 for kind 3
+0x08  4  step, counting every message a station sends from 1
+0x0c  1  tag, 0 on every trade message
+0x0d  1  destination station index, 0xff for every station
+0x0e  2  zero
+0x10     the body
```

`0x116f30(mgr, kind, buf, len, tag, dest)` 在 `mgr+0x288` 处构建头部，步数为 `mgr+0x274` 加一。交换发送方通过 `0x4d94e0`（标签 0，目标 0xff）：`0x34945c`（类型 1）、`0x34a24c`（出示内容）、`0x838300` 和 `0x83838c`（提交）。`0x4d9520` 从调用方获取这两个值；其调用方是 `0x9dce94..0x9dede8` 中的对战场景发送函数，其中一个使用标签 3。

接收函数 `0x1171d0` 从任意站点取出队列中第一条步数为该站点下一步的消息（`mgr+0x278[station] + 1`, `0x117334..0x117354`），每条取出或丢弃的消息都会计数。它会丢弃（`0x11722c`）目标既不是 0xff、也不是本地站点索引的消息，本地站点索引为 `mgr+0x1288`，会话前为 0xfd）；未有信道注册其类型的消息也会丢弃（16 项表 `mgr+0x110`, `0x117398..0x1173f8`）。属于其他已注册类型或标签的消息会保留在队列中，并阻塞其后来自所有站点的消息。交换接收方（`0x4d9570`）请求标签 0（`0x11746c..0x117478`).

类型值是信道 ID，由 `0x116e80` 从每会话计数器 `mgr+0x270` 中自 1 起分配（仅在会话开始时与步数计数器一起清零，`0x116a10`），并存储于 `chan+0x60`，执行者为 `0x4d9450`；已注册 16 个信道时（`mgr+0x118 > 0xf`），ID 为 0。`0x117920` 会压缩表，移除存活计数 `+0x54` 为零的信道。`0x4d9450` 的五个调用方：交换会话对象（`0x3492f8`）、队伍出示对象（`0x349d88`）、同步保存的状态 2（`0x8382a8`）、`0x347e10` 类（`0x3481fc`）、对战场景（`0x9dce1c`）。一次交换由前三者注册 1、2、3，再由交换后保存过程重新创建的队伍出示对象注册 4。每次注册还会通告一个克隆集（`0x4d94b8`，经 thunk `0x11b4c0` 进入 `0x11aec0`），因此克隆 ID 与信道 ID 不同。

这两个界限都不会限制一次入座期间的交换次数。计数器是未经检查便递增的 u32（`0x116ea4..0x116eac`），线上类型字段也是 u32，因此 ID 只有在注册 2^32 - 1 次后才回绕。16 项上限统计的是存活条目：每项保存一个弱句柄（`[chan+0x58]`，由 `0x4d98a0` 创建），而 `0x117920` 在活动会话的每一帧中由管理器更新函数 `0x1175d0` (`0x11761c` 调用），删除信道强引用计数 `handle+0x54` 为零的条目。提交信道随同步保存销毁（`0x838c40`），同步保存随其保存过程销毁（`0x835000`），发生于调度器离开状态 3 之前（`0x886670`）；出示信道随队伍出示对象销毁（`0x349dfc`），该对象在提交后释放（`0x886c70`），并由交换后保存过程替换（`0x3445e0`）。一次入座大约维持四个存活信道。

类型 1，消息体 0x168，身份信息：将存档的 MyStatus 块复制到 `obj+0x450` (`0x3493f4`），两个站点均在状态 6 发送，此时双方尚未收到任何内容。其中的训练家结构对应 PKHeX 的 `MyStatus7b`，名称使用 UTF-16LE：

```
+0x00  4  trainer id, then secret id
+0x04  1  version: 42 Pikachu, 43 Eevee
+0x05  1  gender
+0x35  1  language
+0x38 26  trainer name, up to the Pokemon name; --trainer-name on both launchers
+0x52 16  Pokemon name
```

为接收玩家制作的礼物从这里读取主机的训练家信息（`pb7.first_trainer`, [为接收玩家制作](gift_simulated.md#made-for-the-receiving-player)).

`pokeldn.lgpe.reference` 附带一份此记录，录自模拟存档，其训练家为 `POKELDN`. `bin/lgpe_join.py` 默认发送此记录，并将训练家 ID 对替换为 `--our-trainer`.

类型 2，消息体 0xe8，为出示内容；当站点发布的状态字变为 2 时立即发送，每当玩家更换出示的宝可梦时再以新的步数发送一次（选择过程会浏览盒子）。新步数会得到应答；重复步数属于重传，不再应答。

发送方是队伍出示对象（构造函数 `0x349bf0`，0x278 字节，位于 `mgr+0x68`）。其更新函数 `0x34a210` 会发送位于 `+0xa0` 的结构，只要 `+0x270` 已置位且 `+0x272` 未置位，随后清除 `+0x270`. `0x34a3d0` 由交换 UI 在选择改变时调用（`0x8f0c04`, `0x8f0c38`, `0x8f8fb0`, `0x90b87c`, `0x90b8c0`），将宝可梦打包到 `+0xa0` (`0x7294e0`），并设置 `+0x270`，前提是状态允许（A 0：本地状态不为 1 或 2；A 1：本地状态为 3 或大于 4；A 2：从不允许；A 3：伙伴正在离开，`0x3490c0`). `0x344620` 在提交后销毁该对象（`0x886c70`），连接结束时也会销毁（`0x8869f0`）；交换后的普通保存会重新创建它（`0x8375a4`），并使用新的信道 ID。

类型 3，消息体 4，为提交，是同步保存发送的 u32（见下文“提交与交换锁”）：每个站点都发送 1，其中一方收到对端的 1 后发送 2。负责发送 2 的站点在取出对端的 1 时发送它（状态 5，`0x838310`）；在状态 6 收到 2 会提交，其他消息体均忽略（`0x83839c`），因此加入端额外用 2 应答 2 也可以接受。提交后，站点显示旋转等待图标，不再显示按钮提示。交互未完成会使交换锁保持设置状态。

类型 4，消息体 0xe8，使用普通保存过程在其 `SaveThread` (`0x8377ec`, `0x8375a4` 后 3000 ms 重新创建的队伍出示对象的信道），发生于交换演示之后，并携带下一次交换的选择：先是站点的第一个槽位（与其步数 2 的出示内容逐字节相同），随后每次选择发送一条。类型 4 发出前交换已经保存；类型 4 开启下一次交换。

从 0 开始计数的第 r 次交换，在类型 2 + 2r 上出示，在 3 + 2r 上提交，并以 4 + 2r 结束；后者是第 r + 1 次交换的出示信道（`0x116e80` 从每会话计数器分配 ID；调度器每次交换都重新注册两个信道）。实测连续两次交换中，第 r 次交换的队伍克隆对为克隆 2 + 3r 与 3 + 3r，提交克隆为 4 + 3r；某次交换保存后通告的克隆对属于下一次交换。作为主机端时，`bin/lgpe_host.py --next-offer` 在后续每次交换中以其下一条记录应答主机的选择。作为加入端时，主机端主机的第一条类型 4 是其第一个槽位：`bin/lgpe_join.py` 用其下一份 `--offer` 应答该消息及后续每次选择，在类型 5 上应答提交，并将类型 6 视为该次交换结束；最后一条记录之后不再应答。

两个启动器都会在交换提交值 2（无论发送还是接收）时写入本次收到的记录，因为这会在主机上提交交换；仅出示后又撤回的内容不会写入。

主机端主机对后续每次交换都采用与首次相同的流程：第一条类型 4 前通告下一组队伍克隆对，每次选择对应一个类型 4 步数，确认时通告提交克隆，在类型 5 上提交，并在类型 6 前通告再下一组克隆对。`bin/lgpe_host.py --lead` 扮演主机端主机，无需提示即主动出示并投票，用于 `bin/lgpe_join.py`; `tests/test_esp32.py` 在两者之间双向各交换两条记录。

完整的一次交换，双方分别计数自身步数：

```
step 1  kind 1   identity
step 2  kind 2   the offer, again under a fresh step per selection
step 5  kind 3   commit, body 1
step 6  kind 3   commit, body 2
step 7  kind 4   the first slot, again under a fresh step per selection
```

类型 2 和 4 的消息体为 232 字节盒装结构：第七世代布局配合第六世代加密；+0x00 为加密常量，+0x04 为值为零的有效性检查字，+0x06 为校验和，从 +0x08 起的四个 56 字节块按 `((ec >> 13) & 0x1F) % 24` 排列，再与以该常量为种子的 16 位 LCRNG 流进行 XOR。`pokeldn.lgpe.pb7` 对捕获的出示内容执行往返转换后可逐字节还原。

状态字位于 `f3` 状态数据的字节 12；站点拥有的每个克隆都会依次经过 0、1、2。站点发布 2 并发送自身的类型 2 后，便等待对端的类型 2。

### 游戏自身首条消息的放行条件

连接交换对象逐帧运行的状态机为 `0x349200`（跳转表 `0xf4e994`，依据 +0x68）。状态 6 无需网络输入即可发送第一条游戏消息：两个站点在尚未收到任何内容时，先后相隔 18 ms 发出该消息。唯一的门槛是状态 4，`0x11b080`，检查 Pia 信道是否就绪：

-
-
-
-

SendClone 的检查函数为 `(element+0x3C & ~clone+0xA8) == 0`，SharingClone 的检查函数为 `((clone+0x114 | ~clone+0xA8) & element+0x3C) == 0`；两者共用一个元素。正常会话中，已确认集合逐渐填满，`+0x114` 逐渐清空，且每个 `+0xD8` 变为 1，而参与集合从一开始就是满的。站点对应位只有通过该站点发来的克隆类型 2 上的 0xa2 才会进入 `clone+0xA8`（`0x51c52c` 的跳转表 `0xf76c38` 转入 `0x522350`).

状态 7 将每条到达的首条消息存储在 `this + node * 0x1C8 + 0xC0`，并在 `this+0x470` 处计数；自身消息会回环，因此伙伴不发消息时计数停留在一。

### 作为主机端让零售版主机进入交换界面

主机加入所托管会话时，除加入端各协议层外还需要满足以下条件：

-
-
-
-
-
-
-

### 一次交换经过的两条克隆记录

交换对象在自身克隆上发布状态，并读取对端的状态。克隆类型 2 副本的 20 字节数据包含五个字，由 `0x11bc00` 及同类函数写入：

```
+0x00  4  the state: 1 a vote (0x11bc00), 2 a vote withdrawn (0x11b4e0), 4 a forced leave (0x11bcf0)
+0x04  4  that call's argument, 1 on selection and 2 on confirmation
+0x08  4  a counter, incremented on each call
+0x0c  4  the station's own step, the number of game messages it has sent
+0x10  4  the trailing word
```

克隆类型 4 副本的 32 字节数据表示会话主机端（权威端）的视图：

```
+0x00  4  A, the agreed argument
+0x04  4  B
+0x08 16  one counter per station index (host 0, joiner 1): the counter of the vote it last saw withdrawn
+0x18  4  the station's step
+0x1c  4  the trailing word
```

权威端逻辑 `0x11b6c0` 在会话主机端的每个 tick 运行。只有当每个站点都在当前末尾字对应的轮次发布状态 1、参数 X 时，才会将 A 改为 X，并将 A 与加一后的末尾字一起发布；状态 4 则立即改变 A。对于状态为 2 且参数与 A 不同的站点，它把该站点计数器写入其槽位，将末尾字加一，保持 A 和 B 不变，并在新的末尾字下重新发布自身类型 2 数据。

交换界面的状态由 A 及自身记录的状态通过 `0x34a300` 得出（跳转表 `0xf4e9b0`，依据 A）；`+0x271` 已置位且 `+0x272` 未置位时，优先返回 1。

| A | 本地状态 0 | 1 | 2 | 3 | 4 |
| --- | --- | --- | --- | --- | --- |
| 0（表 `0xf4e9d0`) | 0 | 1 | 1 | 0 | 0 |
| 1（表 `0xf4e9f0`) | 2 | 3 | 3 | 0 | 2 |

无论本地状态如何，A 2 都返回 4，A 3 都返回 5，即伙伴正在离开（`0x3490c0`).

类似的状态函数 `0x3488b0`（表 `0xf4e920..0xf4e980`，循环 `0x9c3300`）属于类 `0x347e10`（0x718 字节，位于 `mgr+0x70`，由 `0x344690` 创建），该类由 `0x886530` 在模式 1 和 2 下创建。

交换 UI 的更新逻辑（`0x756a20`，子状态 `[ui+0xa8]`）基于队伍出示对象（`0x7568ec`）运行。确认操作投票 2（`0x756e34` -> `0x34a4e0` -> `0x11bc00`），进入子状态 2（`0x757058`）。此时状态 4 会将 5 写入 `[[x21+0x78]+0x60]`，调用 `0x74a590(ui, 2)` 并继续（`0x756c0c..0x756c38`）；状态 2 返回选择界面（`0x756cb4`）；状态 1 或 3 下菜单结果为 3 时会撤回投票（`0x756d94` -> `0x34a500` -> `0x11b4e0`，状态 2）。在子状态 0 中，若状态为 1 且 `[x22+0x258]` 为零，则调用 `0x34a4a0` (`0x756b94`），这是另一种撤回操作。

`0x11b688` 将到达的克隆类型 4 记录暂存于 `+0x1638`; `0x11ba20` 比较 `+0x1638` 与 `obj+0x04`, `+0x163c` 与 `obj+0x10`，并将从 `+0x1640` 开始的每节点一个字与 `obj+0x0c` 比较。若主机端在此发布 32 个零字节，主机会停在“正在通信”界面，除“返回”外的按钮全部变灰。

出示队伍克隆依次经过 `1 1 1`，末尾字 1，然后是 `x 2 2`，末尾字 2。提交克隆的 ID 比队伍克隆高一，先采用前两种值，再采用零。零售版与模拟主机端的帧格式相同，克隆类型 2 数据均为五个字：

```
+0 ms     type 4 data, 32 zeros, with the announcement
          the peer publishes 1 1 1 step 0 once its player has confirmed
          1 1 1 step 0                 the host's own confirmation
+30 ms    1 1 1 step 1                 type 4 data 1, zeros, step, 1
+8 ms     the peer answers 0 1 1 step 1
+27 ms    0 1 1 step+1 1               the offered clone goes 0 2 2 step+1 2 in the same frame,
                                       and the kind 3 carrying 1 goes under that step
+3 ms     the peer's kind 3 carrying 1, its copies under its own next step
+63 ms    kind 3 carrying 2 under the next step, every copy republished under it
after the trade demo and the normal save (3000 ms past SaveThread, 0x8377ec):
          two more clones announced, 32 zeros on type 4; the peer publishes 0 0 0 on each
then      kind 4 under the next step, every copy republished under it
```

只有类型 4 副本的第一个字为 1 时，对端才应答末尾字 1；若它在对端的 `1 1 1` 到达前构建，就会携带 0，主机会继续等待。将提交克隆推进至 `1 2 2` 会得到 `0 1 1`，末尾字 2，没有类型 3，主机便停留在确认界面。

主机端主机总是先通告每个克隆：克隆 1、首个槽位前的队伍克隆对 2 和 3、A 2 之后的提交克隆 4（状态 1 的随机延迟，`0x8380d8`），保存后的下一对 5 和 6，然后才是第一条类型 4。它也先投票：`1 1 1` 用于克隆 3，A 1 配末尾字 1，`1 2 2`，A 2 配末尾字 2；提交克隆上为 `0 0 0`, `1 1 1`，A 1 配末尾字 1，随后为 `0 1 1`，并携带值 1 的类型 3，在通告该克隆后 152 ms 发送。加入端若接管每个克隆，并在自身状态字下重新发布主机端的前三个字和末尾字，即可完成交换。

确认操作令按钮变灰时再次按 A 会撤回投票：`2 2 3`（状态 2，参数 2，计数器 3），在 `1 2 2` 之后。以 A 2 应答会得到状态 4：主机开始同步保存，在提交交互之前提交交换锁（600）。这样应答的一台零售版主机重新发布了 `0 2 3`，5.0 s 后通告其提交克隆，随后在该克隆上不再发消息；交互没有完成，锁仍然设置，连接菜单拒绝下一次交换（`0x976634`）。采用同样应答的模拟主机则完成了交换（[尚未解决的问题](lgpe.md#unresolved)）。正确的应答，即类型 4 `1 0 0 3 0 0 step T+1`，会使该记录在 `0x11ba20` 下转为状态 0；A 1 配状态 0 得到状态 2（`0xf4e9f0[0]`），返回选择界面。撤回的选择 `2 1 4` 在 A 0 下会接受 `0 0 0 4 0 0 step T+1`. `bin/lgpe_host.py` 以此方式应答，并在一次发布中同意下一次投票；`tests/test_lgpe_host_withdraw.py` 通过游戏代码运行这两种情况。

两台零售版主机之间交换时，两个方向的克隆类型 4 和 1 都不携带克隆数据；但若主机端在那里不发布数据，加入的主机就无法通过门槛 `0x11b080`，停在搜索界面。

### 交换动画

主机在其步数 `0e` 之后播放交换动画，期间不发送交换载荷。以零售版 Let's Go 为主机端、连接 `bin/lgpe_join.py` 时，从该步起计：约 1.7 s 开始动画，约 15.3 s 出现收到的宝可梦（手动按键，最多延迟 2 s），27.0 s 收到主机的类型 4 载荷（248 字节），约 28.8 s 玩家恢复控制。

### 提交与交换锁

交换锁是存档 MyStatus 块中以秒为单位的 u32 倒计时。交换的保存过程将其设为 600，并在提交交互前将此值提交；交互完成后再次提交，将其设回 0。

MyStatus 块对象为 `[[[0x15fad08]]+0x98]+0x58` -> `+0x78`，数据 `obj+0x58`，0x168 字节（`0x1c9ff0`, `0x1ca000`，虚表 `0x153e0b0` 的槽位 5 和 6），也就是类型 1 的消息体。计数器为 `obj+0xe8`，MyStatus `+0x90`（设置函数 `0x1c9d40`，读取函数 `0x1c9d50`）。在 `savedata.bin` 中，该块位于 `0x1000..0x1168`（训练家名称位于 `0x1038`），计数器位于 `0x1090`：中断交换后保留的存档在该处保存 `58 02 00 00`，块内没有其他变化。捕获到的每条类型 1 都携带值 0，位置为 `+0x90`.

设置函数的调用方：同步保存传入 600（`0x837f90`, `0x837fb0`），应用收到的宝可梦时传入 0（`0x838bec`, `0x838c0c`），倒计时逻辑（`0x1ca54c`, `0x1ca56c`）；载入存档也会写入该块。连接菜单的检查函数 `0x9765f4` 根据连接模式分支：模式 1（交换）读取计数器（`0x976634`），非零时返回 -1，并显示拒绝提示 `0x0248810f825b1fee` (`0x97663c`）；为零时继续检查数量（消息 `0x0248800f825b1e3b`）。模式 3 在 `[x22+0x62] <= 1` 时拒绝（消息 `0x02487f0f825b1c88`).

锁随游戏时间倒计时。`0x1ca450(playtime, seconds)` 在 `seconds > 1` (`0x1ca46c`）或 `playtime+0x100` 未置位时立即返回（`0x1ca474`）；否则从计数器减去 `seconds`，下限为 0（`0x1ca500`），并将这些秒数加入游戏时间（`+0x54` 小时，u16，`+0x56` 分钟，`+0x57` 秒，上限为 999:59:59，`0x1ca5a0`). `0x1ca7e0` 将 `playtime+0x100` 写为 `nn::oe::GetCurrentFocusState() != 3`（后台）。其调用方 `0x1462a0` 每调用 20 次执行一次（计数器 `+0x70`），执行前提为启用字节 `+0x54` 已置位且不存在保存线程（`0x1ce8f0`）：它将 `GetSystemTick` 减去基准 tick（`+0x68`）后转换为整秒，再将相对于已计秒数（`+0x60`）的增量传给 `0x1ca450` (`0x146314..0x14637c`）；只有 tick 倒退时才移动基准（`0x146384..0x1463c0`）。两秒或以上的跳变会被丢弃，所以每次通过门控的调用最多增加一秒。值为 600 的锁持续十分钟计入的游戏时间：仅限焦点状态 1 和 2，后台或游戏关闭时不计时（启动时重新读取基准，`0x14628c`）。秒数遵循实际时间：`0x1462a0` 将转换为纳秒的 tick 差值除以 10^9（`0x14632c..0x146354`）。每帧调用一次、初始周期 33.3 ms 时，门控主体每 0.667 s 执行一次，观察到的增量为 0 或 1，因此 600 的锁在前台持续 600 s 实际时间；若门控间隔超过 1 s，每次被丢弃的跳变都会损失对应秒数。模拟运行 Let's Go 1.0.2、在地图中以每秒 30 帧运行时，调用计数器 `+0x70` 每 0.125 s 增加 4：即每帧调用一次，门控主体每 0.67 s 执行一次。

`0x13c944` 位于 `0x13c850` 中（它也运行 `0x145560`, `0x13f0d0`, `0x142cd0`, `0x1427a0`），仅从 `0x13c5a0` 到达，槽位为 `+0x40`，所属作业为 0x210 字节（虚表 `0x15379d8`，由 `0x13c440` 从 `0x13bfa0` 在设置流程 `0x13b650` 中构建，存储于 `G+0x50`，完成字节 `+0x204`）。执行器 `0x231a0` 从工作线程循环 `0x20f30` 调用，在 `+0x204` 未置位时运行它（`0x23264..0x23288`). `0x13bfa0` 将该作业通过 `0x1ca00` (`0x13c02c..0x13c120` 加入依赖图）；尚不清楚每帧由何处提交该图，因此游戏时间 tick 的实际执行频率也未知。帧周期表 `0xf7eeb8` 包含从 16666667 到 83333334 ns 的五档值，以 `0x39600` 为索引；帧循环从 33333334 ns 开始（`0x38ba0..0x38bb8`，虚表 `0x1529968`），每隔 `clamp(period / 16666666, 1, 5)` 次垂直同步呈现一次（`0x29e80..0x29eb4`).

`0x347190` 构建三种保存序列之一：0“普通保存”（`0x3474d0`），1“同步保存”（`0x347670` -> `0x347ae0`，0xc8 字节），2“致命错误”（`0x347810`）。交换使用同步保存。其初始化函数 `0x837c70` 创建提交信道对象（`0x4d9030`），位置为 `seq+0xb8`，将计数器设为 600（`0x837f88`），并启动 `SaveThread` (`0x1cdc80`），它在调用线程上序列化，并在写入后提交（`0x1cedd4..0x1cede0`, `nn::fs::CommitSaveData`）。其更新函数 `0x838070` 根据 `seq+0xa8` 通过跳转表 `0xf867c4`:

| 状态 | 地址 | 操作 |
| --- | --- | --- |
| 0 | `0x8380ac` | 已记录的网络错误（`0x4d8a70`）会写入结果 2 并离开；否则等待 `SaveThread` (`0x1cdf40`），在 `seq+0xc0` 处存储本站点是否负责发送 2（`0x838660`），应用收到的宝可梦并将内存中的计数器清零（`0x838800`），设置 `netmgr+0x121` (`0x4d8b10`），启动 `FirstSaveThread` (`0x1ce050`) |
| 1 | `0x8380d8` | 等待 `FirstSaveThread` 写入（`0x1ce310`），然后随机抽取延迟，时长为 `2000 + r % 6000` ms，所用 MT19937-64 的种子为 `GetSystemTick` |
| 2 | `0x838234` | 延迟后注册提交信道（`0x8382a8`) |
| 3 | `0x8382b4` | 在提交克隆上投票 1 一次（`0x4d9690`: `chan+0x64 = 1`, `0x11bc00`），然后等待信道门槛（`0x4d94d0`）及克隆空闲，条件为 `[chan+0x74]` 1 |
| 4 | `0x8382ec` | 发送携带 1 的类型 3 |
| 5 | `0x838310` | 取出另一站点的类型 3（跳过自身回环）；消息体不为 1 时进入错误路径（`0x83836c`）；若 `seq+0xc0` 已置位，则发送携带 2 的类型 3（发送失败时留在状态 5，对端的 1 已被消耗） |
| 6 | `0x83839c` | 从任意站点取出类型 3：值为 2 时清除 `netmgr+0x121` (`0x4d8b20`）并发出提交信号（`0x1ce3f0`）；其他消息体均忽略 |
| 7 | `0x8383e8` | 等待 `FirstSaveThread` 提交（`0x1ce410`），结果为 0 |

`FirstSaveThread` 启动时执行序列化（`0x1ce154`），此时计数器已清零；写入后发出 `mgr+0x78` 信号，等待 `mgr+0x84`，且仅在中止字节 `mgr+0x100090` 未置位时提交（`0x1cedf4..0x1cee18`）。错误路径（`0x8383b0` 用于状态 2、3、5、6；`0x838520` 用于错误消息体；`0x8380c8` 用于状态 0）将结果 2 写入父对象（`[x0+0x88]+4`）；前两条路径调用 `0x1ce520`，将中止字节置位并等待线程结束。每条路径最终都会执行 `0x838540(seq, 0)`。第二次保存被丢弃，磁盘存档仍保留 600。

调度器的状态 3（`0x886684`）读取该结果：2 会调用 `0x345b10` (`0x886690`），随后返回，不推进状态。`0x345b10` 将致命错误包装器（虚表 `0x154f1f8`，0xa8 字节，`+0x88 = 0`）压入根过程栈（`0x13a6b0`）；其 `0x346140` 构建类型为 `[proc+0x88] != 0 ? 3 : 2` (`0x3461b8..0x3461d0` 的保存过程），两者均为致命错误序列，其初始化函数 `0x836320` 显示消息 `0x191615296121e064` 对应 2，以及 `0x977c18bf4135ff42` 对应 3（`0x8365f0`，通过 `0x7ed60`），其更新函数（`0x836780`）仅为一个 `ret`。提交中止后停在该界面，不再有后续保存，下次启动时存档仍为 600。

两个 ID 都是 `common/message_error.dat` 中的标签（字符串位于 `0xf22dfc`），采用初始基值为 `0xcbf29ce484222645` 的 FNV-1a-64，更新 v131072 的全部十种语言均相同：

| ID | 标签 | 英语 | 法语 |
| --- | --- | --- | --- |
| `0x191615296121e064` | `error_fatal_save` | 发生错误。无法交换宝可梦。请按 HOME 键结束游戏。 | 发生错误。未能完成宝可梦交换。请按 HOME 键并关闭游戏。 |
| `0x977c18bf4135ff42` | `erro_fatal_storage`（原文如此） | 无法识别 Nintendo Switch 中的存档数据。请关闭主机，然后重试。 | 无法识别 Nintendo Switch 主机的存档数据。请关闭主机，重新开机后再试。 |

游戏只有一个过程栈，根位于 `[G+0x68]` (`G = [0x160d310]`）。运行器 `0x13a780` 只更新栈顶的 `[root+0x78]`，通过 `0x13a160`：返回 3 时在同一帧运行新的栈顶，返回 1 时弹出当前项或换入待处理的 `[root+0x80]`。包装器从不返回 1（`0x346140` 将致命错误过程交给管理器 `[G+0x60]`，通过 `0x39c20`），因此其下方的调度器再也不会得到更新。

连接菜单的拒绝提示 ID `0x02487f0f825b1c88`, `0x0248800f825b1e3b`, `0x0248810f825b1fee` 彼此相差 FNV 素数 `0x100000001b3`：它们是三个仅末字节不同的字符串的 FNV-1a-64 哈希（乘以该素数模 2^64 的逆元后，结尾为 `dd58`, `dd59`, `dd5a`）。字符串未知；文本位于 romfs 的消息归档中。

当 `netmgr+0x121` 已置位时，`0x4d8750` 将每个网络错误记录为严重级别 4（`0x4d8760..0x4d877c`），状态 2、3、5 和 6 会检查该级别（`0x4d8a80`）。已记录错误仅会被更高严重级别替换（`0x4d879c`），因此若在 `+0x121` 置位前已记录高于 4 的错误，该检查便无法命中。`+0x121` 在状态 0 末尾置位（`0x4d8b10`，位于 `0x8384f8`），并由状态 6 在收到 2 时清除（`0x4d8b20`，位于 `0x838494`）。所有状态都没有超时：对端保持沉默会令序列一直等待，直到连接失败。

记录函数：`0x345790`（代码 0xe）、`0x3457d0`（0x11）、`0x345810`（0xf）、`0x345860`, `0x3458a0`, `0x345900`（一个 `nn::err::ErrorCode`), `0x345940`（序列码客户端）、`0x3459f0`, `0x345a50`, `0x345aa0`。位于 `mgr+0x60` 的监听器（虚表 `0x154f068`）将 `0x344c30`, `0x344c60`, `0x344c70`, `0x344c80` 路由至 `0x345790`, `0x344c40` 路由至 `0x345900`, `0x344c50` 路由至 `0x345860`, `0x344c90` 路由至 `0x3457d0`。交换会话对象（虚表 `0x154f608`）将槽位 9（`0x349650`，代码 0xe）、槽位 10（`0x3497d0`）以及槽位 11 到 14（`0x349880`, `0x3498e0`, `0x349940`, `0x3499a0`；14 为代码 0x11）通过以下函数转发给它：`0x3496b0`.

连接状态机 `0x4d9b70`（来自 `0x349520`）在状态不大于 5、没有待执行操作（`[x19+0x20]` 为空）且消息泵 `0x1175d0` 返回 0 时进入状态 6（`0x4d9b98..0x4d9bc8`）；状态 6（`0x4d9fb0`）调用槽位 9。消息泵在 `[x19+0x80]` 为空、传输层的 `+0x48` 不为 5（`0x11c560`），或会话的 u16 `+0x1e6` 不大于 1 时返回 0（`0x1176b0..0x1176bc`）。只有 `0x59eab0` 会写入 `+0x1e6`：它对 `s+0x178` 中每个状态 3 站点记录的字节 `+0x415` 求和（`0x5b5900`, `0x5a9cd0`），该字节由连接响应线上字节 `0x35` (`0x5b962c..0x5b9658` 填充）。零售版 Let's Go 在该处发送 1，因此该值就是站点数量。本地站点也计入：`CreateMeshJob` (`0x581f20`）和 `JoinMeshJob` (`0x583b90`）通过 `0x5a9430` 的模式 0 注册其记录，该模式立即设为状态 3（`0x5a9558`, `0x5a9720`），并使用 `[mesh+0x12b]` (`0x58e960`；网状网络重置后为 1，`0x58bd20`），而 `0x5a3be0` 首先将本地 ID `[s+0xe0]` 加入 `s+0x178`（`0x5a3c48`）。两台主机的会话计数为 2。

重新计数只在以下条件下运行：`[s+0xd8]` 不在 2 到 6 之间，`[s+0xd4]` 为 2 或 4，且 `0x52abf0(s+0x38)` 为假（`0x59eacc..0x59eaf8`）；交换期间三个条件均满足。`[s+0xd8]` 为会话连接状况：1 已连接，2 已丢失（`0x5a0490`），3 正在启动，4 到 6 表示 SessionStatusCheckJob 检测到的失败。`[s+0xd4]` 为会话状态：本地网络建立后为 1（`0x5d70bc`），会话中为 2，3 和 4 仅用于联合会话；在 `CreateSessionJob::WaitCreateMesh` (`0x582a20`, `0x582a24`）以及加入流程的网状网络等待结束时，两者分别达到 2 和 1（`0x586e74`, `0x586e98`). `[s+0x38]` 是 `LocalMatchLeaveSessionJob`（工厂槽位 `+0x1b8`, `0x5c7d20`); `0x52abf0` 当作业状态 `+8` 为 1 到 7 时为真，这只发生于本地主机离开期间。伙伴离开时，会话从网状网络的站点断开处收到事件 1（`0x58be90` -> `0x58c040` -> `0x58ea20`，分支 `0x58ebf4`），其离开处理函数 `0x59dea0`（或 `0x59f1b0`，用于主机端迁移期间）移除 ID 并重新计数（`0x59dfc4`），除非 `[s+0x13d]` 将其延后；该字段只在匹配期间设置（`0x59df34`）。计数降为 1，消息泵返回 0，槽位 9 通过监听器 `[obj+0x98]` 记录代码 0xe；监听器在管理器存储交换会话时设置（`0x343ebc`）。管理器更新函数 `0x344370` 每帧由 `0x13d9d0` (`0x13da00` 调用），因此连接状态机在同步保存期间仍运行：若伙伴在 `netmgr+0x121` 已置位时离开，最终会进入 `error_fatal_save`。尚未分析网状网络会等待多久才判定沉默站点已离开。

连接状态机在六个偏移处调用交换会话对象（虚表 `0x154f618`），每次均来自 `[x19+0x10]`:

| 偏移量 | 函数 | 调用 | 时机 |
| --- | --- | --- | --- |
| `+0x30` | `0x3495e0` | `0x4da584`，位于 `0x4da4b0`（来自 `0x4d9cf0`) | 状态 4 转为 5（`0x4d9cf4`) |
| `+0x38` | `0x349600` | `0x4d9f2c` | 匹配成功，在 `0x116890` |
| `+0x40` | `0x349620` | 位于 `0x4da5e0`（来自 `0x4d9e24`) | 状态 9 转为 10（`0x4d9e28`) |
| `+0x48`，槽位 9 | `0x349650` | `0x4da084`，位于 `0x4d9fb0`（来自 `0x4d9bc8`); `0x4da0e0`（来自 `0x4d9ee0`) | 消息泵失败；匹配失败且 `[job+0x300]` 未置位（`0x4d9e30`），结果为零或位 10 到 12 不为 1 或 2（`0x4da114..0x4da128`) |
| `+0x50`，槽位 10 | `0x3497d0` | `0x4da38c`，位于 `0x4da0e0`，来自 `0x4da294`，两个输出参数 | 匹配失败且 `[job+0x300]` 未置位，结果的位 10 到 12 为 1 或 2 |
| `+0x70`，槽位 14 | `0x3499a0` | `0x4d9efc` | 匹配失败且 `[job+0x300]` 已置位 |

两条匹配失败路径随后都设为状态 6（`0x4d9ee4`, `0x4d9f14`）。对于结果 `0xa46e`（模块 110，NIFM，描述 82），槽位 10 的 out1 是以下偏移处的 u32：`+0x40`，所属对象存于全局变量 `0x163ce00` (`0x4da2a4..0x4da2c4`；全局变量为空时改用槽位 9，`0x4da3bc`），由 `LoginJob::Logout` (`0x5de3ac..0x5de42c` 写入），来源为传输层虚函数 `+0xb0`。其他任何结果都会转换为一个 `nn::err::ErrorCode`，通过 `0x5298a0` 放入 out2（对于 `0xe437`，使用来自 `0x1601e38` 的已存储代码；否则使用 `0x529940(result)` 的 N / 10000 与 N % 10000）。槽位 10 在 out1 非零时通过 `0x345860` 记录它，否则通过 `0x345900` 记录 ErrorCode；管理器在 `0x3443f4..0x34443c` 重复此检查。尚未找到槽位 11 到 13 的调用方。

`0x838660` 决定谁发送 2。设 S = {144, 145, 146, 150, 151}（`species - 0x90`，位于掩码 `0xc7`）且 M = {808, 809}：若站点出示的宝可梦属于 S 或 M，而收到的两者皆不属于，则由该站点发送；反之不发送；其他情况下，由 `0x4d9720` 为真的站点发送（`[mgr+0x128c] != 0`）。因此，以急冻鸟、闪电鸟、火焰鸟、超梦、梦幻、美录坦或美录梅塔换取普通宝可梦的站点，无论处于哪种角色都会发送 2。

父数据块（`[parent+0x88]`，见下文“交换调度器”）在 `+8` 保存自身出示宝可梦的盒子索引，并在 `+0x10` 保存到达的宝可梦。状态 0 调用 `0x838660`，此时盒子槽位中仍是自身宝可梦（`0x1c0d30`：位于 `box + 0x3f800 + idx*8` 的对象，0x3e9 表示无，盒子 `[[[[0x15fad08]]+0x98]+0x58]+0xb0`），随后 `0x838800` 将 `[block+0x10]` 的副本覆盖写入该槽位（`0x838afc bl 0x1c0f30`），并应用交换产生的附带效果：

-
-
-

`mgr+0x128c` 表示本地站点在会话开始时是否为会话主机端，仅由 `0x116890` (`0x59e920(session) & 1` 写入，位置为 `0x116a48`），时机为匹配后连接状态机从状态 2 转为 4（`0x4d9f54`）；Pia 主机端迁移不会重新运行它。`0x59e920` 在 `[s+0xe0]`（本地站点，在创建 `0x59f864` 和加入时设置）等于 `[s+0xe8]`（会话主机端，`0x59f920` 用于加入）且站点 `[s + 0x148 + 8*[s+0x142]]` 对其虚函数返回真时返回 1，虚函数为 `+0xe0`. `mgr+0x1288` 也来自 `[s+0xe0]` (`0x116a3c`).

对于对端：

-
-
-
-
-

### 交换调度器

`0x886530` 负责从菜单到退出的连接流程，根据 `[obj+0x68]` 通过表 `0xf87bc4`:

| 状态 | 入口 | 操作 |
| --- | --- | --- |
| 0 | `0x886578` | 设置 |
| 1 | `0x88669c` | 等待子过程；若已记录网络错误（`0x345af0`）则转至 8；模式 `+0x8c` 为 1 或 2 时创建 `0x347e10` 对象（`0x886f04`）及对战场景（`0x886f18`），然后转至 6；模式 3 等待 `0x344510` 的队伍出示对象报告就绪（`0x886f30`：信道与克隆集均就绪，`0x4d94d0 & 0x11b4d0`) |
| 2 | `0x8866f4` | 将盒子槽位 `[obj+0xf8]` 复制到 `obj+0x148`，作为发出的宝可梦；网络错误转至 8；`[obj+0x100]` 为 5（交换 UI 的继续操作）时启动同步保存，其他值均转至 8 |
| 3 | `0x886670` | 等待子过程（弱引用位于 `[obj+0x90]`，在压入致命错误包装器前销毁）；结果 2 调用 `0x345b10`，即致命错误，并停留；否则销毁队伍出示对象（`0x886c70`），将 `[obj+0xf0]` 放入 `obj+0x150`，启动交换演示（`0x875f40`），进入状态 4 |
| 4 | `0x886930` | 释放 `[obj+0x150]`，进入状态 5 |
| 5 | `0x886950` | 等待子过程；将 `[obj+0x158]` 写入盒子槽位 `[obj+0xf8]` (`0x1c0f30`），启动普通保存，进入状态 7 |
| 6 | `0x886ee8` | 状态 8 |
| 7 | `0x886908` | 等待子过程；结果 1 转至 8，其他结果转至 1 |
| 8 | `0x8869cc` | 销毁队伍出示对象（`0x8869f0`）及 `mgr+0x70` 对象（`0x3447a0`）并离开 |

保存通过 `0x887340` 启动，它构建一个保存过程（`0x346670`，0x128 字节）；调度器将 `&obj+0x178` 存入其 `+0x90` (`0x8868dc`, `0x886e48` 处）。其首次更新函数 `0x8345d0` 通过 `0xef9a80 = {1, 0, 2, 2}` 将保存类型映射为 `0x347190` 的序列种类，并继续传递指针（`0x834688`），作为 `[parent+0x88]`:

```
obj+0x178  +0x00  save type: 0 sync save, 1 normal save, 2 or 3 fatal error
obj+0x17c  +0x04  result, written by the sequence: 0 done, 2 aborted, 1 the link ends
obj+0x180  +0x08  box index of the own offered Pokemon, [obj+0xf8]
obj+0x188  +0x10  the received Pokemon, [obj+0xf0]
```

状态 2 为同步保存填充它（`0x88685c..0x88689c`）；状态 5 将类型设为 1（`0x886e00..0x886e04`）。普通保存的更新函数 `0x8374b0` 运行 `SaveThread` (`0x8377bc`），等待 3000 ms（`0x8377ec`），然后若交换会话对象处于状态 8（`0x349090`），就创建队伍出示对象（`0x8375a4`，每帧重试）并写入结果 0（`0x8375b8`）；其他状态下只写入 0。结果 1 仅来自 `0x837860`，其门控条件为 `[x20+0x258]` 及位于 `[x20+0x250]` (`0x83776c..0x8377a0` 的队列）。交换后调度器从状态 7 返回状态 1（`0x88691c..0x88692c`），此时新队伍出示对象使用新信道，因此一次入座可以连续进行多次交换。

子过程引用 `[obj+0x90]` 在状态 0 保存连接菜单过程（`0x886cf4` -> `0x8871a0` -> `0x887940`，虚表 `0x15afdc0`，模式字的地址 `obj+0x8c` 在 `0x886d44` 处传入），在状态 2 和 5 保存保存过程（`0x887340` -> `0x346670`，虚表 `0x15aa2a0`）。同步保存中止后，位于 `seq+0xb8` 的提交信道在状态 3 读取结果 2 前已经销毁：每条中止路径均通过 `0x838540` 结束序列，运行器弹出过程，其析构函数 `0x835000` 释放序列，序列的析构函数 `0x838c40` 释放信道，而状态 3 首先等待子过程计数降到 0（`0x886670..0x886684`).

模式 1 和 2 是连接对战。它们构建的过程在结束时将存档计数器加 1（`0x95ccbc..0x95ce40`): `local_btl_single_cnt`（ID `0x1de`）用于模式 1，`local_btl_double_cnt` (`0x1df`）用于模式 2，而 `netl_btl_single_cnt` / `net_btl_double_cnt` (`0x1e0`, `0x1e1`）用于 `0x115860` 为真时。模式 2 设置双打标志 `[obj+0x810]` (`0x886f10`, `0x95c4bc`, `0x95c574`）。交换的同步保存（模式 3）按同一标志将计数加到 `local_trade_cnt` (`0x1dc`）或 `net_trade_cnt` (`0x1dd`）（`0x838828..0x838840`）。连接菜单对选项采用不同编号：选项 1（交换）存储 3（`0x97845c`），选项 2 存储 1，选项 3 存储 2（`0x978504..0x978514`).

### 对战场景的信道

位于 `0x9dce94..0x9dede8` 的发送函数是仅有的非零标签发送方；它们将状态保存在 `0x1640eb0` 处的全局块中，其第一个字是信道（`0x9dce10..0x9dce1c`: `ldr x0,[0x1640eb0]; b 0x4d9450`). `0x9dce50` 从块 `+0x78f0` 发送四字节（一个以 u16 表示的站点字节、一个 u16 0x6e），使用标签 1、目标 0xff；`0x9dd3ec` 将宝可梦（`0x721ef0`）打包至 `+0x348` 和 `0x9dd3fc..0x9dd40c` 使用标签 3 发送它。每站点记录为 0x1788 字节（`0x9dcee8`).

注册逻辑（`0x9d2d90`）位于对战过程的分步设置函数 `0x9d2c30` 中（跳转表 `0xf92c1c`；该过程引用 `Pop_BGM_battle_to_field`, `vs_wild` 和 `btl_sky.gfbmdl`），仅在模式 1 和 2 下从调度器状态 1 到达（`0x886f18` -> `0x95c470` -> `0x95c5c0` -> `0x28cd10` -> `0x28e630` -> `0x9cbba0`）。模式 3 从不注册对战信道。步骤 0 创建信道（`0x9dc5c0`）并存入 `0x1640eb0` (`0x9dc6f4`），前提是连接会话对象 `[[[0x15faec8]]+0x50]` 处于状态 8（`0x9dc61c..0x9dc634`); `0x9dce10` 在 `0x1640eb0` 为空时不注册任何内容，而就绪检查 `0x9dce30` 在没有信道时返回 1，因此野生对战不会注册信道。清理逻辑（`0x9d3df0` -> `0x9dcce0`）清空该指针。

### 主机端交换会将什么写入存档

出示的盒装结构按发送时的原样直接写入存档，不经检查。携带以下值的记录，在 Let's Go 皮卡丘的能力界面读取时保持不变：物种 132，经验值 1,000,000（等级 100），隐藏特性槽位中的特性 150，相对于 TID 41234 和 SID 12345 的异色 XOR 为 0 的 PID（显示为 083154，`(sid << 16 | tid) % 1000000`），性格 10，无性别，各项个体值均为 31，各项 AV 均为 200（等级 100 时 HP 为 437，即游戏上限），一个招式，相遇等级 30，相遇地点 4（2 号道路），语言 2，初训家 `POKELDN`。偏移量采用 PKHeX 的 PB7 映射。

### 加入端离开

主机按“返回”退出时，在出示克隆上以新计数器发布状态 4、参数 0，然后发布参数 3。主机端在每次发布后 30 ms 应答，前三个字为零，末尾字加一，类型 4 副本的第一个字采用该参数。随后主机通过克隆类型 4、站点 0xFD 上的 0x83 释放其克隆（克隆类型 3 上的克隆 0），并重复发送（实测约每 100 ms 一次），直到收到 0x84；主机端也释放自身克隆（在自身站点下的克隆类型 2，以及克隆类型 4 上发送 0x83）。最后一次释放后，待克隆协议空闲（[离开前的等待](#the-wait-before-leaving)），主机便在网状网络协议的可靠端口上，使用 24 字节可靠头部发送网状网络离开请求：

```
04 01        leave request, station index
```

对端应在该端口发送可靠确认，并在不可靠端口发送两字节离开响应，内容为 `08` 以及网状网络主机端索引（`08 00`）。离开方的处理函数 `0x591bf4` 仅当响应字节 [1] 是主机端读取函数 `0x58e5d0` (`ldrb [x0,#0xa3]`）指定的站点索引时，才接受响应，然后清除离开作业标志 `+0x78`。该作业（`LeaveMeshJob`，构造函数 `0x589470`）在发送请求时启动 5000 ms 截止期限（`0x5895bc`); `WaitLeaveResponse` (`0x5896c0`）等待标志或期限，期间重传请求（实测每 40 ms 一次），然后断开站点并离开网络。若响应指定的是离开方（`08 01`），则会被丢弃：主机会在离开请求后 5.00 s 解除认证（两台主机六次离开中为 4.98 到 5.01 s，每次均应答了主机端的断开请求）；若两次应答 `08 00`，主机会在离开请求后 0.04 s 发送自身断开请求，并在约 0.06 s 后解除认证。按“返回”后，主机端发送一个字节的站点断开请求，类型为 3；主机在 50 ms 内以类型 4 应答。

主机端主机对加入端离开请求的应答为 `08 00`，发送两次，然后重复发送 Local Protocol 的 start host migration（类型 0x13，实测每 0.3 s 一次）。加入端若在离开响应到达时发送断开请求，主机端玩家就会返回菜单（“另一位玩家选择取消交换”）；若加入端等待，主机端会持续重发 0x13 五秒。`bin/lgpe_join.py --leave-after SECONDS` 执行退出流程（`pokeldn.lgpe.leave`).

当两个站点都在同一克隆上以相同参数发布状态 1 后，主机端主机的类型 4 副本会在 0.27 s 内将 A 改为该参数。权威端读取各站点存储的副本（`container + 0x8d8 + i*0x260`，i 小于会话站点数）。只有时钟严格更新的记录才能替换副本（`0x52184c`）；相同时钟只会确认并保留旧数据。若加入端在提交克隆上发送投票时，沿用自己上一条记录在该克隆上的时钟（两条记录位于同一个网状网络时钟 tick 内），主机会保留旧副本，玩家停在交换界面。`pokeldn.ldn.clone.Participant.record_clock` 为克隆上的每条记录分配严格大于上一条的时钟。`bin/lgpe_join.py` 在任何类型 3 到来前，若此类投票持续未获同意达到 `--stall-leave` 秒（默认 5），就执行退出流程（`pokeldn.lgpe.leave.unagreed_vote`）。退出会结束等待，但不会解除交换锁；同步保存早在提交克隆投票之前就已写入该锁（以下函数的状态 0：`0x838070`).

### 主机端离开

主机端主机的玩家退出时，会发布状态 4、参数 3，释放其克隆（0x83，以 0x84 应答），并在最后一次释放后待克隆协议空闲（[离开前的等待](#the-wait-before-leaving)），于可靠端口发送网状网络迁移开始消息，`44 00 01`（主机端索引、下一主机端索引）。其等待逻辑（`0x58aeb0`）在 `job+0x6e+index` 为每个已连接站点保存一个标志，所有标志清除或经过 5000 ms（`0x58a8f0`）后结束；迁移响应 `48 ` 会清除对应站点的标志（处理函数 `0x591e98` -> `0x58b010`），站点离开也会清除。若无应答，主机每 45 ms 重传开始消息，持续 5.0 s。

然后它广播携带主机端迁移状态 1 的 update session，节点列表不变，并每 301 ms 重复发送 Local Protocol 的 start host migration（类型 0x13）（`0x5d40ac`），直到 LDN 网络中除自身外不再有其他已连接站点（`0x5cc2d0` 负责计数），或经过 10000 ms（`0x5d4050`），随后销毁网络：在 200 ms 内广播八个 LDN 断开帧，原因为 3。加入端若两者都不应答，会令主机端主机在迁移开始后滞留 15.0 s。模拟主机端若收到确认和 `48 01` 应答，会在 34 ms 后发送 update session 和第一条 0x13；零售版主机端采用相同应答时，在迁移开始后 0.06 s 发送第一条 0x13。`bin/lgpe_join.py` 发送两种应答，并在第一条 0x13 到来时离开网络（`pokeldn.lgpe.leave.host_departure`).

### 离开前的等待

游戏的清理步骤 `0x116bc0`（连接对象更新函数 `0x4d9b70` 的状态 8）结束克隆会话（`0x51bee0`），然后若克隆协议状态 `& 0xf0` 为 `0x10`（空闲；由 `0x5db760` 读取到 `obj+0x16f4`），则立即返回。否则先计数 150 次调用（`obj+0x16fc`, `cmp 0x95`，位于 `0x116d38`），再通过 `[obj+0x80]` 的虚函数 `0x68` 调用离开逻辑。两种角色下计数都持续 2.49 到 2.51 s。

协议通过状态 `0x41` 达到空闲；只要有克隆仍有未确认的数据令牌，该状态就会等待（`0x51b0f0`, `0x5180cc`），然后进入 `0x42`，发送克隆退出消息（0x32），并等待各站点的 0x41。在克隆 0 释放后（克隆类型 3 上的 0x83），主机仍会约每 100 ms 发布其克隆类型 2 副本。若对端每次都用自身副本应答，就会让它们保持未确认：主机不发送 0x32，等待完整计数后才离开。若对端在克隆类型 1、站点 0xFD 上以 0xe3 应答每条消息，并携带发布方站点和时钟，则会收到每个克隆在克隆类型 2 上的 0x83、一个 0x32，并在主机最后一次释放后 0.11 和 0.29 s 收到离开请求；主机端主机在最后一次释放后 0.13 s 发送迁移开始消息。`pokeldn.ldn.clone.Participant` 在对端释放克隆 0 后发送确认。

### 主机端如何处理不持有克隆数据的加入端

主机端主机若收到 0x3C 字节的连接响应（无网络 ID、无玩家），会应答克隆通告并通告自身克隆，但始终不发送克隆数据（无 0xb1），并在加入网状网络几秒后离开克隆会话（0x32）。若加入端发送完整响应，则会在参与之后收到克隆数据（实测 1.1 s）。

### 通过门槛之后

门槛通过后，主机端从状态 4 进入稳定状态 8：状态 6 发送第一条消息（来自 `obj+0x450` 的 0x168 字节），状态 7 将自身回环及加入端消息计入 `obj+0x470`，恰好为二时转至 8（`b.ne`），不再接收更多消息。主机端界面随后显示已找到玩家。首条消息的头部：

```
01000000 68010000 01000000 00ff0000    kind 1, 0x168 bytes, step 1
02000000 e8000000 02000000 00ff0000    kind 2, 0xe8 bytes, step 2
02000000 e8000000 03000000 00ff0000    kind 2, 0xe8 bytes, step 3
```

正常会话中，类型 1 消息得到确认，克隆 ID 2 和 3 被通告，随后是类型 2 消息（间隔分别为 70 ms、3.2 s 和 0.4 s）。状态 8 是 `0x349200` 的终态：只要模式字 `+0x8C` 保持为 0，就永远不会通告克隆 ID 2 和 3。

### 门槛之上的状态机

状态 3 属于 `0x349200`，它在 `+0xB8` 分配会话子对象，调用 `0x11aec0`，经由 thunk `0x11b4c0`（对象 `[x0+0x20]`，克隆 ID `[x0+0x18]`），并无条件设为状态 4；状态 4 通过 `0x11b4d0` 调用门槛检查，结果为真时推进。状态 3 和 4 不读取任何网络内容。三个受同一保护条件约束的设置函数位于连续虚表槽位中，只能通过虚表到达：`0x154f648` -> `0x3495e0`（设为状态 3，允许来源为除 9、10、11 之外的任意状态）、`0x154f650` -> `0x349600`（状态 2）、`0x154f658` -> `0x349620`（状态 11，随后执行中止 `0x4d8b00`); `0x349650`, `0x3497d0`, `0x349880`, `0x3498e0`, `0x349940` 随后执行。

`0x11aec0` 在一帧中注册并通告站点的整个克隆集：位于 `game+0x90` 的类型 1 克隆来自 `game+0x678`，位于 `game+0x1258` 的类型 4 克隆来自 `game+0x13f0`，随后为每个队伍成员处理一个（从 `game+0x218` 起以 0x118 为步长，源从 `game+0x8d8` 起以 0x260 为步长）。每个都传入 `0x51a550` 或 `0x51a510`，它们将通告器加入元素列表 `+0xD8`。清扫函数 `0x51b380` 在一个 tick 后清空该列表，根据入队对象的种类从表 `0xf46acc` 获取类型字节（0x81、0xa1、0x83、0xb1）：因此 `0x81` 用于克隆类型 2，`0xa1` 用于类型 4，`0xa1` 用于类型 1，均在一帧内完成。

通告发生在门槛检查之前：发出这组三条消息的站点已通过状态 3；从未发出的站点则尚未到达状态 3，向门槛输入发送任何消息都无济于事。主机端主机的交换状态机只为克隆 ID 1 发出这组三条消息；ID 2 和 3 来自第二个发布器（`0x349a90`，见下文）。作为加入端时，它不发出 `0x81`，只发送接管突发消息。站点对每个克隆 ID 运行一次 `0x11aec0`，先为 1，然后为 2 和 3。

### 第二个发布器及其模式字

`0x11aec0` 有两个调用方。交换状态机在状态 3 针对克隆 ID 1 调用一次。约 3.2 s 后，ID 2 和 3 由另一个逐帧调度器产生：`0x13a780` -> `0x13a160` -> `0x886530` -> `0x344510` -> `0x349bf0` -> `0x349a90`，每个队伍宝可梦对应一个游戏对象，间隔为 0x1680，而状态字始终保持 8。

`0x886530` 从进入地图开始每帧运行，并依据模式字 `+0x8C` (`0x886ed0..0x886ee8`）分支：1 或 2 进入对战场景（`0x886ef8`），3 进入发布分支（`0x886f24`），其他值均停在 8。`0x344510` 是一次性操作：当 `[x19+0x68]` 非空时提前返回，否则分配 0x278 字节并调用 `0x349bf0`.

设置函数 `0x7c4530`（模式 1）、`0x7c4580`（模式 2）和 `0x7c45d0`（模式 3；后两者随后还调用 `0x147c90`，传入 0）通过 `[singleton+0x288]` 写入该字；类虚表 `0x15afa68`（槽位 9 = `0x886530`）由 `0xe13388` 附近的重定位填充。从地图跟踪至稳定交换期间，当模式字从 0 变为 3 时，这三个设置函数和 `0x5a733c` 从未触发。没有类方法会写入 `+0x8C`，且对 `+0x8C` 的十六处常量写入中，没有一处在 `.text` 中写入 3：写入者未知。

### 接管必须携带的序列值

站点通告克隆时会分配一个序列值，并将其写入通告。`0x520c30` 是请求侧逻辑，当克隆的 `+0x38` 为零、`+0x110` 已置位，或 `+0xB0` 和 `+0xB8` 均非空时提前返回；否则将分配的序列值写入 `+0x10C`，并将通告器入队。`0x520ce0` 是完成逻辑，它将通告器出队，并向 `+0x110` 写入 1，前提是 `+0xB0` 和 `+0xB8` 均非空，且 `+0x10C` 等于给定值。`+0x110` 是门槛中按站点检查的项：位于 `+0x250` 的条目是队伍克隆，`station[i]` = `partyClone[i]+0x38`.

加入端的接管（`0x91`，对应克隆的各类型）回显对端通告的时钟；对自身副本的通告则携带自身时钟：

```
host   0xa1 clone type 4   00000cfe 01 2808ab      the sequence it allocated
host   0xa1 clone type 1   00000cfe 01 2808ab
joiner 0x91 clone type 4   00000cfe               echoed
joiner 0x91 clone type 2   00000cfe               echoed
joiner 0xa1 clone type 4   00000d21 01 2808ab      its own clock, the host's content
joiner 0xa1 clone type 1   00000d21 01 2808ab
```

`+0xB0` 和 `+0xB8` 是内嵌于 `sub+0x08`, `sub+0x10` 的通告器的链表链接（`clone+0xA8` (`0x51e790` 建立链接，`0x51e810` 解除链接）；为空表示它不在通告列表中。正常会话中，两个克隆到达时均已链接，不会分配任何序列；队伍克隆若以未链接状态到达，就会进行分配，而随后到来的完成消息会被拒绝。传入的 `0x82` 也会使 `0x520c30` 分配序列，因此每次重新通告都用携带 `0x82` 的突发消息应答，会让每次突发都生成一个序列，约每秒三十个。

每个克隆保存一个通告时钟：通告方将其网状网络时钟写入 `0xa1`，对端确认和针对该克隆的下一条 `0xa1` 携带同一个数值，并由 `+0x10C` 保存。记录携带另一站点针对该克隆最新一条 `0xa1` 的时钟时，才能匹配。`0x520d30` 处理 `0x91`（克隆类型 2 上的否定确认），而 `0x520ce0` 处理 `0xa2`，前置条件相同；两者都会解除通告器链接，但仅有 `0xa2` 会向 `+0x110` 写入 1。匹配的 `0x91` 会取消通告，匹配的 `0xa2` 会完成通告；以加入端自身时钟构建的 `0xa2` 则无法匹配。

序列按队伍克隆分别分配，并会重新分配（位置为 `0x520cb8`），每次分配从 0x34 到 0x38 逐步递增。接管携带加入端自身时钟时，主机端为两个队伍克隆都分配了 `0x1114b`；克隆 0 的完成消息携带 `0x1114b`，并设置 `+0x110`，克隆 1 的完成消息携带 `0x111b0`，因而被拒绝：门槛 `0x11b080` 始终为假，状态字一直停在 4。若只应答对端首次克隆类型 2 发布，而对其余发布发送确认，它便会每次以新序列重新通告。

### 加入端对每个克隆只执行一次的接管交互

接管是一种所有权转移：`0x520d30` 取消对端的通告，加入端再用自身时钟通告该克隆。两个队伍克隆的参考交互如下，以主机端通告时刻为零点：

```
+0 ms   host    0x81 clone 2, 0x81 clone 3, dest 0x0003
        host    0xa1 x2 per clone                        clock 0x197e, the host's
+5 ms   joiner  0x82, 0x91 x2, 0x82, 0x91 x2, 0x84 x2    echoing 0x197e
+75 ms  joiner  0x81 clone 2, 0xa1 x2                    clock 0x19c1, the joiner's own
        joiner  0x81 clone 3, 0xa1 x2                    clock 0x19c1
+102 ms host    0xa2 per clone                           clock 0x19c1, the joiner's
        host    0xa1 per clone                           clock 0x19e2, the host's own
+141 ms joiner  0xa2 per clone                           clock 0x19e2, the host's
```

加入端仅在首次收到不属于自身的克隆通告时接管一次。之后每次重新通告都只回复一条 `0xa2`，携带该次通告的时钟，位于加入端站点下的克隆类型 2，载荷为 ` 00 00 00 02`。再次接管会取消一个本不应转移所有权的通告，导致对端无限重新通告。

该 `0xa2` 驱动完成逻辑。站点自身的通告器会通过自身 `0xa2` 的回环在约 6 ms 内完成，因此第一个队伍克隆总能完成；第二个需要加入端的消息。正常加入端的突发消息不携带确认：对端的 `0xa2` 消息对在 +37 ms 到达，加入端单独的 `0xa2` 在 +72 ms 作为回复发出。若对端从不重新通告，就不会解除链接（逐 tick 构建函数约在建立链接后 30 ms 解除链接），也不会分配序列。

仅面向对端的重新通告会在 20 到 60 ms 后引来对端的 `0x82`，位于克隆类型 1；而 `0x82` 会引来主机端包含 32 个零字节的类型 4 副本，主机以其 `1 1 1` 应答。若零售版主机端在一次重新通告后既未收到 `0x82`，也未收到提交克隆的任何后续消息，就会停在确认界面，而交换锁已经保存。`pokeldn.ldn.clone` 每 100 ms 重发一次仅面向对端的 `0x81`，最多 20 次，直到 `0x82` 到达。

一台零售版主机对提交克隆 4、7、10 的首次仅面向对端的通告，分别在 63、26、62 ms 后应答。若抑制第一条仅面向对端的 `0x81`（`--withhold-announce 1` 用于 `bin/lgpe_host.py` 和 `bin/lgpe_join.py`，仅供测试），100 ms 后的重发会引来主机的 `0x82`，两种角色下均完成了三次交换。

### 通告目标字段决定什么

命令头部 `0x51f820` 将 `+0x10` 定义为站点位图。首次通告克隆的 0x81 携带整个网状网络位图（0x0003）；其后位于克隆类型 4 和 1 上的两条 0xa1，以及 35 ms 后重发的通告，只携带对端位图（0x0001）。收到整个网状网络位图时，对端会回复两个 0xa2，分别位于克隆类型 4 和自身站点下的克隆类型 2；收到仅对端位图时，两者都不回复，而是继续在克隆类型 1 上发送 0xa1，门槛 `0x11b080` 始终无法看到已确认集合填满。

克隆类型 1 上 `0xa1` 的重传次数可区分正常和停滞会话：正常时每站点九次；若每次重新通告都被接管，对端就会无休止地每 0.12 s 发送一次，而游戏不再发消息。

每条克隆消息都通过 `0x51e3d0` 构建，它是协议对象的第九个虚表槽位（第四个返回 0x73）。各调用点的字面类型：克隆类型 2 上的 0xa2 `0x51cbb8`，0x81 `0x51e92c`，克隆类型 3 上的 0xa2 `0x51cdd4`，0xc1 `0x51c9e4`，0x82 `0x51c60c` 和 `0x51cd5c`，0xe3 `0x51ad2c`，0xf3 `0x51ef18`。游戏在同一个元素上保存三个克隆对象，类型 1 位于 `game+0x90` 和 `game+0x1710`，类型 4 位于 `game+0x1258`；消息的克隆类型与这些对象并非一一对应。

| 地址 | 作用 |
| --- | --- |
| `0x51ab20` | CloneProtocol::vfunc9，按元素接收 |
| `0x51c100` | 接收分派：表 `0xf7673c` 根据 (type - 0x11) 区分时钟消息与命令消息，`0xf76800` 根据 (type - 0x84) 到达命令路径 |
| `0xf769c4`, `0xf769e4` | 按高半字节确定结构；克隆类型 |
| `0x51b010` | 回复状态机，表 `0xf76674`，依据 (type - 0x21) |
| `0x51b1d0` | 由时钟驱动的重传调度器 |
| `0x51f9b0`, `0x51fab0`, `0x51fbd0`, `0x51f820`, `0x51f4c0` | 序列化函数：时钟请求、时钟回复、参与、命令头部、ClockAndCount |
| `0x51c1e0` | 若消息 [0xC] 处的计数不大于发送方上次计数，则丢弃该消息 |

元素偏移量：+0x34 站点，+0x40 状态，+0x50 时钟，+0x7a0 发送时间，+0x32c 结果。
