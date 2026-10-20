---
title: 加入 BDSP 会话，以及加密之下的内容
parent: Brilliant Diamond and Shining Pearl
nav_order: 1
---

# 加入 BDSP 会话，以及加密之下的内容

## 广播通告

```
local_communication_id  0100000011d90000
scene_id                4352 (0x1100) Union Room; 5120 (0x1400) Union Room entered with a
                        password; 12608 (0x3140) Grand Underground
version                 4
channel                 a 2.4 GHz channel, band 2, chosen per session (6 in the capture)
accept_policy           ALL
participants            1/8
application_data        17 bytes
```

comm id 是《晶灿钻石》的游戏标题 id，《明亮珍珠》也共用它（`010018e011d92000`）。广播通告仅需 `prod.keys` 就能解密（`tools/ldn/ldn_scan.py`）。17 字节的应用数据由 Pia 的 LDN 广播通告头部（[无线层](ldn.md)，16 字节）和随后一个字节的应用数据组成；无密码房间中的 CRC32 字段为 0。

通过密码进入的房间在此处携带密码 ASCII 数字的 CRC32，采用小端序（00000000 -> `0xC0088D03`），场景 id 为 5120。`bin/bdsp_connect.py` 不作修改即可加入这种房间；`bin/bdsp_host.py --password 00000000` 会广播这两项信息，输入该密码的主机可以加入并交换。主机在三个阶段进行检查（1.3.0 `main`):

| 阶段 | 代码 | 检查 |
| --- | --- | --- |
| 扫描 | `NetworkHelper.CreateUnionGameMode` `0x224e630`; `nn::ldn::Scan` `0x16be184` | 场景 id 表示游戏模式（0x1100 普通、0x1200 群组、0x1400 密码），也是扫描过滤条件（标志 0x25：comm id、网络类型、场景 id）；其它场景根本不会传到游戏层 |
| 浏览 | `LdnMatchmakeSession` `0x16c1abc`; `GameState_BrowseSessionAfter_LocalRandom2` `0x273f804` | +0x04 处的 u32 非零时，房间受密码保护；设置了密码的主机会跳过无保护房间，未设置密码的则跳过受保护房间 |
| 连接 | `LocalMatchJoinSessionJob` `0x16c36c8`；检查 `0x16b8890` | 加入方计算所输入密码的 `crc32`（`0x1719204`）；+0x08 必须为 8，若 CRC 与广播通告中 +0x04 处的 u32 不同，则会以 0x6c51 失败，发生在以下调用之前：`nn::ldn::Connect` |

主机端在 `LdnProtocol` `0x16b6a14` 中写入该头部：网络 id、密码的 CRC32、字节 8、会话参数。没有任何消息将加入方的 CRC 发送给主机端：输入错误密码的主机不会向主机端发送任何内容，而是自行创建房间。密码超过八个字符时，Pia 保留前八个，其余字符移到应用数据中，位于以下内容之后：`INL1` (`IlcaNetSession.SettingSet` `0x2735f14`).

## 口令短语

```
WirelessStrongCryptoKey2021
```

直接使用原始值：27 字节，不填充也不散列（LDN 接受 16 至 64 字节，并显式指定长度）。游戏通过一个 `nn::ldn::CreateNetwork` 将它交给 `nn::ldn::SecurityConfig`；它从不进入 Pia 的密码运算。

## 占用席位

`bin/bdsp_join.py` 扫描、建立关联并报告参与者表：

```
participant 0: ip=169.254.54.1  mac=48f1eb209b22                 <- the console
participant 1: ip=169.254.54.2  mac=58d8122149a2  name=b'POKELDN' <- the client
```

IP 由主机分配。联盟交谊厅的八个席位就是 LDN 的 `max_participants`。LDN 席位位于游戏层之下：屏幕上不会显示任何内容，它也不是 Pia 会话中的席位。

`Connect failed with status code 1` 表示关联失败；ESP32 开发板大约每两次尝试就有一次失败，因此诊断前应先重试。重新进入房间会创建新网络（新信道、SSID 和会话参数），密钥派生会实时处理这些变化。

