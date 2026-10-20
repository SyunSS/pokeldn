---
title: ROM 映射
parent: FireRed and LeafGreen
nav_order: 4
---

# ROM 映射

此处每个地址均通过神秘礼物链路从主机自身卡带读取（`memory-dump`, `memory-scan`, `table-scan`, `call-chain`，参见 [主机上运行的代码](frlg_rom.md)). `pokeldn/frlg/rom/rom_map.py` 记录各地址的获取方式；`tests/test_rom_map.py` 将其与转储核对。卡带镜像与所有记录均一致。

这些地址属于法语《火红》，卡带 BPRF，软件版本 0x0A。《叶绿》的地址参见 [叶绿](frlg_leafgreen.md).

## 卡带镜像

Switch 发行版将 GBA ROM 作为其 RomFS 中的唯一文件。

| 游戏 ID | RomFS 文件 | 大小 | sha1 |
| --- | --- | --- | --- |
| 01004B3023412000 | `/FireRed_f.gba` | 16777216 | `07566b82dbd2a91321698f730f6400ae4c56ddf1` |
| 010087C02342E000 | `/LeafGreen_f.gba` | 16777216 | `9f774956dfbad7f69ddb91fb91d2c26e54408f75` |
| 0100554023408000 | `/FireRed_e.gba` | 16777216 | `baa452d0b24629dd7782cfc07a8984085dde1311` |
| 010034D02340E000 | `/LeafGreen_e.gba` | 16777216 | `62b9fc77549dbc67032eb6cbd0ea6ad3b825690f` |

0xA0 处的头部内容为 `POKEMON FIRE` `BPRF` 和 `POKEMON LEAF` `BPGF`，版本 0x0A。

法语《火红》1.0.1 更新未改变卡带：在零售版主机上通过 `rom-checksum` 读取其客体 ROM，并逐字节读取唯一不同的区段，结果与 `FireRed_f.gba` 在 `0x08000000..0x09000000` 范围内一致，包装层加载时的三处补丁除外（[frlg_rom.md](frlg_rom.md)，断点钩子）；`0x09000000..0x0A000000` 在两者上均读到开放总线值（每个半字的值为其自身地址除以二）。

英语版两款卡带（`BPRE`, `BPGE`，版本 0x0A，基础 v0 软件包）与 `pokefirered_switch.gba` 和 `pokeleafgreen_switch.gba` 逐字节相同，与 `pret/pokefirered` 固定的版本一致：反编译工程就是英语发行版的精确映射。

Program NCA 只有一个 CTR RomFS 分区，没有更新，因此 `bktr_read.py` 拒绝处理它；`scratchpad/base_romfs.py` 可以读取：

```
./.venv/bin/python scratchpad/base_romfs.py "$NSP" --list
./.venv/bin/python scratchpad/base_romfs.py "$NSP" --extract /FireRed_f.gba --out scratchpad/FireRed_f.gba
```

`rom_map.CREATE_MON` 为 0x08041150，镜像在该处读到 `f0b5 4746 80b4 87b0`，这是 `asm/create-mon.s` 所依赖的函数序言。任意函数体都可从镜像离线读取。

## 两个构建中的 EWRAM 地址相同

英语版构建的 EWRAM 符号地址就是法语卡带的 EWRAM 地址。独立测得的三处地址与 `pokefirered_switch.elf`:

```
gDecompressionBuffer  0x0201C000
gPlayerParty          0x02024280
gPlayerPartyCount     0x02024025
```

IWRAM 则不可直接套用：`gSaveBlock1Ptr` 在英语版构建中为 0x030042D8，在卡带上为 0x03004228。

从区域中扣除 ELF 里所有大小已知的 EWRAM 符号，剩下一个未被任何符号占用的区间（`nm -S pokefirered_switch.elf`, `scratchpad/ram_survey.py`):

```
highest symbol end   0x0203FBAC
EWRAM end            0x02040000
```

## 英语版卡带

神秘礼物主机端向英语《火红》（`BPRE`）和英语《叶绿》（`BPGE`）发送基于各自地址构建的代码。`pokeldn/frlg/rom/builds.py` 为每款卡带保存一张表（`BPRF`, `BPGF`, `BPRE`, `BPGE`, `BPRS`, `BPGS`, `BPRD`, `BPGD`, `BPRI`, `BPGI`, `BPRJ`, `BPGJ`）：IWRAM 全局变量、载荷、钩子或场景桩代码调用的 ROM 函数、`call-chain` 命名的函数，以及礼物携带的 ROM 数据指针。

主机端根据主机 `MysteryGiftLinkGameData` 中的游戏代码选择表 [mystery_gift.c:369]，该信息先于所有依赖地址的内容到达。不同构建中字节不同的载荷，会分别构建；若主机没有对应表，或被本次运行排除（`--console-build CODE`，或 `--version` 针对另一个版本），则拒绝且不发送任何内容。不依赖构建的载荷可以发往任何主机。

英语地址来自 `pokefirered_switch.elf` 和 `pokeleafgreen_switch.elf`，每个地址都与零售版镜像核对：函数通过其字节验证，IWRAM 全局变量通过引用它的字面量池验证，并与法语卡带中相同的池配对。

| 区域 | 法语版到英语版 |
| --- | --- |
| EWRAM | 不变 |
| IWRAM 0x03000000..0x03001B6F | 不变 |
| 英语版 IWRAM 0x03002370..0x0300602F，从 `gMain`（法语版 0x030022D0，英语版 0x03002380）起 | +0xB0 |
| 英语版 IWRAM 0x03006090..0x03007583，`gSoundInfo`（法语版 0x03005F80）至 `gFlash` | +0x110 |
| IWRAM 0x03007590 及以上：栈、中断向量 | 不变 |
| ROM | 无单一偏移；每个函数均单独查找 |

英语版的值：`gRngValue` 0x030042D0、`gSaveBlock1Ptr` 0x030042D8、`gSaveBlock2Ptr` 0x030042DC、`gIntrTable[4]` 0x030027E0、`gLastWrittenSector` 0x03004650、`gSaveCounter` 0x03004660。英语《叶绿》的 RAM 与英语《火红》相同；常驻钩子使用的地址中仅 `m4aSoundMain` 会移动（0x081E07C4，对照 0x081E07E8）。

