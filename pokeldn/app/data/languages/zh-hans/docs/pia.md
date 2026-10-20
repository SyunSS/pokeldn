---
title: Pia 层
parent: The wireless layer
nav_order: 1
---

# Pia 层

Pia 是任天堂的点对点会话中间件，在所研究的每款游戏中都使用 UDP 端口 12345。每个数据报都以魔数 `32 AB 98 64` 开头。Pia 版本决定头部布局：

|  | 火红／叶绿（GBA 应用） | 晶灿钻石／明亮珍珠 | 剑／盾 |
| --- | --- | --- | --- |
| Pia 版本字节 | 15/16 (6.32+) | 9 (5.27-5.45) | 4 |
| 头部大小 | 0x1D | 0x20 | 0x20 |
| variable id | 各 2 字节 | 各 4 字节 | 1 字节加一个半字 |
| 线路上的 GCM 标签 |  | 8 字节，由 16 字节截断而来 | 完整的 16 字节 |
| 模块 | `pokeldn/ldn/pia_connect.py` | `pokeldn/ldn/pia5.py`（对捕获数据进行解码再编码，结果逐字节一致） | `pokeldn/ldn/pia4.py` |

除非某节另行注明构建版本，`0x01...` 地址均指《盾》1.3.2 解压后的 `main`（按照 `tools/switch/nso_read.py` 的布局），而 `main.bin 0x01...` 地址属于 BDSP 1.3.0。

## 数据包头部

### 版本 9（Pia 5.27-5.45）

来自 `nn::pia::common::Packet::Header`；解析器对三个字段进行字节序交换，使用 `rev`.

```
0x00  4  magic 0x32AB9864, big-endian
0x04  1  0x80 (encrypted) | version (0x7F)
0x05  4  destination variable id, big-endian   (0 = broadcast to the mesh)
0x09  4  source variable id, big-endian
0x0d  2  packet id, big-endian
0x0f  1  footer size
0x10  8  AES-GCM nonce, a monotonic counter
0x18  8  AES-GCM tag, truncated from 16
0x20     ciphertext: the plaintext padded to a multiple of 16
```

### 版本 4

来自反序列化器 `0x01774730`，它要求数据长度大于 0x1f 字节（`cmp w2, #0x1f; b.hi`):

```
0x00  4  magic 0x32AB9864, big-endian
0x04  1  0x80 (encrypted) | version (0x7F) = 4
0x05  1  connection id
0x06  2  packet id, big-endian
0x08  8  AES-GCM nonce, a monotonic counter
0x10  16 AES-GCM tag, not truncated
0x20     ciphertext
```

两个小字段按目标站点分别维护；数据包不发给特定站点时，两者都为 0：零售版《剑》发出的 484 个数据包全部如此（`0x017beb14`, `0x017beb20`）。发给某个站点时（`0x017beb74`, `0x017beb78`，字节来自调用方，半字来自会话对象）：

-
-

像主机一样将两者都发送为 0，可以通过所有路径。初始化器 `0x017748bc` 将 `0x00000004_32AB9864` 作为一个 64 位字保存，并将 nonce 和标签清零；验证器 `0x017749f0`, `0x01774b60`, `0x01774d00` 检查 `(byte & 0x7f) == 4`（BDSP 相同，但使用 9）。头部以下，版本 4 与版本 9 使用相同的会话密钥和 IV，帧封装也相同，只多一个字段。

### 版本 11：接收器会丢弃什么（《朱》4.0.0）

`0x6e9744` 在任何协议读取数据包之前，先决定接受还是丢弃整个包；一旦丢弃，所有协议都会同时失去它。设 `st` 为源地址对应的站点，`V` 为接收器的 variable id，`D` 为头部目标，`S` 为头部源：

| 检查项 | 丢弃条件 |
| --- | --- |
| 发送方 | `st` 已设置标志（`+0x78`）或处于状态 3 |
| 目标 | `D >= 2` 且 `D != V` |
| 源 id | `S != 0` 未对应任何站点，条件为 `D == V`，或 `D` 为 0 或 1 且带有尾部 |
| 数据包 id，`D == 1` | 在目标为 1 的计数器上，不比来自 `st` 的上一个 id 更新（`st+0x60`, `0x6e9854`) |
| 数据包 id，其它 `D` | 在另一计数器上，不比来自 `st` 的上一个 id 更新（`st+0x48`, `0x6e98b4`) |

计数器检查 `0x6f3ff4` 会放行数据包 id 0，且不保存任何内容；否则要求 `(int16)(id - last) >= 1`，因此使用相同 id 的重发会被丢弃。加入期间，若源地址尚无对应站点，则不检查数据包 id。没有任何检查读取尾部的 id。零售版本发送方（`0x6b6b38`）用一个计数器为目标为 1 的数据包编号（`0x696d04`），用按接收方维护的计数器为发往单个 variable id 的数据包编号（`0x696ce4`）；两者都跳过 0。

## 消息帧封装

一个 Pia 载荷携带一条或多条消息，每条都以存在标记字节开头，说明后面有哪些头部字段。省略的字段继承自包内上一条消息（`0x01853050`，逐位处理）：标志位于 +9，大小位于 +0xA，protocol|port 位于 +0xC，目标位于 +0x10，源位于 +0x18。继承的大小会以 0x589 为界进行边界检查。遍历仅在 `0xFF` 处停止，没有其它终止条件：`0x00` 是合法的单字节头部，表示一条继承全部字段的消息。

各版本范围的读取器都会先复制上一头部，再读取相应位被设置的字段：

| 头部版本 | 所分析游戏 | 读取器 | 终止检查 | 下一条消息的起点 |
| --- | --- | --- | --- | --- |
| 4 | 剑 | `0x01852da0` | `0xFF` | 四字节对齐处 |
| 9 (5.27-5.45) | 明亮珍珠 1.3.0 | `0x159b980`，复制 `0x159b9ec`..`0x159ba10`，字段 `0x159bb60` | `cmp w8, #0xff` 位于 `0x159b9d4` | 四字节对齐处（`0x15abf68`..`0x15abf70`，全部七个调用方） |
| 11 (6.16-6.30) | 宝可梦传说 阿尔宙斯 1.1.1 | `0x7484cc`，复制 `0x748538`..`0x74855c`，字段 `0x7486a8` | `0x748520` | 载荷结束处（`0x743f14`..`0x743f18`) |
| 11 | 朱 4.0.0 | `0x6ed2d0`，复制 `0x6ed348`..`0x6ed360`，字段 `0x6ed4b4` | `0x6ed324` | 载荷结束处（`0x6e9054`..`0x6e905c`) |
| 16 (6.39-7.2) | 宝可梦传说 Z-A | `0x256e088`，复制 `0x256dac4`，字段 `0x256de5c` | 无：数据包头部已注明填充长度 | 载荷结束处 |

