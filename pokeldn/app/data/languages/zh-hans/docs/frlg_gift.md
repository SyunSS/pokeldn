---
title: 神秘礼物
parent: FireRed and LeafGreen
nav_order: 2
---

# 神秘礼物

神秘礼物菜单无需宝可梦中心。在神奇卡片画面中，主机可以接收神奇卡片、投递脚本、神奇新闻、来访的对战塔训练家，以及直接加入队伍的宝可梦。神秘事件虚拟机和原生 ARM 代码参见 [主机上运行的代码](frlg_rom.md).

## 会话

主机客户端启动时使用 `{CLI_RECV, MG_LINKID_CLIENT_SCRIPT}, {CLI_COPY_RECV}` [mystery_gift_scripts.c:15]，并执行收到的任意 `MysteryGiftClientCmd` 数组 [mystery_gift_client.c:87]。它支持完整操作码集，因此主机端可以驱动超出《火红》两个 ROM 服务端脚本范围的流程。

```
console joins  ->  SEND_PLAYER_IDS  ->  LinkPlayer block exchange  ->  one standby barrier
                                                                          |
  server -> CLIENT_SCRIPT (sClientScript_SendGameData, 32 B)
  client -> GAME_DATA     (MysteryGiftLinkGameData, 96 B)   -- validated, card flag compared
  server -> CLIENT_SCRIPT (sClientScript_SaveCard, 48 B)
  server -> CARD          (struct WonderCard, 332 B)
  server -> RAM_SCRIPT    (1024 B: the delivery bytecode, zero-padded)
  client -> READY_END     (1024 B)
                                                                          |
                                          close-link handshake  ->  disconnect
```

主机端发出一次 LinkPlayer 块请求，等待主机的有效数据块，发送自身的数据块，然后等待待机同步屏障。

### 成帧规则

大小 0 表示 1024：`MysteryGiftLink_InitSend` [mystery_gift_link.c:55] 将其展开为 `MG_LINK_BUFFER_SIZE`，而 `SVR_COPY_SAVED_RAM_SCRIPT` 从不设置 `ramScriptSize` [mystery_gift_server.c:275]，因此 RAM 脚本和 `CLI_SEND_READY_END` 都是完整的 1024 字节消息。CRC 覆盖填充后的缓冲区。

数据块节奏控制不带确认。`SEND_BLOCK_INIT` 会被忽略，除非接收端槽位为 `RECV_STATE_READY` [link_rfu_2.c:1146]；该状态只能由主机的 `MGL_ResetReceived` 恢复。父端自身的 `MGL_HasReceived` 标志立即置位 [link_rfu_2.c:1044]；四个 VBlank 的倒计时 [link_rfu_2.c:1220] 仅适用于子端数据块。`MysteryGiftTiming.inter_block_gap_frames` 为 36：主机模型在无丢失时每块最多需要 13 帧，达到 16 帧传输就会失败。丢失一个块会使主机永远等待。主机发送期间的停滞遵循 [镜像规则](frlg_link.md#row-one-of-the-parents-table-is-the-consoles-own-command-mirrored-back).

### 模块

位于 `pokeldn/frlg/gift/` 下，另有说明的除外：

| 文件 | 作用 |
| --- | --- |
| `mg_link.py` | 成帧：6 字节的 `{ident, crc, size}` 头部块 + 不超过 252 字节的分块 |
| `mg_script.py` | 客户端脚本汇编器、反编译工程的预制脚本、`MysteryGiftLinkGameData` 读取器 |
| `mg_server.py` | 服务端脚本解释器（`SVR_*`) |
| `host_mystery_gift.py` | 领队引擎：`tick()` → 父端 gSendCmd，`feed_child_slot()` ← 子端命令行 |
| `host_mg_app.py` | 基于主机端运行时的应用钩子 |
| `wonder_card.py` | 逐字节精确的时拉比与传说的三圣兽卡片／RAM 脚本构建器 |
| `stamp_rally.py` | 集章活动卡片、印章、激活包装脚本、投递脚本 |
| `gift_composer.py` | 动作定义、游标状态验证、RAM 脚本编译器 |
| `gift_registry.py` | 目录 |
| `gift_to_bin.py` | `.bin` 导出器，供外部第三世代神秘礼物工具使用 |
| `pokeldn/frlg/save/save_inject.py` | 存档注入，包含卡片、RAM 脚本和扇区校验和 |
| `bin/frlg_mg_host.py` | CLI |

## 运行

```
(them) Mystery Gift -> Wonder Cards (Recevoir) -> Friend (Ami), wait on the search screen
(you)  POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/frlg_mg_host.py --live --phy auto \
           --keys PROD_KEYS --gift beast-cutscene --flag-id 1005
(them) join the host when it appears; YES on the replace-card prompt if one shows
```

无线设备设置：[ESP32 无线设备](hardware_esp32.md). `bin/frlg_mg_host.py` 每次运行服务一台主机，并在其离开 LDN 后停止（[主机端实现](frlg_host.md)，关闭与清理）；另一台主机需要重新运行。`tests/test_mystery_gift_flow.py` 对数据块接收门控、`MGL_Receive` 和每帧一条客户端命令进行建模；`tests/test_mystery_gift_end_to_end.py` 另加入存在传输损伤的 Reliable／RFU 路径。

## 链路可承载的内容

22 条客户端指令 [include/mystery_gift_client.h:18] 中，有三条会执行代码：

| 指令 | 主机执行的操作 |
| --- | --- |
| `CLI_SAVE_RAM_SCRIPT` (17) | 存储场景脚本；下次与 NPC 互动时运行 |
| `CLI_RUN_MEVENT_SCRIPT` (15) | 运行神秘事件字节码脚本，这是第二个虚拟机，拥有独立的 17 操作码表 |
| `CLI_RUN_BUFFER_SCRIPT` (21) | `func = (void *)gDecompressionBuffer; func(¶m, gSaveBlock2Ptr, gSaveBlock1Ptr)`；执行最多 1024 字节的 ARM 代码，并传入两个存档块指针 |

