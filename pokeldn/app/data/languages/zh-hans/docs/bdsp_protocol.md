---
title: BDSP 自身的协议与角色控制
parent: Brilliant Diamond and Shining Pearl
nav_order: 2
---

# BDSP 自身的协议与角色控制

BDSP 在 Pia 载荷内运行一种带类型的协议。`Dpr.NetworkUtils.NetDataParser` 位于 `TeamLumi/opendpr` 中；后者是通过反编译重建的游戏 C# 项目，其中列出了所有消息：一个 `ANetData`，以一个字节的 `DataID` 包裹普通结构体 `T`.

## 帧封装

```
0x0  1  data id
0x1  2  payload length, big-endian
0x3  .  the struct, little-endian, packed
```

`JoinData` (`byte, byte, byte, short, Vector3`）在线路上占 17 字节，按 C# 默认对齐方式则占 20 字节。

`NetDataParser` 注册了 65 种消息；`pokeldn/bdsp/netdata.py` 包含所有消息，由 `opendpr` 的检出副本通过 `scripts/gen_bdsp_netdata.py` 生成。源代码确定了其中 53 种布局。其余十二种包含 C# 字符串、数组或列表（`netdata.OPAQUE`），其布局由二进制文件确定。

载荷是经过封送的结构体（`ANetData.ConvertStructToBytes` [main.bin 0x27bb0e0]：`Marshal.SizeOf`, `AllocHGlobal`, `StructureToPtr`），字符串和数组作为定长字段。结构体的大小就是其 `native_size`，位于 `Il2CppTypeDefinitionSizes` 中；字符串的长度位于 `global-metadata.dat` 的 `fieldMarshaledSizes` 中；数组元素数由其它字段占用后剩下的空间决定。实际字节由 `marshalToNative` 写出，位于 `CodeRegistration.interopData` [1.3.0 main 0x4acd0c8，0x255 个条目，每个 56 字节] 中。捕获到的四种不透明载荷逐字节吻合（`room.NATIVE_SIZES`, `room.MEASURED`）。标为 1.3.0 main 的地址属于《明亮珍珠》；《晶灿钻石》1.3.0 中相同方法位于其它地址。

| id | 载荷 | 字节数 | 布局 |
| --- | --- | --- | --- |
| 0x02 | `PosListData` | 72 | 12 × `PosData`（ushort posX、ushort posZ、short rotY） |
| 0x13 | `TradePokeData` | 328 | 一个采用存储大小的加密 PB8 |
| 0x14 | `NetRecodeData` | 694 | `RECORD` 120, `RANDOM_SEED` 132, `TvRecodeData` 204，4 × `TV_STR_DATA` 36, `RECORD_HEAD` 48，十个 int，六个字节 |
| 0x15 | `BallDecoData` | 143 | affixSealCount、Is3DEditMode、IsAppliedTemplate，随后是 `AttachSealData` 140（20 × `SealParam{short x, y, z; byte id}`) |
| 0x18, 0x54 | `UgSecretBase` | 616 | short zoneID、posX、posY；byte direction、expansionStatus；int goodCount；30 × `UgStoneStatue` 20；bool isEnable（4） |
| 0x22 | `StanbyListData` | 20 | 5 × `StandbyData`（isAddPlayer、hostIndex、myIndex、langId） |
| 0x24 | `TradeTranerData` | 32 | 13 个 UTF-16 字符，uint tranerId、byte cassetVersion、byte langId |
| 0x29, 0x61 | `UgStationID_to_DigFossilIDList` | 8 | `byte DigFossilIDs[8]`，0..7 的一个排列 |
| 0x38 | `BattleMatchingPokeData` | 481 | 一个 328 字节的 PB8，20 × `SealParam` 7，uint attachPokemonId、uint attachPersonalRnd、byte index、num、is3DEditMode、isAppliedTemplate、affixSealCount |
| 0x42 | `NetPlayerName` | 28 | 13 个 UTF-16 字符，byte genderid、byte languageId |

`BattleMatchingPokeData` 的两个数组将 468 拆成 328 + 20 个贴纸，这是唯一与 `TradePokeData` 和 `AttachSealData`.