房间中的主机可能停止广播通告，而屏幕毫无变化：随机匹配会拆除自身会话并重新匹配。联盟交谊厅通过 `NetworkManager$$StartSessionRandomJoin` [1.3.0 main 0x0224f600]（`SessionManager$$StartSession` 0x01df89e0，来自 `UnionRoomManager$$SetUp` 和 `$$SessionStart`）启动会话，使用一个 `NetworkParam`，其 `Reset` [0x0202ec30] 将 `matchingMode` 设为 1（Random，随机）并设置为本地网络。随机匹配创建或加入会话后（`GameState_JoinProcessAll` -> `ToGameFrontBeforeLocalRandom` [0x02743940]，进入游戏状态 20 的唯一途径），`INL1.IlcaNetSession$$GameState_GameFrontBefore_LocalRandom` [0x02740640] 会在每次会话更新时运行：

| 站点数 | 效果 |
| --- | --- |
| 2 或更多 | `GameFrontRnoInit` 清空两个计数器；继续进入游戏前端 |
| 1 | 计数器 0 和计数器 1（`gameFront_cnt`）各加一 |
| 1，计数器 0 大于 `localRandomMatchmakeHostWaitTime + (localRandomMatchmakeHostWaitTimeMask & r)`，计数器 1 不超过 `localRandomMatchmakeTimeUp` | `CleanupRecoveryToLoggedIn` [0x0273a7f0]，游戏状态 9（`GS_LoggedInReturnWaitWorker`）：关闭会话，重新进行匹配 |
| 1，计数器 0 超过等待值，计数器 1 超过超时值 | `GameFrontRnoInit`；主机继续作为其会话的主机端 |

`r` 是每次进入状态 20 时重新抽取的随机值；进入该状态还会清空计数器 0，而计数器 1 继续运行。`IlcaNetSessionSetting` 构造函数 [0x01f46fc0] 将等待值设为 25、掩码设为 0x7F、超时值设为 270，`SessionConnector$$StartSession` [0x0202f2c0] 不更改这些值。因此，主机独处于新会话中时，会在 25 至 152 次更新后关闭该会话，如此反复，直到累计独处 270 次更新，之后才保留最后一个网络。LDN 接口上的接收器必须过滤自身源 IP：广播会回环。

会话每个渲染帧更新一次，每秒 30 次，因此等待时间为 0.83 至 5.07 s，超时时间为 9.0 s；掉帧会延长两者。1.3.0 main 中的调用链如下：

| 步骤 | 位置 |
| --- | --- |
| `NetworkManager.d__28$$MoveNext` 订阅 `NetworkManager$$OnUpdate` | `Sequencer$$SubscribeUpdate` 调用 [0x0202da38] |
| `SubscribeUpdate` 将回调插入 `Sequencer._orderableList`（静态 +0x8） | [0x01a8fed0] |
| `Sequencer$$Update`，一个 Unity `Update`，使用 `Time.deltaTime` 对列表中每个回调各调用一次，之后才检查其 `isSuspendUpdate`（静态 +0xC8） | [0x01a906d8]..[0x01a9071c] |
| `NetworkManager$$OnUpdate` 调用 `SessionConnector$$OnUpdate`，条件是 `[[this+0x30]+0x60]` 已设置 | [0x02253190] |
| `SessionConnector$$OnUpdate` 调用 `INL1.IlcaNetSession$$Update` 一次 | [0x02030a38] |

