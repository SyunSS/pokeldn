---
title: 《叶绿》及两款卡带的偏移映射
parent: FireRed and LeafGreen
nav_order: 6
---

# 《叶绿》及两款卡带的偏移映射

本节其余内容均从法语版《火红》（BPRF，版本 0x0A）读取。法语版《叶绿》为 BPGF、0x0A（`POKEMON LEAF` 位于其头部）。所有载荷在其中无需修改即可使用，但 ROM 地址不同。测量在神秘礼物菜单内运行，因此主机始终停留在其存档点。

## 测得的地址

| 符号 | 叶绿 | 火红 |
| --- | --- | --- |
| `gDecompressionBuffer` | 0x0201C000 | 相同 |
| 神秘礼物调用点 | 0x08148C50 | 0x08148C74 |
| `Random` | 0x080486B0 | 相同 |
| `SeedRng` | 0x080486D0 | 相同 |
| `gRngValue` | 0x03004220 | 相同 |
| `gPlayerParty` | 0x02024280 | 相同 |
| `gPlayerPartyCount` | 0x02024025 | 相同 |
| `gEnemyParty` | 0x02024028 | 相同 |
| `gSpeciesInfo` | 0x0824CDD8 | 0x0824CDFC |
| `CreateMon` | 0x08041150 | 相同 |
| `sEasyChatGroups` | 0x083E353C | 0x083E3700 |
| `gSpecialVar_0x8000` | 0x020370B4 | 相同 |
| `gSpecialVars` | 0x08163984 | 0x081639A8 |
| `gSaveBlock1Ptr` | 0x03004228 | 相同 |
| `gSaveBlock2Ptr` | 0x0300422C | 相同 |

`rom_map.LEAFGREEN` 保存这些地址及其证据；`rom_map.leafgreen(symbol)` 遇到表中不存在的符号时会抛出异常，而不会退回使用《火红》的地址。

测得的所有 IWRAM 和 EWRAM 地址都相同（同一套代码的链接期全局变量）；0x080486C8 以上的所有 ROM 地址均不同。十五个符号证实了这一点；新的 ROM 符号必须实测，而不是预测。

## 各区域的地址差

《火红》地址到对应《叶绿》地址的偏移，在至少八个区段内呈分段常数，且并不单调（靠低地址的四个区段，各自的差值都比其下方区段少四字节）：

```
+0x0   -0x2C   -0x28   -0x24   -0x20   -0x1C4   -0x124C   -0x1240   -0x12D8
```

`rom_map.leafgreen_guess(firered_address)` 会对已测区段内的地址给出结果，拒绝处理间隙。它用于定位转储，不说明内容。`pokeldn/frlg/rom/leafgreen_twins.py` 保存 738 对地址，每个地址均从对应卡带读取（其中约 200 对是具名函数）；`leafgreen_twins.leafgreen(address)` 在存在地址对时给出精确结果，否则退回使用 `leafgreen_guess`.

### 边界

```
step             span                          what is in it
0     -> -0x2c   644 B, 0x0807CF68..0x0807D1EC  title_screen.o
-0x2c -> -0x28    62 B, 0x080DE2E4..0x080DE322  mystery_event_script.o
-0x28 -> -0x24    90 B, 0x081480CE..0x08148128  mystery_gift.o
-0x24 -> -0x20    31 B, 0x08251D8E..0x08251DAD  pokemon.o rodata
-0x20 -> -0x1c4 1209 B, 0x083B7B47..0x083B8000  title_screen.o rodata
-0x1c4 -> -0x124c  30 KB, 0x0843AFFF..0x08442800  graphics
-0x124c -> -0x1240 17 KB, 0x08442BFF..0x08447000  graphics
-0x1240 -> -0x12d8 63 KB, 0x0844F3FF..0x0845F000  graphics
```

边界就是两个版本存在差异的区域本身，其中不适用任何地址差。其范围从最后一个符合旧地址差的窗口延伸至第一个符合新地址差的窗口。`rom_map.LEAFGREEN_DELTA_BOUNDARIES` 保存这些边界；测试会断言边界表与区段表一致。0x0843C800 以上，两款卡带保存的字节不同（版本专属图形），因此无法根据内容定义该处的地址差。