`SendStandbyPlayerData` 相符的拆分方式。[1.3.0 main 0x01e52fa0] 填充 0x22 的五个槽位，数据来自 `UnionStateController.unionMatchWaitDataList` (`isAddPlayer = 1`, `hostIndex` 0）；空列表是二十个零字节。站点通过 `NetDataStandbyWaitData`（0x59，相同的四个字节）添加自身：在 `59 0004 01 00 01 03`（站点 1，法语）被 `ReciveMatchWaitData` [0x01e539b0] 接受后，下一条 0x22 就是 `22 0014 01 00 01 03` 加十六个零。`isAddPlayer = 0` 将其移除。屏幕没有变化。

封送器不清空缓冲区：定长字段在实际值之后仍携带堆残留数据（[交换页面](bdsp_trade.md)）。id 按半字节分组；低半字节均未达到 0xA。

## 无线链路上实际出现过的消息

独自留在房间中的主机会发送 65 种消息中的四种（接收器会丢弃回环广播）：

| id | 类 | 可靠 | 不可靠 | 大小 |
| --- | --- | --- | --- | --- |
| 0x01 | `NetJoinData` | 2070 | 0 | 17 |
| 0x02 | `NetPosData` | 0 | 60 | 72 |
| 0x12 | `NetRequestData` | 4333 | 55 | 1 |
| 0x23 | `NetDataIsMatchWaitData` | 1734 | 0 | 1 |

收到请求时，它还发送 0x09（一个字节，未设置对战时为 0）和 0x22；开展活动时发送 0x14 和 0x15。交换消息见[交换页面](bdsp_trade.md).

0x23 可能位于存在标记字节 0x00 之后（统计副本中有 1505 个如此），只有将 0x00 也视为消息进行遍历时才能读到它（[消息帧封装](pia.md#message-framing)）。每个载荷（共八千多个）都是格式正确的消息，其长度恰好涵盖全部字节。

## 主机反复发送的消息

`NetJoinData` 表示玩家到来，包含完整的 `JoinData`:

| 偏移 | 大小 | 字段 |
| --- | --- | --- |
| 0x00 | 1 | `avatarId`（8 为女孩，0 为男孩；[模型](#the-model)) |
| 0x01 | 1 | `colorId`, 0 |
| 0x02 | 1 | `cassetVersion`，0x31 |
| 0x03 | 2 | `InitRotY`，以度为单位的朝向（实测为 45 的倍数），小端序，未对齐 |
| 0x05 | 12 | `InitPos`，三个小端序浮点数：x、y、z |

`NetRequestData` 是一个字节，表示所请求消息的 id。`NetDataIsMatchWaitData` `{isMatchWait = 0}` 是主机对自身请求的回答。主机请求两种信息：

| 请求项 | 次数 |
| --- | --- |
| `NetDataIsMatchWaitData`（0x23） | 4333 |
| `NetCharacterStateData`（0x04） | 55 |

游戏创建角色时，会向该角色的站点请求状态，因此 0x04 请求说明角色已经存在（55 次请求；在未绘制角色的 265 次加入中一次都没有）；`bin/bdsp_connect.py` 将其打印为判定结果。主机会重复请求 0x23，直到客户端确认其可靠窗口；未确认时，75 秒内收到了 487 次请求。

`UnionRoomManager$$SetNetData` [1.3.0 main 0x01e50700] 会针对六个 id 回答 `NetRequestData`，其它 id 一概忽略：

| 请求项 | 主机发送的内容 | 通过 |
| --- | --- | --- |
| 0x01 `NetJoinData` | 自身的加入记录 | `UnionRoomManager$$SendJoinData` |
| 0x04 `NetCharacterStateData` | 自身的角色状态 | `UnionRoomManager$$SendOpcStateData` |
| 0x09 `NetDataBattleTypeData` | 自身的对战规则 | `UnionRoomManager$$SendBattleRuleData` |
| 0x13 `NetTradePokeData` | 正在提供的宝可梦 | `UnionRoomManager$$SendPokeData` |
| 0x22 `NetDataStandbyWaitListData` | 自身的待机列表 | `UnionRoomManager$$SendStandbyPlayerData` |
| 0x23 `NetDataIsMatchWaitData` | 是否正在等待匹配 | `UnionRoomManager$$SendIsMatchWait` |

从房间内已有角色的站点发出请求时，其中五种会在可靠流上得到回答，实测延迟为请求后 30 至 130 ms；未选择宝可梦时，0x13 不会得到回答（`SendPokeData` 直接返回）。基础版本游戏的处理器 [base main 0x01fd4600] 回答相同的六种请求，当时 0x22 名为 `NetDataTradeStandbyData`。请求在其回答所使用的流上到达：4333 次 0x23 请求全部走可靠流，55 次 0x04 请求全部走不可靠流。

### 压缩

可靠头部中的 0x10 标志表示 zlib 流。发送端根据大小决定是否压缩：`ReliableSlidingWindow` 的 push [1.3.0 main `0x15a10d0`] 检查窗口的压缩开关（+0x7ac，`0x15a1364`）；开关启用时，`0x159a500` 对整个游戏消息执行 deflate 压缩，包括其 3 字节头部：

```
0x1685384   deflateInit2: level 5, window bits 12, memLevel 5, strategy 0, 4000-byte output
0x16854e0   deflate(Z_SYNC_FLUSH)
0x1685608   deflate(Z_FINISH)
0x159a5b0   compressed size >= raw size  ->  error 0x2c7d, the message goes raw
0x15a1398   otherwise: header |= 0x10, send the compressed bytes
```

主机的全部 55 条带标志消息，都与 Python 的 `zlib.compressobj(5, zlib.DEFLATED, 12, 5)` 先同步刷新再结束的结果逐字节相同；10955 条无标志消息中，没有一条经此处理后变小。加入消息和仅含一条记录的 0x22 列表原样发送；全零的 0x22 列表（按原始数据读取时看起来像 `NetBonusStart`）、记录（0x14）以及球壳（0x15）都会变小。接收端无须执行压缩；`bin/bdsp_connect.py` 根据标志解压。

### 其它不透明消息的发送方

根据 1.3.0 中各个 `ANetData.SendReliableData` 在 1.3.0 中的调用方：

| id | 类 | 发送方 |
| --- | --- | --- |
| 0x14 | `NetDataRecodeData` | `RecodeMatching$$SendRecodeData`, `UnionStateController$$SendRecodeData` |
| 0x15 | `NetDataAttachSealNetData` | `BallDecoMatching$$SendBallDecoData` |
| 0x18 | `NetSecretBaseData` | `UgNetworkManager$$SendMySecretBaseData`；收到请求时（`OnReceiveRequestData`) |
| 0x61 | `NetDigTableData` | 收到请求时（`OnReceiveRequestData`) |
| 0x38 | `NetDataBattleMatchingSelectPokemon` | `BattleMatchingManager$$SendSelectPokemonData` |
| 0x42 | `NetPlayerNameData` | `UgNetworkManager$$SendOnJoinNewPlayer`, `SendPlayerNameData` |
| 0x54 | `NetSecretBaseUpdate` | 没有可靠发送方；`netdata.py` 为它命名 |

### 不可靠流

它承载三种消息：

| 字节数 | 次数 | 消息 |
| --- | --- | --- |
| `04 0002 00 00` | 853 | `NetCharacterStateData{state: NONE, isRecruiment: 0}`，实测每两秒一次 |
| `12 0001 04` | 55 | `NetRequestData`：“把你的 `NetCharacterStateData`” |
| `02 0048 ` | 60 | `NetPosData`，十二个点，在主机的化身行走时发送 |

`room.build_state()` 构造第一种消息，而 `room.build_match_wait(False)` 构造主机自身的 0x23 回答。

主机持续重传可靠消息，直到某个 ack 覆盖它，实测每秒五次；若 ack 比最后序列号大二，则会被忽略。`bin/bdsp_connect.py` 在主机确认客户端自身的数据后，以最后序列号加一发送 ack。

## 发送游戏会实际处理的消息

可靠序列 id 与主机自身发送的数据共享，低于确认消息所指 id 的消息会被静默丢弃。每次发送前都应立即读取该 id。

以已确认序列号发送的加入消息会得到处理：以 0.4 s 间隔发送十五次加入时，主机针对其中 12 至 15 次请求了 0x04，第一次请求出现在首次加入后 0.10 至 0.57 s。`--room-pattern fixed` 在首次请求时停止，每次加入等待 `--join-wait` 秒（默认 1.0）。

`UnionOpcManager` 每次加入都会调用 `CreateCharacter(joinData)`：四十次加入就是四十次到来。在零售版主机上，没有对应会话却被创建的角色，会随玩家穿越地图，直到游戏重启；一个已经移动过的角色则会在其站点离开网状网络时被移除。尚未追踪离开时的移除路径（`OpcManager$$RemoveCharacter` [0x02279ee4] 接受站点索引）。

## 角色记录

`OpcManager.CharaData` 是 `{int stationIndex, string assetName, int colorId, int avatarId, int sexId, int cassetVersion}`，以站点为键（`RemoveCharacter(int stationIndex)`).

### 模型

`OpcManager.CreateCharaData(ANetData)` 从加入消息构造记录，而 `avatarId` 决定显示哪个角色：

```
NetJoinData.avatarId  ->  CreateCharaData  ->  CharaData.avatarId
                      ->  UnionCharacterTable.SheetSheet1{ID, AssetName}
                      ->  OpLoadCharacter("persons/field/" + assetName)
```

`CreateCharaData` [1.3.0 main 0x022796b0] 仅根据化身设置 `sexId`，`avatarId > 7 && avatarId != 16` (`0x02279770`）：8 至 15 为女孩，0 至 7 以及 16 为男孩。`GetOpcSexId` [0x02279840] 返回该值，而 `GetNpcColorId` 读取相同的化身：8 是女孩，0 是戴蓝帽子的男孩（`--join-avatar N`).

主机自身的加入消息携带 work 360（`SendJoinData` [0x01e4f630] 经由 `GetAvaterId` [0x01e54030]）。新存档将它初始化为 0，创建存档时不会选择联盟交谊厅外观：原生代码只读取该 work（上述两个方法），只有两个脚本会写入它。可选的外观柜台（`ev_union_character_select_*`）按存档性别提供八种训练家类型（`_GET_MY_SEX`），男孩保存为 16 或 1 至 7，女孩保存为 8 至 15。否则，只要 work 360 仍为 0，`ev_connect_union_check_save` 和 `ev_connect_global_check_net` 就会调用 `ev_traner_other_see_random`，将它设为 1 加一个小于 16 的随机值（`_GET_RND`, `_ADD_WK`），不限制性别。只有使用柜台后，加入消息才会体现存档的性别，而且消息中没有任何内容说明玩家是否使用过柜台。

