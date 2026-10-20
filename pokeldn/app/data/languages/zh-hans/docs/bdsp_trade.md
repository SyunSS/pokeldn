---
title: BDSP 交换
parent: Brilliant Diamond and Shining Pearl
nav_order: 3
---

# BDSP 交换

零售版《明亮珍珠》可以与 pokeldn 创建的角色交换，接收 pokeldn 组装的宝可梦，并写入存档。搭话与问候流程见 [游戏协议](bdsp_protocol.md).

## 消息顺序

```
NetDataTransitionData{transitionType: 18}     entering the trade
NetDataTradeTranerData        32 B            who they are
NetTradePokeData             328 B            the Pokemon
NetDataTradePokeCheckOkData    1 B, value 1   "yours is fine"
NetDataTradeReadyOkData        2 B            the last message before the exchange
```

每条消息都用客户端自身的一条同类消息回答。

主机唯一实际生效的 check-ok 发送方是 `TradeSelectPokeModel.b__54_2` [1.3.0 main 0x1c28520]，即 `onDecide` 的 `BoxWindow$$Open(otherName, msgLangId, onSelected, onDecide, onConfirm, onComplete, onCancelSelect, ...)`（lambda 表达式 `b__54_1` 至 `b__54_5`）。它将自身检查状态（+0x80）设为 6，向 `{isCheckOk: 1}` 发送 `tradeTargetIndex`（+0x48），并将 `isWaitingOK`（+0x7b）设为 1，将 `isWaitingSelect`（+0x7c）设为 0 [0x1c285a4]。`isCheckOk` 始终为 1：主机从不通过此消息拒绝宝可梦（`SendTradePokeCheckOk` [0x1c27cb0] 没有调用方）。`BoxWindow$$OnTradeContextMenu` 调用 `onDecide` [0x212e99c]，随后将盒子的交换阶段加一 [0x212e9dc]。

`TradeSelectPokeModel$$PokeSelectWait` [0x1c26070] 在盒子阶段超过 2，且已接收（+0x78）和自身已选择（+0x79）标志都被设置后，显示对方的宝可梦；没有任何逻辑检查这只宝可梦。`TradePokeCheckOkWait` [0x1c25f50] 在两个检查状态（自身 +0x80、对方 +0x84）都为 6 时继续。若可靠窗口确认了宝可梦却未交付它，玩家会停在“正在等待回复”，且不出现错误（[Pia 层](pia.md#what-the-receiver-discards-in-silence)).

本地无线模式下，对玩家自身所选宝可梦只检查存档中的非法标志（`CoreParam$$GetDprIllegalFlag`); `NetworkManager$$RequestValidateTrade` 仅在 `UnionFrontDeskStateController.isGlobal` 已设置时运行。

`RequestValidateTrade` [0x02251cb0] 不在客户端执行任何检查。它将每只宝可梦的 `CoreParam` 复制到 0x148 字节的请求中，并发送给任天堂的验证服务器（`IlcaNetServerValidate.CheckRequestAutoAsync` [0x027318c0]）；回复为一个 `ValidateResultID`（None 无、InvalidData 数据无效、SignatureError 签名错误、ProcessError 处理错误），签名或处理错误会弹出错误对话框。`SS_box_182` 是玩家自身宝可梦被标记时选取的消息，文本为“由于你的宝可梦存在问题，无法交换宝可梦。”（法语文本含义为“你的宝可梦存在问题，无法进行任何交换。”）；`SS_box_181` 对伙伴的宝可梦给出相同提示。

## 交换状态机

`UnionTradeManager.currentState`（+0x88；1.3.0 中为 +0x80）是 `TradeFlowState {NONE 0, SELECT_WINDOW 1, SECURIY_TRADE 2, PLAY_DEMO 3, END 4}`:

```
UnionTradeManager$$RecivePokeData          0x1dd2800   currentState == SELECT_WINDOW only
UnionTradeManager$$SetTargetTranerParam    0x1dd2130   TargetTranerParam{uint id, string name}
UnionTradeManager$$ReciveTradeReadyOkData  0x1dd2a70   routed on the same field
```