## 测量方法

### 配对常量

`RAND_MULT` 在两款卡带上扫描时各得到十一处匹配，跨越 1.3 MB 按顺序一一配对。

### 以指针为查找特征

凡是对已在两台主机上测得地址的引用，都能构成一个配对点。在每款卡带上扫描其各自的 `gSpeciesInfo`，各得到 56 处字面量池引用，按地址递增，一一对应：

| 地址差 | 火红地址范围 | 配对匹配数 |
| --- | --- | --- |
| 0 | 0x080001BC .. 0x0805359C | 42 |
| −0x2C | 0x080CBFB0 .. 0x080CE36C | 2 |
| −0x28 | 0x080EBA14 .. 0x0813E8CC | 9 |
| −0x24 | 0x0815A3F4 .. 0x0815A630 | 3 |

0x0815A630 以上没有匹配。

### 在没有符号的地方构造查找特征

0x083E3700 以上没有任何已命名内容。从一台主机转储 1 KB；其中恰好出现一次、且四个字节互不相同的一个字可以作为某位置的指纹，在另一台主机上扫描它即可得到该位置的地址。ROM 内任意位置，每个点运行两次即可：

| 火红 | 叶绿 | 查找特征 | 地址差 |
| --- | --- | --- | --- |
| 0x086003E0 | 0x085FF108 | 0xE1926F4D | −0x12D8 |
| 0x086803FC | 0x0867F124 | 0xC35D61AE | −0x12D8 |

每次扫描都在 2 MB 窗口内返回一处匹配。两个点结果一致，并不能约束两点之间的范围，因此还需要一个校验点。脚本层扫描结果：

| 查找特征 | 取自 | 在叶绿中找到的地址 | 地址差 |
| --- | --- | --- | --- |
| 0x49050B80 | 位于其内部：`ScrCmd_special` | 0x0806D7F4 | 0 |
| 0x4831D940 | 处理函数块的顶部 | 0x080701C0 | 0 |
| 0x49040A00 | 标志／变量工作函数内部 | 0x08071E1C | 0 |
| 0x47708008 | 位于其上方：`FlagGet` | 0x08071FC4 | 0 |
| 0x18210094 | 位于其内部：`AddBagItem` | 0x0809DA80，火红为 0x0809DAAC | −0x2C |

如果扫描了错误的主机，也会得到地址差 0，因此最后一行取自边界以上的位置，必须返回发生偏移的结果。

### 字面量池：现成的指针表

函数会将其访问的地址保存在函数体之后的池中，因此 1 KB 的代码窗口里就有几十个指针。当代码所属区段的地址差已知时，无需额外工作就能在两款卡带上定位该窗口。m4a 代码位于 `lib_text`（−0x24 区段），其字面量池指向 ROM 高地址端的声音数据。两次 1 KB 转储各得到 24 个池字，其中 13 个相同（RAM 地址和常量），五个卡带指针均发生相同的偏移：

| 火红 | 叶绿 | 地址差 |
| --- | --- | --- |
| 0x0847DCF8 | 0x0847CA20 | −0x12D8 |
| 0x0847DDAC | 0x0847CAD4 | −0x12D8 |
| 0x0847DF10 | 0x0847CC38 | −0x12D8 |
| 0x0849758C（`gMPlayTable`) | 0x084962B4 | −0x12D8 |
| 0x084975BC（`gSongTable`) | 0x084962E4 | −0x12D8 |

`gMPlayTable` 和 `gSongTable` 在两款卡带上都相隔 0x30：四个十二字节的 `struct MusicPlayer`，与 `sound/music_player_table.inc` 中的内容一致。

两组各含 16 块的字面量池配对，分别提供了 550 和 288 个配对位置，并发现了 −0x20 区段，它位于 −0x24 和 −0x1C4 之间，跨度超过一兆字节。必须按代码偏移配对，绝不能按索引配对：将分别含 552 和 550 个字的池按顺序配对，在第一个不匹配之后就会产生虚构的地址差（−0x53BADA0）。