`tests/test_frlg_english_cartridges.py` 在两个零售版镜像上通过各卡带自身的 `Client_RunBufferScript` 运行英语载荷；若 `scratchpad/frlg_en/` 中没有镜像则跳过。

英语《火红》（美国版 v0，`0100554023408000`）在游戏数据中报告 `BPRE`，接受并显示神奇卡片，并运行英语版的 `call-chain`: `SpeciesToNationalPokedexNum`，地址为 `0x08046A41` 对种类 277 返回 252，而 `VarGet`，地址为 `0x08071CD5`，会正常返回。已在模拟主机上验证；两个会话均以成功消息结束，并因此保存 [mystery_gift_menu.c:1379]。

## BIOS 包装函数

`libagbsyscall.s` 按反编译工程的顺序链接为一整块 THUMB `svc N ; bx lr` 指令对 [src/libagbsyscall.s]，两款卡带完全相同，但《叶绿》地址低 0x24：

| 包装函数 | svc | 火红 | 叶绿 |
| --- | --- | --- | --- |
| `ArcTan2` | 0x0A | 0x081E21D4 | 0x081E21B0 |
| `BgAffineSet` | 0x0E | 0x081E21D8 | 0x081E21B4 |
| `CpuFastSet` | 0x0C | 0x081E21DC | 0x081E21B8 |
| `CpuSet` | 0x0B | 0x081E21E0 | 0x081E21BC |
| `Div` | 0x06 | 0x081E21E4 | 0x081E21C0 |
| `LZ77UnCompVram` | 0x12 | 0x081E21E8 | 0x081E21C4 |
| `LZ77UnCompWram` | 0x11 | 0x081E21EC | 0x081E21C8 |

游戏的 LZ77 流可安全用于 VRAM（没有复制距离为 1 的情况）：《火红》中 0x08D2FBD4 处的妙蛙种子正面图（676 字节）和 0x08D2FE78 处的调色板（40 字节），与 `gbagfx` 根据反编译工程素材写出的内容逐字节一致。LZ77 无法缩小载荷代码（常驻钩子压缩后相同大小或更大）；它仅对超过 1024 字节的数据有帮助。

## 第一个锚点

`anchors` 返回 `Client_RunBufferScript` 调用之后的地址，即 `0x08148C75`。其他所有地址都由此延伸得到：调用者的字面量池与 `bl` 目标可识别后续函数，它指出的指针表又提供更多地址，而每个条目都必须落在已知函数序言上（`scratchpad/rom_read.py`).

0x08148A00 处转储反汇编为 `Client_RunBufferScript` [mystery_gift_client.c:274]，`cmp r0,#1` 位于 0x08148C74。其字面量池：

```
0x08148C88 -> 0x0201C000   gDecompressionBuffer
0x08148C8C -> 0x0300422C   &gSaveBlock2Ptr
0x08148C90 -> 0x03004228   &gSaveBlock1Ptr
```

`MysteryGiftClient_CallFunc` 随后位于 0x08148C94，从 0x0845DBD0（sClientFuncs）复制八个字，由 `client->funcId` 索引，位置为 `[r0,#8]`。八个条目均落在 `push {r4, lr}` 上；条目 7 为 0x08148C61，即 `anchors` 测得的函数。

从 0x08000000 转储的卡带头部证实，执行的是 `REVISION >= 0xA` 分支：

```
entry      b 0x08000204
title      POKEMON FIRE          [0xA0]
game code  BPRF                  [0xAC]  BPR = FireRed, F = French
version    0x0a                  [0xBC]
header checksum 0x5d, recomputed 0x5d -> VALID
```

## 四张函数表

```
gScriptCmdTable              0x08163650   214 entries   the field script commands
gSpecialVars                 0x081639A8    21 entries
gSpecials                    0x081639FC   444 entries   gSpecialsEnd 0x081640EC
gStdScripts                  0x081640EC    10 entries
gMysteryEventScriptCmdTable  0x081DE144    17 entries
```

`script_data` 从 0x08163650 延伸到 0x081DE188，后者是 `lib_text` 的起点。

### `gSpecialVars`，通过形态发现

其前十二个字各比前一个恰好大 2：`gSpecialVar_0x8000` 至 `0x800B` 是十二个连续的 `u16` [event_data.c:16]。`table-scan` 一次运行即可返回序列起点和首值：`gSpecialVars` = 0x081639A8，`gSpecialVar_0x8000` = 0x020370B4，这是 2.75 MB 中唯一的此类序列。范围根据链接顺序确定：`script_data` 位于所有 `.text` 对象之后 [ld_script_rev10.ld:318]，而 `.rodata` 起始位置低于 `gSpeciesInfo`. `gSpecialVar_0x8000` 是 `EWRAM_DATA`，一个可安全作为常量使用的链接期全局变量。

### `gScriptCmdTable`

`script_data` 以 `gScriptCmdTable` 开头（214 个四字节条目），并紧接着放置 `gSpecialVars` [ld_script_rev10.ld:318]，因此其起点为 0x08163650，一次 856 字节转储即可读取。全部 214 个字都是指向 10488 字节范围内的 THUMB 指针；只有 0 和 213 共用地址，即两个 `ScrCmd_nop`，而 `ScrCmd_nop1` 在索引 1 处具有独立地址。偏差一个条目的读取不可能产生该结果。

```
0x23 callnative   0x0806D854      0x44 additem      0x0806DED0
0x25 special      0x0806D7EC      0x79 givemon      0x0806F834
0x29 setflag      0x0806E0EC      0x90 addmoney     0x0806F998
```

`pokeldn/frlg/rom/scrcmd_names.py` 按操作码为每个条目命名；`scrcmd_names.handler("additem")` 提供离线查询。

### `gSpecials` 和 `gStdScripts`

`ScrCmd_special` 用 u16 索引 `gSpecials`，根据 `gSpecialsEnd` 检查边界，并通过跳板调用 [scrcmd.c:101]。其字面量池给出 `gSpecials` = 0x081639FC 和 `gSpecialsEnd` = 0x081640EC：0x6F0 = 444 × 4，即 `data/specials.inc` 的 444 个条目，从 `gSpecialVars + 21 * 4` 开始。调用经过 0x081E2224，比 `_call_via_r1` 低四字节。转储得到 444 个 THUMB 指针，其中 171 个 `NullFieldSpecial` 索引在两次转储中均对应同一地址。`rom_map.SPECIAL_ADDRESSES` 保存这些内容；`rom_map.special_function("HealPlayerParty")` 按名称解析某一个。