只有在 SELECT_WINDOW 中才会接收宝可梦，存入 `tradeSelectModel.targetPokemonParam`，并设置 `isRecivePokeParam`。一条 `NetDataTradeReadyOkData`（0x21）在 SELECT_WINDOW 中会传给 `TradeSelectPokeModel$$ReciveReadyOk` ([盒子阶段](#box-phases-and-the-messages-that-reset-a-round)）；在 SECURIY_TRADE 中传给 `TradeSecurityController$$ReciveState`（1.3.0 [0x1c34290] 中，仅在控制器的 `GetCurrentState` 非零时如此；为 0 时则调用 `SettingSecurityControllerParam` [0x1c343f4] 并丢弃消息），在其它状态下一律丢弃。

`ReciveReadyOk` [1.3.0 0x1c27d40] 将消息的第二个字节 `tradeState` 复制到 `targetTradeState`（+0x78；1.3.0 中为 +0x84，收到 check-ok 也会在此写入 6）；`isTradeOk` 从不被读取。`UnionTradeManager.d__24` 等待 `myTradeState`（+0x74，由玩家的 `MyReadyOk` 设置）以及 `targetTradeState` 都为 2（`WAIT`），然后将 `currentState` 设为 SECURIY_TRADE，清除选择模型，并发送自身的 0x21，其中 `tradeState` 为 0。只有对方的 0x21 才能使主机离开 SELECT_WINDOW。

### 盒子阶段与重置当前轮次的消息

`BoxWindow.NetTradePhase`:

```
None 0, WaitSave 1, PlayerSelecting 2, WaitSend 3, OtherPokeConfirm 4, WaitOtherDecide 5,
LastConfirm 6, WaitTrading 7, Complete 8, WaitClose 9, CancelOther 10, Error 11
```

`WaitSave` 不写入任何内容：`BoxWindow.d__203` 执行倒计时，时长为 `FieldCommonParam[0xEB]` × 0.001 秒，比较基准为 `Time.deltaTime`.

重置由 `TradeSelectPokeModel$$ReciveReturnSelectPoke` [1.3.0 main 0x1c27f00] 执行。对于 `isReturnSelect` 为 1 的情况，它回答 `NetDataReturnSelectData{0}` [0x1c27f48]，因此主机会对每条 `{1}` 用一条 `{0}` 回答。无论哪种情况，它都会清除 `isWaitingOK`/`isWaitingSelect` [0x1c27fb0]、`isRecivePokeParam`/`isSendPokeParam` [0x1c2803c] 和两个交换状态 [0x1c28040]，并将 `UnionWork` 的静态 +0x50（`boxState`）设为 6，`CANCEL_SELECT` [0x1c28030]。盒子阶段为 3 或更高，或没有盒子时，它随后调用 `CloseOverUIWindows` [0x1c28168]。

`BoxWindow$$UpdateNetworkTrade` [0x2121628] 取出并清除 `CANCEL_SELECT` [0x2121c64]：阶段为 2 时丢弃尚未确认的高亮选择；其它阶段 [0x21225b0] 则关闭窗口、将阶段设为 2，并显示 `SS_box_588`（“另一位玩家选择取消交换。”）。

| 来自对方的消息 | 盒子阶段 | 主机的操作 |
| --- | --- | --- |
| check-ok（0x46） | 没有盒子，或低于 6 | 对方检查状态（+0x84）= 6（`ReciveTradePokeCheckOk` 0x1c34630） |
| check-ok（0x46） | 6 `LastConfirm` 或更高 | 执行与 `{1}` [0x1c34718] 相同的重置，随后 `securityController?.ResetTradeState()` |
| ready-ok（0x21），SELECT_WINDOW | 锁存标志 +0x71 已设置 | 丢弃 [0x1c342e4] |
| ready-ok（0x21），SELECT_WINDOW | 盒子存在，阶段不高于 5 | 执行与 `{1}` [0x1c3440c] 相同的重置，随后 `ResetTradeState()` |
| ready-ok（0x21），SELECT_WINDOW | 阶段为 6 或更高，或没有盒子 | `ReciveReadyOk`，锁存标志 +0x71 = 1 [0x1c3435c] |
| return-select（0x45），任一取值 | 2 `PlayerSelecting` | 重置；盒子丢弃尚未确认的高亮选择 |
| return-select（0x45），任一取值 | 3 或更高 | 重置；盒子返回阶段 2，并显示 `SS_box_588` |
| return-select（0x45） | 任意阶段，处于 PLAY_DEMO 时 | 不重置；[0x1c345c0] 清除 `targetDemoPokemonParam` |

锁存标志（+0x71，`k__BackingField`）由 `Init`, `WaitBoxWindowComplete`, `Cancel`, `RecivePokeData` 和 `ReciveCancelData` 清除；其 setter [0x1c33040] 没有调用方。在最后一次确认后盒子关闭时，主机会发送自身的 ready-ok（`b__54_4` -> `BoxCloseComplete` -> `MyReadyOk` 0x1c26d90 -> `SendReadyOk` 0x1c26f14）。

主机自身的退出操作，`onCancelSelect` (`b__54_5` 0x1c28620），会将盒子设为阶段 2（`ToNextPhase(box, 2)`；非零参数保存于 `[[box+0x390]+0x50]`，参数为 0 则加一），发送 `NetDataReturnSelectData{1}` [0x1c286a4]，并清除等待标志、宝可梦标志和两个交换状态，但不设置 `CANCEL_SELECT`。随后它等待一条新的 `NetTradePokeData`（唯一设置 `isRecivePokeParam` 的位置是 `UnionTradeManager$$RecivePokeData`，位于 SELECT_WINDOW，适用于任意阶段 [0x1c33e9c]）；伙伴的 `{0}` 不会解除等待。

-
-
-

## 安全阶段

随后是 `TradeSecurityController` -> `CreateTradeStateModel` -> `TradeStateModel`，它负责存档：

```
TradeStateModel.TradeState
NONE 0, INIT 1, WAIT 2, SEND_POKE 3, WAIT_POKE 4,
SEND_READYOK 5, WAIT_READYOK 6, START_WRITE_SAVE 7, WRITEING_SAVE 8
```

`TradeStateModel$$InitState` 首先调用 `PlayerSave`。`WriteSaveData` 尾调用 `ReplacePoke`；两者都只能作为已注册委托被调用。`FirstSave` 在写入之前启用断线惩罚。

在安全阶段，宝可梦消息只用于触发下一步。`UnionRoomManager$$RecivePokeData` 在 SECURIY_TRADE 中丢弃已解码的宝可梦，并调用 `SetSecurityTradeParam()`，后者将 `manager.targetPokemonParam`（+0x48，玩家在全屏视图确认时设置）传给安全控制器。玩家确认之前它为空，WAIT_POKE 永远不会结束。

### 谁来主导：较稀有的宝可梦

`CreateTradeStateModel` [1.3.0 main.bin 0x1c24620] 为两种角色都构造一个 `TradeParentStateModel`（`TradeChildStateModel` 的重写方法只有 `ret`）。角色保存在 `tradeParent`（+0x94），`TradeParent {NONE 0, PARENT 1, CHILD 2}`，由 `TradeSecurityController$$CheckPokeRarity` [0x1c25060] 在对方宝可梦到达时（`UnionTradeManager$$SetSecurityTradeParam` [0x1c34750]）根据两种宝可梦的 `Dpr.SubContents.Utils$$GetPokeRarityNum` [0x1cbe560] 写入：

```
POKE_RARITY_VERY_RARE 3, POKE_RARITY_LEGEND_RARE 2, POKE_RARITY_SUB_LEGEND_RARE 1, anything else 0
mine > theirs   PARENT
mine < theirs   CHILD
equal           PARENT if isRecruiment (+0x38), else CHILD
species -1      no role set (to 0x1c25120)
```

`GetPokeRarityNum` 按顺序遍历三个静态 `MonsNo[]` 列表（0x1cbe614、0x1cbe698、0x1cbe71c；未找到时为 0x1cbe730），这些列表由 `Utils$$.cctor` [0x1cbe9a0] 从 1.3.0 的 `global-metadata.dat`:

| 静态字段 | 稀有度 | 元数据 | 种类 |
| --- | --- | --- | --- |
| `very_rare_monsno` +0x78 | 3 | `0x666aa6` | 151、251、385、386、489、490、491、492、493（幻之宝可梦） |
| `legend_rare_monsno` +0x80 | 2 | `0x666b06` | 150、249、250、382、383、384、483、484、487（封面传说的宝可梦） |
| `sub_legend_rare_monsno` +0x88 | 1 | `0x667c39` | 144, 145, 146, 243, 244, 245, 377-381, 480, 481, 482, 485, 486, 488 |

向提供梦幻的主机提供帝牙卢卡，会让主机成为 PARENT。

`TradeParentStateModel$$StateProc` [0x1c23350]，表位于 0x3d80f2f：

```
2 WAIT            targetState == WAIT                    -> 3
3 SEND_POKE       waitRndTime runs out; SendPokeData     -> 4
4 WAIT_POKE       targetPokeData non-null                -> 5
5 SEND_READYOK    PARENT only: send own state            -> 6
6 WAIT_READYOK    targetIsTradeReadyOk; PARENT sends     -> 7
7 START_WRITE_SAVE  WriteSaveData                        -> 8
8 WRITEING_SAVE     CheckReplacePokeData                 -> 10
```

`TradeSecurityController$$ReciveState` [0x1c24f10] 按主机自身状态进行分支处理，表位于 0x3d80f39：

```
1 INIT            -> WAIT, send own state
3 SEND_POKE       send own state
5 SEND_READYOK    CHILD only: peer 5 -> send, go to 6; peer 6 -> send, go to 6, set targetIsTradeReadyOk
6 WAIT_READYOK    set targetIsTradeReadyOk
every case        targetState = the peer's byte
```

`TradeStateModel$$SetTragetPokeData` [0x1c24d70] 最后发送主机状态 WAIT_POKE。CHILD 主机随后进入 SEND_READYOK，并静默等待对方状态为 5 或 6，因此客户端若回显 WAIT_POKE，就会使其死锁。`room.mirror_trade_state` 用 SEND_READYOK 回答 WAIT_POKE，而 `ReciveState` 在两种角色下都会接受它：CHILD 处于自身的 SEND_READYOK（case 5），PARENT 处于 WAIT_READYOK（case 6）。`tests/test_bdsp_trade_states.py` 将这两个函数作为模型，在随机延迟下对照客户端策略运行。

每个可靠序列 id 只发送一条消息：`their_ack_id` 仅在主机确认后才前进，因此同一 id 下后续消息会被当成重传并丢弃。`bdsp_connect` 维护自身的计数器。

## 完成交换

主机作为招募方且为 PARENT 时，安全状态依次如下（先列主机状态，再列客户端回答）：

```
their READY-OK {isTradeOk 0, tradeState 2}  ->  the client's READY-OK
INIT          ->  WAIT
WAIT          ->  WAIT
SEND_POKE     ->  SEND_POKE, and its Pokemon
WAIT_POKE     ->  WAIT_POKE
SEND_READYOK  ->  SEND_READYOK
WAIT_READYOK  ->  SEND_READYOK
```

WAIT_READYOK 之后，主机写入存档、播放动画，并运行 `ReplacePoke`，只发送 `NetCharacterStateData`。离开 WAIT_READYOK 还需要对方再发一条消息。无论角色为何，主机进入 WAIT_READYOK 时都会报告 SEND_READYOK（PARENT 来自 `StateProc` 的 case 5，CHILD 来自 `ReciveState` 的 case 5），因此客户端对此报告的回答会在该状态内到达。在两种角色的 25 次零售版本交换中，25 次主机的下一条可靠消息都在 SEND_READYOK 后 0.16 至 0.24 s 到达，早于任何重复发送；PARENT 的 WAIT_READYOK 报告则在其后 0.02 至 0.06 s 到达（19 次均如此）。客户端仅在主机 SEND_READYOK 之前每秒重复一次自身状态（`room.repeats_trade_state`）：在此之前，CHILD 的 SEND_READYOK 只有在消息于该状态内到达时才会结束。站点绝不能在这个窗口内离开：断开会使主机停在 `FirstSave` 与 `SecondSave` 之间。主机作为房间加入方、pokeldn 作为主机端时，流程也相同。

从主机的 `tradeState` 6 开始计时，零售版 BDSP 加入 `bin/bdsp_host.py`：动画约在 2.7 s 开始，收到的宝可梦约在 18.6 s 出现，玩家约在 29 s 恢复控制（手动按键标记，最多可能晚 2 s）。

完成交换时不会以任何消息收尾。客户端在回答主机 SEND_READYOK 时计为完成；下一轮从主机的下一条 `NetTradePokeData`.

`NetDataReturnSelectData`（0x45），`45 00 01 00` (`{isReturnSelect: 0}`），是主机对重置的回答（[盒子阶段](#box-phases-and-the-messages-that-reset-a-round)）：一条 `{1}`，或在盒子阶段不高于 5 时到达选择窗口的 0x21，都会经相同路径 [0x1c3440c] 重置，并显示 `SS_box_588`。它不要求回答（以 `{1}` 回答会触发一条 `{0}`，并重置已经清空的轮次）。在捕获的 26 次交换中，客户端都在动画期间每秒重复自身状态，26 次均有一条 `{0}` 在客户端某条 0x21 后 25 至 300 ms 到达，玩家也看到了 `SS_box_588`；若在主机 SEND_READYOK 后不再发送 0x21，则在两种角色的 5 次零售版本交换中（每种角色均有两次交换排在同一次关联内），主机都未发送 0x45，也未显示取消。`TradeSelectPokeModel$$SendReturnSelectPoke` [0x01c27c20] 构造该消息（`isReturnSelect` = 参数的逻辑非，目标为 `tradeTargetIndex` +0x48）；它没有直接的 `bl` 调用方。

交换可以在一次关联内连续进行，每次都从选择窗口循环开始，无须再次搭话或发送训练家记录：使用 `bin/bdsp_connect.py` 连续完成了三次交换（每次之后都返回盒子界面），使用 `bin/bdsp_host.py` 作为主机端时完成了两次。`TradeStateModel$$ReturnTradePokeSelectWindow` [0x01c29590] 运行 `PlayerSave`，然后运行模型 +0x80 处的回调；尚未追踪其调用方。第二次交换会读回主机保存的内容。若玩家正在选择时（盒子阶段不高于 5）收到状态为 SEND_READYOK（5）的 0x21，就会重置当前轮次，因此主机 SEND_READYOK 之后不再重复发送。

## 宝可梦

`NetTradePokeData` 携带 328 字节，即第八世代的 `SIZE_STORED`：一个加密 PB8，其格式见 [剑／盾页面](swsh_protocol.md#the-pk8) (`pokeldn/gen8.py`; `pokeldn/bdsp/pokemon.py` 的 PB8 视图）。0x06 处的校验和对解密后的主体求和，因此将构造好的宝可梦重新解码即可验证，但无法发现区块顺序错误，因为 16 位字求和无法识别顺序。

`NetDataTradeTranerData` 是经过封送的结构体 `string tranerName; uint tranerId; byte cassetVersion; byte langId` ([帧封装](bdsp_protocol.md#framing)):

```
0x00  26  tranerName, UTF-16LE, NUL-terminated
0x1a   4  tranerId, the full 32-bit id, secret id in its high half
0x1e   1  cassetVersion, the save's version (49)
0x1f   1  langId, the save's language (3)
```

主机在交换打开时、发送任何宝可梦之前就会发送它，因此它标识存档的训练家；为接收玩家定制的礼物会读取它（`room.traner_trainer`, [为接收玩家定制](gift_simulated.md#made-for-the-receiving-player)）。它不携带性别，会话中其它消息也不指明性别：只有玩家使用过联盟交谊厅可选的外观柜台后，加入消息的化身才会与存档性别一致；在此之前，存档首次连接时会获得随机性别的化身（[模型](bdsp_protocol.md#the-model)）。主机提供的宝可梦会指出该性别：存档是其初训家时使用 OT 性别，否则使用当前训练家性别（[主机如何处理收到的宝可梦](#what-the-console-does-to-a-received-pokemon)).

交换界面根据这条记录显示伙伴名字；问候则使用 Pia 玩家名（[协议页面](bdsp_protocol.md#the-name-in-the-greeting)）：`UnionRoomManager$$SetNetData` [1.3.0 main.bin 0x1e51940] 的 0x24 分支从消息中取得全部四个字段，仅从 `GetGamerData(...).nameStringLanguage` 取得字体语言，将名字包装为 `MessageHelper$$SurroundFontTag`，再交给 `UnionTradeManager$$SetTargetTranerParam` [0x1c33330]。

名字终止符和 id 之间的十个字节是堆残留数据（`AllocHGlobal` 不清空缓冲区；0x14 处的字会变化）。`room.build_trade_traner` 逐字节携带主机自身的残留数据。

提供的宝可梦来自一只真实宝可梦，只修改指定字段（`pokemon.build_from`）；主机自身宝可梦的相遇数据、奖章、当前训练家记录和语言均为非零。

## 主机如何处理收到的宝可梦

初训家收回宝可梦时，有两个字节变化：`IsNicknamed`（0x08F 的位 7，IV32 的位 31）在名字不同于游戏语言对应的种类名时被设置，校验和也随之变化。名字字符串不变；种类名仍保持为种类名。

由其他训练家接收时，有十一个字节变化，而 `ot_name` 不受影响：

```
0x0A8..0x0B2   HandlingTrainerName, UTF-16LE
0x0C3          HandlingTrainerLanguage (3, French)
0x0C4          CurrentHandler, 0 -> 1
0x0C8          HandlingTrainerFriendship, 50
0x006..0x007   the checksum
```

0xC6（PKHeX 的 `HandlingTrainerID`，标注为“未使用？”）保持为零。PKHeX 的 `IsUntraded` (`Data[0xA8] == 0`）变为 false。

`TradeStateModel$$ReplacePoke` [1.3.0 main 0x1c29120] 执行这些修改。它根据存档的 `OwnerInfo` `{trainerId, sex, langID, name}` 构造一个 `DPData.MYSTATUS` (`PlayerWork$$get_playerStatus`，构造函数为 [0x24a1b30]）：包含 id、`sex ^ 1`, `region_code` 以及名字。状态中的 `sex` 对男孩为 true，正如 `_GET_MY_SEX` 读取时所用的含义。它将 `OwnerInfo` 传给 `CoreParam$$UpdateOwnerInfo` [0x2495920]，后者将宝可梦的 OT 性别、32 位 id 和 OT 名字与之比较：

-
-

每次由其他训练家接收时都会写入 0xC2；上述测量中发现它原本已包含接收方性别。不记录当前训练家 id 或版本。GTS（`GMSSceneDataModel$$OnReceivePokeData`）、游戏内交换（`LocalKoukan$$CreateTradePokeParam`）、神秘礼物（`MysteryGiftWork$$CreatePokemonParam`）以及 `RenkeiData$$Get_1`/`Get_2` 都根据存档构造相同的 `OwnerInfo`。`UpdateOwnerInfo` 是游戏中唯一写入当前训练家性别的位置。游戏不含任何 Pokémon HOME 代码：从 HOME 传入的宝可梦由 HOME 写入。

### 重复检测

`PokeDupeChecker`（1.3.0 新增）会给重复的宝可梦设置非法标志。该标志位于解密后 PB8 字节 0x52 的位 0（区块 A + 0x4A，`CoreDataBlockA.set_dpr_illegal_flag` `0x027bb040`）；PKHeX 将其读取为 `PB8.IsDprIllegal`。被标记的宝可梦不能再交换出去（“你的宝可梦存在问题，无法进行任何交换。”）。

`UpdateIllegalFlagAll` [`0x01de5860`] 按顺序对同行队伍、盒子 1 至 40 以及寄放屋执行 `CheckDuplicate` [`0x01de59d0`]。当宝可梦来源游戏为《晶灿钻石》或《明亮珍珠》（`version & ~1 == 0x30`）、不是蛋、标志未设置、也不是游戏内交换宝可梦时，才参与检查（`IsLocalKoukanPokemonParam` [`0x01de66d0`]：相遇地点为 30001，且训练家 id、加密常量和性格与一个 `LocalKoukanData` 条目匹配）。每只宝可梦都与此前每只进行比较；第一个副本保持未标记，之后每个副本都被标记。

`IsDuplicatedPokemonParam` [`0x01de62f0`] 要求以下所有项目都匹配：

| 字段 | 访问器 | PB8 偏移 |
| --- | --- | --- |
| 加密常量 | `GetPersonalRnd` | 0x00 |
| PID | `GetColorRnd` | 0x1C |
| 训练家 id（TID16、SID16） | `GetID` | 0x0C |
| 性格 | `GetSeikaku` | 0x20 |
| 六项个体值 | `GetTalentHp` .. | 0x8C |

铁面忍者（291）和脱壳忍者（292）这一对永远不会被判为重复。不比较种类、形态、昵称或 OT 名字。

`UpdateIllegalSpecialTraining` [`0x01de6830`] 会标记等级不高于 99、且设置了任何极限特训位的《晶灿钻石》或《明亮珍珠》宝可梦。

检查在加载存档时（`PlayerWork.OnPostLoad_NeedMD`）、交换盒子中每次选择时（`TradeSelectPokeModel` [`0x01c28310`]）以及奇迹交换保存之前（`Dpr.GMS`）运行；收到交换宝可梦时不运行任何检查。本地交换中选择被标记的宝可梦，会将 `UnionWork.boxState` 设为 `INVALID_DATA`，盒子便会拒绝它；在线交换则会将所选宝可梦发送给 `NetworkManager.RequestValidateTrade`。`ClearIllegalFlagAll` 没有调用方，因此标志永远不会被清除。

绝不要提供这样的《晶灿钻石》或《明亮珍珠》记录：其加密常量、PID、训练家 id、性格和个体值全部与接收方存档中某只宝可梦一致。`bin/bdsp_host.py --fresh-pid` 会生成新的加密常量和 PID，并保留异色状态；以这种方式交换到已保存原始宝可梦的存档中的记录，没有被标记。

## 断线惩罚

站点若在 `FirstSave` 与 `SecondSave` 之间断开，会使惩罚保持启用，主机会以“目前无法进行网络交换”为由拒绝新的本地交换，直到惩罚清除：

```
TradeStateModel$$FirstSave    0x1cd4fc0   SetPenartyCounter(30); SetPenartyTime(now)
TradeStateModel$$SecondSave   0x1cd5030   SetPenartyCounter(0)
UnionFrontDeskStateController$$CheckPenarty  0x1fcc400   counter >= 1 AND not CheckDateTime()
```

完成交换会清除惩罚；出现惩罚意味着 `FirstSave` 已运行，而且主机已写入存档。`UnionWork$$CheckDateTime` [0x1dd3e30] 和 `SetPenartyTime` [0x1dd32d0] 使用不加权求和：

```
w8 = Year + Month + Day + Hour + Minute + Second
cset w0, mi            ... on  (stored + 30.0) < w8
```

总和每秒增加 1，在分钟或小时进位时下降 58（18:45:20 为 2125，19:20:00 为 2081）；只有 Day 持续向前增长。`Hour+Minute+Second` 的范围为 0..141，因此若在一小时接近结束时启用惩罚，等待就会延续到次日甚至更久。代码中没有固定持续时长。

绝不要通过修改主机时钟或系统设置来清除惩罚：BDSP 会检测到变化，并锁定基于时间的功能一天。将时钟调回去会恢复惩罚；只有 `SecondSave` 会将计数器清零。
