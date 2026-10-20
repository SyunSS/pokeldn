---
title: gRngValue：读取、预测与定向控制
parent: FireRed and LeafGreen
nav_order: 5
---

# gRngValue：读取、预测与定向控制

本文所有内容均在法语《火红》BPRF、软件版本 0x0A 上测得。

## 生成器

```
u16 Random(void) { gRngValue = 1103515245 * gRngValue + 24691; return gRngValue >> 16; }
void SeedRng(u16 seed) { gRngValue = seed; }
```

[src/random.c, include/random.h:18]

| 符号 | 地址 | 获取方式 |
| --- | --- | --- |
| `gRngValue` | `0x03004220` | `Random` 的字面量池 |
| `Random` | `0x080486B0` | 扫描 4 MB 查找 `RAND_MULT` = 0x41C64E6D |
| `SeedRng` | `0x080486D0` | 其字面量池再次标识出 `gRngValue`，这是第二次 |
| `gSpecialVars` | `0x081639A8` | 2.75 MB 中唯一一段十二个字、每次递增 2 的序列 |
| `gSpecialVar_0x8000` | `0x020370B4` | 该序列的第一个条目 |

没有 ARM 或 THUMB 指令能编码 `RAND_MULT`，因此它位于 `Random` 的字面量池中，紧邻 `&gRngValue`。扫描返回十一处匹配；`ld_script.ld` 将 `src/random.o` 放在第 86 项，而该常量的下一个使用者 `src/title_screen.o` 放在第 123 项，因此最低地址的匹配属于 random.o。转储与 `Random` 的每条指令均一致 [random.c:9-13]，随后是 `SeedRng`，使用相同的池字。

`Random` 返回状态的高半部：一个性格值（两次抽取）会留下 216 个候选状态。`pokeldn/frlg/rom/lcg.py` 实现相应算术；`distance(a, b)` 通过小步大步法在任意范围内精确求解（217 次操作）。该映射对全部 232 个状态构成置换，因此距离总是存在，只有距离较小时才构成证据（概率 N / 232).

`gRngValue` 和 `gSpecialVar_0x8000` 是链接期全局变量，绝不移动。存档块地址则会移动：`SetSaveBlocksPointers` 在每次对战和加载时重新随机选择一个按 4 对齐的偏移 [load_save.c:75]。

## 速率：每帧恰好推进 2 次

`ScrCmd_delay` 在恰好 N 帧之后恢复执行 [scrcmd.c:651]。`--gift rng-rate-probe` 读取 `gRngValue`，延迟 N 帧后再次读取；`rng_script.measure_rate` 将 `lcg.distance` 除以 N。

| 帧数（精确） | 推进次数（精确） | 2N + 2 |
| --- | --- | --- |
| 600 | 1,202 | 1202 |
| 3000 | 6,002 | 6002 |

其中 +2 是 `delay` 前后多出的一帧；每帧 2.003333 次的模型可以拟合 N=600，却会在 N=3000 时预测 6010 次。`rng-trace` 对 `gRngValue` 在神秘礼物联机菜单中每帧采样一次，95 次间隔全部恰好为 2。读数之后 n 帧的状态为 `advance(S, 2n)`.