站点会用存在标记 0x00 捆绑连续的等长消息：《朱》的填零记录分块、《明亮珍珠》中跟在同尺寸消息后的可靠消息，以及《阿尔宙斯》的第二条 24 字节记录。将 0x00 视为消息时，每次遍历都恰好结束于 `0xFF` 填充处（5866 个《明亮珍珠》包、11501 个《阿尔宙斯》包、38350 个《朱》包）；若在 0x00 停止，其中 3444 个包就会留下未读字节，并丢弃其后全部内容。`tests/test_pia_bundled.py` 为每款游戏固定了一个数据包作为测试样本。

版本 3（Let's Go 1.0.2）没有存在标记字节：使用固定的 0x16 字节头部，第二个字节必须为 1（`0x5ae7d0`），遍历在 `0xFF` (`0x5ae790`).

版本 4 在十八处内联计算头部大小，始终以 1 为基数，进行五次条件加法：

```
tst w9, #1    -> +1       message flags
tst w9, #2    -> +2       payload size, big-endian
tst w9, #4    -> +4       protocol id and a 3-byte port
tst w9, #8    -> +8       destination
tst w9, #0x10 -> +8       the sender's station constant id
```

存在标记 0x7F 对应 24 字节头部；位 0x20/0x40 不增加任何内容，版本 9 也是如此，而版本 9 的头部为 16 字节。八字节 constant id 是对发送方 MAC 应用 `station_protocol.ldn_constant_id` 所得，即 Local Protocol 的 `host_constant_id`：此处为大端序，Local Protocol 主体中则为小端序。

版本 16（Z-A）缩小了字段：头部大小 `0x256dfc8` 由一个字节起始，再加标志一个字节、大小两个字节，以及位 0x04（协议）、0x08（端口）和 0x10 各一个字节。位 0x10 对应的字节位于协议和端口之间（`0x256df54`，setter 为 `0x256a8e8`）；新头部包含协议 0xFF、该位置值 0xFD，以及端口 0（`0x256a8c0`）。读取器忽略位 0x20 至 0x80，并拒绝大小达到 0x590 或更大的消息（`0x256df04`）。无线捕获中尚未见过位 0x10。`pokeldn.ldn.reliable.parse_messages` 读取该位对应字段。

版本 4 和 9 中，每条消息都填充到四字节的倍数（《明亮珍珠》用 0x00 填充），填充被直接跳过而不读取；数据包尾部为 `0xFF`. `pia4.parse_packet()` 解析继承关系，`pia4.parse_messages()` 则按发送时的形式返回各头部。已消耗字节加上 `0xFF` 填充恰好覆盖每个数据包的完整明文时，遍历才是正确的。

### 压缩

载荷可能是 zlib 流，由每条消息的消息标志指示：5.27-5.45 中为 0x20，版本 4 中为 0x10。版本 5 的可靠头部另有自己的 zlib 标志 0x10；BDSP 会在某些游戏消息上设置它（一条 23 字节消息使用 4 KB 窗口压缩为 20 字节流）（[BDSP 协议](bdsp_protocol.md)).

BDSP 会在会话进行过程中开启压缩。若按原始字节读取，一条压缩后的 31 字节消息会被解析为一个宣称载荷长 0x6260 的头部。在 2835 条版本 4 消息中，`flags & 0x10` 精确预测了是否可解压（256 条设置，全部有效；2579 条未设置，全部不可解压）。zlib 流的前两个字节按大端半字读取时，是 31 的倍数。

### 尾部