`gStdScripts` 紧随 `gSpecials`，位于 `data/event_scripts.s` 中，受一个 `.align 2` 约束，而该约束已满足，因此位于 0x081640EC：十个字，指向 0x081A76xx..0x081AB5xx，五个 msgbox 脚本相互间距在四十字节之内。

### `gMysteryEventScriptCmdTable`，通过实时结构体获取

表中 17 个条目的地址互不相关，但表地址保存在结构体中：

```
static void InitMysteryEventScript(struct ScriptContext *ctx, u8 *script)
{
    InitScriptContext(ctx, gMysteryEventScriptCmdTable, gMysteryEventScriptCmdTableEnd);
```

[mystery_event_script.c:52]。`struct ScriptContext` 将这对指针保存在 +0x5C 和 +0x60 [include/script.h]，两者所指地址相差 68，而上下文为 `EWRAM_DATA static struct ScriptContext sMysteryEventScriptContext` [mystery_event_script.c:27]。`table-scan --table-delta 0x44 --table-runlen 2` 扫描 EWRAM 可找到它；扫描必须在同一次启动中执行过神秘事件礼物之后进行，因为脚本运行前上下文为零。

86 次调用扫描全部 256 KB EWRAM，得到一处匹配，位于 0x0203AA94，内容为 0x081DE144：`sMysteryEventScriptContext` = 0x0203AA38，表地址 = 0x081DE144。17 个条目均为奇数、互不相同、位于 `.text` 内，跨度为 1084 字节，顺序与 `mystery_event.OPCODE_NAMES`:

| # | 命令 | 处理函数 |  | # | 命令 | 处理函数 |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | `nop` | 0x080DE451 |  | 9 | `givenationaldex` | 0x080DE61D |
| 1 | `checkcompat` | 0x080DE401 |  | 10 | `addrareword` | 0x080DE641 |
| 2 | `end` | 0x080DE3F5 |  | 11 | `setrecordmixinggift` | 0x080DE66D |
| 3 | `setmsg` | 0x080DE465 |  | 12 | `givepokemon` | 0x080DE681 |
| 4 | `setstatus` | 0x080DE455 |  | 13 | `addtrainer` | 0x080DE78D |
| 5 | `runscript` | 0x080DE49D |  | 14 | `enableresetrtc` | 0x080DE7D5 |
| 6 | `initramscript` | 0x080DE5B5 |  | 15 | `checksum` | 0x080DE7E9 |
| 7 | `setenigmaberry` | 0x080DE4B9 |  | 16 | `crc` | 0x080DE831 |
| 8 | `giveribbon` | 0x080DE581 |  |  |  |  |

`data/mystery_event_script_cmd_table.o(script_data)` 是 `script_data` 的最后一个成员 [ld_script_rev10.ld:318-330]；0x081DE188 读到 `0x4C41B510`, `push {r4, lr}`，这是 `libgcnmultiboot` 的序言，位列 `lib_text`.

## 从表条目定位背后的函数

处理函数接受一个 `struct ScriptContext *`，从脚本读取参数。其 `bl` 目标按地址顺序排列，对应反编译工程中按源码顺序的调用（`VarGet(ScriptReadHalfword(ctx))` 每个参数一次，最后再一次调用 [scrcmd.c:463-590]），因此一次转储即可按位置命名工作函数：

```
ScriptReadHalfword   0x0806D1E8      AddBagItem           0x0809DA70
VarGet               0x08071DDC      RemoveBagItem        0x0809DBC4
GetVarPointer        0x08071CC8      CheckBagHasSpace     0x0809D9EC
FlagSet              0x08071EF4      CheckBagHasItem      0x0809D92C
FlagClear            0x08071F1C      AddPCItem            0x0809DDB4
FlagGet              0x08071F44      IncrementGameStat    0x080587A4
```

`ScrCmd_additem` 与反编译工程逐条指令一致（`(u8)quantity` 类型转换对应 `lsls r1, #24; lsrs r1, #24`），并通过 0x020370CC 存储，`gSpecialVar_Result`. `ScrCmd_random` 的第三次调用为 0x080486B0，即 `Random`，此前已从其自身字面量池独立发现。

`scratchpad/handler_workers.py` 按顺序打印每个处理函数的 `bl` 目标，并为已知目标显示名称。`tools/frlg/rom_functions.py --table specials|field|mystery-event|callable` 对整张表执行此操作，用下一个条目和自身函数尾声限定每个函数体，并打印下一次运行计划：把尚未获取的条目聚合成已排序的 `--dump-address` 窗口。

ROM 使用 agbcc 构建，THUMB 函数以 `pop {r4,r5,r6}; pop {r1}; bx r1`（BC70 BC02 4708）结束，绝不使用 `pop {..., pc}`。仅寻找 0xBDxx 的读取器会读入下一个函数。`pokeldn/frlg/rom/thumb.py` 还会匹配 `bx Rn`，且只有后面跟着函数序言时，才将返回指令视为边界。

### 离线命名 300 个工作函数

`scripts/gen_worker_names.py` 将每个已转储函数体与反编译源码逐项配对，同时处理全部四张表，并写入 `pokeldn/frlg/rom/worker_names.py`。包含四项检查：

| 检查 | 排除的问题 |
| --- | --- |
| 长度 | 内联、`__umodsi3`、把宏误读为函数调用 |
| 锚点 | 函数体错位：每个实测地址必须重新落到它自身的名称上 |
| 一致性 | 同一目标被两个调用者赋予不同名称 |
| 链接顺序 | 名称在 ROM 中的位置错误 |

在 164 个对齐函数体中，锚点检查命中了 68 个不同的实测名称，共 557 次，每次均落到该名称自身地址。agbcc 按定义顺序输出翻译单元，`ld_script_rev10.ld:53` 按布局顺序列出对象，因此名称与锚点组成一条递增序列；检查保留最长递增链，而非在首次断裂处停止。

两个锚点之间若恰好只有一个未命名目标和一个源码调用，就能强制对应，并可放宽长度规则。开放间隙（首个锚点之前、最后锚点之后）不会命名任何内容。

读取源码时：

-
-
-
-

