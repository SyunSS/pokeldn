---
title: 消息、内容与路由
parent: Sword and Shield
nav_order: 2
---

# 消息、内容与路由

位于 Pia 之上的发布／订阅框架。一条消息由小端序 u16 id、一个鉴别字节、一个零字节以及 protobuf 消息体组成。

## 消息 id 的来源

低位 id 来自位于 `0x01BBFFA0`, `{u64 handler slot, u32 0x402, u32 id, u64 0}` 的表，表中有 838 条 24 字节记录，id 为 1..880（包括 97〔ping 持有器〕、110、120、130）。高位 id 为基值加偏移；20030 或 40040 从不以常量出现，60000 是基值 + 0（41 处 MOVZ）。

## 内容与持有器

每个内容注册三个持有器（注册器 `0x010ccd90` 对应内容 30，`0x010da7d0` 40, `0x010d5150` 对应 50），将基值加到其偏移 `ldrh [content+0x372]` 上，并将各个结果传给 `0x006daeb0(manager, &holder, flag)`:

```
mov w9, #0x2710    id = 10000 + offset   holder 0x010dd910   flag 1
mov w9, #0x4e20    id = 20000 + offset   holder 0x010d85f0   flag 0
mov w9, #0x7530    id = 30000 + offset   holder 0x010d0980   flag 0
```

40000 系列在更低一层生成，其中 40000 使用 MOVN 指令：

```
ldrb w20, [x0, #0x28]          the content offset, 30 / 40 / 50
mov  w9, #-0x63c0              w9 = 0xffff9c40
add  w24, w20, w9
strh w24, [x20, #0x160]        40030 / 40040 / 40050
```

没有监听器的持有器会静默丢弃消息（`0x010d81d0`: `ldr x8,[x0,#0x168]; cbz x8, out`）。安装位置：内容 30 `0x010ccc94`, `0x010ccca4`, `0x010ccf7c`；内容 40 `0x010da6d0`, `0x010da9bc`（清除位置 `0x010dab10`）；内容 50 `0x010d50ac`, `0x010d533c`（清除位置 `0x010d5660`）。这些操作均不会触及内容 40 或 50 的基值 20000 持有器：20040 和 20050 不起作用。

### 30000 持有器

30000+offset 持有器（`0x010d0980`，虚表 GOT `0x02618620` = `0x02528100`，无 RTTI）携带 `gflnet.p2p.framework.pb.SequenceDataHolder`:

```
SequenceDataHolder    oneof message {
                        1 CancelAccepted        cancelAccepted
                        2 RequestCancel         requestCancel
                        3 RequestCancelAll      requestCancelAll
                        4 RequestForcedProceed  requestForcedProceed }
CancelAccepted        { 1 int32 currentSeqNo; 2 bool  isForced    }
RequestCancel         { 1 int32 currentSeqNo }
RequestCancelAll      { 1 int32 currentSeqNo }
RequestForcedProceed  { 1 int32 currentSeqNo; 2 int32 targetSeqNo }
```

解析器 `0x006a7580`（标签 `0x0a`..`0x22`）；RequestForcedProceed 的 `0x006a65c0` 将其字段存放在 `+0x14`, `+0x18`。接收函数位于槽位 8，即 `0x008b9590`，它调用 `[holder+0x168]` 的监听器槽位 (case - 1)，经由 `0x0204c430`.