发送给多台主机的数据包带有尾部：每个接收方占一个大端半字，为其 variable id 的低半部分，长度位于头部字节 0x0f。GCM 标签不覆盖它：密文为 `data[0x20 : len(data) - footer_size]` (`pokeldn/ldn/pia5.ciphertext()`）；若未剥离尾部，认证会失败，却没有其它症状。若只有部分数据包通过认证，应先按尾部大小对失败项分组。

## 会话密钥

每种网络类型各有一套会话密钥实现，分属不同的类：

| 网络类型 | 类 | 派生方式 |
| --- | --- | --- |
| LDN（本地无线，联盟交谊厅） | `nn::pia::local::LocalProtocol` | 以会话值为种子初始化 xorshift128，生成 16 字节，再以游戏密钥执行 AES-128-ECB |
| LAN | `nn::pia::lan::LanProtocol` | HMAC-SHA256（游戏密钥，一个最后一字节已递增的 32 字节参数）的前 16 字节 |
| NEX（互联网） | `nn::pia::nex::*` | 来自匹配服务器的会话密钥 |

已公开文字中所说的“SSID 或以会话参数为种子的随机值”，实际指两种实现；类名能说明某次捕获使用的是哪一种。

### 游戏密钥

```
key = cryptoKeyDataSeed                     the game's own 16-byte constant
key[1]  = (version >> 8) & 0xFF
key[3]  = (version >> 4) & 0xFF             version = the local communication version,
key[7]  = (version >> 1) & 0xFF                       which the advertisement carries
key[12] = (version >> 0) & 0xFF
```

公开的每游戏密钥，就是某个游戏版本下的这个值，仅在字节 1、3、7 和 12 与种子不同（`ldn_game_key()`）。《剑／盾》的密钥是一个 16 字节 ASCII 字面量，用一条 `ldp` 加载后直接使用，不变换，没有种子，也没有版本替换。

### LDN 会话密钥

对于 Pia 5.9-5.45：

```
rnd = four SEAD draws, seeded with the session parameter from the advertisement (+0x0c),
      packed little-endian into 16 bytes
session key = AES-128-ECB(game key).encrypt(rnd)
```

SEAD 是任天堂标准库的随机数生成器，通过 `s[i] = (prev ^ (prev >> 30)) * 0x6C078965 + i` 初始化状态，并运行移位量为 11、8、19 的 xorshift128（`pokeldn/ldn/sead.py`; `pia5.ldn_session_key()`）。对于 Pia 6.16+（火红），会话密钥是以游戏密钥对 SSID 执行 AES 的结果（[无线层](ldn.md#hosting-for-an-emulator)).

### AES-GCM IV

对于 Pia 5.27-5.45 和版本 4（`ldn_nonce_crc()`, `gcm_iv()`):

```
IV[0..2]  = first three bytes of crc32( network id (little-endian) || source MAC address )
IV[3]     = source variable id & 0xFF        from the packet header
IV[4..11] = the packet's 8-byte header nonce
```

源 MAC 不在数据包中；其余信息来自捕获或广播通告。明文使用 `0xFF` 填充到 16 的倍数，这些已知明文可在一个 AES 区块内检验候选密钥。

## 各种协议

来自 `GetProtocolId`（每个 `nn::pia` 协议对象上的 vfunc4，函数体为两个机器字），通过 RTTI 虚表读取。

| id | 类 | 说明 |
| --- | --- | --- |
| 0x14 | MeshStationProtocol | 连接握手；也承载每一条网状网络确认消息 |
| 0x18 | MeshProtocol | 加入、网状网络更新、主机端迁移 |
| 0x1c | SyncClockProtocol |  |
| 0x24 | LocalProtocol | 主机端重播的会话更新 |
| 0x54 | BandwidthCheckProtocol |  |
| 0x58 | RttProtocol | 往返时间测量 |
| 0x68 | UnreliableProtocol |  |
| 0x77 | ClockProtocol |  |
| 0x7c | ReliableProtocol | 可靠滑动窗口 |
| 0x80 | BroadcastReliableProtocol |  |
| 0x84 | ReliableBroadcastProtocol | 与 0x80 不同的类 |
| 0x94 | SessionProtocol |  |
| 0xa4 | MonitoringDataProtocol |  |

BDSP 注册了九种：0x14 v2、0x18 v3、0x1c v0、0x24 v0、0x58 v3、0x68 v1、0x7c v3、0x94 v1、0xa4 v0。网状网络协议版本 3 将库范围限定为 Pia 5.30-5.45，可靠协议版本 3 又将其限定为 5.31-5.43。

### 加入网状网络

站点依次通过会话更新（0x24）、连接请求（0x14）和加入请求（0x18）完成加入；每项每 500 ms 重传一次，直到得到确认。

Mesh Protocol 没有 ack 类型（5.31-5.43 没有对应构建器）：确认网状网络消息的四处位置都调用 `MeshStationProtocol`，因此 ack 是 0x14 上八字节的类型 5 确认消息，`05 00 00 00` 及大端序 ack id。无论消息多长，ack id 都是最后四个字节（`size - 4`，带借位检查；不足四字节时为 0）。`pokeldn/ldn/mesh_protocol.ack_for()`。主机端在发送加入响应之前先确认加入请求；接收器对每个副本都确认。

### 离开会话（Pia 6）

`Session::LeaveAsync` 启动 `LeaveSessionJob`；其第一步 LeaveSessionJob::LeaveMesh 在非主机端站点上启动 `LeaveMeshJob`（`LeaveMeshWithHostMigrationJob` 则用于主机端）。`LeaveMeshJob` 的第一步 SendLeaveRequest 发送 Session 类型 3 离开请求，并等待主机端的类型 4 响应 500 ms，最多发送四次。从调用到首次发送类型 3 之间，Pia 内没有计时器运行；此前的延迟属于游戏层。

|  | 宝可梦传说 阿尔宙斯 1.1.1 | GBA 应用（Pia 6.39） |
| --- | --- | --- |
| `Session::LeaveAsync` | `0x72a6dc` | `0xb1060` |
| `LeaveSessionJob` 启动，第一步 LeaveMesh | `0x72c5a4` -> `0x72c640` | `0xb460c` -> `0xb46f0` |
| 非主机端分支转到 `LeaveMeshJob` 的启动流程 | `0x734f04` -> `0x734dd0` -> `0x73b820` |  |
| SendLeaveRequest | `0x73b898` | `0xcacf4` |

步骤名称来自任务保存在各步骤指针旁的字符串（`LeaveSessionJob::LeaveMesh` 位于 `0x37a2eb9`，在《阿尔宙斯》中；`0x174e53`，在 GBA 应用中）。其它步骤为 WaitLeaveMesh、WaitLeaveMeshWithHostMigration、WaitHostMigrated、MeshCleanup 和 DisconnectNetwork；6.39 还包括 WaitDisconnectNetwork、SendMonitoringData 和 CompleteProcess。

## Local Protocol（0x24）

主机端约每 100 ms 广播一次会话更新（类型 0x11），直到所有站点确认：

```
local message header  version 1, type 0x11, size 73
sequence id
network id            random, not the advertisement's network id
host variable id      the same value as the packet header's source variable id
host constant id
allow participating
node 0..7             address:port and a ranking byte each
host migration state
```

八个九字节节点槽位，外加一个字节。Pia 消息头部为大端序，这些字段为小端序，字段中的本地地址则为大端序。`pokeldn/ldn/local_protocol.py` 解析此消息及版本 4 的对应消息。

### 确认消息

ack（类型 0x21）为 20 字节，来自 `LocalAckMessage::Serialize` (`main.bin 0x016bc0f4`): `1`，位于 0 处；类型位于 1，载荷大小半字位于 2，六个零字节位于 4，序列 id 位于 0x0C，四个零字节位于 0x10。构造函数（`0x016bc0c8`, `mov w8, #0x14; str w8, [x0, #0x14]`）将 20 写入 +0x14 处的半字，并将 +0x16 处的载荷大小清零。

`LocalProtocol` 对全部四种类型使用同一个发送路径（`0x016af22c`），因此 ack 与会话更新采用相同帧封装：存在标记为 `0x7F`，标志为 `0x11`（“目标是位图”加“不可捆绑”），协议 36，端口 0，目标 0。位图（`0x0159a15c`）为 `1 << station index`，广播则为 0。客户端向网络广播地址广播其 ack，数据包的 `dst_var` 为 0，消息目标为 0；重播停止就是通过的信号。

ack 按发送方地址确定归属：`0x016af96c` 调用 `0x016aec94`，后者遍历位于 `this+0x188` 的九个节点槽位（步长 0x40），比较 +8 处的 16 字节地址和 +0x18 处的端口。客户端 variable id 参与 IV 构造（源 variable id 的低字节），因此一次运行内必须稳定且非零。

## Mesh Station Protocol（0x14）

分派器用字节 0 减一作为七项表的索引（版本 4：`0x017c5f50`，表 `0x02081804`；BDSP：`0x0154e848`，表 `0x3e6b38f`）：依次为连接请求和响应、断开请求和响应、ack、中继连接请求和响应。

### 版本 9 连接请求

按以下顺序检查：

| 偏移 | 字段 | 失败结果 |
| --- | --- | --- |
|  | 大小 15..949 | 丢弃 |
| 0x0 | 消息类型、连接结果、平台 id | 丢弃 |
| 0x3 | 目标 constant id，大端 u64，与主机自身的值比较 | 无回复 |
| 0xB | 目标 variable id，大端 u32，与主机自身的值比较 | 无回复 |
| 0xF | 协议数量，与主机自身数量比较 | 无回复（错误 0x11c26） |
| 0x10 | 相应数量的（id、版本）对 | 版本过低 → 结果 2，过高 → 结果 3，两者都会回复 |
|  | 站点位置大小，大端 u16，0x20..0x40 | 丢弃 |
|  | 站点位置本身 | 丢弃 |

`0x0159b850` 对未注册 id 返回版本 0，因此 `(0xFF, 1)` 始终触发“过高”：能触发拒绝的 `(0xFF, 1)` 对数量 N，就是主机的协议数量。

结果字节在以下位置由内部错误映射得到：`0x0154f5e8`:

| 错误 | 结果 | 含义 |
| --- | --- | --- |
| 0x646f | 2 | 请求方版本过低 |
| 0x6470 | 3 | 版本过高 |
| 0xc24 | 4 |  |
| 0xc25 | 1 |  |
| 0x11c0f | 7 | 解析成功，所有版本匹配，但第二阶段拒绝；也表示“此 variable id 已属于我的某个站点”（站点离开、玩家重新进入房间或换用新 id 后解除） |
| 0x11c26 | *（无）* | 协议数量不匹配：无回复 |

从不检查 id：九个 `(0xFF, 0)` 条目即可通过协商。

站点位置中的地址大小字节将端口计算在内：InetAddress 解析器将 `1 << size` 与 `0x00040044` 比较，因此只有 2、6、18 通过。请求解析器忽略位置解析错误，因此畸形位置会被读成 variable id 为 0 的请求，所有 variable id 都会得到相同拒绝。

从二进制读取的大小：ack 为 8 字节（`0x0154fa2c`），拒绝为 15 字节（`0x015501ec`），断开响应为 1 字节（`0x0154ea60`).