该探针在 `delay` (`lock=False` 期间测量锁定的玩家，另一项测量未锁定玩家）；普通地图游玩中的推进次数为偶数。次数由两次读数（`distance`）或生成的宝可梦（`recover_wild_state`）得出；一次推进约为 8 毫秒，因此手动计时的秒数无法确定它。

## 种子的来源，以及为何不能将其带入地图

```
void SeedRngAndSetTrainerId(void) { u16 val = REG_TM1CNT_L; SeedRng(val); gTrainerId = val; }
```

[main.c:264]，由 `Task_TitleScreenMain` 在淡出之后、恰好在 `SetMainCallback2(CB2_InitMainMenu)` 之前调用 [title_screen.c:735]。`StartTimer1` 以 `CB2_InitTitleScreen` 运行 [:351]：种子是按下 START 时对自由运行定时器的采样，共有 65536 种可能值。

联机期间设置的种子不会保留：退出神秘礼物会运行 `MainCB_FreeAllBuffersAndReturnToInitTitleScreen` → `CB2_InitTitleScreen` [mystery_gift_menu.c:463]，按 START 又会重新播种。从神秘礼物菜单到地图世界的任何路径都无法绕过它。在那里设置的种子 `0xC0DE` 并不是下一次遭遇状态的祖先（实测相隔 1,898,278,119 次推进）。

| `SeedRng` 调用点 | 时机 |
| --- | --- |
| `SeedRngAndSetTrainerId` [title_screen.c:735] | 标题画面 |
| `LinkTestScreen` [link.c:318] | 未使用的调试画面 |
| `Debug_RfuIdle` [link_rfu_2.c:2670] | 未使用的调试画面 |
| `RfuMain1` [link_rfu_2.c:2116] | 仅限 Switch，受 Sloop 系统调用门控 |

```
if ((svc_4b() & SVC4B_RESEED_RNG) != 0)
    SeedRng(ReadU16(&GetHostRfuGameData()->compatibility.playerTrainerId));
```

[link_rfu_2.c:2114，`#if REVISION >= 0xA`]. `RfuMain1` 在 RFU 启用期间每帧运行，因此若该位置位，状态会被固定在广播的 `playerTrainerId` 附近。没有任何实测状态源自它：神秘礼物菜单中的采样状态与主机的 `playerTrainerId` 相距 13.7 亿次推进，联盟交谊厅游玩后一次遭遇的采样状态则相距 21.0 亿次推进。该位何时置位尚不清楚。

定时按 START 无法选择种子。定时器 1 以 F/1 运行，一帧为 280,896 周期，因此若读取按帧对齐，结果都应为 `gcd(280896 mod 65536, 65536) = 64` 的倍数。恢复出的种子 `0xB8C0`, `0x3742`, `0x8E94`, `0x1376` 模 64 的余数为 0、2、20、54，说明读取存在子帧级抖动。

## 从宝可梦反推生成它的状态

`GenerateWildMon` 调用 `CreateMonWithNature(..., USE_RANDOM_IVS, Random() % NUM_NATURES)` [wild_encounter.c:233]，反复抽取性格值直到符合性格，然后抽取 IV。野生宝可梦使用四次抽取：性格值低半部、性格值高半部、HP／攻击／防御、速度／特攻／特防。两次 IV 抽取增加 30 位校验，最终恰好只剩一个状态（`lcg.recover_wild_state`). `Random32()`, `(Random() | (Random() << 16))`，在两个调用点都先抽取低半部。

必须搜索两种间隙；不同宝可梦的布局不同。零售版上观察到：

| 方法 | IV 之前的间隙 | IV 之间的间隙 | 观察对象 |
| --- | --- | --- | --- |
| 1 | 0 | 0 | 脚本百变怪、脚本鲤鱼王（2 次） |
| 2 | 1 | 0 | 野生独角虫、脚本鲤鱼王 |
| 4 | 0 | 1 | 野生绿毛虫、独角虫、猴怪；脚本鲤鱼王 |

只搜索一种间隙时，对于其他方法会报告“没有状态能生成这只宝可梦”。额外抽取不出现在 `CreateBoxMon` 的任何一行中；其来源未知。在脚本遭遇中，它间歇出现。某桩代码要求异色 + 爽朗 + 速度 >= 20，却生成了速度 10 的异色爽朗鲤鱼王；在 232 个状态中，恰好只有一个会在接下来两次抽取中得到该 PID：

```
state 0x429D2189
  draws 3,4 -> 15/0/12/25/7/14      what the stub tested: SPEED 25, passes
  draws 4,5 -> 25/7/14/10/10/30     the mon that appeared
```

在提出任何随机数结论之前，先将宝可梦的 PID 和 IV 与概况画面上的六项能力值核对。

## 脚本对战

```
setptr b0..b3 -> 0x03004220      gRngValue = seed          (opcode 0x11)
setwildbattle <species> <level>  CreateMon rolls PID, PID, IV, IV   (0xB6)
dowildbattle                     the battle starts          (0xB7)
```