《盾》1.3.2 只构建 CancelAccepted：在 protobuf 代码（`0x006a3000..0x006a8400`）之外，没有任何代码调用其他构造函数（`0x006a4b50`, `0x006a5730`, `0x006a6330`）或其访问器。`0x006a3db0` 有 21 个外部调用方：发送包装函数 `0x008b7420`，以及十个同步内容中各自的两个回复任务（`0x008b71a0`, `0x008b7700`, `0x008cfb10`, `0x008cfbe0`, `0x00c06420`, `0x00c064f0`, `0x010763a0`, `0x01076470`, `0x010a2090`, `0x010a2160`, `0x010cf460`, `0x010cf530`, `0x010d7760`, `0x010d7830`, `0x010dd0c0`, `0x010dd190`, `0x012a8390`, `0x012a8460`, `0x012bec80`, `0x012bed50`）。零售版交换从不携带分支 2 至 4；不过主机仍会对它们作出响应（[内容 40](swsh_trade.md#the-cancel-and-proceed-messages)）。内容 40 的实例为 30040，端口 0：

```
RequestForcedProceed{c, c+1}   58750000 2204 08<c> 10<c+1>     c=0: 58750000 2204 0800 1001
```

### 三个交换内容

`0x010c9280` 构建会话：

```
+0x120   content 30, the box exchange       ctor 0x010cca10, registers offset 30 at 0x010ce4f0
+0x148   content 40, SyncSaveDataHolder     ctor 0x010da3f0
+0x2b0   content 50, PokemonTradeDataHolder ctor 0x010d4d40
+0x60    an event source, listeners in a vector at its own +0x60
+0x68    own Pokemon        +0x70  theirs
+0x90    a delegate to +0xb0: thunk 0x010cc250 -> box callback 0x010ca800(session, code, payload)
+0x140   the trade state, 1..10            +0x144  the error code
+0x418   send command 3 on the first frame  +0x419  the role bit that suppresses it
```

内容的初始化会注册其持有器，并生成其 40000 id：内容 50 在交换状态 1（`0x010d4d90`），内容 40 在状态 6（`0x010da470`），位于数据交换（状态 3）和状态 4 的决策之后，决策为 `0x01109320`.

## 路由路径

```
0x006a9a20   the sync pump, from the trade session update
0x006db3b0   the poll: per registered entry, drain both streams of its kind (byte +8)
0x006a8490   stream A: mesh port [pia+0xd0+kind*4], Pia protocol 0x7C
0x006a84f0   stream B: mesh port [pia+0xd8+kind*4], Pia protocol 0x80
0x006db9c0   drain: slot 0x78 fills (sender*, length) and the buffer at manager+0xf0
0x006db620   dispatch: match the entry, call the holder's slot 8
0x010d81d0   content 50's 10000-base holder: parse, call the listener's slot 0
0x010d5e40   the listener: sender to station index, memcpy 0x158, invoke
```

### 应用头部

负载为 `struct.pack("\<HBB", id, discriminator, 0)`，随后是消息体，在 `manager+0x240f0` 处由 `0x006db840` (`strh w3` 构建，鉴别值来自 `manager+0x480f0`, `strb wzr`），并由 `0x006db620` 解析。鉴别值是一个世代计数器，`[content+0x370] = (+1) mod 255` (`0x008b6670`），被写入 `[manager+0x480f0]`；强制的 CancelAccepted 会使内容 40 的计数器递增（`0x006db470`, `0x010dcea4..0x010dcec8`）；注册器将其清零（`0x010d53a0`）。在一次未强制 CancelAccepted 的交换中，107 个负载全部携带零值。

### 实时读取注册信息

```
manager = read_u64(read_u64(main + 0x02616750))     0x006a9a70, the poll's caller
count   = read_u64(manager + 0xD8)                  0x006db3dc
array   = read_u64(manager + 0xD0)                  0x006db3e0
entry i = array + i * 0x10                          0x006db3e4
id      = holder's vtable slot 7, called at 0x006db740 (`ldr x8, [x8, #0x38]`)
```

槽位 7 在此返回 `[holder+0x160]`；在其他位置则解码其 `ldrh`。空闲界面中为空；连接交换入座后会增加两个条目（入座后两秒内观察到）；神秘礼物不增加任何条目。

### 分派条件、端口与发送者

一个条目为 16 字节：持有器、位于 +8 的种类（`w2`）、位于 +9 的标志（`w3`，仅 10000+offset 时为 1）：

```
id == holder->slot7()
entry[8] == the drain's kind
entry[9] ? header[2] == [manager+0x480f0] : no check
```

种类就是网状网络端口：内容持有器（20030、10050、ping）为 0，40000 系列为 1（`0x006daf40(manager, &holder, 1, 0)`）。发送者是传输对象指针（`[sp+0x28]`，位于 `0x006db9c0`），向下传给 `0x010d5e40`，再由 `0x006b5850` (`mesh->GetStationIndex` 解析，失败时为 0xfd）；回环传入 `[[0x2616a30]]+0xf0`. `Data.ownerId` 不参与 10050 的处理。

## 消息 `Data` 的封装

`gflnet.p2p.sync.pb`, `data.proto`:

```
1  uint32  syncId        the content offset       30 / 40 / 50
2  uint32  elementId     the base                 10000 / 20000
3  uint64  ownerId       the sender
4  uint64  clock
5  bytes   body          four bytes in a pair; a 344-byte PK8 in a 40050
```

40000 持有器的监听器是 `element+0x18`；其槽位 0，即 `0x006d59f0`，按如下方式路由：

```
[Data+0x14] == [listener+0x10]        syncId, the element's offset
walk [listener+0x28] .. [+0x30]       sub-elements, 0x90 bytes each
  [Data+0x18] == [sub+0x62]           elementId, u16
  [Data+0x20] == [sub+0x68]           ownerId, u64
sub->vtable at 0x48 (sub, body, len, [Data+0x28])     body and clock
otherwise: ret                        dropped silently
```

### 子元素种类

| 种类 | 构造函数 | 虚表 | `+0x88` 创建时的值 | 槽位 9，接收：检查大小，存到 `+0x88` |
| --- | --- | --- | --- | --- |
| 32 位 | `0x006d5c00` | `0x2512bc8` | 0 (`0x006d5ce0`) | `0x006d5f20`: 4, `ldr w8` / `str w8` |
| 配对（阶段） | `0x006d6160` | `0x2512c90` | `0xfc18fc18` (`0x006d6230`) | `0x006d6490`: 4, `ldr w8` / `str w8` |
| 16 位 | `0x006d66d0` | `0x2512d58` | 0 (`0x006d67b0`) | `0x006d69f0`: 2, `ldrh w8` / `strh w8` |

随后，接收操作设置 `[sub+0x78] = clock` 和 `strh 0x0100 -> [sub+0x60]`（就绪字节 `+0x61`）；槽位 7，即参与哈希的值，返回时钟。子元素为 0x90 字节；其构造函数接收元素 `x0` (`+0x80`）、elementId `w1` (`+0x62`）、ownerId `x2` (`+0x68`）、标志 `w3` (`+0x70`），通过以下位置返回：`x8`.

同步元素（`0x006d3f80`）在每个同步内容中构建一次：`0x008b5c60`, `0x008cecb0`, `0x00c05690`, `0x01075610`, `0x010a1230`, `0x010ce604` (30), `0x010d6904` (50), `0x010dc264` (40), `0x012a7530`, `0x012bdef0`。虚表来源为 `0x2512b28`:

```
element+0x00  0x2512b38   primary, 6 slots; 2, 3, 4 are the three constructors with w3 = 1
element+0x08  0x2512b78   interface A: the 32-bit kind (thunk 0x006d5ab0)
element+0x10  0x2512b90   interface B: the pair (0x006d5ac0), the 16-bit kind (0x006d5ad0)
element+0x18  0x2512bb0   the router listener, slot 0 = 0x006d59f0
```

生成函数 `0x006d44e0` 构建四个通道，并加入以下集合中的每个站点：`[element+0x70..+0x78]`:

| 字段 | 构建方 | 大小 | 保存内容 |
| --- | --- | --- | --- |
| `+0xb0` | `0x006cd890` | 0x130 |  |
| `+0xd0` | `0x006d9ca0`，A | 0x38 | 每个站点一个 32 位子元素，elementId 10000（`0x006d9d90`）：全员就绪哈希 |
| `+0xf0` | `0x006d29b0`，B | 0x40 | 位于 `+0x38` 的一个 16 位子元素，elementId 20000，owner 0：[共享值](swsh_trade.md#the-phase-is-the-elements-field)；每个站点一个配对，elementId 20000（`0x006d2aa0`），位于 16 字节的 `{stationId, sub}` 条目中 |
| `+0x110` | `0x006d7980` | 0x30 | 全员就绪哈希遍历的列表 |

### 全员就绪哈希

elementId 10000 上的四个字节，由 `0x006d7b40` 在以下位置构建：`element+0xa8`:

```
h = 0
for sub in subs:
    if (!sub[+0x61]) { h = 0; break }        any station not ready -> zero
    h = crc32(le32(h + sub->slot7()))        slot 7 is the clock
```

非零表示每个站点均已就绪。`0x0065de30` 是 `zlib.crc32`（已在 unicorn 中检查）；`0x0065df04`（多项式 `0x8005`）是一个 CRC-16。所遍历的列表 `element+0x110` 是 `0x006d48b0` 对 `+0x40` 的副本，仅保留 `+0x68` 为零的条目；交换时该列表的长度尚未读明。

此链涵盖发送者的 elementId 0 和 1（无 owner），然后是它自身的 elementId 20000。作为主机端的《剑》所发送的每个非零哈希都吻合，例如内容 50：

```
elementId 0, no owner      clock 2304   the host's own Pokemon (344 bytes)
elementId 1, no owner      clock 2313   the partner's Pokemon, sent back
elementId 20000, host      clock 2278   then 2338 after its pair moved
crc32 chain                8ffa0f2e     then b3615e90
```

消息发送前，时钟可能已经变化。回传主机端哈希的加入端可以与作为主机端的《剑》完成交换。

## 协议 0x84 上的同行队伍负载

`ReliableBroadcastProtocol` 以三个分片携带 3456 字节交换快照，持续发送直到收到确认；第三片使用 zlib（Pia 标志 0x10）：原始大小为 1404 + 1404 + 157，最后一片解压为 648 字节。`trade_payload.py` 会拒绝任何其他总长度。布局（与以下位置相同：`kwsch/PokePiaSWSH`, `lincoln-lm/swsh-lan-client`):

```
0x000  six PK8 records, party form, 0x158 each          -> 0x810
0x810  u32   party count
0x814  MyStatus, 272 bytes      TID/SID at 0xA0, trainer name at 0xB0
0x924  TrainerCard, 456 bytes   trainer name at 0x00, save start date at 0x170
0xAEC  the player profile, 266 bytes                     -> 0xBF6
0xBF6  392 bytes, the Battle Stadium block; zero for Link Trade
0xD7E  2 bytes of padding                                -> 0xD80 = 3456
```

MyStatus 和 TrainerCard 是 PKHeX 存档块（`Saves/Substructures/Gen8/SWSH/`).

构建器 `0x0110c180`: `0x00784f90`（同行队伍）、`0x01424f10`（MyStatus）、一次 0x1C8 的 memcpy（训练家卡片）、`0x01124fa0`（个人资料），以及对可选块执行的 0x188 字节 memcpy 或 memset。在 `0x010fcff0` 的调用方中，连接交换（`0x010967f0`）和密语匹配（`0x00bd80f4`, `ChikaMatchingStateSession`）不传入块；对战竞技场（`0x00b2d7d0`, `StateBtlSpot*Battle`，休闲、级别、竞赛）则传入一个块。接收端 `0x0110cff0` 为每个站点复制这两个区域。

### 对战竞技场块

0x180 字节数据，加上一个 u64 长度。生成方 `0x00b2eb60` 填充一个可选值（标志 `+0`，数据 `+8`）；快照从其持有器的 `+0x60` (`0x0110c378`）处复制 0x188 字节；读取方 `0x00b2d9fc` 要求长度为 0x118。从 0xBF6 开始：

```
0x000  u32    CRC-16 (0x8005) of the 0x22fc-byte regulation core   0x008ff9e0:
              0x0065dd70([reg+0x180]+0x60, 0x22fc); regulation_preset_core_%d.bin (0x008feb34)
0x004  0x100  the team's signature: +0x36 of the 0x136-byte team descriptor at match+0x98
              (0x00b2ef24)
0x104  4      zero
0x108  u64    the manager's optional (value +0x1ab8, flag +0x1ab0, 0x00adc8d0), zero unless
              match type 3                                         0x00b2f100
0x110  u8     the manager's byte +0x191c (0x00adbbe0) when 0x00adb920 yields an object and
              0x00b1ce10(0) == 2                                   0x00b2efc4
0x111  u32, u16, u8   team descriptor +0, +4, +6
0x118  0x68   zero
0x180  u64    length, 0x118
```

接收端 `0x00b2e590` 将伙伴的 CRC 与自身的比较（`0x00b2e760`）；结合 `0x008fc470`，两个条件均成立时结果为 9，否则为 10（`cinc` `0x00b2e778`). `0x010719f0`, `0x01071a98`, `0x01071c00` 将其与以下位置 0x640 字节的 CRC 比较：`+0x188` (`0x008ffa10`）。描述符在 18 处被整体复制，其中四处位于 `StateDownloadTeamMenu` (`0x013e660c` 至 `0x013e7c58`).

match+0x70 是一个可选值（标志 `+0x70`，其值来自 `+0x78`：一个 u64 键、一个指针、一个 u64、一个指针，然后是位于 `+0x98` 的描述符）。它唯一的写入方为 `0x00ad9cf0`（memcpy 位于 `0x00adeaf0`）：对战竞技场匹配更新函数 `0x00ad5750` 在 `0x00ad6a2c` 处使用 `[state+0xb8]+0x20` 填充它，而 `0x00ad6a68` 和 `0x00b1ea88` 将其清除。该请求对象由队伍下载任务（`0x014f7fd0`..`0x014f809c`，完成标志 `+0x18`）从其位于 `[job+0x88]` 的结果持有器中填充：描述符 `+0x00..+0x2f`，六个 u64 来自 `+0x38`, `+0x30..+0x35`，六个字节来自 `+0x68`, `+0x36..+0x135`，来自 `+0x6e`，随后被 `v1/validate` 签名覆盖（`0x014f8094`）。持有器完整获取队伍列表中键与列表所选键匹配的 0x158 字节条目（`0x01503f10`，复制位置为 `0x014fa804`）。列表 `0x0150320c` 保存两类条目：

| 键 | 条目 |
| --- | --- |
| (1, team) | 存档对战队伍：六个 u64 `box \| slot << 32`，每个成员一个，来自 `save+0x525 + team*12 + i*2` (`0x0140a5c0`, `0x0140a5f0`）；名称位于 `save+0x4a0 + team*0x16` |
| (2, i) | 已存储的记录：由 `0x01430670` 加载的 0x87f 字节记录中的字节 0x26..0x15b |

签名采用 RSA-2048、PKCS#1 v1.5、SHA-256，由 `0x011aedf0(team, v, sig)` 检查（调用方 `0x00b2f19c`, `0x00b2f1e0`, `0x00b2f2e0`, `0x0109eb68`），它也是 `nn::crypto::detail::BigNum::ModExp` 的唯一调用方（PLT `0x018fff50`，GOT `0x0260fb38`):

```
0x011aee90  count 0x148-byte stored PK8s        bl 0x7664c0, add w26,#0x148
0x011aeeac  v as BE u16, then 00 01             rev w8,w22; lsr #16; strh 0x100
0x011aef98  Sha256Impl::Initialize
0x011aefa8  BigNum::Set(modulus, .., 0x100), Set(exponent, ..)
0x011aeffc  Sha256Impl::Update(message)
0x011af01c  BigNum::ModExp(out, sig, exponent, 0x100, ..)
0x011af06c  cmp x8,#0xca: the 00 01 FF..FF 00 padding
0x011af090  memcmp(.., Sha256Generator::Asn1ObjectIdentifier, 0x13)
0x011af128  Sha256Impl::GetHash, memcmp(.., 0x20)
```

主机只持有公钥；映像携带 `https://v3-lp1.vp.n.srv.nintendo.net/v1/public_key` (`0x01bd7d41`）和 `.../v1/validate` (`0x01c11a93`），因此推测由任天堂服务器签名。连接交换从不到达此检查。

`v1/validate` (`0x011a2a70`）发送一个以 NUL 结尾的字符串（`v1/public_key` 的整个消息体）、大端序 u16 的密钥版本（密钥持有器 `+0x68`，由 `v1/public_key` 从回复中设置，设置方为 `0x0144fb90`）、以大端序 u16 表示的主机版本 `0x007d4270() = 0x2D`（《盾》）、`00 01`、大端序数量以及 0x148 字节记录（`0x007664c0`）。被签名的消息保存相同的记录、版本和 `00 01`；其中 `v` 是伙伴的 MyStatus 字节 `0xA4` (`obj+0x104`, `0x01424bf0`，默认 `0x2D`，位置为 `0x014245f0`，PKHeX `MyStatus8.Game`）。回复解析器 `0x011a2870`：字节 0 为状态（2：密钥过期，重新获取；`R+0x70` = status == 1），字节 5-6 为大端序数量 n，最大限制为 6，n 个大端序 u32 写入 `R+0x74`，状态为 0 时将 0x100 字节写入 `R+0x8c` (`0x011a29e4`）。五个调用方中仅 `0x014f8c00` 保留它们（存到 `obj+0x183`); `0x014f808c` 将它们写入 `+0x36`，所在区域是一个描述符形状、长 0x136 字节的连续区域。

匹配类型由虚表的槽位 8（`+0x40`）提供，虚表为 `0x2538238`, `0x2538358`, `0x2538478`：1 为休闲（`0x00adda60`），2 为级别（`0x00adde60`），3 为互联网大赛（`0x00ade340`). `0x00adcfb0(obj, mode)` 构建它们，只能经由 `0x00b1cdd0` 从 `StateBtlSpotTop` (`0x00b23080` 中的六个位置到达），随后转入 `StateBtlSpotCasualMatchEntrance`, `StateBtlSpotRankMatchEntrance` 或 `StateBtlSpotCompTop`. `+0x108` 由 `0x00adc8b0` (`str x1,[x0,#0x1ab8]` 写入，标志 `+0x1ab0 = 1`），数据来自 `0x00b41b7c`，位于 `StateBtlSpotCompTop`，并附带存档块 `0x88F6D6AE` 中 0x33C0 处的 u64（0x33D0 字节，键位于 `0x02072fac`，由 `0x01444ac0` 读取；前一个键 `0xEEE5A3F8` 是 PKHeX 的 `KOfficialCompetition`).

### 玩家个人资料

位于 0xAEC 的 266 字节，也是信标中 0x1F 处的记录（[会话](swsh_session.md#taking-a-seat)). `0x01111970` 从单例 `[0x2610958]` 复制它（+0x310 至 +0x564，互斥锁 +0x580）；`0x01125080` 要么打包所有组，要么全部不打包，因此布局固定；位打包组按最低有效位优先。`trade_payload.read_tail` 将其解码。

```
0x00  16  nn::oe::GetPseudoDeviceId
0x10  16  nn::account::GetUserId, the account Uid
0x20   8  nn::account::GetNetworkServiceAccountId, or zero
0x28  24  trainer name, UTF-16, from MyStatus+0xB0; stale bytes after the terminator
0x40  25  appearance, bit-packed:
            bit 0      MyStatus+0xA5 (gender) != 0
            bit 1      set by 0x0111cfec; 0 in every capture
            bits 2-5   MyStatus+0xA7, the language (3, French)
            bits 6-7   zero
            8 bits     MyStatus+0xCC
            17 x 10    the model 0x0111dd60 unpacks from the MyStatus bitfield at +0x00
            2, 2, 10   the last three of that unpacking
0x59  55  position samples, bit-packed:
            2, 2 bits  `a` (sample object +0x47) and `b` (+0x1c9), below
            8 bits     generation: random at ring reset (0x00eb98a8), +1 per re-seed
            8 bits     player object byte +0x136 (7 in every capture)
            3 x 17     at 0x5C, 0x6D, 0x7E, newest first: 5-bit counter (0x01123be0, +1 per
                       push); 3-bit state (+0x1c8, below); x, y, z floats; yaw in radians
                       (Euler component 1, 0x006101c0). 0x00ebf590 pushes at most once a second
                       from the field object's +0x60 (position) and +0x50 (rotation);
                       0x00b4f140 and 0x00b54450 re-push the current sample three times.
            8 bits     at 0x8F: player object byte +0x140 (1 in every capture)
0x90  37  activity, bit-packed: an 8-bit kind (below; 13 in trade), an optional 28-byte part,
          a 24-byte field, a u16 at 0xB2, a bool; only kind and u16 non-zero. The u16 is the
          location, the line of `script/place_name.dat` (0x00f27d70), PKHeX's met-location
          id (170 Challenge Beach); setter 0x0111bc60, readers 0x0111b8c8, 0x0111b8f4.
0xB5  37  two more groups (56 and 16 source bytes), zero in every capture
0xDA  32  sixteen u16 records, `0x010f5060`: Record8 indexes 6, 32, 0, 33, 17, 27, 34, 24,
          12, 3, 10, 35, 38, 7, 36, 37, each clamped to 0xFFFF (PKHeX `RecordList_8`:
          total_capture, evolution, egg_hatching, net_battle, trade, license_trade, cooking,
          campin, pretty, capture_raid, rotomu_circuit, poke_job_return, bike_dash, dress_up,
          get_rare_item, whistle)
0xFA   8  an optional u64, zero in every capture
0x102  8  zero
```

接收函数（0x00dd5e24）将位置存到 +0xB0，将偏航角以四元数形式存到 +0xA0（0x00992cd0）；0x011a68a4 仅在状态 1、2、3、6 采样。

采样状态是 `+0x1c8` 的 `[[0x261bd18]]`，仅由 `0x00ebf570` 设置，由重置函数 `0x00eb97b0` 清零（唯一调用方 `0x00dd2e00`, `0x00eb986c`）；该值为 0 时，推送操作立即返回（`0x00ebf5a8`):

| 状态 | 设置方 |
| --- | --- |
| 0 | `0x00dfd1d4`，虚表 `0x2561ec8` 槽位 9 |
| 1 | 场景玩家槽位 13（`0x00d98f28`), 30 (`0x00d9d2a8`), 76 (`0x00da0188`); `0x00d97730` 动作 0 |
| 2 | `0x00d97730` 动作 1 或 2；槽位 7（`0x00d97644`，动作 1；当 `[+0x5b8]` 在动作 2 中变为 1 或 2 时）；槽位 75（`0x00d9fcc4`) |
| 3 | 虚表 `0x253e358` 槽位 15（`0x00b4f028`，所属类为 `StateCreateSession`）；虚表 `0x25614c0` 槽位 8（`0x00dedf80`），条件为 `[[obj+0x98]+0x58]` 已置位 |
| 4 | 虚表 `0x253e8d0` 槽位 16（`0x00b54338`，所属类为 `StateConnect`）；`0x25614c0` 未置位时的槽位 |
| 5 | 无 |
| 6 | `0x00da09a0` (`0x00da0a04`），来自 `0x00cebe00`, `0x00cebea4`, `0x01466d90`，位于原生函数 `CallRaidBattleMatchingEvent_` (`0x01466d30`，表 `0x25aac68`) |

`0x00d97730(player, motion)` 通过 `player->vtable[0x190]` 将动作存储到键 `[0x261e8a0]` 下，原生函数 `IsPlayerRideBicycleType` (`0x0148b960` -> `0x00da0210`）也会读取它；位于 `0x00e57940` 的 Lua 枚举将动作命名为 `NORMAL`, `BICYCLE_GROUND`, `BICYCLE_WATER` (`1 | 2<<32`，位置为 `0x00e5793c`）。`0x25614c0` 槽位还会启动一条种类为 11 的活动记录（`0x0111b660`），将其交给 `[0x26108d8]` (`0x00fa13c0`），并推送一个样本。`0x25614c0` 对象表示访问宝可梦露营：原生函数 `PokeCampToVisit`（请求 `0x0100`，状态 3）和 `NpcPokeCampToVisit` (`0x0000`，状态 4）会构建它，网络侧请求 `0x0101`（状态 3）和 `0x0001`（状态 4）也一样；映像中还携带多人露营的 `contents.pokecamp.pb.KwSyncData`。状态 6 是极巨团体战匹配。

`a` 和 `b` 分别打包到位 0-1 和 2-3（`0x01123710`; `0x01123760` 将 `b` 的值 3 读取为 0）。重置函数 `0x00eb97b0` 在模式 0 中根据区域键设置 `a`，区域键为 `[[[0x2617c48]]+0x180]` (`0x00eb97d0..0x00eb9848`):

| 键 | 区域 | `a` |
| --- | --- | --- |
| `0x5742865396e549d0` | `wr0101` | 1 |
| `0x5ea5c3539ab81c81` | `wr0201`，铠之孤岛（抓包时位于地点 170） | 2 |
| `0x674edc539f9f74a6` | `wr0301` | 3 |
| 其他 |  | 0 |

这些键采用 FNV-1a 64（基值 `0xcbf29ce484222645`, `0x01369700..0x01369724`）计算，输入为 `a_wr0101`, `a_wr0201`, `a_wr0301`（逆推最后两个字符，均得到 `0xb8123d750dc24af8`）。它们也构成数组 `0x02061f98`（循环位置 `0x00ecd418`），在以下位置映射为巢穴发射器名称：`0x01c25bbb`, `0x01be5bad`, `0x01c2d3a5` (`0x00ec51b4..0x00ec5218`），而 `0x00de19c0` 在第一个条目上复制 `a_wr0101` (`0x01c0ae67`）；romfs 中有 `a_wr0201.bnk` 和 `a_wr0301.bnk` 音效库。`b` 由 `0x00ebf580` 设置，来自虚表 `0x259add8` 槽位 8（`0x0110e850(...) < 4`, `0x012dfaec`）和槽位 11（2，`0x012dfca8`），每次之后都会推送。

0x90 处的活动记录为 `0x49` 字节，由 `0x0111b660(rec, kind)` 设置（种类位于 `+0`，零值位于 `+4`, `+0x24..+0x3e`, `+0x40`, `+0x48`）。按调用点划分的种类：9 `0x0102437c`; 11 `0x00dedf3c`, `0x0126e37c`; 12 `0x01272120`; 18 `0x01027d38`; 19, 21, 23, 25 `0x01027d2c` (`0x13 + 2n`); 27 `0x00de7a0c`; 28 `0x00de727c`; 29 `0x01026290`; 30 `0x0109659c`; 31 `0x015d595c`; 255 `0x01027fac`, `0x010962b8`, `0x01097990`, `0x01097bc4`；以及 `0x010961b0`，根据通信模式 `[obj+0x70]` 通过以下位置的表确定：`0x2066c40`:

```
mode   0    1  2   3   4   5   6
kind   255  1  13  14  15  16  30
```

`SetMode` (`0x01096d10`, `str w1,[x0,#0x70]`）被连接交换以参数 2 调用（[会话](swsh_session.md#how-a-searching-sword-finds-a-partner)），此外也使用 0、1、6 调用。

训练家名字出现四次（MyStatus、训练家卡片、同行队伍记录、个人资料）；`pokeldn/swsh/trade_payload.rewrite` 同时修改这四处，交换界面显示该训练家的名字。空同行队伍槽位为零；0x810 处的数量与之吻合。

## PK8

在 `pokeldn/gen8.py` 中与 BDSP 共用（PKHeX `PK8` 和 `PB8` 均为 `G8PKM`）。《剑》发送 0x158 大小的同行队伍格式（`pokeldn/swsh/pokemon.py`），BDSP 则发送 0x148 大小的存储格式。

```
0x00  u32  encryption constant, in the clear. Seeds the cipher and the block order
0x06  u16  checksum, in the clear, over the decrypted body only
0x08       four 80-byte blocks, LCG-encrypted and permuted by (EC >> 13) & 31
0x148      the party stats, LCG-encrypted with the stream restarted, never permuted
```

两种不会报错的误读：

-
-

解码同行队伍后的核对项：昵称应与种类匹配；等级（未打乱的尾部）应与经验值匹配；0x126 处的极限特训数据应与 0x8C 处的个体值字匹配；MyStatus 的训练家 id 应与每个 PK8 的 id 匹配。

## 交换消息

`net_contents.trade.common.pokemon_trade.protocol_buffers`:

```
Pokemon                  { 1 bytes   serializePokemonParam }
PokemonTradeDataHolder   { 1 Pokemon pokemon }
```

交换提议通过 10050 携带一个 344 字节 PK8（`trade.py` `pokemon_offer`）。解析函数 `0x010d81d0` 构建一条 0x28 字节消息（`0x010d9c90`），调用 `ParseFromArray` (`0x0070c180`），并传入 `[msg+0x18]`; `MergePartialFromCodedStream` (`0x010d9ee0`）仅接受标签 0x0a。监听器将 `[Pokemon+0x18]` 读取为 libc++ 的 `std::string`（字节 0 的位 0 选择位于 +0x10 的堆指针），复制 0x158 字节。

### 接收处理函数的两种静默丢弃

`0x010d5e40`:

```
w0 = 0x006b5850(senderPointer)                            0xfd on failure
if (w0 == 0xfd) { [content+0x1a4] = 1; return; }          silent
memcpy(stack, body, 0x158)
subscriber = [content + 0x30 + index*8]
if (subscriber == null || its refcount is 0) return       silent
... invoke it, then content 50's send 0x010d6000
```

内容 50 的初始化仅填充 `+0x30` 和 `+0x38`，所以站点索引大于 1 时会返回；内容 40 的 `0x010dbc90` 也在 `+0x38`/`+0x40` 处执行相同门控。主机收到 10050 后会立即回复自身的 10050；没有收到 10050 回复意味着提议根本没有到达 `0x010d5e40`。内容 30 的槽位（`0x010ce080`）仅拒绝其自身 id（`[[0x2616a30]]+0xf0`）：没有 owner 的提议能通过盒子阶段，但会在内容 50 失败。

### 内容 40 的消息

`net_contents.trade.common.sync_save.protocol_buffers`:

```
SyncSaveDataHolder { 1 SyncCommand syncCommand }
SyncCommand        { 1 int32       data       }
```

解析函数 `0x010ddb20`（与 `0x010d81d0`); `0x010df6d0` 对应）仅接受标签 0x0a，子消息解析器 `0x010debc0` 仅接受标签 0x08。`trade.sync_command` 构建该消息。