### 版本 4 连接请求

处理器 `0x017c62a0` 在相同协议上读取不同的消息：

```
[0]     message type            1
[1]     a byte compared against the station's own byte at +0x79
[2]     platform id             must be 9   (5.27-5.45 checks 4)
[3]     0 or 1; anything higher is rejected. 1 means the request also names a target variable id
[4]     target constant id      big-endian u64, compared against the console's own
[0xC]   target variable id      big-endian u32, checked only when [3] is 1
[0x10]  protocol count          compared against the console's own count at +0x78
[0x11]  the sender's station location
```

从偏移 3 起，版本 9 的各字段都提前一个字节。没有协议列表：从 0x11 起就是站点位置（一次序列化器调用，上限 0x40 字节），与版本 9 相同（反序列化器 `0x0185ee20`，偏移相同，地址大小为 2、6 或 18），因此 [1] 和 [0x10] 是它的 NAT 标志和 NAT 位置。

[3] = 1 时主机不回答（96 次请求）。[3] = 0 时，主机以自身请求回答：其位置、constant id、会话更新分配给加入方的 variable id、服务 variable id、一组 NAT 四元组，最后是 ack id，即逐消息计数器，由 `0x017d5750` 在消息大小减四处读取。

平台检查（`0x017c62e8`）最先运行，不匹配时会回答：响应发送方 `0x017c6c30` 分配 17 字节，`[0] = 2`, `[1] = result`, `[2] = 9`, `[3] = 0`。后续检查失败都没有回复，因此错误平台可以区分“从未到达处理器”与“未通过后续检查”。平台 4 从零售版《剑》获得 `02 02 09 00 00 00 00 00 00 00 00 00 00 00 00 00 00`：结果为 2。

清除 [3] 后的握手：

```
->   the console's connection request
<-   the joiner's connection response, result 0, carrying the console's constant and variable ids
->   `05 00 00 00 <ack id>`, a type-5 ack, eight bytes
->   its own connection response, result 0, ~600 bytes, carrying the joiner's constant id,
     variable id and the player's name in plain ASCII, repeated until acknowledged
```

ack 中的 u32 是被确认消息尾部的计数器。发送主机请求对应的类型 5 ack，即可停止其重传（`--ack-request` 在桥接驱动上发送它）。响应处理器不读取任何 ack 状态：类型 5 处理器（`0x017c6034`）只从待处理表中清除该 id（`0x017d5770`），而主机的连接任务（`0x017afa70`）在收到 ack 或站点进入状态 5 时都会完成。零售版《剑》读取了未附带 ack 发送的全部 12 条响应。

### 连接响应被读取所须满足的条件

类型 2 和 7 到达处理器 `0x017c6e70`（条目 `0x017c5fb4` 和 `0x017c60c0`，表 `0x02081804`；类型 7 条目传入 w2 = 1）。结果不为 2 的响应会逐字段检查，每次失败都会静默丢弃：

| 处理器读取项 | 要求 | 失败结果 |
| --- | --- | --- |
| `[1]` 结果字节 | 2 走独立路径 |  |
| `[5]` 一个大端 u64 | 接收方自身的 constant id | 丢弃，`0x017c6f48` |
| `[0xD]` 一个大端 u32 | 接收方自身的 variable id | 丢弃，`0x017c6f68` |
| 发送方的站点位置 | 解析为它已知的站点 | 丢弃，`0x017c6f04` |
| `[0x37]` 一个字节，仅限结果为 0 时 | 小于 5 | 丢弃，`0x017c6ff0` |
| +0x48 处的站点状态 | 4，在发送 ack 后检查（`0x017c71a4`) | 返回；接受时为 5（`0x017c7990`) |

主机在 `0x017c7134` 处确认响应，位于 `[0x37]` 检查之后、状态检查之前：从未得到 ack 的响应，是 id、位置或 `[0x37]` 未通过检查。结果非零，或 `[0x37]` 大于等于 5 时，会将其结果（该门槛对应 2）保存到 station +0xa0 所指对象的字节 +0x79。