## 唯一的 RAM 脚本槽位

主机只能持有神奇卡片或绑定的 RAM 脚本，不能同时持有两者。`ValidateSavedWonderCard` 检查卡片 CRC、`ValidateWonderCard`，然后检查 `ValidateRamScript` [mystery_gift.c:186]，后者要求 `magic == RAM_SCRIPT_MAGIC`、地图组与编号 `MAP_UNDEFINED`，以及 `objectId == 0xFF` [script.c:538]。场景通过 `GetRamScript(gSpecialVar_LastTalked, script)` [field_control_avatar.c:458] 运行 RAM 脚本，这要求提供交谈对象的坐标。`CLI_SAVE_RAM_SCRIPT` 调用 `InitRamScript_NoObjectEvent`（MAP_UNDEFINED，0xFF [script.c:578]）；神秘事件虚拟机的 `initramscript` 写入实际坐标。绑定脚本后，卡片仍保存在存档中且 CRC 正确，但菜单会隐藏它，`MysteryGift_LoadLinkGameData` 报告 `flagId` 为 0 [mystery_gift.c:349]（`HAS_NO_CARD`).

下一张神奇卡片会重新绑定槽位（`magic` 仍为 51，坐标为 0xFF），卡片便会重新显示；缓冲区脚本不发送卡片，也不改动槽位。在绑定脚本之上投递普通卡片，会重写 +0x32E0 处的卡片和 +0x361C 处的 RAM 脚本，两者位于同一存档扇区，SaveBlock2 不变；实测 SaveBlock1 的 15872 字节中有 564 字节发生变化。

槽位的校验和（`ramScript.checksum`，SaveBlock1 + 0x361C）为 `CalcCRC16WithTable`，计算范围为 `sizeof(RamScriptData)`，范围共 1000 字节：声明的 999 字节，加上一个填充字节，`InitRamScript` 会先将其清零 [script.c:500]。`CalculateRamScriptChecksum` 传入 `250 << 2` (`0x0806D43C` BPRE、`0x0806D5A0` BPRF）。所有回读的游戏写入槽位都带有覆盖 1000 字节的 CRC。仅覆盖 999 字节 CRC 的槽位，会在首次与其对象交谈时被 `GetRamScript` 清除 [script.c:526]。

## 礼物目录

`--gift NAME`; `--help` 列出标志 ID（1000..1019）。只以当前持有的卡片为准：相同 ID 表示“已持有此卡片”（`MysteryGift_CompareCardFlags`).

| 礼物 | 效果 |
| --- | --- |
| `beast-cutscene-share` | 可重复触发的传说的三圣兽过场；默认演示卡片 |
| `celebi` | 组合生成的 50 级时拉比卡片 |
| `porygon-tm-gift` | 多边兽卡片、皮皮场景，先给 TM29 精神强念，再给 TM46 小偷 |
| `solrock-stamp` / `lunatone-stamp` | 同一张集章活动卡片的两个部分 |
| `altering-cave` | 移植的官方变幻洞窟活动 |
| `wish-egg`, `pokepark-egg`, `pc-japan-egg` | 官方配信蛋；参见“配信蛋” |
| `event-pokemon` | 第三世代配信宝可梦，直接加入队伍；参见“活动宝可梦” |
| `starter-egg` | 九种最初的伙伴之一的蛋，由以下内容随机选择：`random` |
| `rare-berries` | 谜芝果、兰萨果和星桃果，每个阶段给一种 |
| `national-dex` | `EnableNationalPokedex`（special 367），除非 `IsNationalPokedexEnabled`（403）返回 1 |
| `nature-mint`, `pc-anywhere` 以及另外 42 种 | GB-Link Team 卡片；参见“GB-Link Team 卡片” |
| `battle-count-card` | 官方对战计数卡 |
| `visiting-trainer` | 以 ident 26 发送的对战塔训练家（仅火红） |
| `mystery-event-probe` | `givenationaldex; setstatus 42; checksum`，虚拟机自身的自检 |
| `mystery-event-celebi` | `givepokemon`：携带邮件的 30 级时拉比，直接加入队伍 |
| `mystery-event-npc` | `initramscript`：将场景脚本绑定到真新镇的胖男人 |
| `rng-seed-reader`, `rng-rate-probe`, `rng-shiny-hunt`, `rng-mon-hunt`, `rng-mon-hunt-both`, `rng-mon-hunt-log` | 参见 [随机数生成器](frlg_rng.md) |

已持有该卡片的主机只接收神秘事件礼物，不出现提示。

### 传说的三圣兽

配送员过场先给予兰萨果和枝荔果，再给予大师球，然后根据存档中最初的伙伴，开始一场与 65 级野生传说的三圣兽的对战：

| 最初的伙伴 | 三圣兽 |
| --- | --- |
| 妙蛙种子 | 水君 |
| 杰尼龟 | 炎帝 |
| 小火龙 | 雷公 |

保存的脚本会保留，因此活动可以重复。

### 多边兽招式学习器礼物

带多边兽图标的卡片；在玩家右侧三个格子处生成朝西的皮皮精灵；先给 TM29 精神强念，再给 TM46 小偷，并设置独立投递检查点，因此重试小偷不会重复获得精神强念。默认标志 ID 为 1007；查看器在 `7` 右上角显示（`flag_id % 100`).

### 集章活动

两个活动共用一张 `SUN AND MOON RALLY` 卡片（念力土偶图标、两个印章槽位、显示编号 `6`、标志 ID 1006），可按任意顺序接收。