`ScrCmd_setptr` 向绝对地址写入一个立即数字节 [scrcmd.c:300]。`setwildbattle` 调用 `CreateScriptedWildMon` → `CreateMon(&gEnemyParty[0], species, level, 32, 0, 0, OT_ID_PLAYER_ID, 0)` [script_pokemon_util.c:128]：随机 IV、无固定性格值、不循环匹配性格，使用普通四次抽取的 Method 1。两条命令均返回 FALSE，场景引擎会不断执行命令，直到某条返回 TRUE，因此四条 `setptr` 与生成过程在同一帧内运行。其间不能放入任何让出执行权的命令（一个 `playse` 就会破坏它）；测试会断言不存在此类命令。

由 `initramscript` 将其作为绑定到地图对象的 RAM 脚本投递，以 `end`（0x02）结束，而不是 `endram`（0x0d），使绑定保留并可再次触发。`setwildbattle` 不需要草丛，也无需随机判定是否遭遇。在主机见到种子之前已离线预测：真新镇中的一只异色 50 级百变怪：

```
PREDICTED   PID 0x026F38B2   nature 17   IVs 31/23/27/18/30/30   shiny
ACTUAL      PID 0x026F38B2   nature 17   IVs 31/23/27/18/30/30   shiny
```

### 由无人设置过的种子预测宝可梦

一个不写入任何内容的脚本读取实时状态、打印状态、生成宝可梦，再次打印状态：

```
BEFORE  0x9A4F5DAA        (read off the console)
AFTER   0x8EEB8648
```

仅根据 `BEFORE` 预测，从 `gPlayerParty` 转储出的宝可梦在全部七个字段上均匹配：PID 0x0BF87DD1、性格 13 爽朗、非异色、IV 25/10/28/9/19/3。四次抽取从读到的状态开始，偏移为零。

`distance(BEFORE, AFTER)` 为 6，而 `CreateBoxMon` 消耗 4 次：2 次用于 `Random32()`，OT 不消耗，因为玩家就是 OT [pokemon.c:1796]，2 次用于 IV [:1836,1845]。额外的 2 次（一帧地图世界消耗）发生在生成之后。

## 读取种子的 NPC

`--gift rng-seed-reader`，标志 ID 1015。六条命令，由 `initramscript` 一次性安装为 RAM 脚本，并以 `end` 结束以保留绑定：

```
copybyte gSpecialVar_0x8000+0, 0x03004220      (opcode 0x15, byte at any address to any address)
copybyte gSpecialVar_0x8000+1, 0x03004221
copybyte gSpecialVar_0x8001+0, 0x03004222
copybyte gSpecialVar_0x8001+1, 0x03004223
buffernumberstring 0, VAR_0x8000               (0x83)
msgbox                                          the NPC prints the value
```

它不改动任何内容；`rng_script.seed_from_printed(low, high)` 重新组装该字。

-
-
-

相隔约二十秒的两次读取结果：

```
reading 1   RNG HI 4685   RNG LO 26687   -> 0x124D683F
reading 2   RNG HI 54871  RNG LO 55616   -> 0xD657D940
distance    2,595 turns
```

互不相关的字约相距 231 次；2,595 对应概率为 1／1,655,093（`rng_script.check_two_readings`).

绑定到玩家的妈妈（组 4、地图 0、对象 1）：`MOVEMENT_TYPE_FACE_LEFT`，标志为 0，因此绝不隐藏，距离玩家仅一步。真新镇的两个对象事件都是 `MOVEMENT_TYPE_WANDER_AROUND` [data/maps/PalletTown/map.json]，会在倒计时中途走开。

## 人手按 A 的精度

同一玩家针对 30.00 秒后的目标按键四次，由打印种子的 NPC 读取结果：

| 试验 | 经过的帧数 | 相对 1791.8 的误差 |
| --- | --- | --- |
| 1 | 1801 | +9.2 |
| 2 | 1807 | +15.2 |
| 3 | 1800 | +8.2 |
| 4 | 1796 | +4.2 |

平均 +9.2 帧（会被抵消的固定偏移），标准差 4.5，极差 11。四次推进次数均为偶数。

异色帧约每 8192 帧（约 137 秒）出现一次；在 4.5 帧的离散程度下，按键命中某个选定帧的概率约为 9%，因此手动定向获得异色约需 25 分钟，而随机遭遇约需 23 小时。未命中的偏差可以精确测得。`pokeldn/frlg/rom/rng_countdown.py` 是倒计时；`--aimed-at STATE` 将未命中偏差转换为有符号帧数。当 RAM 脚本槽位被神奇卡片占用时，仍可使用此方法。