`Sequencer$$Awake` 将 `Application.targetFrameRate` 设为 30 [0x01a8ed68]。1.3.0 的 `globalgamemanagers` (`Ultra`，Unity 2019.4.27f1）中唯一的画质级别将 `vSyncCount` 设为 2；在 60 Hz 输出下，这也对应每秒 30 帧，并使 Unity 忽略 `targetFrameRate`；没有托管代码设置 `vSyncCount` 或画质级别。`TimeManager` 保存 1/30 s 的固定时间步长。唯一另一个调用 `NetworkManager$$OnUpdate` 的方法是 `SoftwareKeyboard$$Open` [0x01c980c8]。

未经认证的 Pia 数据会被静默丢弃，不报错，也不会失去席位。

## 线路上的内容

在某个站点确认之前，作为主机端的主机会每 100 ms 向 `169.254.x.255:12345` 广播其会话更新，目标为 `dst_var = 0`；捕获中的每个数据报均为 176 字节：

```
32ab9864 89 00000000 11bac90d 0000 00 f5a83bd383ce712d 59baa5cbc320cb56 <144 bytes>
magic    v  dst=0    src      pid  f  nonce (a counter) tag              ciphertext
```

版本字节 `0x89` 表示已加密，版本为 9：对应 Pia 5.27-5.45；可靠协议的版本 3 将范围缩小到 5.31-5.43。头部、消息帧封装和传输协议见 [Pia 层](pia.md). `pokeldn/ldn/pia5.py` 对 674 个捕获数据包进行解码再编码，结果逐字节一致。

## 密钥层级

```
cryptoKeyDataSeed  9918bd0fdcfa65779918bd0fdcfa6577    from global-metadata.dat
game key           9900bd0cdcfa65639918bd0fc7fa6577    = seed derived with version 199
session param      0x36dee059                          advertisement +0x0c, little-endian
session key        7b182cb087eeabd228a2efd91a8be147    = AES-ECB(game key) over 16 SEAD bytes
network id         b4c85cf8                            advertisement +0x00, little-endian
source MAC         48:f1:eb:20:9b:22
crc32(netid||MAC)  0xda291352
IV (first packet)  da29130df5a83bd383ce712d
```

参考捕获中的全部 674 个数据包都通过认证；重新加密每个明文，都能逐字节复现主机的密文和认证标签。

### 种子所在位置

`INL1.IlcaNetSessionSetting` 的构造函数设置默认值：

```
IlcaNetSessionSetting..ctor
  byte[16] cryptoKeyDataSeed  <- RuntimeHelpers.InitializeArray(array, fieldHandle)
  string   wirelessCryptoKey  <- the "WirelessStrongCryptoKey2021" literal
  ulong    localCommunicationId = 0x0100000011d90000
```

字段句柄解析为 `.33F804682DF9E210AABDC4D939CBCD380EC7517F`，即这十六个字节的 SHA-1。该数据块位于 `global-metadata.dat` 的字段默认值区段中，既不在可执行文件中，也不在 RomFS 中；具体方法见 [逆向分析 Switch 游戏](switch_re.md).

### 公开的密钥由种子派生

```
seed (metadata)   9918bd0f dcfa6577 9918bd0f dcfa6577
published key     9900bd0c dcfa6563 9918bd0f c7fa6577
                    ^^   ^^         ^^         ^^        bytes 1, 3, 7, 12
```

游戏根据本地通信版本覆盖字节 1、3、7 和 12，1.3.0 对应 199（广播通告的 `app_version`); `ldn_game_key(seed, 199)` 复现了公开的密钥。

### 会话密钥

来自 `nn::pia::local::LocalProtocol`:

```
seed  = a u32 session value held at LocalProtocol+0x5b0
state = for i in 1..4:  prev = ((prev ^ (prev >> 30)) * 0x6C078965 + i)
rnd   = four consecutive xorshift128 draws (shifts 11, 8, 19) -> 16 bytes, little-endian
key   = AES-128-ECB(game key at LocalProtocol+0x5bc).encrypt(rnd)
```

生成器是 SEAD 的随机数生成器；`pokeldn/ldn/sead.py` 实现了它。

### GCM nonce

IV 由流对象构造，每种网络地址族一个对象：

```
nn::pia::local::LdnOutputStream::vfunc3     0x16b39c4      the LDN sender
nn::pia::local::LocalOutputStream::vfunc3   0x16bca80
nn::pia::lan::LanOutputStream::vfunc3       0x16a0f80
nn::pia::nex::NexOutputStream::vfunc3       0x16eca0c
```

每个都接受 `(this, buf, buflen, packet)`；发送方在 `PacketWriter+0x948` 调用，接收方在 `PacketReader+0xc8`.

```
IV[0..3]  = u32be( crc32(ten bytes) )
IV[3]     = overwritten with (packet.source_variable_id & 0xFF)
IV[4..11] = the eight-byte header nonce, copied from packet+0x1b
```

位于 `0x1719204` 的 CRC 是普通 CRC32（`0xEDB88320`），计算输入为网络 id（小端序，从广播通告 +0x00 经网络对象的 +0x450 取得）和站点记录中的源 MAC。源 MAC 无法从正在解密的数据包中恢复。