| 状态 | 含义 |
| --- | --- |
| `VAR_MYSTERY_GIFT_1` | 时拉比完成游标 |
| `VAR_MYSTERY_GIFT_2 = 0/1/2` | 太阳岩：无／已激活／已领取 |
| `VAR_MYSTERY_GIFT_3 = 0/1/2` | 月石：无／已激活／已领取 |
| `FLAG_MYSTERY_GIFT_DONE` | 集章活动完成状态 |
| 卡片领取标志 | 成功领取时拉比时同步 |

每个印章可获得 30 级太阳岩或月石；集齐两个可获得 50 级时拉比，全部使用普通的 `givemon`。放入队伍或电脑均可；若两者均满则不推进进度。两个待领取印章可一次投递全部三只。

```
matching =
    saved flag ID == distribution flag ID
    and max stamps == 2
    and metadata icon species == CLAYDOL

if no card:                install shared card + delivery script + selected stamp, run activation
else if not matching:      offer the toss prompt; on accept, install as above
else if stamp species or ID already exists:   HAS_STAMP, no activation
else if neither slot empty:                   NO_ROOM_STAMPS, no activation
else:                      save the stamp, run activation, STAMP_RECEIVED
```

激活使用神秘事件包装脚本（`runscript` 加上嵌入的场景脚本）。印章仅支持实时主机端。`IsStampInMetadata` [mystery_gift.c:272] 会拒绝 ID 或种类冲突的印章（最多 7 个）。`CLI_SAVE_STAMP` 仅写入 `cardMetadata.stampData` [mystery_gift.c:307]，避免 `CLI_SAVE_CARD`.

### 变幻洞窟

官方脚本 [data/mystery_event_msg.s:325]：`addvar VAR_ALTERING_CAVE_WILD_SET, 1`、达到 10 时回绕 [:328]、显示一条消息；它以 `end` 结束，因此每次交谈推进一组。读取器会将 9 及以上值归到表 0 [wild_encounter.c:192]。变量（0x4024）位于 SaveBlock1 + 0x1048：

```
--buffer-script save-dump --dump-block sav1 --dump-offset 0x1048 --dump-size 2
```

交谈三次将其设为 3，此后 GROTTE METAMO（变幻洞窟，六之岛）从表 3 中抽取 `sSixIslandAlteringCave_4_FireRed` [src/data/wild_encounters.json]（在零售版《火红》中遇到 16 级戴鲁比）。

| 变量 | 种类 |  | 变量 | 种类 |
| --- | --- | --- | --- | --- |
| 0 | 超音蝠 |  | 5 | 长尾怪手 |
| 1 | 咩利羊 |  | 6 | 壶壶 |
| 2 | 榛果球 |  | 7 | 惊角鹿 |
| 3 | 戴鲁比 |  | 8 | 图图犬 |
| 4 | 熊宝宝 |  |  |  |

### 配信蛋

三种日版配信，从 GB-Link-Switch-LDN 携带的字节移植而来（`web/js/gift/official.js`）。每张卡片包含该次配信的所有蛋，主机使用 `random` [scrcmd.c:455] 选取一个；蛋带有配信的四个招式、命运般的相遇标志位及相遇地点 0xFF，与原始脚本的设置一致。队伍已满时会在抽取前拒绝，卡片保持可领取状态。

| 卡片 | 蛋 |
| --- | --- |
| `wish-egg`（纽约宝可梦中心） | 吉利蛋、催眠貘、蛋蛋、大葱鸭、袋兽、大舌头；每只均会祈愿 |
| `pokepark-egg`（宝可梦乐园 Market Fantasia） | 刺球仙人掌、龙虾小兵、太阳珊瑚、宝宝丁、负电拍拍、皮丘、正电拍拍、可达鸭、向尾喵、晃晃斑、跳跳猪、溜溜糖球、傲骨燕、咕妞妞、小果然 |
| `pc-japan-egg`（日本宝可梦中心） | 喇叭芽（摇晃舞）、喵喵（花瓣舞）、走路草（寄生种子）、蚊香蝌蚪（天使之吻） |

相遇地点为 0xFF 或带有命运般的相遇标志位时，概况画面显示“在美好的地方获得的神奇宝可梦蛋。”[pokemon_summary_screen.c:2799]。

### 活动宝可梦

`--gift event-pokemon --event-pokemon NAME` 发送第三世代配信宝可梦的一份新副本：PKHeX.Core 根据自身的活动表（`EncounterGift3`，非蛋、非日语条目），使用该活动的 PID／IV 方法生成，并保留其训练家名称、训练家 ID、等级、招式、携带道具、奖章和命运般的相遇标志位，而且必须通过合法性检查。记录通过神秘事件的 `givepokemon` 在卡片保存时立即加入队伍，与 `mystery-event-celebi` 的行为相同；队伍已满时返回状态 3，无法获得任何宝可梦，卡片可以再次接收。未指定 `--event-pokemon` 时，卡片发送一只预存的 WISHMKR 基拉祈。

`NAME` 是训练家名称、一个空格和种类：`WISHMKR Jirachi`, `CHANNEL Jirachi`, `Aura Mew`, `MYSTRY Mew`, `DOEL Deoxys`, `SPACE C Deoxys`, `ROCKS Metang`, `10 ANIV Pikachu` 以及所有其他 `10 ANIV` 种类，欧洲的 `10ANNIV`, `10JAHRE`, `10ANNI` 和 `10ANIV` 配信。如果某活动曾以多种语言发布，则发送与 `--language` 匹配的版本。

该卡片不依赖具体构建：神秘事件虚拟机的 17 项表、其 `givepokemon` 以及礼物客户端包含 23 个分支的 `Client_Run` switch，在全部十二款卡带上均具有相同布局，而 `tests/test_frlg_english_cartridges.py` 通过各卡带自身的 `RunMysteryEventScript` 运行卡片脚本（状态 2 时记录加入队伍；队伍已满时状态 3，不获得任何内容）。