`NetDataTranerCardData`（0x05，75 字节：`fashionId`, `bodyType`, `genderid`，……）传给 `UnionOpcManager.CreateTranerCard()`；在联盟交谊厅中，收到此消息不会在屏幕上绘制任何内容。

### 状态字节

`StateData` 是 `{byte state, byte isRecruiment}`, `state`，类型为 `OpcState.OnlineState`:

| 值 | 名称 | 值 | 名称 |
| --- | --- | --- | --- |
| 0 | `NONE` | 5 | `RECRUITMENT_RECORD` |
| 1 | `DIG_FOSILL` | 6 | `RECRUITMENT_GREETINGS` |
| 2 | `SECRETBASE_ACTION` | 7 | `RECRUITMENT_BALL_DECORATION` |
| 3 | `RECRUITMENT_BATTLE` | 8 | `COMMUNICATE` |
| 4 | `RECRUITMENT_TRADE` |  |  |

17 至 21 是 `NOW_*` 状态，每种活动一个（[transitionType 表](#talkstate-and-the-value-that-crashes-the-game)). `OpcController.ShowEmoticon(OnlineState)` 和 `GetEmoticonType(state)` 会读取它；取值为 `RECRUITMENT_*` 时会显示对话气泡。用 `StateData{RECRUITMENT_TRADE, 1}` 回答主机请求，会在零售版主机屏幕上显示交换气泡；`StateData{NONE, 0}` 则不会改变任何内容。

收到的 0x04 按以下路径传递：`UnionRoomManager$$OnReceiveData` [1.3.0 main 0x01e506c0] -> `OpcManager$$SetNetData` [0x02279450]（站点没有角色时丢弃）-> `UnionOpcController$$SetNetData` [0x01e48c50]，后者是唯一使用方：

```
if state != GetOpcOnlineState():      SetOpcOnlineState(state)                 0x02277be0
                                      isRecruiment == 1 ? SetEmoticonHost()    0x022779b0
                                                        : SetEmoticonNormal()  0x02277a50
if state != 0:                        AnimationPlayer.Play(animation 0)
```

地下大洞窟中的对应实现是 `UgOpcController$$SetNetData` [0x01f7f820]。

`OpcState` 是 `{OnlineState _curretOnlineState +0x18; Action _OnChangeState +0x20}`，由 `OnlinePlayerCharacter$$Start` [0x02276ff0] 添加，Action 绑定到 `ShowEmoticon` [0x02277094]；状态初始为 0。`SetOpcOnlineState` [0x02277c80] 是唯一实际生效的写入点（`OpcState$$OnChangeOnlineState` [0x02277d10] 没有调用方）。在该 setter 的调用方中（虚调用，类偏移 0x190），有三个会触及远端角色：`UnionOpcController$$SetNetData` [0x01e48d7c] 写入收到的状态，以及 `OpcManager$$RemoveCharacter` [0x02279ee4] 和 `UgOpcManager$$RemoveAllCharacter` [0x01f80cac] 写入 0。因此远端角色的状态只会因自身站点发来的 0x04 而改变。其余调用方设置主机自身的角色：`UnionSystemController$$ChangeOpcState` [0x01c2d3f8]（使用其参数，随后广播 0x04 [0x01c2d4d0]），`RusultGreetJoinYesNoWindow` [0x01c2e8ac] 设置为 6，`b__0` [0x01f8b790] 设置为 3，`UnionTradeManager$$InitPlayerState` [0x01c33a58]、`UnionStateController$$InitPlayerState` [0x01e4e83c] 和 `SwitchCancelEnd` [0x01e4fd70] 设置为 0，`UnionStateTransitionController$$StartFadeOut` [0x01e5a00c] 使用其模型的 +0x2c，`UgNetworkManager$$OnReceiveJoinDigPermission` [0x01f7ca94] 和 `SendOnPlayDigFossil` [0x01f79f78] 设置为 14，以及 `UgNetworkManager$$SetMyEmoticon` [0x01f79148]。

在 `Start` 运行之前，getter 返回 0 [0x02277dcc]，setter 则丢弃该值 [0x02277c50]。角色的 0x04 请求紧接着 `SetActive(true)` 发出，位于 `CreateCharacter` 的加载回调 [0x01e49854] 中，因此在 `Start` 之前到达的回答会丢失；应像主机一样，每两秒重复发送状态。

`OnlinePlayerCharacter$$IsCanTalkState` [0x02277af0]：玩家可以与状态为 1、3 至 8 以及 17 至 21 的角色对话，但不能与状态为 0、2 或 9 至 16 的角色对话。

### 行走

主机自身的 `NetPosData` 每 0.410 s 到达一次，跨越 0.935 个单位（`room.POS_PERIOD`, `room.POS_STRIDE`; `--room-walk-period`, `--room-walk-stride`）；每 0.35 s 移动 0.1 个单位会呈现为卡顿。

`PosData` 是 `{ushort posX, ushort posZ, short rotY}`, `pos = (-posX * 0.05, posZ * 0.05)`：单位为二十分之一个游戏单位，x 取反。远端角色会与墙壁碰撞（玩家不会与它碰撞），并原样保持 `rot_y`。应将行走限制在房间内：以主机的步幅发送六十条消息，会穿过整个房间并从远端墙壁走出去，`--room-walk-steps 8` 则保持在房间内。

交换无须行走：一台零售版主机与一个没有发送任何 `NetPosData` (`--room-walk-steps 0` 的客户端角色完成了两次交换，这是交换路径的默认行为）。

## 被搭话

玩家显示表情时会停在原地，直到有人互动；当玩家自身状态非零时，按 A 没有效果（[主机主动搭话](#the-console-approaching)）。主机会广播该表情：

```
NetCharacterStateData{state: 4, isRecruiment: 1}     the trade emote, up
NetCharacterStateData{state: 0, isRecruiment: 0}     and down again
```

以 `isRecruiment` 作为门槛：状态 18 表示主机已处于交换中，此时接近会被拒绝。一台零售版主机对在其交换表情出现后 0.0 s 发出的搭话请求，于 40 ms 后作答，与 3.0 s 后发出的请求所得回答相同：`IsCanTalk 0, IsRecruitment 1, emoticonStateType 4` (`bin/bdsp_host.py --approach-delay`，默认 0）。

搭话消息是 `NetDataTalkReserveData`（0x63），`63 00 01 00`，与主机发送的内容一致（`bin/bdsp_connect.py --initiate-talk`）。主机玩家主动接近客户端角色时，顺序如下：

```
cli ->  64 0003 00 01 04      NetDataTalkReserveResultData{IsCanTalk, IsRecruitment, emoticonStateType}
con ->  06 0005 00 01000000   NetDataTalkData{talkOpcSexId: 0, talkState: GREETING}
con ->  10 0002 01 04         NetDataTalkCancelEndData{IsRecruitment: 1, emoticonStateType: 4}
```

对话等待 0x64；未得到回答时，玩家角色会一直僵住。

| `IsCanTalk` | 随后发送 | 屏幕表现 |
| --- | --- | --- |
| 0 | 不发送任何内容 | 问候继续进行，随后停在“等一下！” |
| 1 | 不发送任何内容、`NetDataSelectData{0}` 或 `{1}` | “抱歉，我另有安排”，对话关闭 |

断开站点会解除停住的问候；按 B 并不能可靠地退出。

### 主机主动搭话

`UnionRoomManager$$MyUpdate` [1.3.0 main 0x01e49fb0] 处理 A 键 [0x01e4a644] 的前提是玩家自身状态为 0、`UnionWork.isTalking`（静态 +0x85）为 0、没有打开菜单或消息窗口，且玩家位于所有 `EnterCollision` 圆圈之外。它遍历 10.0 单位内、位于玩家的 `talkDistance`（+0x38）范围中且状态通过检查的角色：`IsCanTalkState`:

| 角色状态 | A 键的效果 |
| --- | --- |
| 0、2、9 至 16 | 无效果 |
| 8、17 至 21 | 遍历后，对最近的角色调用 `UnionRoomManager$$StartTalk(opc, 0, 0, 0)` [0x01e4c2d0]；不发送消息 |
| 4 | `UnionSystemController$$CheckErrorMessageTrade` [0x01c2e8d0]；无错误时，同最后一行 |
| 7 | `UnionSystemController$$CheckBallDeco` [0x01c2ec20]；检查通过时，同最后一行 |
| 1, 3, 5, 6 | `NetDataTalkReserveData`（0x63）发送到角色的站点 [0x01e4ac94]，状态保存到 `nowTalkReserveState`（+0x188），`isTalking` 被设置，`UnionStateController$$CreateSelectStateModel(state, 1)` [0x01e4b620] |

对于状态 1 和 3 至 7，遍历会立即对第一个符合条件、且比此前角色更近的角色执行操作。

主机回答 0x63，处理位置为 `UnionRoomManager$$SetNetData` [0x01e50c3c]：

```
r.IsCanTalk = UnionWork.isTalking
if stateController._currentModel (+0x88) is null:
    r.IsCanTalk = 1; SendOpcStateData(requester)
r.IsRecruitment = 1
r.emoticonStateType = the console player's own state
send r (0x64) to the requester                           0x01e5110c
if isTalking was 0 and r.IsCanTalk is 0: isTalking = 1
```

主机发出自身的 0x63 后读取 0x64 [0x01e50dec]：

```
canTalk = IsCanTalk == 0 and not isCancelStock (+0x183, cleared here)
if emoticonStateType != nowTalkReserveState:
    send NetDataTalkCancelEndData{0, 0}                  0x01e50f24
else:
    nowTalkReserveState = 0                              0x01e50ea0
    canTalk ? StartTalk(opc, IsRecruitment == 0, 1, 0)
            : the refusal path 0x01e512f0 (the character's state against 3 to 7)
```

一个宣告 `{4, 1}` 的角色，在按 A 时会触发 `63 0001 00`，而 `64 0003 00 01 04` 会打开对话。任何其它 `emoticonStateType` 都会触发 `NetDataTalkCancelEndData{0, 0}`；针对同一条 0x63 的第二条 0x64 也是如此，因为第一条已清除 `nowTalkReserveState` [0x01e50e94]。每条 0x63 只回答一次，不要对每个重传副本都回答。

主机作为搭话方时，客户端角色就是招募方。招募方同意交换邀请（`UnionTradeContextMenu.<>c__DisplayClass10_0.b__0` [0x01c32f70]；拒绝则是 `TradeRecruitmentStateModel$$Cancel` 0x01c24150）会打开消息 8，并尾调用 `UnionContextMenu$$SendTransitionData(station, 0)` [0x01f86480]，后者通过可靠流发送 `NetDataTransitionData{menu+0x50, 0}`；`SetTransitionType` [0x01c32ef0] 将 +0x50 设为 18。同意消息是 `07 0002 12 00`，这也是招募中的主机在客户端接近时发送的消息（[交换页面](bdsp_trade.md#the-message-sequence)）。0x64 之后的一条类型为 18 的 0x07，无须搭话主机的玩家确认，就会在该主机上启动交换（`SwitchTransitionMessage` [0x01e53bf0] -> `TransitionTradePoke` [0x01e5c1c0]，见下文）：主机发送自身的 `NetDataTradeTranerData`（0x24），并打开交换盒子。一台零售版主机在接近客户端状态为 4 的角色后，接受了一条 `07 0002 12 00`；它在 0x64 回答之后发送，并使交换完成。

在搭话主机上，对状态为 4 的角色按 A，会在 `TradeJoinStateModel` 处构造一个 `UnionStateController+0x50` (`CreateSelectStateModel(4, 1)`，写入点为 0x01e4b814，这是唯一写入点，且从不清除）。0x64 执行 `SwitchTalkStateMine` [0x01e4c41c]：将 18 写入 `UnionSystemController.onlinePlayerSelectState`（+0x28），并调用 `SetTargetStationIndex(station, cassetVersion, 1)` [0x01e54ae8]。0x07 不经状态检查 [0x01e52610] 就传给 `SwitchTransitionMessage` [0x01e53bf0]；它读取该类型的模型（字节表 0x03db869b），不检查空值；对于交换，`TradeJoinStateModel$$OpenSwitchFadeMsg` [0x01c22f50] 根据发送方性别打开消息 9 或 10，以 `OPPONENT` (`SpeakerID` 1）的身份发言，关闭后进入 `StartFadeOut`。淡出之后，`SwitchTransition` [0x01e5ba70] 将 18 传给 `TransitionTradePoke` [0x01e5c1c0]，后者取出并清除目标站点，检查 `IsGamerActive`，再发送主机的 0x24 [`SendTranerData` 0x01e5c2b0]：这就是加入方方向上的交换起点。若主机自 `UnionStateController` 构造以来还未对交换招募者按过 A，收到 0x07 就会解引用空指针（0x01e53c4c）；其它转换类型在各自模型上也具有相同结构。

### 问候中的名字

问候、发言者标签以及对战流程中的“正在选择”文本，都以角色所在站点的 Pia 玩家名来称呼该角色：`UnionBaseMsgWindow$$SetTargetDataMessage` [1.3.0 main 0x01f86810] 和 `GetSpeakerName` [0x01f87050] 读取 `NetworkManager$$GetGamerData(station)` [0x02250e50]（`IlcaNetGamer.gamerName` +0x30，`nameStringLanguage` +0x38）。`NetGamerNameGet` [0x0273a9a0] 在 Pia 加入事件发生时，将来自 `length - 1` 的 80 字节缓冲区中的 `INLpiaSessionGetPlayerInfo` [0x01e15cd0] 字节按 UTF-8 解码（长度小于 2 时为空），并原样复制语言字节。

`Utils$$CheckNGTrainerName` [0x01cbdc30] 会将名字替换为 `Utils$$GetReplacedNGName(UnionWork.nowTargetCassetVersion)` [0x01cbde20]，条件为名字为空、被 `CheckNgWords` [0x01c99220] 标记为不合规，或其 UTF-16 单元数超过 `SoftwareKeyboard$$LanguageMaxLength(6, lang)` [0x01c995b0]：

| `lang` | 上限 |
| --- | --- |
| 1, 8, 9, 10 | 6 |
| 任何其它正值 | 12 |
| 0 或负值 | 由界面当前语言决定 |

语言位于 PlayerInfo 的字节 0x7A。Mesh Station Protocol 的解析器 [0x0154f044..0x0154f5e0] 每次迭代读取一个 195 字节的 PlayerInfo（`add w23, w23, #0xc3` 0x0154f588）；无论使用何种编码，偏移都固定：

| 偏移 | 字段 | 读取方式 |
| --- | --- | --- |
| 0x00 | 名字编码 | 2：20 个 UTF-16 单元（0x0154f078..0x0154f15c）；其它值：80 字节 |
| 0x01..0x50 | 名字 | 写入站点记录的 +0x120 + index*0x80 |
| 0x51 | 第二个字符串的编码 | 0x0154f220 |
| 0x52..0x79 | 第二个字符串，40 字节 | 编码 2：10 个 UTF-16 单元，写入 +0x320 + index*0x58 |
| 0x7A | 语言 | `strb w8, [x20+x25, #0x480]` 0x0154f5a0 |
| 0x7B..0xBA | 64 字节 | 0x0154f5b8 |
| 0xBB..0xC2 | u64 | 写入 +0x490 + index*8 |

`INLpiaSessionGetPlayerInfo` 传到 `0x01391a90`；它将该字节默认设为 0xFF [0x01391b44]，并将站点记录的 +0x480 原样复制到 `NetGamerNameGet` 的 `nameStringLanguage` [0x01391bb0]。该字节的类型是 `MsgLangId`:

```
JPN 1, USA 2, FRA 3, ITA 4, DEU 5, ESP 7, KOR 8, SCH 9, TCH 10
```

主机发送自身的 `MessageManager$$get_UserLanguageID` 以及经过 `CheckNGTrainerName` 检查的名字（`SessionConnector$$ResetParam` [0x0202f050]），经由 `IlcaNetBase$$PlatformInitialize2` [0x01e13ce0] 和 `PiaPlugin$$RegisterStartupSessionSetting` [0x0227d5a0] 传递；站点协议的 PlayerInfo 写入器将 +0x480 写到字节 0x7A [0x01550e98]。法语主机的连接响应（站点协议种类 2）携带编码 1、自身名字、值为 0 的字节 0x79，以及值为 3 的字节 0x7A。

语言表示发送方的游戏文本语言，保存在存档的 `CONFIG.msg_lang_id`（PlayerWork +0xac，`get_msgLangID` [0x0237e100]）；`GameManager.` [0x01e0eb44] 从系统语言（`GetCurrentIetfCode`）填入它，但仅在保存值不在 1..10 范围内时如此。自身站点记录的 +0x480 经过四次复制填充，每次复制的都是 PlayerInfo 的语言字节：

| 步骤 | 代码 | 来源 | 目标 |
| --- | --- | --- | --- |
| `RegisterStartupSessionSetting` | `0x0156f918`（设置构建器，`0x0156fa08`), `0x0168d4c8` | 插件的玩家数组（步长 0x28） | 框架保存的设置 +0x3220：PlayerInfo +0x18，语言 +0x98，步长 0x98 |
| `ChangeStateJob::StartupSession` | `0x01690d6c` -> `0x0168c5b8` -> `0x0157d36c` -> 控制器 vfunc 2（`LocalMatchMeshLayerController` `0x016c3e70`) | 设置中的第一个 PlayerInfo（`0x016c3f48`) | 控制器的玩家列表 +8，语言 +0x88，+0x268 处的数量为 1 |
| `CreateSessionJob::MeshStartup` `0x015873b0`, `JoinSessionJob::MeshStartup` `0x015884bc` | 控制器 vfunc 4（`MeshLayerController` `0x0171a068`) -> `0x01546fa4` | 控制器的列表 | 网状网络对象（`[0x04c4db60]`）+0x128 + n*0x98，语言 +0x80（`0x015472e4`），数量 +0x388 |
| `CreateMeshJob::SetupLocalPlayerInfo` `0x0155a764`, `JoinMeshJob::SetupLocalPlayerInfo` `0x0155b988` | `0x015494f0` | 网状网络对象的列表 | 自身站点记录 +0x480 + n（`strb w8, [x23, x22]` `0x0154956c`) |

`ChangeStateJob::StartupSessionBegin` (`0x01690c70`）可直接到达 StartupSession；框架 +0x7c 为 0 时，则经过 `StartupSessionJob` (`0x0168ec7c`，设置位于任务 +0x70）以及 `WaitStartupSessionLdnInitialize` (`0x01690e30`). `StartupSessionJob` 后到达。它只有一个实际工作步骤 InitializeLdn（`0x0168ed74`），不复制任何 PlayerInfo。法语主机发出的 30 个 PlayerInfo（17 个连接响应、13 个连接请求）全部在字节 0x7A 发送 3，在字节 0x51 发送 0。

无论 `bin/bdsp_connect.py` 还是 `bin/bdsp_host.py`，都通过 `pokeldn/bdsp/host.py` `player_info` 构造 PlayerInfo（编码 1、UTF-8 名字、字节 0x51 为 0），并发送 `--language`，默认值为 3；桌面应用传入其训练家语言。语言为 3 时，11 字符的名字可以完整显示。

替代名字取决于被搭话角色的 `CharaData.cassetVersion`，即字节 2，所属结构为 `NetJoinData` 的字节 2；两个问候调用方（`SwitchSpokenStateMine` 0x01e53b58、`MessageEndSpokenData` 0x01e57ab8）都会将其保存到 `UnionWork.nowTargetCassetVersion`（静态 +0x8C）。`GetReplacedNGName` 取标签 247，来自 `dp_characters`，适用于 0x31；其它值则取标签 206（0x01cbdecc），并追加句号。文本来自 1.3.0 RomFS 的 `Message/` 资源包：

| 资源包 | 0x31（《明亮珍珠》），`DP_CHARACTERS_247` | 其它值，`DP_CHARACTERS_206` |
| --- | --- | --- |
| 英语 | `Pearl.` | `Diamond.` |
| 法语 | `Perlo.` | `Diamant.` |
| 德语 | `Perl.` | `Diamant.` |
| 意大利语 | `Perl.` | `Diaman.` |
| 西班牙语 | `Perla.` | `Diamant.` |
| jpn、jpn_kanji（日语、日语汉字） | `パール.` | `ダイヤ.` |
| 韩语 | `펄.` | `다이아몬드.` |
| 简体中文 | `帕尔.` | `戴亚.` |
| 繁体中文 | `帕爾.` | `戴亞.` |

### talkState 与会导致游戏崩溃的值

`TalkState` 是 `{CHECK = 0, GREETING = 1, NONE = 2}`；停住的主机在 `GREETING`. `UnionStateController$$SwitchSpokenStateMine` 中等待，它把除 CHECK 外的任何值都传给 `StartOpenGreetingMsgWindow` (`b 0x1fd85e0`，地址为 0x1fd5e80）；CHECK 会加载 `systemController->msgWindow`（0x1fd5e84），并在没有空指针保护的情况下解引用它（0x1fd5ec0）。站着显示表情的玩家没有消息窗口，因此 CHECK 会导致游戏崩溃；`pokeldn/bdsp/room.py` 拒绝发送它。在阅读接收方处理器之前，绝不要发送从发送方代码中读到的状态值。

`NetDataTransitionData{transitionType, isRecruitment}`（0x07）将停住的问候推进到某项活动。游戏通过尾调用发送它，因此只扫描 BL 的调用方分析会将其报告为从未发送（[查找调用方](switch_re.md#finding-callers)). `transitionType` 的类型为 `OnlineState`; `UnionStateTransitionController$$SwitchTransition` [1.3.0 main 0x01e5ba70] 通过一个 19 项表按该值分派，而 `SwitchTransitionMessage` 从 `UnionStateController` 加下列偏移的位置读取模型：

| transitionType | 活动 | 进入路径 | 模型 |
| --- | --- | --- | --- |
| 3, 17 | 对战 | `TransitionBattle` | +0x38 或 +0x40，取决于 `isRecruitment` (`tbz w4`) |
| 4, 18 | 交换 | `TransitionTradePoke` | +0x50，`tradeJoinStateModel` |
| 5, 19 | 混合记录 | `RecodeMatching$$Open` | +0x60 |
| 6, 20 | 训练家卡片 | `TransitionShowTrainerCard` | +0x70 |
| 7, 21 | 球壳 | `BallDecoMatching$$Open` | +0x80 |
| 8 至 16 | 无 |  | 无；直接返回 |

`RecodeMatching$$Open` 和 `BallDecoMatching$$Open` 会立即发送主机自身的记录（0x14、0x15）并等待；只有伙伴的记录（`StartRecodeTradeFlow`, `StartBallDecoTradeFlow`）才会写入存档。

### 混合记录

主机通过 Y 菜单中的“交换数据”招募（状态字节为 5）。客户端上前搭话且玩家同意后，它会发送 `NetDataTransitionData{5, 0}`，然后发送自身 694 字节的 `NetDataRecodeData`（205 字节的 zlib 流；实测在 1.5 s 后发送），随后以状态 19 等待（`NOW_RECORD`）。没有回答时，它显示“有一位参与者已无法继续”，并返回房间；唯一一次实测等待时间为 44 s，尚未定位计时器。`room.parse` 将记录头部返回为 `recode`:

```
RECORD.record[30]        thirty uint counters indexed by RECORD_ID (CLEAR_TIME, DENDOU_CNT,
                         CAPTURE_POKE, ..., CONTEST_RATE_SINGLE)
RANDOM_SEED              group_name (16 chars), name (32 chars), int sex, int region_code,
                         ulong seed, ulong random, long time_stmp (a Windows FILETIME),
                         int user_id (the trainer id)
TvRecodeData             five TV records (personality, ball decoration, fossil digging,
                         statue, fashion), each `bool isEmpty` (4 bytes), ints, a TV_STR_DATA
4 x TV_STR_DATA          {16-char value, byte language, genderId, two reserved}
RECORD_HEAD              13-char username, int language, byte sex, int body_type,
                         uint uniqueID (the trainer id again)
ten ints, six bytes      the per-TV branch values, myVersion (0x31), five *IsNotEmpty flags
```

未写入的字段含有 64 位堆指针。`RECORD_HEAD.sex` 和 `RANDOM_SEED.sex` 在同一条记录内也可能不同（捕获的一条记录中分别为 0 和 1）。`RECORD`, `RANDOM_SEED` 和 `RECORD_HEAD`（命名空间 `DPData`）按 pack 4 封送，`TvRecode*` 结构体按 pack 8 封送；这些字段大小不会产生填充。

### 对战的逐级流程

对战（“对战”，招募时状态字节为 3）按逐级流程进行；招募主机在每一级都等待加入方（此处是客户端）：

| 加入方发送 | 主机执行 |
| --- | --- |
| `NetDataTalkData{GREETING}` | 显示“要对战吗？好啊！稍等我一下！”并等待 |
| `NetDataSelectData{0}`（0x08） | 显示“POKELDN 正在选择要做什么……”并等待 |
| `NetDataBattleTypeData{0}`（0x09，`BattleModeID.Single`) | 询问玩家“要按照这些规则对战吗？”；同意时发送 `NetDataTransitionData{17, 0}`，状态字节变为 17，并打开单打大厅，显示“正在连接” |
| `NetDataBattleMatchingJoin`（0x30）`{uint id, byte stationIndex, index, language, colorId, avatarId, sexId, cassetVersion}` | 用自身的加入消息回答（`id` 为自身训练家 id，站点为 0，索引为 0），并将加入方的加入消息转发回去；加入方角色出现在大厅第二个槽位 |
| `NetDataBattleMatchingReady`（0x32，空） | `BattleMatchingManager$$ReceiveReadyData`：所有成员就绪后，`NetDataBattleMatchingState{0, 6}`（0x33），`MatchingState.SelectBattleTeam`（单打对战跳过 4 和 5），玩家获得队伍选择按钮 |
| 不发送任何内容 | 玩家选好队伍时，发送六条 `NetDataBattleMatchingSelectPokemon`（0x38，481 字节），随后显示“正在等待其他人” |

每条 0x38 包含一个校验和正确的加密 PB8（按顺序排列所选队伍），二十个 `SealParam` 槽位内含相同的堆残留数据，其中 `affixSealCount` 0, `attachPokemonId` 和 `attachPersonalRnd` 0, `index` 为 0 至 5，而 `num` 为 6。一台主机接受了一条 `id` 为 0x0badc0de 的 0x30；尚未定位到针对该字段的检查。`BattleMatchingManager.MatchingState`：None（无）0、Initialize（初始化）1、Load（加载）2、RecruitmentMember（招募成员）3、SelectTeamMember（选择队伍成员）4、SelectRule（选择规则）5、SelectBattleTeam（选择对战队伍）6、SelectPokemon（选择宝可梦）7、GoBattle（进入对战）8、Result（结果）9、Resume（恢复）10、Closing（关闭）11、LeavedOtherMembers（其他成员离开）12。

`NetDataSelectData`（0x08）是 `{byte index}`。其唯一接收器 [`UnionRoomManager$$SetNetData`，0x01e52a30] 读取发送方站点，但从不读取索引：

```
m = stateController.battleRecruitmentModel                  UnionStateController +0x38
m.ChangeBattleRecruitmentState(BATTLE_RULE_SELECT_WAIT 4)   0x01d2aab0
m.currentCancelModel = {SelectCancel 0, station}
m.CloseWindow()
if m.unionMsgBattleWindow != null:
    SetTargetDataMessage(window, station, 1, 1); OpenMsgWindow(window, 3, 2)   0x01f86fa0
```

无论当前打开哪种对话，0x08 都会驱动对战招募模型。两个发送方都写入 0（`UnionBattleContextMenu$$SendRuleSelectState` [0x01f87c60]，尾调用，以及 `b__0` [0x01f8800c]）。

接收器从不检查模型是否为空：它加载 +0x38 [0x01e52a78]，case 4 则在 `NetStateModel$$SetState` [0x023e2604] 中通过该指针写入。+0x38 的唯一写入点是 `CreateSelectStateModel` [0x01e4bb08]，它构造一个 `BattleRecruitmentStateModel`，用于玩家招募对战时的状态 3 或 17（`stateModelType` 为 0；按 A 则传入 1，并构造一个 `BattleJoinStateModel`). `UnionStateController` 每个 `UnionRoomManager` (`UnionRoomManager$$SetUp`, `.ctor` 只构造一次，地址为 0x01e4d01c），连接对战会保留两者（`EvDataManager$$UpdateStart` -> `UnionRoomManager$$ReturnBattle` [0x01b02a78]，没有构造函数）。每次进入都会构造一个新的 `UnionRoomManager`: `EvDataManager$$EvCmdUnionProc` [0x01b35f70] 在传送进房间之前，将其添加到一个 `new GameObject("UnionRoomManager")` [0x01b36090] 中，且没有 `DontDestroyOnLoad`. `UnionRoomManager$$Init` [0x01e49e40] 将区域 {484, 491, 492, 493}（`UNION`, `UNION01` 至 `UNION03`）传给 `NetUseManager.SetEnableZone` [0x026cfca0]，它订阅 `FieldManager` 的区域变更事件；`NetUseManager.OnZoneChange` [0x026cfef0] 在首次进入列表外区域时调用 `Object.Destroy(gameObject)` [0x026d00f0]。离开（`LeaveUnion` [0x01e4e300]，其协程在 [0x01e560e0] 设置转换区域）就是这种变更，因此 `UnionRoomManager$$OnDestroy` [0x01e4c540] 会运行并调用 `Clear`。所以每次进入时，招募模型都从空值开始。如果主机玩家在本次进入期间还未招募过对战，收到 0x08 就会通过空指针写入：接收器不检查空值，直接将空模型传给 `BattleRecruitmentStateModel$$ChangeBattleRecruitmentState` [0x01d2aab0]；其中 case 4 用它尾调用 `NetStateModel$$SetState` [0x023e25f0]，随后 `str x2, [x20, #0x18]!` [0x023e2604] 向地址 0x18 写入。此构建没有在该路径上生成 IL2CPP 空值检查，映像也未导入 `nn::os::SetUserExceptionHandler`.

流程表中的 0x08 一行，是在已经招募对战的主机上测得的。如果 0x08 使用了客户端已用过的序列 id，就会被可靠窗口丢弃（[Pia 页面](pia.md#what-the-receiver-discards-in-silence)）；发往尚未招募的搭话主机的 22 条消息，所用 id 已被客户端自身的一条 0x64 回答占用，因此没有一条到达空指针路径。

绝不要发送 0x08，除非主机自身的 0x04 表明状态为 3，并且带有 `isRecruiment` 1.

### 地下大洞窟

地下大洞窟在场景 id 12608 下广播相同的 `local_communication_id`；同一会话命令行可以建立关联，不带加入记录（`--room-walk 0`）。站点到来时，`UgNetworkManager` 发送：

| id | 类 | 字节数 | 内容 |
| --- | --- | --- | --- |
| 0x17 | `NetZoneData` | 16 | `Vector3 pos`, `int zoneID`（捕获中为 519） |
| 0x42 | `NetPlayerNameData` | 28 | 13 个 UTF-16 字符，byte genderid、byte languageId（3，法语） |
| 0x50 | `NetKousekiCount` | 4 | `int Value` |
| 0x41 | `NetSecretBaseInfo` | 16 | 在秘密基地内（区域 633）代替 0x17：`Vector3 pos`, `int zoneID`，位于上一层的入口（519） |

一条 `NetUgJoinData`（0x16，18 字节：`byte avatarId, colorId; short zoneID, InitRotY; Vector3 InitPos`）若指定玩家所在区域，就会在玩家身旁放置一个角色：`OnReceiveJoinData` [1.3.0 main 0x01f7bd80] 请求该角色的 `NetCharacterStateData` 和 `NetNaminoriData`（0x55，一个 4 字节 bool），主机则每 0.41 s 向它发送 `NetPosData`。位置使用与房间相同的编码（`--ug-join --room-walk-steps N`).

`UgNetworkManager$$OnReceiveRequestData` [1.3.0 main 0x01f7c050] 会回答对 0x01、0x04、0x18、0x19 `NetDigData`、0x54、0x55 和 0x61 的请求：

| 请求项 | 字节数 | 内容 |
| --- | --- | --- |
| 0x18 `NetSecretBaseData` | 616 | 玩家自身的 `UgSecretBase`；当其 `zoneID` 为 0 时不发送任何内容 |
| 0x54 `NetSecretBaseUpdate` | 616 | 相同的 616 字节 |
| 0x61 `NetDigTableData` | 8 | 八个挖掘化石 id，`01 06 04 02 05 03 00 07` |

在主机窗口尚未承载任何数据前，以序列号 1 发送的请求未得到回答。请求其它任何 id 都不会触发响应（已试过 0x29 和 0x42）。

0x61 是 `UgFieldManager.ugDigGroupList`，一个 `Guid.NewGuid()` 类型的 0..7 排列（`UgStationID_to_DigFossilIDList$$Init` [0x02031830]）；封送器 [0x002498c0] 复制元素 0 至 7，不带长度前缀，元素不足时抛出异常。只有自身表已就绪，主机才回答 0x61 请求（`UgNetworkManager.IsDigTableReady`，+0xA8，在 0x01f7c440 检查）。

`UgNetworkManager$$OnSessionEvent` [0x01f77510] 根据 `SessionEventType` 分支处理（字节表 0x03db8970）：

| 事件 | 目标 | 效果 |
| --- | --- | --- |
| 1 `JoinIn_Mine` | 0x01f77588 | 主机端：设置标志 [0x01f7763c]，`DeleteAllDigPoints`, `CreateDigPoints(MyStationIndex)`；非主机端：`NetRequestData{0x61}` 发给所有人 [0x01f77738]，标志保持为 0 |
| 2 `JoinIn_OtherPlayer` | 0x01f776bc | `SendOnJoinNewPlayer` |
| 3 `ChangeHost_Mine` | 0x01f776d4 | 标志为 0 时将其设置 [0x01f77740]，不生成新表 |
| 4, 5 | 0x01f776dc | 无操作 |
| 6 `Leave_OtherPlayer` | 0x01f776ec | `OnLeaveOtherPlayer` |
| 7, 8, 9 | 0x01f77574 | `OnCrash` |

`UgNetworkManager$$OnReceiveDigTableData` [0x01f7dad0] 会采用标志为 0 时收到的第一条 0x61，无论来自哪个站点，也无论在自身的 `JoinIn_Mine` 之前还是之后：它只检查标志 [0x01f7db0c] 和类，将数组未经检查就保存为 `ugDigGroupList` [0x01f7db94]，重建挖掘点 [0x01cfd6d0、0x01cfdab0] 并设置标志。对 +0xA8 的三个写入点都写入 1，因此之后所有 0x61 都被忽略。公共分派逻辑（`SessionManager$$OnReceivePacket` `0x1df8ac0`）从不查询 `INetData.FromStationIndex`.

`CreateDigPoints` 读取元素 `[MyStationIndex]` [0x01cfdc7c]（8 或更大时抛出异常），找到具有该 `UgDigFossilePosGroup` 的 `ID` (`List.Find`，地址为 0x01cfdcd8），再读取它的 `Grids`，位置在 `CreateDigPointModel` [0x01cfe470]，不检查空值。在 1.3.0 的 `ugdata` 资源包中，35 个区域（508 至 542）各有八组，ID 为 0 至 7，每组有 6 至 26 个格子。只应发送 0..7 的排列：更大的字节值会使主机发生故障。

每个 `UgFieldManager` 都会构造一个新的 `UgNetworkManager`，位于 `StartSession` [0x01cfebb0] 中（唯一的 `AddComponent`，0x01cfed54），并在 `OnDestroy` [0x01cff530] 中销毁，因此每个实例都会重新采用一张表。没有场景放置这两个管理器中的任何一个：在 1.3.0 RomFS 的 14052 个资源包及根文件内，53861 个 MonoBehaviour 中，没有一个以 `UnionRoomManager` 或 `UgNetworkManager` 作为脚本。两者只存在于 `globalgamemanagers.assets` 的脚本表中，而没有资源包引用它。

0x29 `NetDigGroupIdData` 与 0x61 共用结构体和方法。只有 `NetDataParser` 的构造函数 [0x0224a420] 引用它：没有任何代码发送它，`UgNetworkManager$$OnReceiveData` [0x01f7a880]（22 个 id）也没有对应分支。

`bin/bdsp_connect.py --inject-file PATH` 会以可靠方式发送文件中每个新的 `ID:HEX` 行。

### 球壳

主机通过“球壳装饰”招募（状态字节为 7）。它发送 `NetDataTransitionData{7, 0}`，进入状态 21（`NOW_BALL_DECORATION`），再将自身 143 字节的 `NetDataAttachSealNetData` 作为 116 字节的 zlib 流发送（实测在 1.8 s 后发送）。没有回答时，它显示“有人结束了通信”，并返回房间；唯一一次实测等待时间为 45 s，尚未定位计时器。用客户端自身的 143 字节（`bin/bdsp_connect.py --answer-with 0x15:FILE`）回答后，它会应用这些数据（`BallDecoMatching$$ReceiveBallDecoData`，见下文），然后返回房间，状态字节为 0；实测这一返回过程不到五秒。应通过独立任务发送回答：若在接收器内部发送，它所等待的 ack 将始终无法被读取。

在 1.3.0 映像中，`BallDecoMatching$$ReceiveBallDecoData` (`0x021ca5e0`）会在主机发出自身设计（第一个贴有贴纸的槽位）后运行。它写入 99 个球壳槽位中第一个没有贴纸的槽位（`0x021ca674`）；若所有槽位都有贴纸，则不写入。`BallDecoWork$$CopyTradeCapsuleData` (`0x01f23eb0`，基础版本游戏中不存在）清空该槽位，包括关联的宝可梦，将 `Is3DEditMode` 和 `IsAppliedTemplate` 保存为 `byte == 1`，并遍历 `affixSealCount` 个贴纸：

```
if SaveSealData[id].Count >= 1:  place it at (x, y, z) / 100, then SubSealCount(id, 1)
else:                            drop it
```

玩家球壳上的贴纸在取下前不计入库存（`CapsuleInfo$$RemoveAffixSeal` `0x01e940d0` 调用 `BallDecoWork$$ReturnSealCount`）。没有库存时不写入任何内容；槽位紧凑保存实际贴上的贴纸。至少贴上一张且没有任何贴纸被丢弃时，结果为 true，并由此选择结束消息（`0x021c9f80`): `DLP_net_union_room_090` 为 true 时使用 `_114`，否则使用“仅贴上了你拥有的贴纸”）。数量超过 20 或贴纸 id 达到 200 及以上时，会访问数组边界之外（`0x01f24254`, `0x0238b7b0`）并抛出异常。

位置以球壳半径的百分之一为单位，两种模式下表面的向量长度都为 100。“有贴纸”的判定是 `AffixSealCount != 0` (`0x01e93630`）。3D 模式在每张贴纸的实际位置绘制。2D 模式（`Capsule2DViewController$$UpdateGridCells`, `0x01e90de0`）只在网格单元的 `BallDecoWork$$Convert2DPosition` (`0x01f24da0`）处绘制贴纸：半径为 1，正面（+z）的行列间隔为 28 度，背面为 25 度，每个分量四舍五入到 0.01。

`Capsule2DViewController$$Initialize` (`0x01e909b0`）获取网格根节点的 `Capsule2DGridCell` 子节点，以中间那个作为中心（+0x78），以根节点 `GridLayoutGroup` 的单元大小加间距作为步长，并为每个单元赋予 `GridPosition` = 它相对中心的偏移除以步长后取整（`0x01e90c48`); `Capsule2DGridCell$$Setup` (`0x01e905e0`）将 `Convert2DPosition(GridPosition, isFront)` 保存到 +0x30。1.3.0 资源包 `/Data/StreamingAssets/AssetAssistant/UIs/ui/uiresidentwindow` 包含三个 `Capsule2DViewController`，每个根节点 `Grid` 都有一个 `GridLayoutGroup` {单元 72x72，间距 3x3，固定 7 列}，覆盖 37 个单元和 12 个角落占位项。正反两面的网格都是 7 × 7 正方形去掉 `(|x|, |y|)`，位于 `{(3, 2), (2, 3), (3, 3)}`:

```
row  3   columns -1..1
row  2   columns -2..2
row  1   columns -3..3
row  0   columns -3..3
row -1   columns -3..3
row -2   columns -2..2
row -3   columns -1..1
```

主机自身的 2D 球壳将贴纸放在正面单元上。不落在网格上的 2D 设计会占用一个标记为已装饰的槽位，却不绘制任何内容；正面单元上的贴纸在有库存时会被绘制。

这些网格位置在零售版本的缩放比例下仍成立。`Initialize` 将世界空间偏移（`Transform$$get_position`, `0x01e90bd0`）除以局部步长，两轴都是 75（`fdiv` `0x01e90c10`）。向上直到根节点 `Seal` 或 `SealTemplate` 的所有祖先节点，其局部缩放均为 1；根节点 `Canvas` 是屏幕空间叠加层，其 `CanvasScaler` 按宽度从 1280 × 720 进行缩放，而 `Window` 动画器仅绑定平移。因子 `Screen.width / 1280` 为 1：1.3.0 的 `/Data/rawsettings` 在 +0x1c 处的 u32 为 0，使默认分辨率开关 `0x006062e8` 在底座和掌机模式下都保持 1280 × 720（1 跟随操作模式，2 跟随性能模式，3 同时跟随两者），且没有托管代码调用 `SetResolution` 或任何 `Screen` setter。

`Screen.width` 是唯一原生屏幕对象 +0x68 处的 int（`0x04efe760`），通过虚表槽位 0xa8 读取（`0x002c2c24`）。有三处写入：构造函数 `0x002c257c`（1280 × 720）、唯一一次启动时的 `SetMode(0)` `0x002c2858` 使用 `0x006062e8` 的值，以及 `SetResolution` `0x002c2888`，后者仅由操作模式和性能模式处理器 `0x002c2a1c` 与 `0x002c2af0` 调用，并且只在 rawsettings +0x1c 非零时调用。此路径不读取 `globalgamemanagers` 中的玩家设置；托管的 `Screen.SetResolution` 只将参数保存到 `[obj+8]`，不改变任何内容。