`rom_map` 命名的内容在反编译工程中也存在，并由所有可达该地址的函数体确认（`rom_map.DECOMP_NAMES` 为连接操作）：

| `rom_map` 名称 | 反编译工程 | 一致的函数体数 |
| --- | --- | --- |
| `GET_MON_DATA` | `GetMonData3` | 15 |
| `SCRIPT_CONTEXT_SET_NATIVE` | `SetupNativeScript` | 11 |
| `SET_RESPAWN` | `SetLastHealLocationWarp` | 1 |
| `SCRIPT_MOVEMENT_START` | `ScriptMovement_StartObjectMovementScript` | 2 |
| `CHANGE_AMOUNT_MONEY_BOX` | `ChangeAmountInMoneyBox` | 2 |
| `ME_CHECK_COMPATIBILITY` / `ME_SET_INCOMPATIBLE` | `CheckCompatibility` / `SetIncompatible` | 1 / 3 |

`GetMonData` 是根据参数数量分派的宏 [include/pokemon.h:343]；`GetMonData2` 就是 `__attribute__((alias("GetMonData3")))` [pokemon.c:2970]：一个地址，三个名称。

若到达某工作函数的命令数恰好与反编译工程给出的调用数量一致，就能确认该函数：`Compare` 由八条 `compare_*` 命令到达，`StringCopy` 由七条 `buffer*` 命令，加上两个从 `gText_BigGuy`. `0x0806D0EC` 是 `StopScript(ctx)` [script.c:76]，为 `ScrCmd_end` 所调用；`ScriptContext_Stop(void)` [:360] 位于 0x0806D418，由十二个处理函数调用，以及除 `ScrCmd_waitstate` 之外的整个 `return TRUE`.

### 混用镜像的两个隐患

-
-

### 实测内容

所有表背后的每个函数体均从卡带读取：213 个场景命令、17 个神秘事件操作码、27 个可调用函数、272 个 special。

-
-
-
-
-

神秘事件虚拟机的工作函数：

| 工作函数 | 地址 | 调用者 |
| --- | --- | --- |
| `StringExpandPlaceholders` | 0x0800CADC | 每个留下消息的处理函数的最后一次调用 |
| `RunScriptImmediately` | 0x0806D438 | `runscript`，位于 `ScriptReadWord` 之后，无其他调用 |
| `InitRamScript` | 0x0806D5F0 | `initramscript` |
| `GiveGiftRibbonToParty` | 0x080A43B0 | `giveribbon`，两次调用中的第一次 |
| `EnableRareWord` | 0x080C1658 | `addrareword`，两次调用中的第一次 |
| `CheckCompatibility` | 0x080DE300 | `checkcompat`，分支之前 |
| `SetIncompatible` | 0x080DE330 | `checkcompat` 的 else 分支；两个停用操作码各自唯一的调用 |
| `memcpy` | 0x081E44F4 | `addtrainer`，第二次调用 |
| `CalcCRC16` | 0x080489A0 | `crc`，其唯一工作函数 |
| `StringCopyN` | 0x0800C8CC | `setenigmaberry` 和 `givepokemon`，各两次 |
| `StringCompare`, `SetEnigmaBerry` | 0x0800C938, 0x080A01B0 | `setenigmaberry` |
| `VarSet` | 0x08071DF8 | `setenigmaberry`，最后一次调用 |
| `SpeciesToNationalPokedexNum` | 0x08046994 | `givepokemon` |
| `GetSetPokedexFlag` | 0x0808C860 | `givepokemon`，两次：先 SEEN（已见），再 CAUGHT（已捕获） |
| `ItemIsMail`, `GiveMailToMon2`, `CompactPartySlots` | 0x0809BB18, 0x0809B964, 0x080971FC | `givepokemon` |

`memcpy`（libgcc，位于 `lib_text`）处于 0x081E44F4，高于 0x081DE188，与边界一致。

`VarSet` 只能从这里到达：没有 ScrCmd 函数体调用它（`setvar` 通过 `GetVarPointer` 的结果存储，因此 `call-chain` 的 `prev`). `event_data.c` 按顺序声明 `GetVarPointer`, `VarGet`, `VarSet`，地址为 0x08071CC8 < 0x08071DDC < 0x08071DF8；最后两个之间的 0x1C 是 `VarGet` 的函数体。

调用跳板为 `bx rN` 加上对齐填充，每个四字节：已测得 r0 为 0x081E2224、r1 为 0x081E2228、r3 为 0x081E2230，因此 0x081E2234 是 `_call_via_r4`，0x081E223C 是 `_call_via_r6`.

## 存档备份与恢复