## 执行搜索的桩代码

`--gift rng-shiny-hunt`, `pokeldn/frlg/rom/native_script.py`, `asm/field/shiny-seek.s`。本页每段桩代码都已在零售版硬件上验证：

| 桩代码 | 礼物 | 零售版验证结果 |
| --- | --- | --- |
| `shiny-seek.s` | `rng-shiny-hunt` | 从妈妈处获得异色百变怪，使用两个不同状态验证 |
| `mon-seek.s` | `rng-mon-hunt` | 5 级鲤鱼王：异色、爽朗、速度 IV >= 20 |
| `mon-seek-far.s` | `rng-mon-hunt-far` | 异色爽朗鲤鱼王，证明 559 个填充字节已送达 |
| `mon-seek-both.s` | `rng-mon-hunt-both` | 异色、爽朗、速度 22；叶绿中的异色超梦 |

```
bool8 ScrCmd_setptr(struct ScriptContext * ctx)          // 0x11
{ u8 value = ScriptReadByte(ctx); *(u8 *)ScriptReadWord(ctx) = value; }
bool8 ScrCmd_callnative(struct ScriptContext * ctx)      // 0x23
{ void (*func)(void) = ((void (*)(void))ScriptReadWord(ctx)); func(); return FALSE; }
```

[scrcmd.c:300, :120]

`setptr` 可在任意位置写入一个字节，`callnative` 则运行它，因此 RAM 脚本可以将代码暂存到 EWRAM 并在地图世界运行，那里是 `CLI_RUN_BUFFER_SCRIPT` 无法到达的地方。`notblisy/RUBYSAPPHIREDLC` 在《红宝石／蓝宝石》上采用相同方法（`writebytetoaddr` + `callasm`，LCG 循环直到 PID 为异色）。

`hasFixedPersonality` 在 `CreateScriptedWildMon` 中为 0，因此性格值为 `Random32()`，而 `OT_ID_PLAYER_ID` 不消耗抽取：是否异色由该状态之后最初两次抽取决定。`setptr`, `callnative` 和 `setwildbattle` 返回 FALSE，因此桩代码留在 `gRngValue` 中的状态，就是 `CreateScriptedWildMon` 消耗的状态。

桩代码读取 `playerTrainerId`，地址为 `gSaveBlock2Ptr + 0x0A`（位于固定 IWRAM 地址的指针），因此相同字节可用于《火红》和《叶绿》。它写入一个字：`gRngValue`。搜索有上限；耗尽时，`gRngValue` 保持不变，遭遇为普通结果。每段桩代码暂存前都在 unicorn 下运行（`tests/test_native_script.py`），并将其结果与 `rng_countdown`.

### RAM 脚本可能无法从对战返回

`CB2_InitBattle` 和 `InitOverworldBgs` 调用 `MoveSaveBlocks_ResetHeap` [battle_main.c:614, overworld.c:1337]，将 `gSaveBlock1` 重新随机偏移 0..124 范围内的某个 4 的倍数 [`SAVEBLOCK_MOVE_RANGE` 128，load_save.c:75]。引擎在对战期间保留指向 `gSaveBlock1Ptr->ramScript.data.script` [`GetRamScript` 的指针，script.c:514]，因此恢复执行时脚本已不在那里，`dowildbattle` 之后的任何内容均不可达。

症状包括：意外触发第二场对战（落到 0xB6／0xB7）；正常退出（落到零填充，`nop`）；地图世界冻结，A、B、START 均无效（995 字节中第 972 字节的恢复点落在六字节的 `setptr` 记录内部，解码出一条永远等待的命令）。`releaseall` + `end` 无法修复此问题。

修复方法是从存档块之外启动对战，只需十个字节 [`rng_script.battle_and_exit`]:

```
setvar 0x8000, 0x02B7      ->  0x020370B4: B7 02  =  dowildbattle ; end
goto   0x020370B4
```

`gSpecialVar_0x8000` 不会移动，对战或地图世界代码也不会写入它。`ScriptContext_RunScript` 会在脚本停止时调用 `UnlockPlayerFieldControls()` [script.c:335]，因此 `end` 会交还控制权。任何 RAM 脚本都不能指望存档块地址跨越对战或地图加载仍保持有效。