该对象是站点的网状网络 ConnectStationJob。其步骤 `0x017afa70` 读取该字节（`0x017afc34`），条件是仍未到截止时间且站点未处于状态 5：0 继续等待，1 表示错误 `0xc25`，2 表示 `0x646f`, `0x6470` 或 `0x11c26`，由 `+0x7c` (`response[2] - 9` 的符号决定），其它值为 `0xc24`。它将错误交给等待上下文（`0x01769720`），释放待处理 ack id（`0x017d5770`），并将站点从状态 4 转为 6（`0x017afafc`）。状态 4 通过指向 station +0x48 的指针（`str w9, [x8]`）由 `ProcessConnectionRequestJob::ConnectToRequesterStation` (`0x017c8e90` 写入，写入点为 `0x017c8fd8`），用于类型 1 请求；以及 `::WaitInverseConnection` (`0x017c9760`，写入点为 `0x017c98a8`），用于类型 6 消息；两者均由请求处理器 `0x017c62a0` (`0x017c6aac`, `0x017c6aa4`）调用，调用前它会将对方 id 保存到 +0x79、将状态设为 3，并将自身 id 保存到 +0x78。在状态 3 且 `request[3]` 不为 1 时，两者分别向对方启动 ConnectStationJob（`0x017af520` 或 `0x017b0120`），写入状态 4、设置截止时间并安装步骤 `0x017c9080`；上下文中出现错误时，该步骤结束（`0x017c90d4`）。当 `request[3]` 为 1 时，它们返回 0，不写入任何内容。

一条 17 字节响应（`RESPONSE_SIZE`，短格式分配 `mov w3, #0x11` 位于 `0x017c6c30`）会使 `[0x37]` 落在消息末尾之外 38 字节处的旧缓冲数据中，因此能否读取取决于发送方无法控制的内存：在 ldn_mitm 下模拟运行的《盾》1.3.2，无论是否确认其请求，52 条中只接受 3 条；零售版《剑》则 12 条全部接受。模拟运行的《盾》对填充到 56 字节、且在 `[0x37]` 处写入 1 的响应，23 条全部接受；该处写入 5 时，4 条中接受 0 条。填充形式即使不确认其请求，也在首次发送就被接受（`bin/swsh_connect.py --ip-join`）。主机自身表示接受的响应为 840 字节，在 `[0x37]`; `station4.build_connection_response(..., min_size=ACCEPTED_RESPONSE_SIZE)` 填充到 0x38 并写入 1。在这一层被接受并不意味着上层游戏启动：《剑》和《盾》还在等待 0x37 之后的字段（[到达游戏层](swsh_session.md#reaching-the-game-layer)).

响应之后：主机发出连接响应表示接受；若每 500 ms 重传尾部计数器相同的请求，则表示拒绝（携带加入方自身 id 的响应触发了 20 次重传，随后沉默）；单纯沉默两者都不代表。用主机 id 回答请求、且始终不确认该请求时，44 s 内没有触发重传。

主机请求 [1] 处的 NAT 标志字节会随连接变化，不对应加入方可控制的任何字节（在 26 次连接中，对每项尝试的两种解释都测试过）。谁写入它仍未知；其记录由站点位置解析器 `0x0185ee20`.

## Mesh Protocol（0x18）

`MeshProtocol::vfunc9`（接收槽位）以字节 [0] 减一作为表索引，上界为 0x80（版本 4：分派器 `0x017c0c80`，表 `0x02081564`）。129 个条目中有十九个实际生效；版本 4 相比 BDSP 少了 0x22 DUMMY_MESSAGE 和 0x23 DUMMY_ACK。

加入请求为六字节：类型 1、站点索引 253（“尚未处于网状网络中”）、一个 ack id。版本 4 处理器（`0x017c1700`）检查 [1] 是否为 0xFD，通过 `0x017d5750` 取得 ack id，并在 0x14 上确认（`0x017c6dd0`）。Pia 会重传该请求约十秒。

两个版本范围中的加入响应头部都是十六字节。版本 4 解析器 `0x017b4830` 先读取拒绝形式（`[1] == 0`, `[2] == 0xFF`, `[3] == 0xFF`，原因位于 [4]），随后检查 [1] 的站点数是否超过最大值，将 [8] [9] [0xA] 作为一个大端 24 位值读取，并读取 0xC 处的大端更新计数器。

站点条目：5.31-5.45 使用 68 字节（64 字节站点位置、站点索引、大端半字加入顺序）；版本 4 使用 64 字节，索引位于 0x3E，没有加入顺序（游标从 `0x10 + 0x3E`, `ldrb w8, [x20], #0x40` 开始；超过 `0x810 = 0x10 + 32 * 0x40` 的响应会在 `0x017bfa34` 处因 32 站点上限被拒绝）。两个长度验证了这一点：

```
join response   148 B  =  0x10 + 2 * 0x40 + 4        68-byte entries would give 156
update mesh     524 B  =  12   + 8 * 0x40            BDSP's eight 68-byte seats give 556
```

版本 4 的不同路径从不同字段取得条目数：未分片路径（`fragments == 1`, `0x017b48f4`）从基准 0 开始遍历 `stations` 个条目，从不读取 [6] 或 [7]；分片路径（`0x017b4b6c`，最多三个分片）将 [6] 个条目写入槽位 [7]，并对照第一个分片检查 [1]-[4]。5.31-5.45 两条路径都取 [6]，因此在那里，[6] 为零的单分片响应会被读成空网状网络。`parse_join_response(version4=True)` 同时遵循这两条路径。

UPDATE_MESH（0x20）约每秒一次，是主机端提供的在网状网络内成员列表；BDSP 中始终是完整的 556 字节，未用席位清零，因此应按 `entries` 字节遍历（`mesh_protocol.parse_update_mesh()`）。5.31-5.45 的加入顺序统计自网状网络建立以来的加入次数：同一机器连续连接三次后，主机端为 0，索引 1 的客户端为 3。

### 主机端迁移

被指定为下一任主机端的站点必须回答。0x18 端口 1 上的网状网络消息在可靠头部之下到达。

MIGRATION_START（0x44）为三字节。处理器 `0x017c1f00` 会拒绝消息，除非满足：

```
size == 3                                     0x017c1f54
[1] == the mesh's HOST index, byte 0xAB       0x017c1f64, getter 0x017bbfe0
[2] <= 0x1F                                   0x017c1f78, the 32-station bound
[2] != that host index                        0x017c1f8c
```

且发送方 `0x017c31b8` 构造的内容恰好是 `[0x44, host index, new host index]`.

回答是 `[0x48, own station index]`：MIGRATION_RESPONSE 处理器 `0x017c10ac` 要求 `size == 2`，而构建器 `0x017c3310` 写入 `[0x48, w22]`，其中 w22 来自 `0x017bc430`。两个 getter 相隔一个字节：`0x017bbfe0` `ldrb w0, [x0, #0xAB]`（主机端索引）、`0x017bc430` `ldrb w0, [x0, #0xAC]`（自身索引），在承载网状网络的站点上两者相等。

MIGRATION_FINISH（0x41）结束流程：`[0x41, host index, flag & 1]` (`0x017c2ef0`），处理器 `0x017c0fb0` 检查 `size == 3`，并检查 [1] 是否为主机端索引。

响应发给新的主机端（`0x017c3250`，由 `0x017ca1a0` 调用）。该站点广播 `MIGRATION_FINISH`；将响应发给即将离开的主机端，无法完成交接。

`pokeldn/ldn/mesh_protocol.py`: `parse_migration_start`, `build_migration_response`, `build_migration_finish`, `parse_migration_finish`。公开的四个《剑／盾》客户端都不处理迁移；两台主机之间则由被指定站点回答。

## RTT 协议（0x58）

主机端从每个站点进入网状网络起对其测时（wiki 中没有页面介绍这一点）。版本 9 的消息为十三字节：

```
u8   kind        0 = request, 1 = response; anything else is dropped
u64  timestamp   big-endian, the sender's own clock
u32  target      big-endian, whose reply this is; zero is accepted by everyone
```

版本 4 保留 id 0x58（vfunc4 `0x0185d590`）；其解析器（`0x0185d2a0`）固定读取十六字节，忽略十三字节回答。观察到的每个请求中，字节 1..7 都为零，含义未知；`rtt_protocol.response_for_v4()` 原样回显它们，只设置种类。

站点回答种类 1 时会回显时间戳。主机端将 `(now - echoed) / ticks per ms` 存入每站点九样本环形缓冲区，填满后以中位数作为 RTT；BDSP 时间戳约以 31.36 MHz 运行。在测量过的 BDSP 会话中，RTT 协议不会移除沉默站点，只会停止采样。更新请求周期在 `0x015ace54` 之后分为 410 ms 和 500 ms 两个分支：无回答时，BDSP 每 410 ms 请求一次；所有环形缓冲区填满后，每 508 ms 一次，可靠重传间隔也随实测的小 RTT 调整（约每秒六轮）。

BDSP 地址：id 与版本 `0x015ada10`/`0x015ada18`，大小（`mov w0, #0xd`) `0x015adab4`，序列化／解析 `0x015ada24`/`0x015ad54c`，更新 `0x015acd90`，回答构建器 `0x015ad024`，目标检查 `0x015ad000`，样本环形缓冲区 `0x015ad058`.

## 可靠滑动窗口（0x7c）

### 版本 9（Pia 5.29-5.43）

```
0x0  1  flags     1 application data, 2 message start, 4 message end, 8 is initialized,
                  16 zlib, 32 reset, 64 reset ack
0x1  1  stream id
0x2  2  payload size, big-endian
0x4  2  sequence id, big-endian
0x6  2  lowest sequence id pending ack, big-endian
0x8  1  number of destination bits (N)
0x9  4 * ceil(N / 32)  destination bitmap words, big-endian
        payload
```

`GetSize` 是 `9 + (((N + 0x1f) >> 3) & 0x3c)`，因此为 9 或 13 字节。N 达到 0x20 或更大，以及载荷达到 0x5a1 或更大时都会被拒绝。

应用数据标志未设置时，载荷为批量确认：

```
0x0  1   a bitfield; 0 in every captured ack. Its bit 0 sets a flag on the receiver
0x1  1   entry count, refused at 0x21 or more
0x2  21 * n  entries: u8 stream id, u16be ack id, u16be `ack id - 1`, 16-byte ack mask
```

零售版主机对序列号 0 和 1 的 ack：

```
00 00 0017 ffff 0003 00   00 01   00 0002 0001  00 * 16
```

无标志，流 0，序列 id 为 0xFFFF（控制消息没有序列号），随后是发送方仍在等待的最低 id。`ack id` 比已接收的最高序列号大一。`pokeldn/ldn/reliable5.build_ack_message()` 逐字节复现它。序列号为 0 的数据消息不触发 ack；序列号 1 则会触发。

### 接收器静默丢弃的内容

接收路径针对端口窗口检查单条消息，并将载荷复制到槽位：《朱》4.0.0 为 `main.bin` `0x006f0330`；《晶灿钻石》1.3.0 为 `0x159fb98`，由 `ReliableSlidingWindow` 接收 `0x159f1e4` 在标志位 0 被设置时进入（位 5 表示重置，位 6 表示重置 ack，其它情况都是窗口槽位 13 的 ack；`0x159f88c..0x159f8b8`）。五种条件会丢弃消息却仍返回成功；其中两种还会设置“待发 ack”字节（《朱》协议 `+0x48`，BDSP 窗口 `+0x738`），因此发送方会读到某条消息的 ack，但应用从未收到该消息。

| 消息被丢弃的条件 | 朱 | BDSP | 是否仍发送 ack |
| --- | --- | --- | --- |
| 窗口未初始化，且标志缺少 `is initialized`（位 3） | `0x6f037c` | `0x159fbd8..0x159fbe4` | 否 |
| 序列 id 低于窗口基准 `+0x18` | `0x6f03cc` | `0x159fc30..0x159fc3c` | 是，`0x6f03d0` / `0x159fc3c` |
| 目标数量（解析后的头部 `+0x10`）非零，且位图没有接收方对应位 | `0x6f0430` | `0x159fc7c..0x159fca4` | 否 |
| 流 id（线路字节 1，解析后的头部 `+9`）与初始化时锁存在窗口 `+0x1e` 处的值不同（BDSP 为 `strb w26, [x24, #0x1e]` `0x159fc14`) | `0x6f0454` | `0x159fcc0..0x159fcc8` | 否 |
| 环形缓冲槽位已占用 | `0x6f0540` | `0x159fdb0..0x159fdb4` | 是，`0x6f0530` / `0x159fda4`（在检查之前） |

三种条件会返回可读取的结果（《朱》）：序列号超过窗口末端 `0x4c0d` (`0x6f04a4`）、重组超过 `0x5a1` 字节 `0x10407` (`0x6f05cc`）、zlib 载荷无法解压 `0x2c03` (`0x6f0580`).

BDSP 接收环形缓冲区位于窗口 `+0x38`：槽位缓冲区 `+0x8`、槽位数 `+0x10`、环形队首 `+0x14`、基准序列号 `+0x18`、流 id `+0x1e`、已初始化标志 `+0x1f`。每个槽位为 `0x5b8` 字节；环形索引通过减法回绕。槽位内容：占用字节 `+0`、消息结束标志 `+1`、zlib 标志 `+2`、载荷大小 `+4`、载荷起于 `+6`、逐端口句柄 `+0x5a8`、时间戳 `+0x5b0`。不保存消息开始标志；重组从基准开始，一直到第一个带结束标志的槽位。

流中的第一条消息将基准设为自身序列 id（`strh w25, [x24, #0x18]` `0x159fc10`）；只有目标和流 id 检查通过后，才设置已初始化标志（`0x159fce4`）。序列号会以 `0x4c0d` 被拒绝，条件是 `seq - base + [ring+0x1c] >= [ring+0x10]` (`0x159fc60..0x159fc78`); `+0x1c` 是环形队首偏移，新流上为 0。

BDSP 窗口更新 `0x159fea8` 在计时器（窗口 `+0x740` 加周期 `+0x778`）到期时发送待发 ack（`0x15a003c..0x15a005c`），调用窗口槽位 11 `0x15a1c78`，所用数据包写入器位于 `+0x750` (`0x15a0318`, `0x15a0354..0x15a0364`）。若 `+0x738` 为 0，槽位 11 直接返回（`0x15a1cb8`）；否则构造序列号为 0xFFFF 的控制消息（`0x15a1de4`），可像数据一样选择压缩（`+0x7ac`, `0x15a1f70`），通过槽位 10 发送（`0x15a203c..0x15a2044`），清除 `+0x738` (`0x15a1fe8`）并重启计时器（`0x15a1ff8`）。槽位 10 将位于 `+0x748` 的协议与端口字写入头部（`0x15a1be8`），再将数据包交给写入器（`0x15a1c0c`, `0x15a1c20`）。ack 会发给窗口 `+0x638` 中的每个活跃对端；若一个也没有，则不发送，直接清除该字节（`0x15a1eb4`, `0x15a1fd8..0x15a1ff8`）。槽位 11 也会在数据路径上运行（`0x15a0298..0x15a02b8`），因此 ack 会随数据一起发送。

《朱》在窗口 `+0x18` 处写入基准，写入位置包括 `0x6f03a8`（初始化）、`0x6f0238`（每交付一条消息前进一步）以及 `0x6f1734`/`0x6f176c`，后者朝窗口 `+0x20` 处的目标遍历空槽位（由 `0x6ef228` 设为 -1，负数时不遍历，遇到首个已占用槽位就停止）。接收函数 `0x6efc2c` 在窗口检查之前，将头部反序列化到 `sp+0x18`（`0x6efdc8`, `MessageHeader` vfunc3）；`0x6eff24`/`0x6eff28` 将它的 `lowest pending`（头部 `+0x6`, `[sp+0x26]`）复制到窗口 `+0x20`，而 `0x6eff2c` 处的遍历最多将基准和环形队首推进 `lowest pending - base` 个槽位。

因此，发送方自身的 `lowest pending` 会驱动对端的接收基准。若宣告值高于发送方下一序列号，就会使基准越过尚未发送的消息；这些消息之后到达时已低于基准，会在 `0x6f03cc` 被丢弃但仍获 ack：一个模拟运行的《朱》站点在基准为 8 时丢弃了主机端的提交消息（序列号 7），一台 BDSP 主机则将主机端序列号 5 和 6 确认为 `(7, 7)` 和 `(8, 8)`，却从未交付它们。ack 在头部和条目的第二个半字中，都携带发送方自身最低的未确认序列号。

### 窗口发给谁（Pia 6）

一个 `ReliableSlidingWindow` 的目标是位于窗口 `+0x40` 处的站点指针，按站点索引排列，大小由 `[[0x46d0860]]+0x50` 决定（《朱》4.0.0 `main`），由 Pia 在站点事件发生时填充，无须游戏代码。唯一的非空写入是 `0x6ef69c` (`str x23, [x8, x25, lsl #3]`），位于 `0x6ef588` 中，它将站点注册到某个索引；空值则在 `0x6ef3dc`, `0x6ef4e0`, `0x6ef9b4`. `0x6ef588` 在以下情况下拒绝：

| 拒绝条件 | 代码 |
| --- | --- |
| 窗口无容量，`[w+0x28]` 为零 | 0x1040c |
| 站点为空、等于窗口自身的 `[w+8]`，或索引等于窗口自身的 `[w+0x10]` | 未读取 |
| 索引已被占用 | 0x10407 |
| 该索引的逐站点记录（窗口 vfunc `0x40`）的字节 `+0x1f` 已设置（`0x6ef650`..`0x6ef664`) | 0x10408 |
| 该站点已注册到另一索引 | 0x10408 |

成功时，它重置该记录（vfunc `0x10`），将索引写到 `+0x24`，并将来自 `w3` 的一个 u16 写到 `+0x26`，再在 `[w+0x74]` 中设置该索引对应位。其调用方是槽位 11 的站点事件方法：`0x6e6288`，BroadcastReliableProtocol（0x80），`bl` 位于 `0x6e630c`，先由 StreamBroadcastReliableProtocol 的槽位 11 `0x6f51a8` (`0x6f51bc` 调用）；以及 `0x6ee528`，ReliableProtocol（0x7C），调用位置为 `0x6ee5d4`. `0x6e6288` 根据事件 `+8` (`[[0x46d0860]]` -> `0x1e7c4e8` 处的 id 查找事件对应站点 -> vfunc `+0x38`），当协议自身站点索引为 0xfd（`0x6ec4f0`）或该站点就是自身时返回（`0x6ec4a8`，与 `[station+0x30]` 比较）。事件 0 将 `[station+0x30]` 注册到索引 `[station+0x28]`，使用 `[station+0x38]`；事件 1 移除该索引（`0x6ef75c`).

站点只有在加入事件之前、离开之后、协议的站点索引为 0xfd，或 `0x6ef588` 拒绝它时，才会不在列表中。批量 ack 组合器 `0x6f2138` 读取相同列表：跳过空项（`0x6f2324`..`0x6f232c`），检查站点的 ack 状态后，设置该站点的头部目标位（`0x6f22f8`..`0x6f230c`），否则退回调用方掩码（`0x6f2360`..`0x6f2370`）。ack 中出现某一位，只表明窗口已注册该站点，不能说明向它发送过什么消息。

### 版本 4

同一个头部类同时用于 0x7C 和 0x80：`nn::pia::transport::ReliableSlidingWindow::MessageHeader`（GetSize `0x0184e480`、Deserialize `0x0184e390`、Serialize `0x0184e230`).

```
0x0  1  flags
0x1  1  stream id
0x2  2  payload size, big-endian    refused at 0x589 and above (0x0184e3cc)
0x4  2  sequence id, big-endian
0x6  2  lowest sequence id pending ack, big-endian
0x8  1  destination count           refused at 0x20 and above (0x0184e404)
0x9  8 * count  station constant ids, big-endian
```

`GetSize` 是 `9 + 8 * count`。两个版本只有在数量为 0 时一致，而双方发送的每条 0x7C 消息都如此，因此版本 9 解析器读取了 221887 条版本 4 消息，没有任何字段错位。

接收路径（`0x01859338`）会静默拒绝五种情况：

```
0x0185952c   payload size <= 0x57F - 8 * count     tighter than the deserialiser's own bound
0x0185954c   the Pia message length equals 9 + 8 * count + size exactly
0x0185956c   the stream id is the window's own for this station, [w + 0x18*st + 0x46]
0x01859578   a count above 0 is a list the receiver must find itself in; count 0 is unfiltered
0x01859ca0   the first message on a stream carries FLAG_IS_INITIALIZED
```

它按 `0x01859734` 处的标志分派：位 5 为 RESET，位 6 为 RESET_ACK，位 0 为 APPLICATION_DATA；其它情况，包括无标志，都进入 ack 处理器 `0x01859a70`.

只要逐站点字节 `[window + 0x18*station + 0x47]` 为零，流就不存在；第一条数据消息必须携带 FLAG_IS_INITIALIZED，并设置流 id（`+0x46`）和起始序列号（`+0x40`）。主机第一条消息发送标志 0x0F，之后发送 0x07。`reliable4.build_data_message(bytes.fromhex("610000000a00"))` 逐字节复现主机的序列号 1：`0f0000060001000100610000000a00`.

ack 载荷恰为 0x260 字节，即 wiki 原有的“Ack Data”，5.29 将其替换为带数量的列表：

```
5.29-5.43   1 unknown byte, 1 count, then `count` x 21 bytes
                u8 stream id, u16be ack id, u16be the window's field 0x50, 16-byte mask
version 4   32 entries of 19 bytes, always
                u8 stream id, u16be ack id, 16-byte mask
```

处理器 `0x01859a84` 打开 `ldrh w8, [x2, #0xa]; cmp w8, #0x260; b.ne`，不读取主体就返回 0x2c03；序列化器 `0x0185bfb0` 循环 0x20 次，写入流 id、大端 ack id，以及作为两个大端 u64 半部写入的十六字节掩码。所读槽位是来自处理器第四个参数的站点索引，该位置无法表明是哪个站点；槽位流 id 必须与窗口流 id 匹配（`0x01859c1c`). `reliable4.build_ack_payload` 将每个槽位都填为同一条目，无论哪种解释都正确。

《盾》会在未使用的槽位中保留旧字节，流 id 为 0（`22284`, `16`, `57080`, `2517` 位于槽位 1、2、4、5，而槽位 0 为 2）。只应读取被确认流对应的条目：所有槽位的最大值是旧数据，跟随该值的发送方会越过主机窗口（窗口在 97 时发送了 401 条消息），之后主机便停止确认。

序列 id 不断增长，而 `lowest_pending` 固定不变，表示积压持续增长；应按消息测量 `lowest_pending`，并按序列 id 测量重传次数。

## 协议 0x80：广播可靠窗口

`nn::pia::transport::BroadcastReliableProtocol`（vfunc4 `0x0184d880` 返回 0x80），与 0x84 的 `ReliableBroadcastProtocol` 是不同的类。其消息经过压缩（版本 4 标志 0x10）：原始 42 字节，解压后 625 字节，可靠头部的目标数量为 1，在 0x260 ack 载荷之前带有一个八字节站点 constant id（按版本 9 的位图规则则为 621 字节）。ack 按站点索引，为网状网络可容纳的每个站点各设一个槽位：主机将真实 ack id 填入 0..7，8..31 保持为零，其中 8 来自 `max_total`，取自加入响应。

## 协议 0x81：流式广播可靠传输（Pia 6）

`StreamBroadcastReliableProtocol` 将一个定长数据块分块从某个站点传给每个请求该块的站点（《朱》4.0.0 `main`）。槽位 10 是其更新方法 `0x6f5360`，槽位 11 为 `0x6f51a8`，槽位 17 为 `0x6e6818`，槽位 19 为 BroadcastReliableProtocol 的 `0x6e69a0`，它从 `[proto+0x70]` 加载窗口，并运行 `ReliableSlidingWindow` 发送循环 `0x6f0638` (`bl`，位于 `0x6e69c0`），字节预算为 `[proto+0x64]`；循环从重传截止时间 `0x6f0d14` (`bl` 取得各槽位的下一时间，位于 `0x6f073c`）。分块通过 `0x6f1994` (`0x6f5c2c`, `x0 = [proto+0x70]`）入队，它为槽位标记当前时间（`0x6f1bd4`）。0x81 传输与 0x7C、0x80 使用相同截止时间进行重传；只要任一目标没有 RTT 样本，就绝不会重传。

每条消息携带一个十一字节的 StreamData 头部，由 `0x6f60e8`:

```
+0  1  kind: 0 a receive posted, 1 the first chunk, 2 a later chunk, 3 to 6 control
+1  1  transfer id
+2  1  percent of the block delivered after this chunk
+3  4  big-endian u32: the receive capacity in a kind 0, zero in a chunk
+7  4  big-endian u32: the length of the data that follows
+11    the data
```

游戏发送 API 接受缓冲区、大小和传输 id；接收 API 接受发送方、缓冲区、容量和 id，提交接收请求时会发送携带容量的种类 0 消息。大小超过 `[proto+0xa0]`、id 为 0xff，或没有任何站点的 `[proto+0x98]` 字节等于该 id 时，发送会被拒绝。分块循环（`0x6f5b54`..`0x6f5c58`，位于 `0x6f5560`）只要 `0x6f1ef8` 找到空闲槽位就继续入队：每块 `[window+0x70] - 11` 字节，种类为 `(offset != 0) + 1` (`0x6f5bb0`..`0x6f5bbc`），id 来自 `+0xa4`，百分比为 `(offset + chunk) * 100 / size` (`0x6f5b78`..`0x6f5b98`），同时保存在 `+0xba`.

接收循环 `0x6f5cdc` 在更新中于 `0x6f5560` 之后调用，使用 BroadcastReliableProtocol vfunc13 拉取每条消息（`0x6e644c`，发送方位于 `sp+0xb80`），通过 StreamData vfunc3 解码头部（`0x6f635c`），使用 `0xe42ddc` 解析发送方索引，再通过位于 `0x3c0d5e5` 的字节表按种类分支处理，忽略大于 6 的种类：

| 种类 | 目标 | 接收方的操作 |
| --- | --- | --- |
| 0，已提交接收请求 | `0x6f5e5c` | 自身状态为 1、2、4、5、8、9 或 10（掩码 0x736）时，在 `[+0xc0]` 中标记发送方；否则（`0x6f6094`) `[+0x98][sender] = id` 和 `[+0xa0] = min([+0xa0], capacity)` |
| 1，首个分块 | `0x6f5e90` | 清除已接收数量 `+0xac` 和 `+0xba`，状态从 4 转为 5，然后按种类 2 处理 |
| 2，分块 | `0x6f5eb4` | 仅在状态 5，针对 id `+0xa5`，来自发送方 `+0xb0`：将数据复制到 `[+0x88] + [+0xac]`，前提是能容纳于 `+0x90`，累加长度，并将百分比保存在 `+0xba` |
| 3，忙碌的发送方拒绝接收请求 | `0x6f5f2c` | 仅在状态 4：重置传输，将每个 `[+0x98]` 设为 0xff，状态设为 7 |
| 4，发送方取消 | `0x6f5f9c` | 重置传输，将每个 `[+0x98]` 设为 0xff，状态设为 0xC |
| 5，接收方取消 | `0x6f6000` | `[+0x98][sender] = 0xff`，将发送方标记于 `[+0xc8]` |
| 6，发送方确认取消 | `0x6f6024` | 仅在状态 0xA：重置，状态设为 0xB |

控制类种类携带 id 0xff。更新方法 `0x6f5560` 向在 `[+0xc0]` (`0x6f6268` 中被标记的站点发送种类 3，使用 `w2 = 3`, `0x6f5750`），并发送种类 6，目标是在 `[+0xc8]` (`0x6f57d8` 中被标记的站点）；在状态 9，向预期发送方发送种类 5，`[+0xb0]` (`0x6f5904`，通过 `0x6f1de8`）单播，然后进入状态 0xA；在状态 8，向其目标发送种类 4（`0x6f5984`）。已提交的最小容量，决定发送 API 所接受数据块的上限。

位于 `+0x78` (`0x6f53b0`）的状态：当 `+0xba` 达到 0x64 时，接收从 5 转为 6（`0x6f5460`）；当 `[+0x98]` 的一个条目等于 `+0xa4`，且窗口报告序列号 `+0xb8` 已确认时，发送从 2 转为 3（`0x6e7128`, `0x6f54e4`）；若无匹配条目，则转为 0xC。

## 协议 0x84：可靠广播传输

`nn::pia::transport::ReliableBroadcastProtocol` 承载《剑／盾》的交换快照：

| 种类 | 含义 |
| --- | --- |
| 0x11 / 0x12 | 数据分片；[4] 处为计数器，[10] 处为容量 |
| 0x19 | 传输完成 |
| 0x21 | 确认消息，携带连续接收基准和表示提前到达内容的位掩码 |
| 0x28 | 对 0x19 的回答 |

从不回答的接收方永远看不到后三种，发送方会持续重传（尚未测得上限）。`pokeldn/ldn/broadcast4.py`。主机在端口 0 发送自身传输，在端口 1 确认对方传输。

## 未解决的问题

-
-

## 致谢

头部版本表、会话密钥派生和 nonce 布局来自 [NintendoClients 维基](https://github.com/kinnay/NintendoClients/wiki/Pia-Protocol)（其中的 `Pokemon-Brilliant-Diamond.md` 说明了游戏密钥派生；`Pia-Game-Keys` 只列出派生后的密钥；如何搜索它见 [逆向分析 Switch 游戏](switch_re.md)）。各派生方式分别属于哪种网络类型、`cryptoKeyDataSeed` 值以及版本规则，均从零售版本游戏自身代码中读取。