### GB-Link Team 卡片

GB-Link Team 的自定义神奇卡片（GB-Link-Switch-LDN `cards/`，GPL-3.0）由一张神奇卡片与配送员 RAM 脚本组成，脚本携带 THUMB 代码，通过 `callnative` 调用。其 ARM 源码位于 `vendor/gblink-cards/`; `scripts/gen_team_cards.py` 将其针对五款卡带汇编到 `pokeldn/frlg/data/team_cards.json`，而 `pokeldn/frlg/gift/team_cards.py` 按各自 ID 注册每张卡片，不带 `custom-` (`--gift nature-mint`）。使用未经修改的源码及其 RAM 地址，生成器能够逐字节复现其自身的 `BPRE 1.10` 载荷，共 44 个。

`starter-egg`, `rare-berries` 和 `national-dex` 是其无需原生代码的三张卡片，现已使用组合器重建：树果对应道具 173、174 和 175，全国图鉴卡设置 `FLAG_SYS_NATIONAL_DEX`（0x840）。活动宝可梦来自 PKHeX（参见“活动宝可梦”），但 PKHeX 表遗漏的四只除外；它们的跟随、大师球、加速和遭遇钩子由本项目自身的功能覆盖。

| 分组 | 卡片 |
| --- | --- |
| 修改宝可梦 | `nature-mint`, `ability-capsule`, `poke-ball-changer`, `pokemon-gender`, `nickname`, `stat-judge`, `hidden-power`, `hidden-power-type`, `ev-training`, `friendship`, `pp-max`, `max-conditions`, `pokerus`, `unown-letters`, `trade-evolution`, `espeon-umbreon`, `move-tutor` |
| 逐帧钩子 | `speed-2`, `speed-3`, `speed-4`, `speed-0-75`, `speed-0-5`, `fast-text`, `travel-anywhere`, `pc-anywhere`, `hm-moves`, `reusable-tms`, `physical-special-split`, `exp-share`, `shiny-hunting`, `roamer` |
| 其他 | `no-encounters`, `legendary-respawn`, `instant-eggs`, `gift-box`, `pocket-casino`, `gift-ribbons`, `trainer-ids`, `gender-swap`, `rival-name` |
| 活动宝可梦 | `box-eggs`, `colosseum-pikachu`, `ageto-celebi`, `mattle-ho-oh` |

与其构建的不同之处：

-
-
-
-
-

每张卡片都已在 mGBA 下、全部十二款卡带上绑定到妈妈进行测试；这些检查覆盖入口、消息和菜单，而非每张卡片中的所有选项。`nature-mint`, `pc-anywhere` 和 `rival-name` 也已在零售版法语《火红》上运行。发送到另一游戏卡带的载荷会回复“此礼物不适用于此游戏版本。”（日语版为“游戏错误。”）。当常驻钩子运行时，`nature-mint` 保持 `0x0203FC00..0x02040000` 不变，而 `pc-anywhere` 接管 `gIntrTable[4]`，并将 `0x0800071D` 保存在 `0x0203FBFC`.

`colosseum-pikachu` 和 `ageto-celebi` 携带其日语训练家名称，欧洲版卡带会将其绘制为圆点；PKHeX 报告这四只活动宝可梦均合法。

### 对战计数卡

`MysteryEventScript_BattleCard` [data/mystery_event_msg.s:162] 读取 `GET_CARD_BATTLES_WON`，通过 `GetMysteryGiftCardStat`（special 390），恰好为三时给予伤药。移植版本将官方的 `FLAG_MYSTERY_GIFT_DONE` 门控替换为自己的奖品变量，因此仍可重复触发。

伙伴负责启用计数器：`Task_ExchangeCards` 仅在满足以下条件时启用 `MysteryGift_TryEnableStatsByFlagId`：在 `BLOCK_REQ_SIZE_100` 缓冲区中，96 字节训练家卡片后面的 u16 等于持有卡片的标志 ID [union_room.c:1777]；此检查发生在进入交换中心或竞技场时（`frlg_trade_host.py --card-flag-id N`).

| 触发递增的事件 | 位置 | 规则 |
| --- | --- | --- |
| `numTrades` | 完成一次交换 [trade_scene.c:2609] | 卡片尚未计入的训练家 ID |
| `battlesWon` / `battlesLost` | 联机俱乐部对战结束 [cable_club.c:792] | 同上，每项统计记住 5 个 ID |