一条 `bl` 是相对寻址的，因此两款卡带中的相同指令所解析的目标，其差值等于目标位置的地址差；16 KB 的处理函数窗口内有 834 条。`tools/frlg/cartridge_pair.py` 会从两款卡带均有转储的每个窗口读取字面量池和 `bl` 指令：共 1592 个点，每个位置均完成配对（734／734、834／834），每个窗口内有四种不同地址差，没有离群值。

### 在同一地址转储两款卡带

在地址差为 d 的共同地址处，《叶绿》的块相当于《火红》的块偏移了 d；当 |d| 小于一千字节时，互相关可直接读出 d。`memory-dump-scatter` 将相同的 27 个地址发送到两台主机。在块内逐窗口测试哪个地址差仍然匹配，可以将阶跃定位到字节：五个代码阶跃的边界总计 2036 字节，全部 272 个 special 都有对应的《叶绿》地址。

较大的间隙可能隐藏多个阶跃：从 −0x1C4 到 −0x12D8 的 421 KB 内有三个。图形数据具有自相似性，因此每次读数都要与其他候选项比较评分：在 0x08442800，−0x124C 得分 436／436，−0x1240 为 6.9%，−0x12D8 为 2.7%；在 0x08457000，74.7% 对 57.3% 的结果记录为无法判定。

## 参照火红表格读取叶绿转储

这里的所有表格都从《火红》读取。`tools/frlg/rom_functions.py --console leafgreen` 通过实测的对应地址转换条目、函数体和名称，并丢弃落在边界内的条目：213 个场景函数体中恢复了 184 个，252 个可定位 special 中恢复了 33 个，且存在与《火红》相同的三个未命名调用目标。

两款卡带在 0x0807AF04 以下的脚本层完全相同（`rom_map.SHARED_WITH_LEAFGREEN_THROUGH`）：`gScriptCmdTable` 处理函数块（0x0806D7C0..0x080700B8）、脚本引擎（`ScriptContext_Stop`, `ScriptJump`, `ScriptCall`, `ScriptReturn`、原生指针设置函数 `callnative` 所使用的）、`GetVarPointer`, `VarGet`, `FlagSet`, `FlagClear`, `FlagGet`，以及 `_call_via_r0` 跳板。

## 地图世界与异色超梦

以下内容中的每个字面量：[搜索桩代码](frlg_rng.md)，都是与《火红》共用的链接期 IWRAM 字（`gRngValue`, `gSaveBlock1Ptr`, `gSaveBlock2Ptr`），因此桩代码无需移植即可运行。RAM 脚本需要绑定到地图对象：`initramscript` 接受地图组、地图编号和对象 ID，`GetRamScript` 则运行该脚本，替代对象自身的脚本 [field_control_avatar.c:458]。华蓝洞窟 B1F 是第 1 组第 74 张地图 [data/maps/map_groups.json]；超梦是对象 3 [data/maps/CeruleanCave_B1F/map.json]。`rng-mon-hunt-both` 使用 `setwildbattle`（种类 150、等级 70）绑定到那里后，会替换超梦的脚本，并立即开始一场定向生成超梦的对战（已在零售版《叶绿》验证为异色）。

-
-
-