## 选择性格与 IV

`--gift rng-mon-hunt`, `asm/field/mon-seek.s`，标志 ID 1019。检查全部四次抽取：性格值决定是否异色及性格（`personality % 25` [pokemon.c:5020]）；第 3 和第 4 次抽取为 IV [pokemon.c:1836，先 HP／攻击／防御，再速度／特攻／特防]。

```
--hunt-nature adamant,jolly   --hunt-iv speed=31 --hunt-iv attack=20   --hunt-cap N
```

捕获的鲤鱼王回读结果为 PID 0x01503B8A、异色值 4、爽朗、IV 6/2/25/28/12/7；`lcg.recover_wild_state` 得出状态 0x7041F74F，`rng_countdown` 复现了每个字段。

是否异色在包含十五条指令的热点循环内检查；除以 25 和 IV 比较仅对每 8192 个状态中的 1 个执行，因此增加条件会成倍增加所需迭代数，但不会拖慢单次迭代：

| 要求 | 平均多少状态命中一个 | 典型冻结时间 | 达到上限时的最坏情况 |
| --- | --- | --- | --- |
| 异色 | 8,192 | 0.02 秒 | 0.10 秒 |
| 异色 + 指定一种性格 | 204,800 | 0.55 秒 | 2.5 秒 |
| 异色 + 性格 + 一项 IV >= 20 | 546,133 | 1.5 秒 | 6.7 秒 |
| 异色 + 两项 IV = 31 | 8,388,608 | 22 秒 | 拒绝 |

`native_script.search_cost` 负责计算；若最坏情况超过 `--hunt-freeze-frames`（默认 900，约 15 秒），主机端会拒绝。搜索期间玩家看到静止画面，音乐继续播放。

`mon-seek.s` 在 163 字节暂存预算中占 160 字节：异色值的异或运算具有自反性，因此 `pidLo` 用两条指令返回，除数兼作循环计数器，IV 下限在第 30 位携带终止标记，且两个字段都移到第 27..31 位，使五位比较成为无符号比较。

## 脚本正文中的载荷

`setptr` 每个代码字节消耗六个脚本字节（操作码、立即数、4 字节地址）：995 字节 RAM 脚本正文中约能放 162 字节代码。引擎就地运行正文，从不读取最后一条命令之后的内容：

```
const u8 *GetRamScript(u8 objectId, const u8 *script)
{ ... return scriptData->script; }
```

[script.c:514]，来源为 `gSaveBlock1Ptr->ramScript.data.script`，因此追加到最后一条命令之后的字节会被作为存储空间投递，每个字节只占一个脚本字节。脚本运行所在帧内，存档块偏移固定，且 `&gSaveBlock1Ptr`（0x03004228）保存它，因此运行时读取可精确定位。`asm/field/ram-jump.s`（36 字节）是唯一需要暂存的部分：

|  | 暂存方式 | 正文方式 |
| --- | --- | --- |
| 每个载荷字节的成本 | 6 个脚本字节 | 1 个脚本字节 |
| 995 字节正文内的容量 | 162 字节代码 | 755 字节 |

```
setptr x36    the trampoline, into gDecompressionBuffer        216 bytes
callnative    -> trampoline -> payload -> back                   5
setwildbattle / setvar / goto                                   16
pad to a multiple of four                                        3
payload                                                        755
```

跳板执行尾部分支（`bx r0`, `lr` 保持不变），因此载荷的 `pop {r4-r7, pc}` 返回到 `ScrCmd_callnative` 的调用方。它首先检查 `ramScript.data.magic` 是否为 `RAM_SCRIPT_MAGIC` = 51 [script.c:12]；偏移错误时直接返回，遭遇为普通结果。

### 四字节对齐

THUMB `ldr rN, [pc, #imm]` 和 `adr` 使用 `Align(PC, 4)`。若偏差两字节，分支可以到达且代码会运行，但每个字面量池字都从晚两字节的位置读取。四字节对齐成立：`offset = Random() & ((SAVEBLOCK_MOVE_RANGE - 1) & ~3)` [load_save.c:75] 为 `& 0x7C`, `gSaveBlock1` 按字对齐，且 `RAMSCRIPT_BODY_OFFSET`（0x3624）保持该对齐。`native_script.emulate_body_script` 会通过遍历实际脚本字节发现未对齐（36 条 `setptr`、`callnative`、跳板的 `gSaveBlock1Ptr` 读取，以及跳入正文的分支）。