## 解码 Local Protocol

参考捕获中的每个数据包都携带相同消息：

```
presence 0x7f  flags 0x11  size 121  protocol 36  port 0  destination 0
```

它是 Local Protocol 的 `0x11` 会话更新，每 100 ms 重播一次，直到所有站点都确认：

```
local message header  version 1, type 0x11, size 73
sequence id           4
network id            8b4a3b22        random, not the advertisement's network id
host variable id      11bac90d        the same value as the packet header's source variable id
host constant id      0000 48f1 2022 9beb
allow participating   1
node 0                169.254.54.1:12345          the console
node 1                169.254.54.2:12345   01     the client
nodes 2-7             empty, marked 0xff
host migration state  0
```

八个九字节节点槽位，对应房间的八个席位，之后还有一个字节。将主机端 constant id 按小端序读取，再按 LDN 规则（`mac[2] << 56 | mac[4] << 48 | mac[5] << 40 | mac[3] << 32 | mac[1] << 24 | mac[0] << 16`）解包，便得到扫描到的 MAC `48:f1:eb:20:9b:22`。Pia 消息头部是大端序，Local Protocol 字段是小端序，而其中的本地地址又是大端序。存在标记字节 0x7F 设置了三个位，在 Pia 5.27-6.30 中没有字段与其对应。

### 确认消息