绑定期间，主机报告未持有神奇卡片；卡片本身仍完好无损（[唯一的 RAM 脚本槽位](frlg_gift.md#the-one-ram-script-slot)).

## 转储区域不能发生变化

对 `memory-dump` 0x03004220（`gRngValue`，每帧两轮）进行转储时，会在传输中途失败并显示 *连接错误*：CRC 计算与发送发生在不同帧。转储在帧间变化的区域会导致 CRC 校验失败；同等大小的 ROM 区域则不会。机制和防护措施参见：[主机上运行的代码](frlg_rom.md#repointing-the-consoles-outgoing-message).

起始地址提高 4 字节即可读取存档块指针。两个指针一起移动，使用同一个按 4 对齐、取值范围为 0..124 的偏移，由 `SetSaveBlocksPointers` 随机生成 [load_save.c:75]。

## 英语版构建

`pret/pokefirered` 将两款卡带均构建为 REVISION 10，即 Switch 发行版的修订版本：

```
make firered_switch     -> pokefirered_switch.gba    baa452d0b24629dd7782cfc07a8984085dde1311
make leafgreen_switch   -> pokeleafgreen_switch.gba  62b9fc77549dbc67032eb6cbd0ea6ad3b825690f
```

使用 binutils 和 `pret/agbcc` 构建时，两者均与反编译工程的 sha1 一致；不匹配的构建不可用。ROM 绝不提交到仓库。

这是英语发行版：在同一地址处，法语版主机与英语版构建只有 3.7% 的字节相同，因为法语字符串长度不同。它可作为第二组卡带，采用相同源码和链接顺序，且每个符号均已知。

### 偏移：从法语地址到英语地址

偏移呈分段常数，仅在某个对象因语言不同而改变大小时发生阶跃；连续代码区间长达数万字节，其中一个达 1.3 MB。两种独立读取方法在共同适用的所有位置均一致：

-
- 转储：在英语 ROM 中恰好出现一次的 16 字节窗口，可以定位相同的法语版字节；一千字节的代码可提供数百次投票，块内的阶跃会表现为两个连续区间。
  ```
  ./.venv/bin/python tools/frlg/english_build.py --offsets
  ```

### 校验

英语 ELF（与链接映射不同，它包含静态函数）可通过偏移为法语地址命名。与 `worker_names` 对照，其中每个名称都由主机自身的函数体测得：232 个一致，0 个不一致。`GetBoxMonData2` 就是 `__attribute__((alias("GetBoxMonData3")))` [pokemon.c:3332]；读取器保留同一地址对应的所有名称。

```
./.venv/bin/python tools/frlg/english_build.py --check
```

来自英语版构建的名称属于推断。`rom_map.CALLABLE` 表示已在硬件上调用并产生效果；`worker_names` 表示主机自身的函数体按源码顺序调用了它。`pokeldn/frlg/rom/english_names.py` 保存以这种方式命名的 7573 个法语版函数地址（`scripts/gen_english_names.py`），以及各个偏移区间。`rom_functions` 最后读取这些内容，并标记为 `[english]`，因此推断绝不会覆盖主机函数体确定的名称；`gen_worker_names` 传入 `with_english=False`.

177 个未命名调用目标中，158 个落在实测偏移区间内并得到命名。其余位于区间之间，交由 `english_names.BRACKETED` 处理：仅当两个相邻偏移中有一个恰好落在函数起点、另一个没有时，才使用前者命名（`[english?]`）。最终剩下两个。另有三个目标各自从十几个函数体被调用，它们被识别为 `__divsi3`, `__modsi3` 和 `__umodsi3`，即 agbcc 的除法辅助函数。

### 英语版卡带组自身的地址差映射

比较两个英语 ROM，得到与法语卡带实测相同的六种地址差，顺序如下：

```
+0x0   -0x2c   -0x28   -0x24   -0x20   -0x1c4
```

每个阶跃均位于版本间有差异的对象内部（`title_screen.o`, `mystery_event_script.o`, `mystery_gift.o`, `pokemon.o`），其中不存在两个构建共用的符号；字节比较将各阶跃范围限定为 79..1606 字节。经偏移映射转换后，预测的五个法语版边界全部落在硬件实测的范围内。

```
./.venv/bin/python tools/frlg/english_build.py --boundaries
```

### 陷阱

-
-
-
-

## 不可用的参考

`gSongTable` (347 `{header, ms, me}` 个条目）在 9 KB 内密集存放 122 个乐曲头部，因此只能确定一个位置。

《火红》的 ROM 数据终止于 0x086ABE68（最后一个乐曲头部）与 0x08800000 之间：0x08800000 读取结果全为 `0xFF`，0x08E00000 全为 `0x00`，0x08680000 则是高熵数据。