`IncrementCardStatForNewTrainer` [mystery_gift.c:630] 对每个训练家 ID 仅计数一次。联盟交谊厅对战通过 `CB2_ReturnToField` 返回，不会计数；只有 [竞技场](frlg_link.md#the-cable-club-colosseum) 会计数。计数器位于 SaveBlock1 + 0x3434（`buffer_script.SAV1_CARD_METADATA`），读取时不检查 CRC [mystery_gift.c:490]：

```
0x3434: 0000 0000 0000 2300     battlesWon 0, lost 0, trades 0, icon 35 (CARD_TYPE_GIFT)
0x3434: 0000 0000 0100 2300     trades 1                       (CARD_TYPE_LINK_STAT)
```

一张 `CARD_TYPE_GIFT` 卡片即使已启用，计数仍保持为零。无线俱乐部的交换中心会经过 `union_room.c` 的 `Task_StartActivity`，这是唯一会在偏移 96 处写入标志 ID 的构建器。

### 来访训练家

`CLI_RECV_EREADER_TRAINER`（18，ident `MG_LINKID_EREADER_TRAINER` = 26）将缓冲区复制到 `gSaveBlock2Ptr->battleTower.ereaderTrainer`，并调用 `ValidateEReaderTrainer` [mystery_gift_client.c:233]。该结构体长 188 字节 [global.h:286]：

```
0x00 u8  unk0                  0x10 u16 greeting[6]            0x34 BattleTowerPokemon party[3]
0x01 u8  trainerClass          0x1C u16 farewellPlayerLost[6]  0xB8 u32 checksum
0x02 u16 winStreak             0x28 u16 farewellPlayerWon[6]
0x04 u8  name[8]
0x0C u8  trainerId[4]
```

验证条件：前 46 个字不全为零，末尾 u32 为它们的总和 [battle_tower.c:1354, :1384]；失败时静默清除。`SevenIsland_House_Room1` 仅以此为门控：老妇人在 Room2 提供一场 3 对 3 对战，由 `CreateBattleTowerMon` 根据该结构体构建 [battle_tower.c:928]；战后恢复状态，可重复进行。此处从不调用等级规则和禁用列表（`ShouldBattleEReaderTrainer` [:232]）。

`CreateBattleTowerMon` 设置种类、道具、四个招式（PP 来自招式表）、等级、ppBonuses、EV、IV、abilityNum、otId、personality、昵称和亲密度。短语由六个简易聊天词组成；`farewellPlayerWon` 在玩家获胜时说出。FRLG 显示八个名称字节中的五个 [`CopyEReaderTrainerName5`，battle_tower.c:1343]。`CLI_MSG_TRAINER_RECEIVED`（12）[strings.c:1296] 视为成功，因此主机会保存。

`--gift visiting-trainer` 在同一次会话中发送卡片、RAM 脚本和训练家：没有卡片 → 三者全发；相同卡片 → 仅发送训练家，无丢弃提示；另一张卡片 → 显示丢弃提示，然后三者全发。

## 神奇新闻

神秘礼物菜单是 {神奇卡片、神奇新闻} × {无线通信、朋友}。`struct WonderNews` [global.h:646] 长 444 字节，不携带身份标识：

| 偏移 | 大小 | 字段 | 说明 |
| --- | --- | --- | --- |
| 0x000 | 2 | `id` | 这是 `ValidateWonderNews` 唯一检查的内容：不能为 0 [mystery_gift.c:113] |
| 0x002 | 1 | `sendType` | `SEND_TYPE_DISALLOWED` 隐藏主机自身的“发送”选项 [mystery_gift.c:120] |
| 0x003 | 1 | `bgType` | 不进行验证；`WonderNews_Init` 会将 `>= NUM_WONDER_BGS` 归为 0 [mystery_gift_show_news.c:110] |
| 0x004 | 40 | `titleText` | 在 224 像素窗口内居中 |
| 0x02C | 400 | `bodyText[10][40]` | 屏幕显示八行；索引 7 之后存在非空行时会启用滚动指示器 [:346] |

新闻没有 `flagId`、元数据、RAM 脚本或领取标志，也从不查询 `sReceivedGiftFlags`. `IsWonderNewsSameAsSaved` [mystery_gift.c:140] 会比较全部 444 字节，因此只改一个字节就会把旧新闻变为新新闻（`--news-id N`）。与神奇卡片主机端相比：

-
-
-

来自朋友的新闻会在 `ITEM_RAZZ_BERRY` 和 `ITEM_NOMEL_BERRY` 之间随机选择一种树果 [mystery_gift_menu.c:1367, wonder_news.c:21]，由 `CeruleanCity_House4` 中的男人给予：最多五次，然后需要走 500 步 [`MAX_REWARD`]。四个树果的奖励需要 `WONDER_NEWS_RECV_WIRELESS`，这条路径尚未打通。

`--news` (`--news berry`, `--news-id N`）；玩家选择神奇新闻、“是否输入？”，再选择朋友（已持有新闻的主机会先显示新闻：按 A，然后选择接收）。一次会话的消息顺序（约 18 秒）：

```
ident 16  sClientScript_SendGameData
ident 17  MysteryGiftLinkGameData
ident 16  sClientScript_SaveNews
ident 23  MG_LINKID_NEWS - 444 bytes in three blocks
ident 19  MG_LINKID_RESPONSE - FALSE: the console saved it
ident 16  sClientScript_NewsReceived
ident 20  READY_END                              -> SVR_MSG_NEWS_SENT
```

## 将问卷用作口令门控

`SVR_CHECK_QUESTIONNAIRE` 按顺序比较友好商店问卷中的四个词 [`MysteryGift_DoesQuestionnaireMatch`，mystery_gift.c:422]，将结果放入 `param`，供 `SVR_GOTO_IF_EQ` 使用；ROM 服务端脚本均未使用它。`mg_server.gate_on_questionnaire(script)` 将它拼接在游戏数据前缀之后：

```
MysteryGiftServer(card, ram_script, questionnaire=phrase, denied_message="Say the words.")
bin/frlg_mg_host.py --gift ... --questionnaire species:55,FEELINGS/60,move:177,why
```

词可以是英语名称、`species:N`, `move:N`, `GROUP/INDEX` 或原始 ID。短语错误时，通过 `CLIENT_SCRIPT_DYNAMIC_ERROR` 和 `SVR_MSG_NOTHING_SENT` 显示主机端的 64 字节消息；不会发送或丢弃任何内容。先测试拒绝情形：门控通过与没有接入门控看起来一样。

法语词 ID 从主机读取：每次会话都会在 `MysteryGiftLinkGameData` [mystery_gift.c:361] 中发送四个词，主机端将其记入日志。

```
questionnaire: POKEMON/55  done [FEELINGS/60]  MOVE_1/177  why [MISC/37]
```

对于 AKWAKWAK FURAX AEROBLAST POURQUOI：`EC_GROUP_POKEMON` 按种类索引（哥达鸭，55），`EC_GROUP_MOVE_1` 按招式 ID 索引（气旋攻击，177），英语表中的 MISC/37 正确，而 FEELINGS/60 错误。参见 [法语简易聊天词汇表](frlg_rom_map.md#the-french-easy-chat-vocabulary).

## 主机主动报告的自身信息

每次会话的 `MysteryGiftLinkGameData` 都携带简易聊天资料和卡片统计（`CARD_STAT_BATTLES_WON` / `_LOST` / `_NUM_TRADES` / `_NUM_STAMPS`）[mystery_gift.c:361]。`--game-data-log PATH` (`pokeldn/frlg/gift/game_data_log.py`）将每次会话追加到 JSONL 台账，并打印自该主机上次会话以来发生的变化；`tools/frlg/game_data_read.py PATH` 读取该台账。计数器只有在相同卡片标志 ID 上的差值才可作为证据。台账会标出法语简易聊天表缺失的每个词 ID。

## 存档备份与恢复

通过“神奇卡片、朋友”会话，可以将主机完整的 128 KiB 存档芯片复制到主机端，或将一个 `.sav` 写入芯片并让游戏加载、保存它。不会发送或替换任何卡片。两个载荷 `asm/save-backup.s` 和 `asm/save-restore.s`，移植自 GB-Link Team 的 `cards/savebackup.s` 和 `cards/saverestore.s` (`GB-Link/GB-Link-Switch-LDN`，GPL-3.0）；主机端为 `pokeldn.frlg.gift.save_transfer` 和 `bin/frlg_mg_host.py --save-backup FILE` / `--save-restore FILE`。应用可从神秘礼物工具的“你的存档”选项卡运行两者（[你的存档](gui.md#your-saves)).

两者均支持全部十二款卡带。载荷中会修补两个构建相关地址；其余存档布局共用（[存档备份与恢复](frlg_rom_map.md#save-backup-and-restore)).

### 令牌编码

双向都以令牌形式传输芯片字节：字节 `n = 0x80` 后跟一个需重复 `n - 0x80 + 3` 次的字节。连续三个及以上相同字节会整体编码，最多 130 个；字面字节连续段最多 128 个。存档大部分为 `0x00` 和 `0xFF` 连续段。

### 备份

客户端脚本重复 `CLI_LOAD_TOSS_RESPONSE, CLI_RUN_BUFFER_SCRIPT, CLI_SEND_LOADED` 最多 32 次，然后请求下一段脚本；主机端根据目前速度估计剩余所需轮数，再多发送一轮。每轮为最多 8 KiB 芯片数据发送最多 1 KiB 令牌，绝不跨越 64 KiB 存储体边界。芯片偏移保存在 `client->param` 中，形式为 `0x5A << 24 | offset` [mystery_gift_client.c:276]；不带 `param` 的 `0x5A` 表示会话的第一轮，从头部字 `first`.

| 载荷字 | 偏移 | 值 |
| --- | --- | --- |
| `first` | `0x004` | 第一轮开始的芯片偏移 |
| `send_queue` | `0x008` | `&gRfu.sendQueue.count` |

每轮将对应范围分帧暂存到 `gDecompressionBuffer + 0x800`, `0x800`，每帧若干字节（返回 0），然后将其压缩到 `gDecompressionBuffer + 0x400`，并将 `link.sendBuffer` (`param + 0x3C`）和 `link.sendSize` (`param + 0x34`）指向该消息。当 `gRfu.sendQueue.count` 不为零时，每轮返回 0：丢失的片段会在每帧发送之外重新入队，40 条命令的队列只有在不再发送新内容时才会排空。

会话在一条 64 字节消息之后以 `CLI_MSG_BUFFER_FAILURE` 结束，因此主机显示消息但不保存 [mystery_gift_menu.c:1379]。中途截断的备份按游戏代码和训练家 ID 保留在主机端；该主机下次备份时将 `first` 设为上次停止的位置。

### 恢复

1.
2.
3.
4.
5.

| 载荷字 | 偏移 | 值 |
| --- | --- | --- |
| `b install` | `0x000` | 第一条消息的入口 |
| `b entry` | `0x004` | 此后每条消息的入口，位于 `gDecompressionBuffer + 0x404` |
| `load_game_save` | `0x008` | `LoadGameSave \| 1` |

主机端会拒绝加载副本不完整的存档，以及布局不同的存档：日语版 SaveBlock1 短 40 字节，而全零填充扇区的校验和无法体现这一点，因此根据玩家自己的宝可梦（OT ID 等于训练家 ID）的语言字节（`+0x12`）读取布局。拒绝时不写入任何内容。

### 实测内容

离线测试，对照脚本化主机（`tests/test_save_transfer.py`）：在法语《火红》、英语《叶绿》和日语《火红》上，备份逐字节还原芯片；在 40 KB 后中断的备份可以续传并完成；恢复后，文件中加载的副本成为芯片最新副本，额外扇区与文件一致，主机原有副本仍完整；写入八个扇区后中断恢复，主机仍加载自身的副本。

通过 ESP32 板在零售版法语《火红》上备份，共 64 轮，从第一轮到最后一块耗时 219 秒；文件中的两个槽位均完整，训练家也与主机一致。主机显示了消息并保留其存档。

通过 ESP32 板在零售版英语《火红》（BPRE）上，使用 `--console-build auto` 根据主机游戏代码选择 BPRE，备份读取了两个完整槽位（计数器 2 和 1）。恢复该文件时，19 个扇区全部写入，并以成功消息结束。紧接着进行的备份显示，槽位 1、计数器 3 下的副本与文件中加载的副本逐字节一致，而槽位 0、计数器 4 下为主机自行保存的已加载游戏；该副本与文件在扇区 1 至 7 存在差异，这些块携带加密密钥，`LoadGameSave` 会重新随机生成该密钥。

第二次恢复将一个法语《火红》存档放到了同一英语卡带上。它以成功消息结束，选择“继续”后将法语版游戏加载到了地图世界。

## 编写礼物

`pokeldn.frlg.gift.gift_composer` 根据不可变的 `WonderGift` 定义构建卡片和配送员脚本：

```
MEWTWO_GIFT = WonderGift(
    slug="mewtwo-encounter",
    card=WonderCardSpec(icon_species=150, title="MYSTERIOUS ENCOUNTER",
                        body=("Visit the deliveryman.",), default_flag_id=1008),
    intro_message="A powerful presence is waiting!",
    event=GiftSpec(shareable="once"),          # or StampRallySpec(...)
    delivery=DeliveryPlan(delivery=(
        DeliveryStage(Message("Take this."), GiveItem(1)),  # Master Ball
        DeliveryStage(ShowSprite(0, RelativeToPlayer(dx=1)), BattleLegendary(150, level=70)),
    )),
    completed_message="That mysterious encounter is over.",
)
```

`GiftSpec` 保存可重复、可分享属性；`StampRallySpec` 保存集章槽位和完成钩子。一个 `DeliveryPlan` 有三个序列：`WonderGift.delivery` 使用 `delivery`; `StampSlot.delivery`，而 `StampRallySpec.completion` 使用 `pre_stages` 和 `post_stages`；其他内容一律拒绝。

编译器显示 `intro_message`，从 `VAR_MYSTERY_GIFT_1` 恢复各阶段，成功时设置 `FLAG_MYSTERY_GIFT_DONE` 以及卡片领取标志。再次访问时显示 `completed_message`; `GiftSpec(repeatable=True)` 则改为重置游标。

### 阶段与条件

每个 `DeliveryStage` 都是一个检查点：奖励发放失败会重新提供该阶段，并跳过此前已成功的阶段。切勿在同一阶段放入两个可能失败的奖励（`GiveItem`, `GivePokemon`, `GiveEgg`）。`GiveEgg` 接受与 `moves=(...)` 相同的 `GivePokemon`；带指定招式的蛋需要一个队伍槽位，因此队伍已满时会稍后重试，而不是送入电脑。第一个招式之后的招式为 0 时，会清空相应槽位。`GiveRandomEgg(eggs)` 接受 `(species, moves)` 对，并通过 `random` 选择一个给予：使用跳转表，因此十五个各带四个招式的蛋可放入一个 RAM 脚本（944 字节）。

`condition=` (`VarEquals`, `FlagSet`, `Not`, `AllOf`, `AnyOf`）为假时会跳过某阶段的动作，但仍推进游标，可用于互斥分支。`RequireSpecialResult(...)` 将场景 special 的调用结果写入 `VAR_RESULT` 并进行比较，失败时显示其消息而不推进进度。

```
DeliveryStage(ShowSprite(142, RelativeToPlayer(dx=1)),
              condition=VarEquals(0x4031, 0))  # VAR_STARTER_MON == Bulbasaur
DeliveryStage(BattleLegendary(243, level=65),
              condition=Not(AnyOf((VarEquals(0x4031, 0), VarEquals(0x4031, 1)))))
DeliveryStage(RequireSpecialResult(SPECIAL_HAS_ALL_KANTO_MONS, 1, "Finish the KANTO POKEDEX first."),
              GivePokemon(251, level=50))
```

### 写入玩家存档

`SetVar(variable, value)` 生成 `setvar`（0x16），而 `AddVar(variable, value)` 生成 `addvar`（0x17）；两者都仅允许使用存档变量（0x4000..0x40FF）或特殊变量（0x8000..0x8011）。

### 对战

`BattleLegendary` 先生成 `setwildbattle`, `special StartLegendaryBattle`，然后生成 `end`，不带 `waitstate`，因此对战移动 SaveBlock 内存后，不会继续使用 RAM 脚本指针（[RAM 脚本可能无法从对战返回](frlg_rng.md#a-ram-script-may-not-come-back-from-a-battle)). `BattlePokemon` 生成普通的 `dowildbattle`。两者都必须是所属阶段的最后一个动作。印章槽位路径禁止对战，包括集章活动共用的中间部分；允许将条件对战阶段作为终止分支。

### 分享

`GiftSpec.shareable` 映射到神奇卡片的 `sendType` 位：

| 值 | 行为 |
| --- | --- |
| `"never"` | 不能继续分享 |
| `"once"` | 可分享一次；接收游戏将卡片改为不可分享 |
| `"always"` | 接收后仍可继续分享 |

### 命运般的相遇标记

`GivePokemon(..., fateful_encounter=True)`（以及 `GiveEgg`）生成官方冲浪皮丘使用的指令对：`setmonmodernfatefulencounter` (`0xCD`）和 `setmonmetlocation` (`0xD2`, `METLOC_FATEFUL_ENCOUNTER` = 0xFF）[data/mystery_event_msg.s:71]。这是显式启用的功能，因此旧卡片的字节保持不变。

`ScrCmd_setmonmodernfatefulencounter` 不检查索引边界 [scrcmd.c:2239]（`setmonmove` 会限制范围 [script_pokemon_util.c:144]），因此组合器值为 7 的 `LAST_PARTY_MON_INDEX` 不能传到它。索引是给予前的队伍数量（`specialvar ... CalculatePlayerPartyCount`）；队伍已满时会跳转到失败标签，因此送入电脑的宝可梦绝不会被标记。

概况画面的命运般的相遇文字仅由相遇地点决定 [pokemon_summary_screen.c:2665，在 :2799 做或运算]。`modernFatefulEncounter` 是 Misc+0x08 处奖章字的第 31 位 [include/pokemon.h:40-82]；`mon.decode_mon` 从队伍转储中读取它。

### `initramscript` 在组合器中

`gift_composer.build_bound_script(actions)` 将组合器动作编译为场景脚本，供 `initramscript` 绑定；`build_mevent_npc_script(actions=...)` 则直接接受这些动作。使用相同的字节码、解释器和 `ramScript` 槽位，因此道具、宝可梦、精灵和对战均可使用。没有阶段游标或领取标志：脚本以 `end` 结束，并会完整重跑，因此仅触发一次的效果需要自己的 `SetVar` 或条件。

### 注册与验证

```
from pokeldn.frlg.gift.gift_registry import GIFT_REGISTRY
GIFT_REGISTRY.register_definition(MEWTWO_GIFT)
```

注册时验证并编译默认标志 ID；运行时的 `--flag-id` 会再次编译。验证覆盖卡片文字和标志、计划结构、动作取值范围、游标边界、印章唯一性、对战位置、虚拟指针和 995 字节 RAM 脚本上限，并指出对应部分：

```
example-rally.event.slots[1].delivery.post_stages[0].actions[1]: battles are not allowed in stamp-slot delivery plans
```

## 静态工具

```
./.venv/bin/python -m pokeldn.frlg.gift.gift_to_bin --gift beast-cutscene --flag-id 1005 --out-dir exported-gift
./.venv/bin/python -m pokeldn.frlg.save.save_inject game.sav --gift beast-cutscene --flag-id 1005
```

`gift_to_bin` 按照 `pokemon-gen3-mysterygift-tool` 预期的格式写入 336 字节神奇卡片和 1004 字节 RAM 脚本。`save_inject` 将两者写入当前存档槽位，重建卡片 CRC、RAM 脚本 CRC 和扇区校验和，并保存 `.gift.sav` (`--in-place` 会覆盖）。`--make-artifact` 在 `.ram.lst` 下写入确定性的 `artifacts/`（字节、解码后的指令、校验和、目标、阶段摘要）。

## 尚未打通的路径

### 无线通信（JoySpot）

被 RFU 序列号门控阻挡。两条路径都会进入相同的礼物交互流程：

|  | 朋友 | 无线通信 |
| --- | --- | --- |
| 监听器 | `Task_ListenForCompatiblePartners` [union_room.c:3757] | `Task_ListenForWonderDistributor` [union_room.c:3799] |
| 接受的 RFU 序列号 | `IsRfuSerialNumberValid` → `{0x0002, 0x7F7D}` | `== 0x7F7D`，仅此值 [link_rfu_3.c:920] |
| 选择方式 | 玩家从列表选择 | 自动连接，无需按键 |
| Switch 是否可达 | 是 | 否 |

`Task_CardOrNewsOverWireless` [union_room.c:2415] 扫描后等待 120 帧，再对候选项 0 进行门控：

1.
2.
3.
4.

错误序列号会静默地在门控 1 失败（不播放 SE_BOO）。Switch 桥接层报告 `0x0002` (`RFU_SERIAL_GAME`）：朋友（`sAcceptedSerialNos` [link_rfu_2.c:240]）列出所有候选项，而无线通信忽略所有候选项。广播数据没有序列号字段；原生广播除四个字段外均为零：

```
50 10 | c1 cc bf bf c8 ff 00 00 | 65 ac | 00 00 00 00 | 84 15 | 00 00 00 00 00 00
TID   | uname                   | parent| unexplained | search| unexplained
```

`svc_47` [sloopsvc.c:34] 接受 `{u8 HostRfuGameData[0x10]; u8 HostRfuUsername[8]}`，共 24 字节，不含序列号，而桥接层通过 `svc_45_rfu_link_status()`.

未能让无线通信路径发起 802.11 身份验证的广播变体（共尝试 21 种）：场景 ID（0、21、0x7F7D）、LDN 和 Pia 应用版本、`0x7F7D` 在偏移 12、13、14、18、19、20、22 处的两种字节序、活动（0、4、21）、`hasCard`，以及搜索字的第 7 位。保持不变的参数：`local_communication_id = 0x01006fa0233f8000`、LDN 版本 4、信道 1、`max_participants = 2`、Pia `sysCommVer = 22`、场景 22287。

`0x1584 & 0x7F = 4 = ACTIVITY_TRADE` 出现在原生抓包中，而在该偏移处设置活动 21 会使其出现在朋友列表并成功加入，因此位于 `record[16:18]` 的搜索字是 `activity:7 | bit7 | version:3 | language:3 | hasCard?:1 | startedActivity:1`（该抓包中的版本 5 = 叶绿，语言 2 = 英语）。

尚未测试：`local_communication_id`（修改后主机端被隐藏，无法与门控区分）、场景穷举、多变量组合。若有桥接层证据表明可以从可广播内容中给 `partner[].serialNo` 赋值，或抓到 Switch 认作神奇配信端的广播，则可重新研究。此阻碍使零按键路径及神奇新闻的四树果奖励不可用。

### e-Reader 本身

训练家之塔套组和 `CEReaderTool_SaveTrainerTower`: `ereader_screen.c` 通过 `gLinkType = LINKTYPE_EREADER_FRLG` 打开，使用 GBA 串行链路，而非无线适配器。

### 极光船票与神秘船票

船票卡片在 Switch 发行版中没有作用。配信脚本位于 `data/mystery_event_msg.s:200`，但 Switch 发行版会在首次进入名人堂时授予两张船票和两个 `FLAG_RECEIVED_*` 标志 [post_battle_event_funcs.c:52，`#if REVISION >= 0xA`]，因此在已通关存档中脚本不会产生任何效果。展示库的 `FL - Item AuroraTicket` 脚本首先检查 `FLAG_RECEIVED_AURORA_TICKET`；进入名人堂后，配送员只说“感谢使用神秘礼物系统。”，不会给予任何东西。该卡片的 `iconSpecies` 为 `0xFFFF`：除了 `SPECIES_NONE` 以外的任何值都会绘制图标，而超出 `SPECIES_UNOWN_B - 1` 的种类会绘制 `SPECIES_NONE` 的问号 [mystery_gift_show_card.c:466, pokemon_icon.c:1102]。古老海图仅适用于《绿宝石》[mystery_gift.c:30]。

## 陷阱

-
-