### 验证大小，而不仅是跳转

异色结果能确认跳转成功，却不能确认送达的大小。`asm/field/mon-seek-far.s` 之后添加非零填充直至第 995 字节；桩代码对其求和，仅在匹配时搜索。`InitRamScript` 会将剩余部分填零 [`ClearRamScript`，script.c:495]，因此投递不完整时不会改动 `gRngValue`。`--gift rng-mon-hunt-far` 携带 196 字节桩代码和 559 字节填充。

## 搜索不受额外抽取影响的结果

`asm/field/mon-seek-both.s`（232 字节，`--gift rng-mon-hunt-both`，标志 ID 1001）在两种布局下检查下限，覆盖全部三种方法。令 d3、d4、d5 为性格值之后的抽取：

| 方法 | 前三项（HP／攻击／防御） | 后三项（速度／特攻／特防） |
| --- | --- | --- |
| 1（无额外抽取） | d3 | d4 |
| 2 | d4 | d5 |
| 4 | d3 | d5 |

字 A 为 `d3 | d4<<15`，字 B 为 `d4 | d5<<15`。同时要求两者，使前三项下限应用于 d3 和 d4，后三项应用于 d4 和 d5，因此 Method 4 无需专门的字也能通过。

只有 IV 项的概率被平方：异色 + 爽朗 + 速度 >= 20 从每 546,000 个状态命中一个，变为每 1,456,000 个命中一个，典型耗时约 4 秒。上限采用 95% 覆盖率，因为未命中只需再按一次 A，而 99% 在运气不好时会耗时 18 秒。

状态 0xFCB5674F 在零售版上以 Method 1 生成了异色、爽朗、速度 22，且所有方法均通过：

| 方法 | IV | 下限 |
| --- | --- | --- |
| 1（无额外抽取） | 4/1/10/22/14/21 | 通过，主机实际生成的结果 |
| 2 | 22/14/21/25/1/18 | 通过 |
| 4 | 4/1/10/25/1/18 | 通过 |

状态 0x4FB97B07 精确预测了 PID，IV 来自 Method 4（速度 21，下限 20）：

```
  Method 1 (clean)  25/10/30/20/ 9/25
  Method 2 (stray)  20/ 9/25/21/ 3/ 1
  Method 4          25/10/30/21/ 3/ 1   <- the mon that appeared
```

## 搜索报告写入的位置

`asm/field/mon-seek-log.s`（288 字节，`--gift rng-mon-hunt-log`，标志 ID 1002）将 `{marker, start, found, iterations, cap}` 写入 `gSaveBlock1Ptr + 0x348C`, `u8 unused_348C[400]` [include/global.h]。没有代码写入 `unused_348C`，零售版存档中读到的值为零。该块位于 `ramScript` 之外，因此 `CalculateRamScriptChecksum` 保持不变，绑定得以保留；每次交谈覆盖日志。它能跨对战保留（`MoveSaveBlocks_ResetHeap` 会复制这些块），并在保存时写入闪存。

```
--buffer-script save-dump --dump-block sav1 --dump-offset 0x348C --dump-size 32
```

`native_script.decode_hunt_log` 读取它。搜索耗尽时写入 `found` 为 0，并带上标记。

|  |  |
| --- | --- |
| 迭代次数 | 603,745 |
| `lcg.distance(start, found)` | 603,745，差值 0 |
| 指令数（每次 15 条） | 9,056,175 |
| 每条指令 3 周期的模型 | 1.62 秒 |
| 玩家观察值 | 2–3 秒 |
| 推算值 | 3.7–5.6 周期／指令 |

`CYCLES_PER_INSTRUCTION_FROM_EWRAM` 为 3。观察时间来自秒表读数，而搜索时间呈指数分布；低估只会使冻结上限更早拒绝请求。

## 叶绿

桩代码无需移植即可运行：每个字面量都是链接期 IWRAM 字，或在《叶绿》中相同的常量，且 `TID ^ SID` 在运行时读取。绑定到超梦即可定向控制超梦遭遇；参见 [叶绿](frlg_leafgreen.md).