`LoadGameSave` [decomp:src/save.c:803] 和 `gRfu.sendQueue.count` [link_rfu_2.c:3131] 在每款卡带上均与英语修订版 0x0A ELF 匹配，匹配时屏蔽 `bl` 目标和字面量池字。`LoadGameSave` 以 `push {r4-r6, lr}; lsls r0, r0, #24` (`70 b5 00 06`）开头，字面量池包含 `gDecompressionBuffer`, `0x0201C000`，全部十二款均如此。队列计数由一个 12 字节叶函数读取，即 `ldr r0, =gRfu; ldr r1, =0x8D2; adds r0, r0, r1; ldrb r0, [r0]; bx lr`，每款卡带各有一份。

| 卡带 | `LoadGameSave` | `gRfu` | `gRfu.sendQueue.count` |
| --- | --- | --- | --- |
| `BPRE` | `0x080DDBF4` | `0x03005590` | `0x03005E62` |
| `BPGE` | `0x080DDBC8` | `0x03005590` | `0x03005E62` |
| `BPRF` | `0x080DDFD4` | `0x030054E0` | `0x03005DB2` |
| `BPGF` | `0x080DDFA8` | `0x030054E0` | `0x03005DB2` |
| `BPRD`, `BPRI` | `0x080DDF14` | `0x030054E0` | `0x03005DB2` |
| `BPGD`, `BPGI` | `0x080DDEE8` | `0x030054E0` | `0x03005DB2` |
| `BPRS` | `0x080DDFFC` | `0x030054E0` | `0x03005DB2` |
| `BPGS` | `0x080DDFD0` | `0x030054E0` | `0x03005DB2` |
| `BPRJ` | `0x080DED68` | `0x03005520` | `0x03005DF2` |
| `BPGJ` | `0x080DED3C` | `0x03005520` | `0x03005DF2` |

`sSaveSlotLayout` 在全部十二款上都一致，扇区 ID 4 除外：拉丁字母语言卡带为 3816 字节，日语卡带为 3776 字节。

# 读取主机的脚本

已测得 `gScriptCmdTable`，且操作数宽度由反编译工程的宏生成（`scripts/gen_scrcmd_args.py` → `pokeldn/frlg/rom/scrcmd_args.py`：每个 `.macro` 将操作码作为 `.byte` 输出，然后为每个参数输出一个 `.byte`/`.2byte`/`.4byte`），因此 `memory-dump` 加上 `scrcmd.disassemble` 即可读取卡带中的任意脚本：

```
0x081A7624  6A  lock
0x081A7625  5A  faceplayer
0x081A7626  67  message 0x00000000
0x081A762B  66  waitmessage
0x081A762C  6D  waitbuttonpress
0x081A762D  6C  release
0x081A762E  03  return
```

这就是 `Std_MsgboxNPC` [data/scripts/std_msgbox.inc]。证据在于每段脚本停止的位置：从每个 `gStdScripts` 条目开始遍历，必须恰好在下一个条目前的字节遇到终止符；任何位置的宽度错一字节都会导致失步。

## 条件宏

十一种宏包含条件正文。生成器遍历每个分支，遇到未知子宏时抛出异常。

| 命令 | 宽度 | 结构 |
| --- | --- | --- |
| `applymovement` | 7 字节 | `.ifb \map` 分支 |
| `waitmovement`, `removeobject`, `addobject` | 3 字节 | `.ifb \map` 分支 |
| `applymovementat`, `waitmovementat`, `removeobjectat`, `addobjectat` | 9、5、5、5 字节 | 备选分支 |
| `warp` 以及另外八种传送 | 8 字节 | `formatwarp` 子宏 |
| 十条 `buffer*` 命令 | 4 字节 | `stringvar` 子宏 |
| `showobjectat`, `hideobjectat`, `resetobjectsubpriority` | 5 字节 | `map` 子宏 |
| `trainerbattle` | 6 + 4..16 字节 | 依赖类型的分支 |

`warp` 为先 `.byte 0x39` 再 `formatwarp`：一条指令，被调用者被内联。`giveitem` 为先 `loadword` 再 `callstd`：两条指令，从不内联。只有当宏内每条路径都以自身的字面操作码字节开头，且不会到达其他命令宏时，它才是命令宏。

`trainerbattle` 的头部包含 type、trainer 和 localId，随后是由类型决定的一至四个指针。其格式为 `scrcmd_args.VARIABLE`；类型不在反编译工程的十种类型中时，会使 `scrcmd.shape` 返回 `None`.

0x081A7699..0x081A77A3 是 `data/scripts/trainer_battle.inc`。这些宏使 `applymovement` 为 7 字节，`waitmovement` 为 3 字节；若将其读作固定宽度命令，就会使该区域失步。正确读取结果：

```
0x081A76A8  4F  applymovement 0x800F, 0x081A77B0     @ VAR_LAST_TALKED, Movement_RevealTrainer
0x081A76AF  51  waitmovement 0x0000
0x081A76B2  26  specialvar 0x800D, 0x0036            @ VAR_RESULT, Script_HasTrainerBeenFought
```

即 `EventScript_TryDoNormalTrainerBattle` [data/scripts/trainer_battle.inc:8]。该区域由首尾相接的标签构成，提供七项边界测试；`goto` 与 `end` 和 `return` 一样是终止符，因为 `EventScript_NoTrainerBattle` 位于某个终止符之后的字节 [:17]。五个标准脚本只使用七种固定宽度命令，不足以验证整张表；训练家对战区域全部 266 字节作为固定测试数据保存在 `tests/test_script_cmd_table.py`.

## 为操作数命名

`tools/frlg/script_read.py DUMP.bin --base ADDR`:

```
0x081A76A8  4F  applymovement 0x800F (VAR_LAST_TALKED), 0x081A77B0
0x081A76B2  26  specialvar 0x800D (VAR_RESULT), 0x0036 (Script_HasTrainerBeenFought)
0x081A76BC  06  goto_if 0x05 (!=), 0x081A76CD
0x081A76C2  25  special 0x0038 (PlayTrainerEncounterMusic)
```

-
-
-

变幻洞窟计数器在 SaveBlock1 + 0x1048 处变化；`GetVarPointer` 为 `vars[idx - VARS_START]`，因此它是变量 0x4024，即 `VAR_ALTERING_CAVE_WILD_SET`. `tests/test_script_symbols.py` 保存其名称。

## 追踪脚本可到达的内容

`scrcmd.follow` 从一组入口点追踪每个 `goto`, `call`, `goto_if` 和 `call_if`，收集所有到达但转储中不包含的地址。数据指针（`text`, `movements`、多选列表）只报告，不继续追踪。`scrcmd.dump_plan` 将缺失项转换为 `--dump-address` 行，按收益从大到小排序。

`charmap.decode` 用于名称（固定宽度、无控制码，未知字节显示为 `.`）；对话需要 `charmap.decode_message`. `scrcmd.data_pointers` 和 `scrcmd.read_string` 解码转储包含的内容。全部十个标准脚本的代码和文本均从主机读取。

若已知命令的操作数超出转储末尾，说明转储不完整，读取器会明确报告。

# 种类表

`gSpeciesInfo` = 0x0824CDFC，步长 28。

以 `friendship`, `growthRate` 和 `eggGroups` 为查找特征，按反编译工程的 26 字节步长搜索，16 MB 中没有任何匹配；卡带步长为 28。数据与英语反编译工程一致：`CalculateMonStats` [pokemon.c:2095] 根据五只队伍宝可梦的种族值、等级、IV、EV 和性格重新计算，复现了全部 30 项已存储能力值。

梦幻、时拉比和基拉祈的六项种族值均为 100，因此 `0x64646464` 位于条目偏移 0 和 2，无论步长如何，其中一个必然按字对齐：

```
scan: 3 match(es) for 0x64646464 in 0x08000000..0x08400000
   0x0824DE80   0x0824E970   0x0824FAB8
```

间距 2800 和 4424，分别对应 100 和 158 个 28 字节条目。从基址前 60 字节开始转储，读取的 34 个条目（884 字节）全部与反编译工程一致；每个条目额外的两个字节都是 `00 00` 填充。

对反编译工程建模时的陷阱：`[SPECIES_NONE] = {0},` 是单行块，会被多行正则吞掉；`genderRatio` 是宏 `PERCENT_FEMALE(x)`, `noFlip` 是不一定被设置的位域，而十六进制的 `#define` 会漏过只匹配十进制的正则。

## 查找 `CreateMon`，以该表为线索

扫描 `0x0824CDFC` 可找到每个含有 `&gSpeciesInfo` 的字面量池：在 `0x08028000..0x08048800` 内有 31 处匹配，低于 `Random` 所在的 0x080486B0。其中五处恰好相隔 `0x14`，这是一个函数的多个池，因此数量不能作为证据，对象边界才可以。最大间隙（37 KB）在 `battle_ai_switch_items.c:88` 以下，而不在 `pokemon.o` 处。下一个间隙为 15.6 KB，对应 `src/battle_controller_link_opponent.o`，它从不引用 `gSpeciesInfo`.

在 `pokemon.o` 的块中，第一处匹配是 `CreateMon` [pokemon.c:1755]，逐条指令均一致：

| 符号 | 地址 | 确定方式 |
| --- | --- | --- |
| `CreateMon` | `0x08041150` | 反汇编 |
| `ZeroMonData` | `0x08041090` | 其第一次调用 |
| `CreateBoxMon` | `0x080411C0` | 其位于 ZeroMonData 和 SetMonData 之间的调用 |
| `SetMonData` | `0x08043A78` | 先以 56（`MON_DATA_LEVEL`）调用，再以 64（`MON_DATA_MAIL`）及 255（`MAIL_NONE`) |
| `CalculateMonStats` | `0x08041B78` | 其最后一次调用 |