20 字节的 ack 见 [Pia 层](pia.md#the-local-protocol-0x24)。可行的帧封装与主机端自身相同：广播，数据包的 `dst_var` 为 0，消息目标为 0；单播帧封装尚未测试。第一个 ack 会使更新停止：捕获中有 42 次更新，间隔为 100 ms，ack 在最后一次更新后 34 ms 到达。随后只要站点不再发送任何内容，主机也不再发送。

## 加入网状网络

三次握手与 ack 规则见 [Pia 层](pia.md#joining-a-mesh)。BDSP 的地址如下：

| 功能 | 位置 |
| --- | --- |
| 站点协议接收分派器 | `0x0154e848`，表 `0x3e6b38f` |
| 连接请求反序列化器 | `0x0154ebd0` |
| 内部错误到结果的映射 | `0x0154f5e8` |
| 按 id 查询协议版本 | `0x0159b850`，未注册的 id 返回 0 |
| 读取网状网络消息的 ack id | `0x01542db8` (`size - 4`，大端序） |
| 发送 ack（8 字节，通过 0x14） | `0x01550324`, `mov w3, #8` |
| 加入 REQUEST 处理器，主机端侧 | `0x0154b790`, `0x0154b868` |
| 加入 RESPONSE 处理器 | `0x0154b984`, `0x0154b9a4` |

`0x01550324` 属于位于 `session + 0xa0` 的 MeshStationProtocol。加入响应处理器是 `JoinMeshJob` 在 `MeshProtocol + 0x128` (`0x0154e5c4`）处保存的指针，保存发生在发送加入请求之后。

主机注册了九种协议（[实测值](#measurement-methods)):

```
0x14 Station v2   0x18 Mesh v3      0x1c SyncClock v0
0x24 Local v0     0x58 RTT v3       0x68 Unreliable v1
0x7c Reliable v3  0x94 Session v1   0xa4 MonitoringData v0
```

版本为 0 的四种协议，在版本探测中无法与未注册协议区分。

包含两个站点的网状网络，其加入响应如下：

```
stations 2, host index 0, joiner index 1, max_active 8, update counter 0
station 0   the console
station 1   the client: its own station location and ids, read back
```

不到一秒，主机就开始发送 RTT（0x58）和可靠（0x7c）流量。结果 7 表示 variable id 已经属于其某个站点。

### Session Protocol（0x94）

`nn::pia::session::SessionProtocol` (1.3.0 `main`，虚表 `0x4b5da50`）承载联合会话功能，在 LDN 上不工作。Pia 会话启动时会构造它 [`0x157c66c`]，除非某个设置字节（GOT `0x4c4b850` 后的 +0x38）已设置；将其保存在 session+0xC8，并为每个其它站点分配一个 `transport::ReliableSlidingWindow` [`0x1581938`]。其分派器 [`0x15820b8`，跳转表 `0x3e6b986`] 的所有处理器在联合会话任务（session+0x70）为空时都会返回，而在 LDN 上它总是为空：`LdnNetworkFactory` 的槽位 61 [`0x16b30ac`] 返回空值，其它唯一的写入也都是空值（`0x157c618`, `0x157d0e8`）。Lan 和 Nex 工厂构造 `LanMatchJointSessionJob` 和 `NexMatchJointSessionJob`.

其窗口使用游戏流的 `ReliableSlidingWindow` [构造函数 `0x159dab4`]，具有双槽环形缓冲区，协议为 0x94，端口为 1（`0x159de54(window, 2, 2, 0x94000001)`）；接收位于槽位 10 [`0x1581c98`]。窗口之前没有任何逻辑读取 session+0x70，因此有效的可靠 0x94 消息（第一条带有标志 `is initialized`，序列号小于基准值加二）会先得到确认，再由处理器丢弃。尚未捕获或发送过 0x94。

## 作为主机端

主机进入联盟交谊厅时，会优先加入任何有空席位的房间，然后才自行创建房间（`matchingMode` `IlcaNetSessionInitMode.Random`, `localRandomMatchmakeHostWaitTime` 25, `localRandomMatchmakeTimeUp` 270). `bin/bdsp_host.py` 可以创建房间，进入联盟交谊厅的主机会加入它；`pokeldn/bdsp/host.py` 保存主机端侧的实现。零售版本房间的广播通告如下：

```
LDN protocol         1 (AES-CTR advertisement)
frame version        4
security mode        1
scene_id             4352 (0x1100)
app_version          199
accept policy        ALL, 1/8
application_data     17 bytes, the Pia header with a fresh network id and session
                     parameter, then one zero byte
```

主机端发送的内容，每项都根据零售版主机端的数据逐字节重建（`tests/test_bdsp_host.py`):

| 步骤 | 消息 | 帧封装 |
| --- | --- | --- |
| 站点建立关联 | Local Protocol 会话更新，每 100 ms 发送一次直到确认，加入方作为节点 1，排名为 1 | 广播，`dst_var` 0 |
| 其连接请求 | 接受连接的响应，949 字节：采用请求布局，类型为 2，包含主机端的九种协议、其站点位置、广播通告中的网络 id、一个填零的 PlayerInfo，最后为 ack id | `dst_var` 0，标志 0x01 |
| 其网状网络加入请求 | 针对请求的 ack id 发送站点 ack，随后发送加入响应（两个站点，`max_active` 8，加入方条目内使用其自身的位置字节） | `dst_var` 0 |
| 加入响应得到确认 | `NetJoinData` 通过可靠窗口发送，序列号 1，标志 0x0F | `dst_var` 加入方的 |
| 此后 | 每秒一次网状网络更新（556 字节）、RTT 请求、`NetCharacterStateData{0, 0}` 通过 0x68 发送 | `dst_var` 1，目标 0xFFFFFFFF |

主机端的站点位置不含公网地址，NAT 字段均为零，共 36 字节；加入方两者都有，共 40 字节。主机端站点条目的索引和加入顺序为 0，加入方为 1。

加入响应得到确认后，加入方约每秒发送一次 Sync Clock（0x1C）请求；主机端用请求中的 tick 和以毫秒为单位的网状网络时钟回答。若 Sync Clock 请求未获回答，加入方会反复解除认证并重新关联，屏幕显示“正在通信”。实测离开发生在首次请求约十秒后；尚未读取超时值。得到回答后，它发送 `NetJoinData`，并请求 0x04 和 0x23，与零售版主机端相同；从此房间流程是对称的：搭话、问候以及 [交换](bdsp_trade.md) 在主机作为加入方时也完全相同。

## 离开

主机离开房间时，作为加入方会执行 Pia 的网状网络离开流程，作为主机端则执行主机端迁移离开流程。两者都从网状网络协议的可靠窗口开始，即 0x18 端口 1，可靠头部的序列号为 1，且都等待通过端口 0 以不可靠方式发送的回答。零售版本 Pia 对每种回答都发送两次，第二次使用独立数据包。网状网络分派器是 `0x0154ac94`（跳转表 `0x3e6b25a`，类型 0x40 至 0x4A 位于 `0x3e6b35c`).

| 主机角色 | 发送内容 | 所需回答 | 结束等待的处理器 |
| --- | --- | --- | --- |
| 加入方，`LeaveMeshJob` | `04 `，离开请求 | `08 `，来自主机端 | `0x0154baf8`，清除 job+0x7c |
| 加入方，随后 | 站点断开请求，`03` 通过 0x14 | `04` |  |
| 主机端，`LeaveWithHostMigrationJob` | `44 `，向每个站点各发一条 | `48 `，来自每个站点 | `0x0154b068`，清除 job+0x6e[index] |

主机端的离开请求处理器 `0x0154b9e0` 拒绝大小不为 2、索引为 0xFD 或自身索引的请求，通过 `0x0154c860` (`08` 和主机端自身的站点索引）回答，然后移除该站点。`LeaveMeshJob::WaitLeaveResponse` `0x0155fd2c` 在响应清除其标志或截止时间到达时继续执行。`LeaveWithHostMigrationJob::WaitMigrationResponse` `0x015607bc` 只要任一在场站点的标志仍被设置，就会等待；离开的站点会清除自身标志。

不回答任何内容时的实测结果：

| 主机角色 | 首条消息 | 随后 | 离开时刻 |
| --- | --- | --- | --- |
| 加入方离开主机端创建的房间（4 次捕获） | 每 0.125 s 发送离开请求，持续 4.9 至 5.0 s | 从 3.6 s 开始，每 0.5 s 发送断开请求（有一次捕获记录至结束） | 该次捕获中，在首次请求后 9.0 s 解除认证 |
| 主机端离开有一个站点加入的自身房间（4 次捕获） | 每 0.125 s 发送迁移开始消息，持续 4.9 s | 会话更新，序列号 +1、迁移状态 1，每 0.11 s 一次，持续 10 s；随后每 0.3 s 发送 Local Protocol 0x13（开始主机端迁移），持续 10 s | 首次迁移开始消息发出后 25.3 s，网络关闭 |

得到回答时（`08 00` 两次，以及 `04`），离开的零售版加入方在离开请求后 0.06 s 发送一条断开请求，并在离开请求后 0.15 s 解除认证。得到回答时（`48 01`、会话更新 ack、在 0x13 时离开），离开自身房间的零售版主机端分别在迁移开始后 0.11 和 0.45 s 发送 0x13（2 次运行），并关闭房间。

0x13 阶段是 `LocalDestroyNetworkJob::WaitUntilAllClientsDisconnection` `0x016b95b8`。自上次发送经过 301 ms 后，它就再次发送 0x13（`job+0x68`），并在以下任一条件最先发生时结束：请求的取消字节被设置（设置为 `WaitForCancel` `0x016b9330`）；从 `0x016b014c` 取得的在场站点数等于 1（`0x016b9614`）；自上一个状态起经过超过 10000 ms，`WaitUntilAllClientsReceiveUpdateSessionMessage` `0x016b936c`，保存于 `job+0x70` (`0x016b9644`）。后两种情况进入 `StartDestroyNetwork` `0x016b950c`，由它关闭网络。站点离开会使该阶段在下一次更新时结束；站点留下则会使其维持完整的 10 s。前一状态在 `[[protocol+0x4f0]+0x5c]` 被设置时（`0x016b0888`）或经过 10001 ms 后退出。

`pokeldn.bdsp.session.answer_departure` 构造两种回答；`bin/bdsp_host.py` 回答离开的加入方及其断开请求，而 `bin/bdsp_connect.py` 回答迁移开始消息，确认之后的每条会话更新，并在 0x13 时离开网络（`--no-leave-on-host-migration` 则留下）。

离开交换盒子不发送离开消息：盒子的关闭回调 `TradeSelectPokeModel$$CheckComplete` [1.3.0 main 0x1c26810] 发送 `NetDataCurrentFlowCancelData{0}`（0x25，`SendCancel` 0x1c26bf0），而 `UnionTradeManager$$Cancel` [0x1c33780] 发送 `NetCharacterStateData{0}`，两者位于同一数据包中，不等待伙伴。

## 测量方法

-
-