## 西班牙语火红卡带

西班牙语《火红》基础 v0（`0100EB702342C000`，显示版本 1.0.0）包含 `FireRed_s.gba`，游戏代码为 `BPRS`，修订版本为 0x0A。16 MiB ROM 的 SHA-256 为 `d4dee5aeb5313e073d6067bee37278b0204886958467633978bb746bbe3d5b76`。其软件包的四个 NCA 签名、分区头部哈希、PFS0 与 IVFC 块哈希，以及 CNMT 内容哈希均通过验证。控制元数据中的标题为“宝可梦 火红版（西班牙语版）”和“宝可梦 火红版”。

`builds.BPRS` 为原生礼物、活动宝可梦和常驻钩子提供西班牙语地址。`vendor/gblink-cards/symbols.json` 提供 167 个卡片符号；生成器的语言 ID 为 7。主机端在发送载荷前，会根据主机游戏数据选择 `BPRS`。西班牙语《叶绿》（`BPGS`）也有自己的实测表，见 [国际版修订版本 0x0A 卡带](#the-international-revision-0x0a-cartridges).

函数先通过唯一的函数体窗口，与逐字节一致的英语反编译工程匹配，然后使用屏蔽指针字和 THUMB BL 操作数的指令序列匹配。RAM 或数据指针从对应已映射函数的字面量池读取。共用同一指令序列的小函数需要独立引用来确认：`IsEnoughMoney` 调用 `GetMoney`，地址 0x080A376C；`SpeciesToNationalPokedexNum` 位于 0x080469A8，读取 0x0824B9DE 的表，其中种类 277 的条目返回 252。这些地址均单独查得；即使同一构建内部，ROM 偏移也会变化。

| 符号 | 西班牙语火红 |
| --- | --- |
| `gRngValue`, `gSaveBlock1Ptr`, `gSaveBlock2Ptr` | 0x03004220, 0x03004228, 0x0300422C |
| `gMain`, `gIntrTable[4]`, `gSoundInfo` | 0x030022D0, 0x03002730, 0x03005F80 |
| `VBlankIntr`, `Client_RunBufferScript` | 0x0800071C, 0x08148CD0 |
| `CreateMon`, `GetMonData3`, `Random` | 0x08041164, 0x080432F8, 0x080486C4 |
| `CB1_Overworld`, `CB2_Overworld`, `RunTextPrinters` | 0x08059E5C, 0x08059EDC, 0x08002D50 |
| `m4aSoundMain`, `ReadFlash` | 0x081E089C, 0x081E224C |
| `MapGridGetElevationAt`, `MapGridGetCollisionAt` | 0x0805C658, 0x0805C6D8 |
| 居合斩、碎岩、怪力消息的返回指针 | 0x081C1909, 0x081C19FD, 0x081C1AE6 |

场景招式的返回指针位于其脚本的八字节 `loadword` 和消息调用序列之后。徽章检查指向 0x081C1901、0x081C19F5 和 0x081C1ADE 的消息脚本。翻译后文本的长度改变了每条消息与其恢复脚本之间的距离。

全部 44 张卡片均通过模拟的主机端／客户端交互接收，并在该 ROM 的 mGBA 中绑定到妈妈运行。随附的 4 倍速卡片跳板将 0x0203FC01 安装到 `gIntrTable[4]`，并在 0x0203FBFC 保留 0x0800071D。按下 R、松开、再次按下时，它分别额外分派三对、三对和零对地图回调，并执行四次、四次和零次文本处理，每帧均调用一次原始 VBlank 处理函数（`tests/test_team_cards.py`).

`tests/test_frlg_english_cartridges.py`, `tests/test_noclip.py` 和 `tests/test_follower.py` 包含位于 `scratchpad/frlg_es/FireRed_s.gba` 的西班牙语镜像；不存在镜像时跳过基于 ROM 的检查。卡带自身的神秘礼物客户端从训练家探针返回，创建一只带校验和、语言为 7 的皮卡丘，调用 `GetVarPointer`，安装常驻钩子，并加载保存在存档中的钩子。碰撞和跟随检查也使用西班牙语地址表运行。

# 法语简易聊天词汇表

全部 1006 个依赖语言的简易聊天词均从主机 ROM 读取。`pokeldn/frlg/text/easychat_french_words.py` 是该表；`easychat_french.french(id)` 根据该表提供查询。

## 槽位问题

简易聊天 ID 为 `(group << 9) | index`，表示一个槽位。`pokeldn/frlg/text/easychat_words.py` 来自英语反编译工程，命名的是英语 ROM 在该槽位保存的词；每个本地化 ROM 都有自己的 `gEasyChatGroup_*` 表。邮件、训练家卡片上的话语、来访训练家的台词、`--denied-message` 和问卷门控都依赖法语表。在主机上显示时，`EC_WORD_ENJOY` 显示为 STRESSE（紧张），`EC_WORD_DONE` 显示为 FURAX（暴怒），`SPEECH/12` 显示为 LES（法语复数定冠词）。

## 查找表

`sEasyChatGroups[]` 是包含 22 个 `struct EasyChatGroup { const void *wordData; u16 numWords; u16 numEnabledWords; }` 的表 [src/data/easy_chat/easy_chat_groups.h:26]，每项 8 字节。组 8、9 和 10（结尾、感受、状态）各有 69 个词，69 个均启用，因此 `0x00450045` 会以 8 字节间隔出现三次。`--buffer-script memory-scan --scan-word 0x00450045` 扫描 0x08000000..0x08480000，恰好返回这三处匹配。范围依据：`src/easy_chat.o(.rodata)` 是 `ld_script.ld` 中第 99 个对象，低于 `src/mystery_gift_client.o(.rodata)` (#182, `sClientFuncs` 已知）。该表位于 0x083E3700。

全部 22 个条目的计数都与英语版构建相同，因此同一个 ID 在两种语言中表示同一个槽位。词数组及其文本跨越 0x083DE2C8..0x083E3700，共 21560 字节，每组字符串位于自身数组与下一数组之间。`string-gather` 每次运行读取一组；条目 42 和 60 是 STRESSE（紧张）和 FURAX（暴怒），与显示结果相同。`tests/test_easychat_french.py` 要求显示证据与 ROM 证据一致。

`TRAINER/11` 为 DRESSEUR（训练家，单数）；表中没有 DRESSEURS（训练家，复数）。

## 表中揭示的情况

与英语表的差异取决于分组：

-
-
-

专有名词组差异很小；普通词汇差异很大。

807 个槽位无需读取：`EC_GROUP_POKEMON`, `POKEMON_2`, `MOVE_1` 和 `MOVE_2` 从 `gSpeciesNames` / `gMoveNames` 打印 [easy_chat.c:155]，由主机本地化。`easychat.species_word(55)` 和 `easychat.move_word(177)` 构建它们；`easychat.is_language_safe` 识别它们。

## 使用

```
from pokeldn.frlg.text import easychat, easychat_french
easychat_french.french(easychat.WORDS["enjoy"])     # 'STRESSE', not 'enjoy'
easychat_french.render(ids)                          # the line as the console will print it
easychat_french.check(ids, strict=True)              # raises on anything unread
```

`check` 可捕获不代表词的 ID，例如超出所属组末尾的索引。

```
POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/frlg_mg_host.py --live --keys PROD_KEYS \
    --buffer-script string-gather --gather-address 0x083DF5C0 --gather-count 42 \
    --gather-stride 12 --dump-file DUMP.bin --version firered    # one group per run
./.venv/bin/python scratchpad/ec_words.py --group 4 DUMP.bin
./.venv/bin/python scratchpad/ec_words.py --report
```

`scratchpad/ec_locate.py` 从扫描结果中找到表，并根据反编译工程的计数检查转储；`scratchpad/ec_words.py` 保存 22 个词数组地址。

《叶绿》整个简易聊天区域相当于《火红》偏移 −0x1C4，词汇完全相同：22 个条目，每个计数均相等，对某一组执行 `string-gather` 会在相同槽位读取到相同的词。`easychat_french` 可为两款主机提供查询。

## 国际版修订版本 0x0A 卡带

六种语言版本各包含一个 16 MiB GBA ROM，头部修订版本为 `0x0A`。主机端提供英语、法语、德语、意大利语、西班牙语和日语两款游戏的地址表。

函数通过唯一指令窗口与英语修订版 0x0A ELF 配对，必要时屏蔽相对调用和指针字面量。RAM 全局变量和指针表从对应字面量池读取。场景招式脚本族作为命令序列配对，屏蔽其中的 ROM 指针；本地化文本位于这些序列之后。`SpeciesToNationalPokedexNum` 与两个相邻的转换函数一起配对，因为这三个叶函数共用相同的指令序列。

| 卡带 | ROM 文件 | SHA-256 |
| --- | --- | --- |
| `BPRD` | `FireRed_d.gba` | `04f43a43f7cf9109561cd1744d108f50202c931ce31b30abaa6f18950824d20d` |
| `BPRE` | `FireRed_e.gba` | `d32c8df8702293716ad8de68755fe5903161f4829a0a2e486bfa7e74a0b62e94` |
| `BPRF` | `FireRed_f.gba` | `9edf7a3137536b0ccf024a732025da9a0ea1330eb9fd13b2ffed19f5e008c147` |
| `BPRI` | `FireRed_i.gba` | `cf7fa25cf57fbf12f24709efdd1d1aa8056efb4e9b6520ac7d068d3de13ff135` |
| `BPRJ` | `FireRed_j.gba` | `e2cdfb0415ef09e887e9d27b925ff02a713a92f004843490cf6b88b68db6cd01` |
| `BPRS` | `FireRed_s.gba` | `d4dee5aeb5313e073d6067bee37278b0204886958467633978bb746bbe3d5b76` |
| `BPGD` | `LeafGreen_d.gba` | `eb0e340b5efb3ccb7bab104183d2050fa834261dd816c5ad8221e4e98c04342b` |
| `BPGE` | `LeafGreen_e.gba` | `993a8a5695a4f7e4dfe8ceec55beb43e020e82b492854d457d4aa3f864d20f08` |
| `BPGF` | `LeafGreen_f.gba` | `751346c16c0cf3a3ec601d6c2d3c482b54609c5d00ca74f2f668d75b31b8efde` |
| `BPGI` | `LeafGreen_i.gba` | `b99b9c58c83a61b5bd8a1a69b6f21ce0cfab8d1f6065b53b81a323801c9b2895` |
| `BPGJ` | `LeafGreen_j.gba` | `a2aa939a23a36610902be51169042efac78f2f6db6a433e06443a2ee09d4f19e` |
| `BPGS` | `LeafGreen_s.gba` | `a943ecfd6560115b184dc244daed71ba328a67334f343eb35b39932c3ce7c731` |

| 符号 | 德语火红 | 德语叶绿 | 意大利语火红 | 意大利语叶绿 | 西班牙语叶绿 |
| --- | --- | --- | --- | --- | --- |
| `gmain` | `0x030022D0` | `0x030022D0` | `0x030022D0` | `0x030022D0` | `0x030022D0` |
| `sb1ptr` | `0x03004228` | `0x03004228` | `0x03004228` | `0x03004228` | `0x03004228` |
| `sb2ptr` | `0x0300422C` | `0x0300422C` | `0x0300422C` | `0x0300422C` | `0x0300422C` |
| `rng` | `0x03004220` | `0x03004220` | `0x03004220` | `0x03004220` | `0x03004220` |
| `vblank_intr` | `0x08000730` | `0x08000730` | `0x08000730` | `0x08000730` | `0x0800071C` |
| `create_mon` | `0x08041178` | `0x08041178` | `0x08041164` | `0x08041164` | `0x08041164` |
| `client_run_buffer_script` | `0x08148BA4` | `0x08148B80` | `0x08148BE4` | `0x08148BC0` | `0x08148CAC` |
| `save_slot_layout` | `0x083FCEC0` | `0x083FCCFC` | `0x083F464C` | `0x083F4488` | `0x083F7674` |

基于 ROM 的测试运行每款受支持卡带的 `Client_RunBufferScript`, `CreateMon`, `GetVarPointer`, `VBlankIntr` 和已存储钩子加载器。碰撞测试在安装钩子后调用卡带的 `MapGridGetCollisionAt` 和 `MapGridGetElevationAt`。

西班牙语《火红》的 `EventScript_CurrentTooFast` 起始于 `0x081AA346`，包含 `lockall` (`0x69`）。先前的卡片表指向 `0x081AA347`，即其后的 `loadword` (`0x0F`）。现在生成的 HM 卡片使用该脚本的入口。

### 日语版布局

日语《火红》和《叶绿》使用不同的 EWRAM 布局。其队伍起始于 `0x020241E0`，玩家角色位于 `0x02036FA8`，对象事件位于 `0x02036D68`，调色板渐变位于 `0x020379E8`，禁用野生遭遇的字节位于 `0x02038624`. `RunTextPrinters`，地址为 `0x08002D38`，读取其数组指针 `0x02020030`，所用字面量位于 `0x08002D60`，并按 `0x20` 递增，位置为 `0x08002D94`。国际版数组则按 `0x24`.

两款日语卡带均使用 `gMain`，地址为 `0x030022E0`, `gSaveBlock1Ptr`，地址为 `0x03004238`, `gSaveBlock2Ptr`，地址为 `0x0300423C`, `gRngValue`，地址为 `0x03004230` 和 `gIntrTable[4]`，地址为 `0x03002740`. `gSpecialVar_0x8000` 为 `0x02036FE8`；队伍数量位于 `0x02023F85`.

日语版 SaveBlock1 为 `0x3D40` 字节；国际版 SaveBlock1 为 `0x3D68`。最后一块（扇区 ID 4）在日语版覆盖 `0xEC0` 字节，国际版覆盖 `0xEE8`。存档注入和原生闪存修补使用所选卡带的长度。`RamScript` 保持相同偏移：校验和 `0x361C`、魔数 `0x3620`、脚本正文 `0x3624`。基于 ROM 的校验和测试会从每个 ROM 的 `sSaveSlotLayout` 中读取块长度。

日语版神奇卡片占 164 字节，神奇新闻占 224 字节。`BPRJ` 的 `SaveWonderCard` 位于 `0x081481F4`，复制 164 字节并计算校验和；`BPGJ` 使用 `0x081481CC`。对应的验证例程为 `0x08148250` 和 `0x08148228`。在基于 ROM 的测试中，这两个例程会保存并验证应用生成的卡片。卡片 CRC 位于 SaveBlock1 `+0x3204`，其数据位于 `+0x3208`；新闻数据起始于 `+0x3124`. `BufferCardText`，地址为 `0x08149934`，读取字节 10..27 的标题、28..40 的副标题、41..120 中四行各 20 字节的正文，以及 121..160 中两行各 20 字节的页脚。内置配信为日语卡带使用这种紧凑布局。原生的 `.wc3` 布局说明参见 [礼物文件](gifts.md#native-formats).

日语卡带以不同活动编号列出神秘礼物朋友。其 `sAcceptedActivityIds` 中神奇卡片和神奇新闻的条目为 6 和 7（`BPRJ` `0x08410EC4` 和 `0x08410EC8`, `BPGJ` `0x08410E4C` 和 `0x08410E50`），而其他所有卡带均为 21 和 22 [src/data/union_room.h:405-406]；其 `LINK_GROUP_UNK_11` 列表在相同位置也包含 6 和 7。广播 21 的主机端永远不会出现在日语版朋友画面中。接受的 RFU 序列号为 `{0x0002, 0x7F7F}` (`BPRJ` `0x083FC378`），而国际版为 `{0x0002, 0x7F7D}`。日语和法语《火红》的 Switch 可执行文件代码相同；两者仅字符串和 ROM 路径不同，全部十二款游戏都将 `0x01006fa0233f8000` 列为首个本地通信 ID。

两款日语卡带均在 Unicorn 下执行原生客户端、`CreateMon`、变量查询、VBlank 处理函数和已存储钩子加载器。`CreateMon` 为种类 25 生成日语昵称“ピカチュウ”（皮卡丘）。日语名称使用假名表，训练家名称上限为五个字符；拉丁重音字母与假名共用字节值。内置礼物文本仍使用拉丁字母，日语卡带上会去除重音。对话文本每 26 个字符换行，两行后换页，因为日语对话字体更宽。日语版 Team 卡片使用其源码中的日语结构体大小和动态菜单宽度；两个提示被缩短以符合 RAM 脚本上限。

新增的德语和意大利语两款卡带、西班牙语《叶绿》及日语两款卡带均进行 mGBA 卡片检查。这些检查基于提取出的卡带 ROM，属于离线检查。

### 零售版验证

| 卡带 | 零售版硬件上的验证内容 | 来源 |
| --- | --- | --- |
| 意大利语叶绿（`BPGI`，修订版本 `0x0A`) | 全部 41 个 `Build` 字段均与主机内存匹配；跟随功能安装；大师球卡片与道具投递 | [贡献者验证](https://github.com/Decryptu/pokeldn/issues/13) |
