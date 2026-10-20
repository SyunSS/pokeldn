---
title: 在主机上运行代码
parent: FireRed and LeafGreen
nav_order: 3
---

# 在主机上运行代码

神秘礼物客户端通过两个解释器运行发送给它的代码：`CLI_RUN_MEVENT_SCRIPT`（操作码15）将字节交给神秘事件虚拟机，`CLI_RUN_BUFFER_SCRIPT`（操作码21）则交给CPU。两者都不需要利用故障、预先准备存档或进行任何设置；主机始终停留在神秘礼物菜单。

本页地址对应法语版《火红》，卡带编号BPRF，软件版本0x0A。《叶绿》的地址见[《叶绿》](frlg_leafgreen.md)；相关表格见[ROM映射](frlg_rom_map.md).

# 神秘事件虚拟机

这是一个独立解释器[src/mystery_event_script.c]，具有自己的17条命令表[data/mystery_event_script_cmd_table.s]，不同于神秘卡片的交付脚本所编译到的场景脚本虚拟机。`pokeldn/frlg/rom/mystery_event.py`可汇编每一条命令（`MysteryEventScript.blob()`保存数据，汇编器解析指针）。所有操作码均已在零售版硬件上验证。

## 命令表

| # | 命令 | 操作码字节后的操作数 | 返回值 | 效果 |
| --- | --- | --- | --- | --- |
| 0 | `nop` |  | FALSE | 无操作 |
| 1 | `checkcompat` | u32 base, u16, u32, u16, u32 | TRUE | 兼容性检查关卡 |
| 2 | `end` |  | TRUE | `StopScript` |
| 3 | `setmsg` | u8 selector, ptr | FALSE | `StringExpandPlaceholders(gStringVar4, str)`，条件是选择器为`0xFF`或等于状态值 |
| 4 | `setstatus` | u8 | FALSE | `ctx->data[2] = value` |
| 5 | `runscript` | ptr | FALSE | `RunScriptImmediately`，作用于场景脚本 |
| 6 | `initramscript` | u8 group, u8 map, u8 object, ptr, ptr | FALSE | `InitRamScript`，绑定到任意地图和对象 |
| 7 | `setenigmaberry` | ptr | FALSE | 写入`gSaveBlock1Ptr->enigmaBerry` |
| 8 | `giveribbon` | u8 index, u8 ribbonId | FALSE | 为队伍中每只非蛋宝可梦添加一枚礼物奖章 |
| 9 | `givenationaldex` |  | FALSE | `EnableNationalPokedex()` |
| 10 | `addrareword` | u8 | FALSE | `EnableRareWord`（简易聊天中的一句流行语） |
| 11 | `setrecordmixinggift` |  | TRUE | 无实际作用：`SetIncompatible` |
| 12 | `givepokemon` | ptr | FALSE | 将完整的`struct Pokemon`及其附带邮件加入队伍 |
| 13 | `addtrainer` | ptr | FALSE | 一个188字节的`BattleTowerEReaderTrainer` |
| 14 | `enableresetrtc` |  | TRUE | 无实际作用：`SetIncompatible` |
| 15 | `checksum` | u32, ptr, ptr | TRUE | 状态值为1，条件是`CalcByteArraySum`在指定范围内的结果不匹配 |
| 16 | `crc` | u32, ptr, ptr | TRUE | 同上，但使用`CalcCRC16` |

## `checkcompat`是可选的

`checkcompat`位于所有官方脚本开头，并检查语言及版本掩码（反编译项目中的`LANGUAGE_MASK`为英语）。脚本可以跳过它：

```
bool32 RunMysteryEventScriptCommand(struct ScriptContext *ctx)
{
    if (RunScriptCommand(ctx) && ctx->data[3])   // data[3] is set only by checkcompat
        return TRUE;
    return FALSE;
}
...
while (MEventScript_Run(&ret));
```

`RunScriptCommand`[script.c:107]在一次调用中循环，直到某条命令返回TRUE。没有`checkcompat`, `data[3]`会保持为0：脚本运行到第一条返回TRUE的命令（通常为`end`），然后外层的`while`停止。掩码不会产生影响，指针按`operand - ctx->data[1] + ctx->data[0]`重定位，其中`data[1]`为0（仅由`checkcompat`设置），而`data[0]`为主机的1024字节`client->recvBuffer`：操作数N表示所发送数据中偏移N字节的位置。`checkcompat`是汇编器唯一允许在其后放置代码的命令。

## 返回通道

`MEventScript_Run`将状态值写入`client->param`[mystery_event_script.c:75]；`CLI_LOAD_TOSS_RESPONSE`将其载入`MG_LINKID_RESPONSE`[mystery_gift_client.c:204]。以下四条客户端命令返回由脚本选择的u32值：

```
CLI_RECV MG_LINKID_RAM_SCRIPT
CLI_RUN_MEVENT_SCRIPT
CLI_LOAD_TOSS_RESPONSE
CLI_SEND_LOADED
```

`setstatus`可设置任意值。原有状态值如下：

| 状态值 | 含义 |
| --- | --- |
| 0 | 没有命令设置过状态值 |
| 1 | `setenigmaberry`无法验证树果，或出现`checksum`/`crc`不匹配 |
| 2 | 成功；每条完成自身工作的操作码都会设置此值 |
| 3 | `SetIncompatible`，或者`givepokemon`发现队伍已满 |

`CLI_COPY_RECV_IF`和`CLI_COPY_RECV_IF_N`可据此让客户端脚本分支[mystery_gift_client.c:170]（未使用）。

菜单根据`CLI_RETURN` [`GetClientResultMessage`，mystery_gift_menu.c:884]打印结果，因此`setmsg`在这里不可见。只有成功消息才会进入`MG_STATE_SAVE_LOAD_GIFT`[:1379]；若不经过此处，事件写入的内容会在重置后丢失；`CLIENT_SCRIPT_MEVENT_DONE`因此会返回`CLI_MSG_CARD_RECEIVED`，即使没有卡片也是如此。`CLI_MSG_BUFFER_SUCCESS`（13）是另一个成功退出路径，会打印由`CLI_COPY_MSG`推送的64字节。

### 探测脚本

`--gift mystery-event-probe`不会造成影响：`givenationaldex`在全国图鉴已开启时不执行任何操作，而`checksum`只进行读取。

```
givenationaldex; setstatus 42; checksum 1026, 16, 31
```

| 状态值 | 所证明的情况 |
| --- | --- |
| 42 | 命令链已运行至末尾，且指针操作数是发送缓冲区内的偏移量 |
| 1 | 命令链已运行，但重定位后的指针没有指向探测字节 |
| 2 | `givenationaldex`已运行，但其后没有任何命令运行 |
| 0 | 已进入虚拟机，但未执行任何命令 |
| 无返回 | 客户端脚本结构有误，而非虚拟机有误 |

`checksum`是终止命令，匹配时保留此前的状态值。零售版《火红》返回42。

## `givepokemon`

`pokeldn/frlg/save/mevent_pokemon.py`构建载荷：先是100字节的加密队伍宝可梦，随后是34字节的`struct Mail`，主机会从`pointer + sizeof(struct Pokemon)`. `--gift mystery-event-celebi`提供一个现成实例。与场景脚本的`givemon`不同，它会：

-
-
-

状态值2表示成功，3表示队伍已满且未写入任何内容。绝不要在它后面放置`setstatus`。

构建器强制规避的陷阱：

-
-
-
-

## `initramscript`

`initramscript 3, 0, 2`将场景脚本绑定到组3、地图0、对象2，即真新镇南部的胖子。重启后，他会说出脚本中的台词，并展开`{PLAYER}`。

`CLI_SAVE_RAM_SCRIPT`使用`InitRamScript_NoObjectEvent`（MAP_UNDEFINED，对象0xFF）[script.c:578]，只有送货员的`GetSavedRamScriptIfValid`[:554]会读取它，而且要求存在有效的神秘卡片。实际坐标会进入`GetRamScript(gSpecialVar_LastTalked, script)`[:514, field_control_avatar.c:458]，它会用该脚本替代对象自身的脚本运行，并忽略卡片。`gSpecialVar_LastTalked`是对象的局部ID，按`map.json`的顺序从1开始编号。

代价是失去神秘卡片（[唯一的RAM脚本槽](frlg_gift.md#the-one-ram-script-slot)）；在下一张普通卡片重新占用该槽之前，会话日志会显示“未持有神秘卡片”。绑定期间，对象失去自身脚本：若绑定到固定遭遇战对象，该脚本就会替代该遭遇战。

## 陷阱

-
-
-
-
-
-

## 连接方式

-
-
-
-

# 原生ARM代码

```
case CLI_RUN_BUFFER_SCRIPT:
    memcpy(gDecompressionBuffer, client->recvBuffer, MG_LINK_BUFFER_SIZE);
    client->funcId = FUNC_RUN_BUFFER;
    ...
static u32 Client_RunBufferScript(struct MysteryGiftClient * client)
{
    u32 (*func)(u32 *, struct SaveBlock2 *, struct SaveBlock1 *) = (void *)gDecompressionBuffer;
    if (func(&client->param, gSaveBlock2Ptr, gSaveBlock1Ptr) == 1)
```

[mystery_gift_client.c:237,276]。每个载荷都基于五个事实：

-
-
-
-
-

`gDecompressionBuffer`位于0x0201C000（通过`anchors`测得）。载荷与位置无关。

## 构建

应用的神秘礼物构建器使用相同工具链（`pokeldn/frlg/rom/custom_code.py`）汇编ARM源代码，或接受原始的`.bin`，并在发送之前先在模拟主机上运行它。`.pokegift`文件包含已编译的ARM字节、目标卡带及响应设置。[神秘礼物文件](gifts.md#console-code)介绍了打包和共享方法。

-
-
-
-
-

每次都先离线测试：

```
./.venv/bin/python -m pytest tests/test_buffer_script.py -q
./.venv/bin/python scratchpad/mg_client_harness.py --buffer-script -v
```

在硬件上，主机停留于“神秘礼物→神秘卡片→朋友”并加入主机端。下方运行命令中，`HOST`代表`POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/frlg_mg_host.py --live --keys PROD_KEYS --dump-file DUMP.bin`，而`IP_HOST`代表`./.venv/bin/python -u bin/frlg_mg_host.py --over-ip --dump-file DUMP.bin`，它通过局域网向模拟主机提供服务，无需无线电和密钥。在`DUMP.bin`出现之前，切勿向主机端发送SIGTERM；该文件会在以下事件发生数秒后写入：`Buffer script dump: N bytes`:

```
until ls DUMP.bin >/dev/null 2>&1; do sleep 2; done
```

## 载荷可存放的位置

缓冲区脚本每帧都会重新复制，因此它对自身映像的任何写入都无法保留。需要在菜单关闭后继续存在的代码应放在游戏从不写入的位置：

```
0x0203FC00 .. 0x02040000    1024 bytes, above every symbol the game links
```

具有已知大小的最高地址EWRAM符号结束于0x0203FBAC（[两个构建版本的EWRAM地址相同](frlg_rom_map.md)）。根据反编译项目中的符号命名（`gHeap`的114688字节在符号表中没有大小），这是唯一未被占用的EWRAM区间；其余空隙只是三字节和八字节的对齐间隙。

```
0x0203F768 .. 0x0203FBAC    1092 bytes, newlib's malloc state
```

`__malloc_av_`及其后的malloc计数器仅会被newlib的stdio访问，而stdio只有`AGBPrintf`会调用，发布构建不使用它（pokefirered_switch.elf：唯一指向`bl`的`_malloc_r`, `_calloc_r`以及`_free_r`均位于libc内部）。在mGBA运行的法语版《火红》中，此处填入的0xA5经过菜单、行走和完整一场野生战斗后仍然保留。GB-Link Team卡片将重定位后的脚本放在这里（[frlg_gift.md](frlg_gift.md#gb-link-team-cards)). `scratchpad/ewram_symbol.py ADDR LEN`可检查某个地址。

绝不要仅因某地址读出来为零就选用它。0x0202B280、0x020185C4和0x0203B0E9可读出数十千字节的零，但它们分别属于战斗及盒子缓冲区、通向`gDecompressionBuffer`之前的区域，以及分配器管理数据；0x02012304位于`gHeap`。0x0202B280位于`gPokemonStorage`内部：写入该处可能落在盒中宝可梦的校验和上，随后存档就会保存一枚坏蛋。

软重置会清空EWRAM两次：`DoSoftReset`调用`SoftReset(RESET_ALL & ~RESET_SIO_REGS)`[main.c:488]（`svc 0x1`随后是`svc 0`[libagbsyscall.s:69]），接着`AgbMain`调用`RegisterRamReset(RESET_ALL)`[main.c:134]；0xFF的位0表示`RESET_EWRAM`[include/gba/syscall.h:4,12]。Switch包装层也会重新启动模拟主机，因此`AgbMain`运行两次：`gIntrTable`和`INTR_VECTOR`（0x03007FFC）每次启动都会清空并重建两次，期间条目1、2和7会设为无线相关值（以每秒328000次采样：33.3毫秒，然后133.6毫秒到第二次清空，再过33.6毫秒完成重建）。启动过程不会重建0x0203B0E8以上的任何内容。两次启动之间，没有任何操作写入0x0203FC00..0x02040000：该处标记经过标题画面、重新载入、菜单、存档、切换地图、战斗及PC盒子仍然存在，而软重置（A+B+START+SELECT）会将其清除。

## 每帧钩子

`gIntrTable`在法语版卡带上位于0x03002720；条目4是垂直消隐处理程序，保存`VBlankIntr`（0x0800071D）。它包含十四个函数指针，由`InitIntrHandlers`根据`gIntrTableTemplate`[main.c:339]一次性写入，BIOS通过`IntrMain`调用它，其地址存放在0x03007FFC处的向量中。替换条目4可使代码在所有游戏状态下每帧被调用；`gMain.vblankCallback`和`gMain.callback2`则在每次打开菜单或开始战斗时都会重写。

在主机的IWRAM中定位：`IntrMain_Buffer`位于0x03002760（英语版为0x03002810），而`gSaveBlock1Ptr`位于0x03004228（英语版为0x030042D8），因此这些地址处，卡带IWRAM比英语构建低0xB0。IWRAM地址不能像EWRAM那样直接在不同构建间通用。

| 条目 | 卡带 | 英语版 |  |
| --- | --- | --- | --- |
| 0 VCount | 0x08000805 | 0x0800081C | `VCountIntr` |
| 1 串行通信 | 0x03004B34 |  | 连接建立期间的IWRAM处理程序 |
| 2 Timer3 | 0x08005AE1 |  | `Timer3Intr`，ROM段和地址差值均不同 |
| 3 HBlank | 0x080007D5 | 0x080007EC | `HBlankIntr` |
| 4 VBlank | 0x0800071D | 0x08000734 | `VBlankIntr` |
| 5, 6, 8-13 | 0x08000885 | 0x0800089C | `IntrDummy`，重复八次 |
| 7 | 0x081E0D35 |  | RFU定时器处理程序，`sTimerIntrFunc = gIntrTable + 0x7`[main.c:85] |

无线运行期间，条目1和7与模板不同，符合反编译项目的预期；会话结束后，条目1和2保留无线相关值，直到重置。游戏写入条目4仅发生于`InitIntrHandlers`中写入条目4，而该函数只有在软重置时才会重新运行。

### 会话结束后仍继续运行的代码

暂存区中有一个二十字节的桩程序，安装到条目4后，会在会话关闭之后的所有游戏状态下每帧运行。`asm/resident/vblank-hook.s`:

```arm
    ldr     r0, .Lcounter
    ldr     r1, [r0]
    add     r1, #1
    str     r1, [r0]
    ldr     r0, .Loriginal
    bx      r0                      @ tail branch: lr still points at intr_return
```

`IntrMain`以SYS模式进入处理程序，此时`lr`位于`intr_return`，并允许它覆盖r0-r3[crt0.s，`jump_intr`]，因此被替换的处理程序通过自身的`bx lr`返回。两个字面量都会在发送前修补。

使用一个`call-chain`安装它：先写五个字，最后写条目4，每次写入都回读。

```
read32  [0x03002730]                gIntrTable[4], 0x0800071D
write32 [0x0203FC00] = 0x68014802   the stub
write32 [0x0203FC04] = 0x60013101
write32 [0x0203FC08] = 0x47004801
write32 [0x0203FC0C] = 0x0203FC40   the counter's address
write32 [0x0203FC10] = 0x0800071D   the handler being replaced
write32 [0x03002730] = 0x0203FC01   the hook, THUMB bit set
read32  [0x0203FC40]                the counter
```

钩子在所有游戏状态下每帧运行一次：在19995帧中，在菜单、标题画面、大地图、队伍菜单、野生战斗以及游戏内重新开始前后，测得每秒调用59.0到63.3次。软重置会终止它：`InitIntrHandlers`重写条目4[main.c:339]（`gIntrTable[4]`先读为零，随后为0x0800071D）。神秘礼物只能在启动后访问，而启动会清空EWRAM，因此若载荷需要在不新建会话时也存在，其安装程序必须存放在存档中。

### 重置后重新启用

`--gift resident-hook`发送一张神秘卡片，其神秘事件脚本通过`initramscript`将场景脚本绑定到玩家的母亲。绑定保存在存档中，断电重启后仍然存在（[唯一的RAM脚本槽](frlg_gift.md#the-one-ram-script-slot)）；每次启动后与她交谈即可安装钩子，无需连接，也无需主机端。

`asm/field/install-vblank-hook.s`，共68字节，使用`setptr`暂存，每次占六个脚本字节，再用`callnative`运行：占用RAM脚本主体可容纳995字节中的418字节。

```
read  gIntrTable[4]
if it already names the stub: return, writing nothing
write the five words of the V-blank stub to the staging area
write the handler just read into the stub's fifth word
zero the counter
write the staging area, Thumb bit set, into gIntrTable[4], last
```

尾跳转目标取自表中，因此钩子会串接当时已有的处理程序。开头的保护检查不可缺少：安装两次会让桩程序尾跳转到自身，从而在中断处理程序中死循环，冻结大地图。

位于`SaveBlock1 + 0x32E0`的脚本块在软重置后仍然存在，只是指针会重新随机生成（已在模拟器上验证）。

脚本每次启用时都会重建代码，因此代码大小受脚本主体限制：暂存方式最多162字节，或在最后一条命令后追加约755字节并通过跳板进入。

### 比脚本主体更大的载荷

`asm/field/save-loader.s`，共64字节，无论载荷多大，RAM脚本都只需暂存这些内容：它重新读取`gSaveBlock2Ptr`，加上0xB20，将N个字复制到暂存区，将第一个字与魔数比较（用于识别从未写入的存档，或后来被其他卡片占用的区域），然后跳转进入。它只使用r0-r3且从不压栈，因此载荷直接返回到`ScrCmd_callnative`的调用方。

二进制块为936字节，一次`save-write` (`MAX_SAVE_WRITE_BYTES`，即1024字节接收缓冲区减去写入程序）：

```
+0x000  magic 0x444C4B50
+0x004  installer
+0x054  the V-blank hook
+0x068  filler
+0x3A4  checksum over the filler
```

只有填充内容的求和结果正确，安装程序才会安装任何内容（[验证大小](frlg_rng.md#proving-the-size-rather-than-the-jump)).

存档副本中的钩子尾跳转目标必须是实测的`VBlankIntr`，绝不能为零：加载器会覆盖一个可能已在运行的钩子，第二次访问时安装程序会发现钩子已安装，因而不做任何修补。若该处为零，第二次对话后主机就会崩溃并黑屏。

不论载荷大小，RAM脚本都占995字节中的394字节。`filler_B20`可容纳1024字节，存档中其他未用区域约可容纳700字节。更大的二进制块在一次会话中分为936字节的片段写入，每个载荷负责一片（[`save-write`](#save-write)）。当达到完整1024字节时，二进制块延伸至EWRAM顶端，计数器则移至暂存区下方的84字节中。暂存副本与存档一致，只有钩子的第五个字例外，每次启用都会暂存相同字节（已在模拟器上验证，计数器每秒增加60.0次）。

### 调用包装层

GBA代码通过Sloop系统调用访问Switch模拟器：从`swi 0x40`到`swi 0x62`之间有23个，空缺为0x46、0x4E、0x52以及0x58到0x60[src/sloopsvc.c]。常驻载荷可发起其中任意一个：构建器把一个跳板`swi N ; bx lr`汇编进二进制块，并修补调用编号。标记应在调用前写入，因为若系统调用不返回，就没有其他内容可读取：

```
+0x00  0xB0B00001   the probe was reached
+0x04  the syscall number
+0x08  0xB0B00002   it returned, and zero until it does
+0x0C  r0, r1, r2, r3 as the syscall left them
```

`swi 0x54`, `svc_CommsAllowedByParentalControls`[sloopsvc.c:182]，在未启用家长控制的主机上返回非零值。

#### 分发器：Sloop系统调用边界

分发器位于`main + 0x057014`，其跳转表位于`main + 0x17D7F6`。它接受`N`，范围为0x40..0x62：

```
cmp   w2, #0x2b ; b.lo default       below 0x2B, the BIOS syscalls
sub   w9, w19, #0x40 ; cmp w9, #0x22 ; b.hi default
ldrh  w12, [table, w9, lsl #1]       a u16 word-offset from 0x05706C
br    base + offset * 4
```

三十五个条目，二十三个不同处理程序。凡是`sloopsvc.c`命名的编号都有对应处理程序。0x46、0x4E以及0x58到0x60共用默认处理程序，恰好对应反编译项目中的空缺。0x48和0x56共用一个处理程序（`WriteSector`, `ReplaceSector`）；0x40和0x41共用一个根据编号分支的处理程序。分发器的`x0`是CPU对象，`w2`是编号，而`x3`是处理程序读取的寄存器上下文：加入端的`r0`位于`+0x48`，而`r1`位于`+0x4C`（即`0x52`处理程序在`ldp w1, w22, [x20, #0x48]`之后的`mov x20, x3`).

默认处理程序为`cmp w19, #0x2a ; cset w0, hi ; ret`。这个`w0`是包装层自身的“已处理”布尔值，而不是加入端的r0，因此未实现的编号没有作用（不会卡死），并保持加入端所有寄存器不变。若探测时传入零，读出也是零，那就没有测得任何东西。

切勿盲目遍历0x40..0x62：0x48和0x56接受扇区编号及指针，0x4C完成存档，0x55传入SaveBlock2指针，而0x43、0x57、0x61和0x62都需要参数。放在r0中的标记会变成无效的闪存源地址。

探测程序会在每次调用前重写自身的`swi`（没有指令缓存），先写入编号以便卡死时能够识别对应调用，并在七个头部字之后，为每个编号记录`r0`（35个结果，共140字节）。`p_probe_num_step`递增编号；`p_probe_a0_step`递增`r0`，同时将编号步长设为零。

| 编号 | 输入r0 | 输出r0 |
| --- | --- | --- |
| `swi 0x52` | `0xA5A00052` | `0` |
| `swi 0x53` | `0xA5C00052` | `1` |
| `swi 0x54` | `0xA5E00052` | `1` |
| `swi 0x55` | `0xA6000052` | `0xA6000052`，未变化 |
| `swi 0x56` | `0xA6200052` | 包装层发生故障 |

`swi 0x56` (`ReplaceSector`），若目标地址被区域表拒绝（r0中放入标记），模拟器会在以下位置发生故障：`0xFF8` (`main+0x573F8`），存档未被修改：

```
Invalid memory access at virtual address 0x0000000000000FF8
PC  = main+0x573F8     LR = main+0x573EC
x19 = 0x56                  the syscall number
x22 = 0xA6200052            the guest's r0
x13 = 0x0203FFC2            the guest's PC, the halfword after the thunk's `swi`
x03 = 0x655DB09BE8          0x2D0 above the object 0x52's index 45 resolves to
```

日志将`0x0855D3F8`标记为`gba-app:0x573f8`，由此可得`main`的基址为0x08506000。

#### `swi 0x52`和`swi 0x55`：内存总线

0x52具有反编译项目中缺失的处理程序，位于`main + 0x05728C`:

```
ldp   w1, w22, [x20, #0x48]     guest r0 into w1, guest r1 into w22
lsr   x9, x1, #0x15             r0 >> 21
ldr   x8, [x21, #0xe0]!         the region table
and   x9, x9, #0x7f8            bits 3..10, so x9 is a BYTE OFFSET, not an index
add   x8, x8, x9
ldr   x0, [x8, #0x50]           the object for this selector
ldr   x8, [x0]                  its vtable
ldr   x8, [x8, #0x48]           slot 9
blr   x8
mov   x0, x20 ; mov w1, wzr ; mov w2, wzr ; b 0x0855D584
```

返回值被丢弃：位于`main + 0x057584`的回写操作接收到`w1 = wzr`，所以加入端读到的r0始终为0，r1到r3保持不变。`swi 0x52`在大地图中，对选择器45到54均返回r0 = 0，r1到r3及存档保持不变（`r0`按`1 << 21`). `swi 0x55`递增，位于`main + 0x057304`以相同步移索引同一张表，调用槽9并经由`main + 0x057588`退出，跳过回写；这就是它返回时r0不变的原因。

要读取对象及目标，请在以下位置暂停：`blr x8`, `main + 0x0572AC`（虚拟`0x0855D2AC`): `x0`为对象，`x8`为槽9的目标，`w1`为加入端r0。再执行一条指令，返回值仍位于`x0`。要检查全部256个条目，请在`ldr x8, [x0]`, `main + 0x0572A4`暂停，此时还没有解引用任何内容：对象为空或未映射时，会在此处发生故障。

`0x7f8`在一条指令内完成掩码及缩放：

```
entry = (r0 >> 24) & 0xFF        and the byte offset is entry * 8
```

如果将它解读为`(r0 >> 21) & 0xFF`，每个条目都会被放大到实际大小的八倍。`r0`是GBA地址，而该表就是内存总线：最高字节选择区域，槽9负责区域地址折叠。

| 条目 | 区域 | 对象 | 槽9 |
| --- | --- | --- | --- |
| 0x00 | BIOS | 独立对象 | `and w0, w1, #0xffffff` |
| 0x01 | 未映射 | 默认对象 | `and w0, w1, #0xffffff` |
| 0x02 | EWRAM，256 KB | 独立对象 | `and w0, w1, #0x3ffff` |
| 0x03 | IWRAM，32 KB | 独立对象 | `and w0, w1, #0x7fff` |
| 0x04 | I/O | 独立对象 |  |
| 0x05 | 调色板，1 KB | 独立对象 | `and w0, w1, #0x3ff` |
| 0x06 | VRAM，96 KB | 独立对象 | `and w8, w1, #0x1ffff`，然后`0x18000..0x1FFFF`通过以下方式向下折叠：`0x8000` |
| 0x07 | OAM，1 KB | 独立对象 | `and w0, w1, #0x3ff` |
| 0x08, 0x09 | ROM等待状态0 | 两个区域共用一个对象 | `ldr w8, [x0, #0x34] ; and w0, w8, w1`，即卡带的大小掩码 |
| 0x0A, 0x0B | ROM等待状态1 | 两个区域共用一个对象 | 相同的虚函数表 |
| 0x0C | ROM等待状态2 | 独立对象 | 相同的虚函数表 |
| 0x0D | 等待状态2的顶部，EEPROM所在位置 | 独立对象 | 默认虚函数表 |
| 0x0E | SRAM | 与所有其他区域对象分开分配 |  |
| 0x0F | SRAM镜像 | 独立对象 |  |
| 0x10到0xFF | 未映射 | 默认对象 | `and w0, w1, #0xffffff` |

条目0到15共对应14个对象和11张虚函数表。VRAM折叠对应硬件镜像（`0x18000`读取`0x10000`, `0x1FFFF`读取`0x17FFF`）。默认对象为`0x655DB09918`，虚函数表为`main + 0x1C1FB0`，槽9为`main + 0x01F7D8`；其槽10为`mov x0, xzr ; ret`，槽11仅为一条`ret`，槽2是执行两次存储的设置器。每张虚函数表在以下位置都有空的typeinfo指针：`-0x08`：没有RTTI，也没有类名。

EWRAM的虚函数表，`main + 0x1C21A0` (`x0`为区域对象，`x1`为周期计数器，`x2`为地址，`x3`为值）：

| 槽 | 用途 |
| --- | --- |
| 2 | 将两个字存入对象的`+0x24`和`+0x2C` |
| 3, 4, 5 | 读取16、32和8位 |
| 6, 7, 8 | 写入16、32和8位 |
| 9 | 将地址折叠进区域范围 |
| 10, 11 | 返回空指针，以及无操作 |

访问器先增加周期计数器（半字或字节增加三，字增加六），然后索引位于以下位置的主机端后备内存指针：`+0x10`。大小位于`+0x20`，ROM大小掩码位于`+0x34`.

七个系统调用会访问该表（0x45、0x47、0x48及0x56、0x4D、0x52、0x55、0x62），每个都只调用槽9；读写访问器属于模拟器的CPU核心。`swi 0x62`包含四条指令，用于递增一个计数器。

应根据处理程序自身的控制流确定边界：有些在最后一个表条目之后还有脱离主体的后续代码，若以下一个处理程序起点为边界，就会错误归属这些代码。

### 闪存扇区路径

`swi 0x48`和`swi 0x56`共用位于`main + 0x057084`的处理程序，其后续代码位于`main + 0x057364`。加入端的`r0`是4 KB扇区编号，加入端的`r1`是源地址：

```
source      = r1, resolved through the region table and folded
destination = 0x0E000000 + r0 * 0x1000, resolved the same way
```

目标地址通过32位运算生成[main + 0x05737C]：`0x0E000000 + ((r0 & 0xFFFFF) > 12)`模256，因此`r0`选择区域。目标位于EWRAM、IWRAM或卡带缓冲区时，可通过两项边界检查（`fold = 0x1000`）；当使用`r0 = 0xFA000 + n`时，目标会折叠到ROM副本中以下位置的4 KB区域：`n * 0x1000` （`n` 的范围为 0..0xFFF），源可来自任意区域。

ROM目标会实时写入卡带缓冲区，这已在打过补丁的Ryubing构建中的模拟主机上，通过IP主机端测得（未操作零售版主机）：设置`r0 = 0xFA3FF` (`dest`为0x083FF000，`n`= 0x3FF，区域条目为0x08），并使用EWRAM源（`r1`为0x0201C400，折叠值0x1C400，掩码0x3ffff），两项检查均通过，复制实际生效：卡带缓冲区0x3FF000处的字节完全变为源数据自身的0x1000字节（0x3FF000..0x3FF31F处是选定模式的200个字，随后0x3FF320+处也一并带入源自身的尾部字节，例如两处的第200个字均为0x11111000）。随后加入端从0x083FF000加载时，会通过折叠后的ROM窗口读到该模式。主机端会话保持正常：载荷返回1，`client->param`携带该模式自身的第一个字，主机显示成功消息并正常关闭连接。

用同样方式复制的代码能够执行。将源的第0个字设为包含两条指令的THUMB例程（`0x47706001`: `str r1,[r0]; bx lr`），第1..199个字设为模式；复制后，载荷回读折叠地址（`0x47706001`，即该例程），并跳转到`0x083FF001`，其中`r1`中放入一次性随机数，`r0`中放入自身结果字的地址：主机的响应携带该随机数，证明包装层取指读取的正是系统调用写入的同一块实时后备内存，复制的字节通过正常取指路径作为代码运行。会话以成功消息结束，游戏完成保存。

写入在软重置后仍然保留。按下A+B+START+SELECT之后，通过调试器回读折叠地址0x3FF000的同一4 KB区域，字节完全一致（4096字节中有0字节变化），而EWRAM源暂存区已清空。重置后开启第二次会话，读取0x083FF000（`0x47706001`），然后携带新的随机数跳转到0x083FF001；常驻例程返回该随机数。完全重新启动应用会从模拟器ROM文件恢复这些字节：新进程在折叠地址处持有文件的原始字节。这种写入的存续时间等于模拟器进程的生命周期。

若区域位于`+0x10`的后备指针为空、折叠偏移达到或超过位于`+0x20`的大小，或剩余不足`0x1000`字节，对应一侧就会被拒绝（指针设为空）。两侧都解析完后，才会复制`0x1000`字节。随后`swi 0x56`将`0xFF`存入目标地址`+0xFF8`，但不检查空指针：

```
cmp   w19, #0x56
b.ne  exit
mov   w8, #0xff
strb  w8, [x21, #0xff8]
```

`+0xFF8`为扇区签名[pokeldn/frlg/save/save_inject.py]：`0x08012025`变为`0x080120FF`，扇区失效。`ReplaceSector`写入并使扇区失效，`WriteSector`仅写入。被拒绝的目标使`x21`保持为空，因此`swi 0x56`会在`0xFF8`处发生故障，即上文的中止。

使用`swi 0x48`在模拟主机上测得：

| 调用 | 结果 |
| --- | --- |
| `r0`为超出闪存大小的扇区，`r1`为未映射区域 | 没有写入，闪存字节完全一致，无故障，无冻结 |
| `r0 = 30`, `r1 = 0x08000000`（ROM头部） | 扇区30变为卡带最前面的4 KB，4096字节全部一致，相邻区域未改变 |
| `r0 = 30`, `r1`为载荷填充的EWRAM缓冲区 | 扇区30变为这些字节；缓冲区回读结果未变化 |
| `r0 = 0xFA3FF`（目标0x083FF000），`r1`为EWRAM缓冲区 | 复制落入卡带缓冲区：折叠地址0x3FF000处的字节逐字节变为源的4 KB内容；加入端读取0x083FF000时返回该模式；会话正常结束 |
| 相同复制操作，源的第0个字为THUMB例程，随后跳转到`0x083FF001`，其中随机数放入`r1` | 复制后的例程返回该随机数；主机显示成功、保存并正常关闭 |
| 软重置后，通过调试器读取相同折叠地址 | 4 KB逐字节一致（4096字节中有0字节不同），而EWRAM源暂存区已清空 |
| 重置后，第二次会话读取例程并跳转到`0x083FF001` | 常驻例程返回新的随机数，同一进程内跨重置仍可调用 |
| 完全重新启动应用后，通过调试器读取相同折叠地址 | 折叠地址处恢复ROM文件的原始字节；写入存续时间等于进程生命周期 |

它不修改加入端任何寄存器，也不返回状态：只有读取闪存才能区分调用是被接受还是被拒绝。

模拟器仅在游戏保存时提交其128 KiB闪存映像，外来扇区也会一起保存。系统调用写入后若强制终止进程，主机端文件保持不变。在神秘礼物会话中写入后，若会话以成功消息结束，就会保存并持久化[mystery_gift_menu.c:1379]；其他结果下的写入以及常驻钩子中的写入，都要等待下次保存。

### 断点钩子

包装层的GBA CPU对象在以下位置有256个钩子槽：`cpu + 0x170`，每个对应一个`bkpt`立即数。ARM解码检查`(insn & 0xFFF000FF) == 0xE1200070`，THUMB解码检查`(insn & 0xFF00) == 0xBE00`，位于`main + 0x01FCE4`；位于`main + 0x01EFC0`的THUMB处理程序调用槽`imm8`中钩子的虚函数表槽2（钩子、`&insn`、`bkpt`的地址、CPU），通过`main + 0x01F820`调用。钩子返回1时，核心会执行它存入`insn`的指令；返回0或槽为空时，`bkpt`就变为无操作。`main + 0x022A2C`注册钩子，并拒绝已占用的槽。有两个槽被占用：

| 槽 | 所有者 | 钩子 | 作用 |
| --- | --- | --- | --- |
| `bkpt #0x52` | Sloop组件，虚函数表为`main + 0x1C3878` | `main + 0x05499C` -> `main + 0x056368` -> `main + 0x03E850` | 下文的librfu补丁 |
| `bkpt #0xFF` | 应用对象，虚函数表为`main + 0x1B4078` | `main + 0x001140` | 投递事件`0x82EF0054`，参数为1，该事件会退出应用 |

加载时，包装层向加入端的ROM副本写入三处补丁，这是整个`0x08000000..0x09000000`中仅有的与卡带不同的十个字节，v0和1.0.1均如此（通过块校验和及神秘礼物客户端回读验证，零售版及模拟版均已测试）：

| 地址 | 卡带 | 加入端 |
| --- | --- | --- |
| `0x081E1696` | THUMB `mov ip, r1` (`468c`) | `bkpt #0x52` (`be52`) |
| `0x081E187C` | ARM `ldr r3, [pc, #0x50]` (`e59f3050`) | `bkpt #0x52` (`e1200572`) |
| `0x081E1F90` | ARM `mov lr, r0, lsr #14` (`e1a0e720`) | `b 0x081E1FB8` (`ea000008`) |

第三处补丁删除等待循环。位于`0x081E1F74`的函数轮询`REG_SIOCNT` (`0x04000128`）的位2，与调用方的`r0` (`r0`比较，后者掩码为u16，`lr = r0 >> 14`），当位于`[*(0x03000030) + 0x10]`的字节为1时提前返回，将它清零并返回1。在模拟环境中，轮询永远不会匹配，因此包装层将函数主体替换为`mov r0, #0; return`：等待操作立即返回0。

`bkpt #0x52`以地址为键：其钩子持有两条记录`{u32 pc, u32 original insn, ..., u32 hits at +0x0C}`，位于`+0x120`和`+0x148`，而`main + 0x0546C0`匹配地址并返回原始指令。在`Sio32IDMain`补丁处（`0x081E1696`），它解析加入端的`r0` (`&gRfuSIO32Id`），并将`0x8001`存入`+0x0A`，这就是适配器ID，即`AgbRFU_checkID`所等待的值[librfu_sio32id.c]。若在其他任何地址执行一条`bkpt #0x52`，就会将第二条记录（`0x081E187C`补丁）的键改为该地址，持续到本次会话结束。

#### 记录解析器（`main + 0x03E850`)

钩子`main + 0x05499C`将`bkpt`本身写入`insn`，然后调用位于`[[x0 - 0x60] + 0x98]`的虚函数，并以`x0 - 0x60`作为`this`（反汇编，`main + 0x549c4`-`0x549cc`）；对于Sloop组件，这会解析为`main + 0x056368`，它推导出记录持有者`[component + 0x40] -> [+0xA8] + 0x68`，并尾调用解析器`main + 0x03E850`，参数为该持有者、`&insn`、`bkpt`的地址及CPU（`0x3e850`在整个映像中只有一个调用方，`0x56378`）。加入端的`r0`的最高字节只会在稍后的解析器内部Sio32ID模拟中用于选择区域。解析器会：

-
-
-
-
-

加入端控制整个触发过程：载荷跳转到`0x081E1696`（打补丁的位置，THUMB模式），并使用选定的`r0`，就会使包装层将`0x8001`写入`fold(r0) + 0xA`，并设置`r1`为位于`fold(r0) + 1`的字节；若载荷在其他任何位置执行一条`bkpt #0x52`，就会在该处执行陈旧的`e59f3050`。两者都相对于加入端；其中`+0xA`写入是唯一会越出加入端区域的路径：它可将`0x8001`这两个常量字节写到任意区域后备分配末端之外最多11字节处，包括16 MB的ROM副本。

#### ROM缓冲区之后是什么：Sloop组件

ROM对象的掩码（`+0x34`）为`0x1ffffff`，而卡带占用`0x1000000`字节，因此折叠值`0xFFFFF6..0xFFFFFF`会通过边界检查，并把写入落在紧随ROM缓冲区之后的十个字节内。该处对象是Sloop组件（[断点钩子](#the-breakpoint-hooks)）：其第一个字是虚函数表指针`main + 0x1C3878`, `+8` `0x000004bf`, `+0xC` `0x0A828400`, `+0x18`，而`+0x20` `main + 0x16EB83`, `+0x28`是一个`0x655db`堆指针，`+0x60`和`+0x88`是另外的虚函数表（`main + 0x1C3948`, `main + 0x1C3978`), `+0xE0`为CPU总线对象。

相邻对象会随启动而变化：某次启动时，ROM相邻对象的第一个字是虚函数表`main + 0x1C36D8`，其`+0x60`是虚函数表`main + 0x1C3790`。构造函数`main + 0x547CC`恰好写入这两个值，并读取位于`main + 0x86D67E8`的静态指针（加数`main + 0x1C36C8`[main_relocs.json]）。该类字段由自身构造函数和自身代码写入；加入端会话中的任何存储都不会触及它们。

在打补丁的位置，卡带自身的代码保留了自身的`r0` (`ldr r0, [pc, #0x10]`加载`0x0300744A`，即自身的`&gRfuSIO32Id`，位于IWRAM），因此游戏自身的分发总是折叠到游戏自身的结构体：包装层的`0x8001`存储是将适配器ID传入`gRfuSIO32Id.lastId` (`RFU_ID = 0x8001`[librfu.h]），即`AgbRFU_checkID`等待的值。若载荷直接跳转到`0x081E1696`，就会跳过该加载并保留自身的`r0`，从而改变存储位置。

在strh本身（`main + 0x3E928`）及其后续代码处插桩：直接跳转并使用`r0 = 0x08FFFFF6`时，存储操作的`x8`为`backing + 0xFFFFF6` (`0x66209f9ff6`，尾部的`ff`为其后的填充），前后内存转储中，`0x66209fa000`在存储前为`78 98 6c 08 ...`，存储后为`01 80 6c 08 ...`：两次存储相隔约90毫秒（第一次为载荷触发，随后保留相同的寄存器值再次通过同一位置分发，`r0`).

覆盖组件最前面的两个字节后，虚函数表指针会被置为`0x086C8001`，随后分发器`main + 0x1F820`从中读取钩子槽19（偏移`+0x98`）：位于`main + 0x1C2099`的八个字节为`f7 01 00 00 00 00 00 00`，因此包装层下一次虚调用会在加入端PC`0x1F7`处执行，该地址未映射，加入端其他路径均不会到达。在模拟器上，这会中止进程（`Unhandled guest exception InstructionAbortLowerEl`）；若同样触发但折叠地址位于区域内部，会话只会写入局部折叠地址后结束，不会发生这种分发。该位置的卡带自身代码排除了另一种候选原因：`mov ip, r1`将`ip`作为值存储（`mov r0, ip; strh r0, [r4]`），从不会通过它跳转。

只有当位于`[component + 0x40] -> [+0xA8] + 0x170`的字节被设置时，钩子才会生效：这是虚拟适配器的电源开关。`swi 0x40`设置它，`swi 0x41`清除它（处理程序`main + 0x05706C`存储`number == 0x40`；即[sloopsvc.c:23]中的“未被引用的标志设置器”）。`swi 0x41`在神秘礼物菜单中调用它会停止RFU帧：游戏报连接错误并离开LDN。软重置后适配器仍保持关闭，因此下次无线菜单会报告“未连接GBA无线适配器”。该字节在软重置后保留；重新启动应用或调用`swi 0x40`可恢复它。该字节每帧读取一次：`swi 0x41`之后紧接着`swi 0x40`，放在同一载荷中不会造成影响。

#### 从bkpt到解析器的调用链

NSO的虚函数表槽在文件中保存尚未重定位的加数；加载器会加上映像基址（`main`位于`0x8506000`）。应用该基址后，加入端的一条`bkpt #0x52`会运行以下调用链：

-
-
-

因此，覆盖组件前十个字节的存储会在槽`+0x98`处被使用；而`+0x10`读取发生在钩子子对象上，位于这十个字节之外。解析器的写入目标为`buffer_data + fold + 0xA`，折叠由选定区域的槽9执行（[`swi 0x52`和`swi 0x55`：内存总线](#swi-0x52-and-swi-0x55-the-memory-bus)).

#### 跨分配边界植入会发生什么

当使用`fold = size - 0xB`（范围内）时，写入字节对为`(size-1, size)`：区域的最后一个字节被写为`0x01`，相邻分配的第一个字节被写为`0x80`。当使用`fold = size - 0xA`时，字节对为`(size, size+1)`: `0x01 0x80`，写入相邻对象的前两个字节。每次进入神秘礼物会话，只能选择一个折叠地址。

该位置之后的函数主体通过五个字的栈帧返回：其位于`0x081E177C`的尾声为`movs r0,#0 ; pop {r4,r5,r6,r7} ; pop {r1} ; bx r1`。直接跳到该位置的载荷跳过了函数序言，必须自行压入该栈帧，并将`lr`设为后续执行位置；主体随后返回载荷，载荷便可继续执行代码并正常结束会话。如果载荷压入其他栈帧，就会改为沿调用方的栈展开，实测运行会带着相同的保留值重新进入该位置，`r0`.

窗口4，即GBA IO寄存器，映射到一个大小为0x400字节的区域对象，该对象紧随其自身的后备分配：后备内存位于总线`+0x14C0`，对象位于总线`+0x18C0`，按键中断子对象嵌入在对象`+0x88`处。因此植入落在总线每次IO访问都会经过的分发对象上。该映像的CPU核心中有210处调用采用访问器形态（[`swi 0x52`和`swi 0x55`：内存总线](#swi-0x52-and-swi-0x55-the-memory-bus)).

在模拟主机上：

| 植入位置 | 使用位置 | 结果 |
| --- | --- | --- |
| 组件字节对`01 80` (`0x086C8001`) | 槽`+0x98`在以下位置读取：`main + 0x1C2099`，未重定位，`0x1f7` ([见上文](#what-follows-the-rom-buffer-the-sloop-component)) |  |
| 组件字节 0：`0x80` (`0x086C9880`) | `main + 0x5492C`，即相同方法但不含`-0x60` | 它重新读取`[x0] + 0x98`，此时组件仍处于植入后的状态，因而递归调用自身；线程栈耗尽，进程以数据中止终结（`InvalidMemoryRegionException`) |
| IO 对象字节 0：`0x80` (`0x086C8480`) | 总线的存储槽`+0x38`/`+0x40`，植入后的目标为原始值`0xffffffffffffe5e0`和`0` | 植入后第一次IO存储会在约30毫秒内中止进程；加载目标（`main + 0x30EAC`, `main + 0x31114`, `main + 0x36D54`）从未运行 |
| 名称哈希块字节0（`0x80`) | 该块是SDK的binder/表面描述符对象（`android.gui.IGraphicBufferProducer`及相关名称都是SDK映像中的静态字符串），不是会被分发调用的对象 | 无反应；游戏继续运行，直到自身正常退出 |

植入`0x086C8080`（字节为`80 80`：此后每次`bkpt #0x52`都运行纯计数器读取器`main + 0x1F7F0`，使每条bkpt变为无操作）需要两次写入，且中间不能有分发；一次会话只能写入一次，而过程中的两种单次写入状态都会终止进程。改用调试器植入该指针后，游戏持续运行五分钟，指针保持原位，进程仍存活。映像中没有任何代码位置会在初始化之后写入包装层对象的头部。

#### 一次写入可实现的所有植入位置

一次植入会在相邻对象上写入两种字节模式之一：`80`写在第一个字节（区域自身的最后一个字节接收`01`），或者将`01 80`写在字节`k`和`k+1`, `k`，取值范围为0..9。相邻对象的前八个字节是虚函数表指针，因此后续使用方读取到的指针可对照文件映像及其重定位解析。有四种放置方式会读取实时main内存：

| 对象 | 写入字节 | 植入后的指针 | 使用方 |
| --- | --- | --- | --- |
| 组件（虚函数表`main + 0x1C3878`) | `80`位于+0 | `0x086C9880` | 该`bkpt #0x52`调用链的`[P + 0x98]` = `main + 0x1C3918` = `main + 0x5492C` |
| 组件 | `01 80`位于+0..1 | `0x086C8001` | `[P + 0x98]` = `main + 0x1C2099`= 原始值`0x1F7` |
| IO对象（虚函数表`main + 0x1C2408`) | `80`位于+0 | `0x086C8480` | 下方的总线访问器槽 |
| IO对象 | `01 80`位于+0..1 | `0x086C8001` | 总线访问器槽：`0x1F7`、零、原始加数 |

其他放置方式会解析到映像之外。`01 80`位于+1时得到`0x08800178`（组件）和`0x08800108`（IO对象），均位于main的bss中。全零bss模型预期这里会发生空指针调用；仅凭文件映像无法确定实时会话中的内容。`01 80`位于+2到+7时会改变字节2或字节3，因此使用方的读取本身就会发生故障。位于+8和+9时，字节对落在以下字段上：`+8`（组件的`0x000004BF`在+8时变为`0x00008001`，在+9时变为`0x008001BF`），虚函数表指针保持不变，因此仍由对象自身执行分发。

若两次访问之间没有发生`0x04`访问，就可在IO对象上组合两次写入的字节对；载荷从ROM或EWRAM取指本身不会访问该对象。重复同一种放置具有幂等性，+8或+9处的写入不会改变虚函数表指针。仅限于字节0和1的不同放置组合，仍可能得到上文某个映像内指针；会改变指针更高字节的组合需另行分析。对于组件，下一个`bkpt #0x52`会使用当前植入。连接建立期间，STWI驱动每秒产生约60次此类调用，但仅凭这个频率，不能证明每两次载荷访问之间都一定会插入一次调用。

按总线槽列出IO对象植入后的代码块。访问类别根据调用方的结果掩码确定（`and #0xffff`位于`main + 0x18378`，对应16位加载；位于`main + 0xBDB8`的字旋转对应32位加载；`and #0xff`位于`main + 0xD914`，对应8位加载）。

| 总线槽 | 访问类型 | 植入后的目标 | 以IO对象作为`this` |
| --- | --- | --- | --- |
| `+0x18` | 16位加载 | `main + 0x30EAC` | 按键处理程序的默认分支：`w2`是完整的`0x04xxxxxx`地址，高于处理程序switch处理的所有寄存器ID，因此它将`w3 & 0xffff`存入`[x1]`；位于`main + 0x18330`的调用点传入`x1 = CPU + 0x20`和`w3 = 1`，加入端的加载返回处理程序遗留的`w0` |
| `+0x20` | 32位加载 | `main + 0x31114` | 调用`main + 0x3580C`，参数为`(x1 from the site, IO + 0x20)`，然后尾调用`main + 0x22404`，参数为`x0 = [[IO + 8] + 0x90]` |
| `+0x28` | 8位加载 | `main + 0x36D54` | 一个0x76000字节对象的析构相关函数族：`[x0 + 0x76C70]`, `+0x76C30`, `+0x76C00`, `[x0 + 0x4E68]` |
| `+0x30` | 存储 | `main + 0x36E40` | `x0 -= 0x1A10`，然后`main + 0x3664C`，即对重新定位后的指针执行同一析构函数族 |
| `+0x38` | 存储 | 原始值`0xFFFFFFFFFFFFE5E0` | 调用发生故障 |
| `+0x40` | 存储 | `0` | 空指针调用 |
| `+0x48` |  | `main + 0x36E4C` | 位于以下位置的析构函数族：`+0x76C60`, `+0x76C20`, `+0x76BF0`, `[x0 + 0x4E58]` |
| `+0x68` |  | `main + 0x310A8` | `x0 -= 0x10`，然后`main + 0x30EAC` |

以上任何放置都未进入由加入端内存提供的分发目标：四种main内放置读取的都是main自身数据，IO对象的代码块也使用总线参数调用main自身处理程序。

在零售版上（一台Switch Lite，英语版《火红》，载荷由XIAO ESP32S3无线模块通过LDN发送），组件植入与范围内写入的区别体现在连接拆除过程，而非画面。每次运行都在脚本执行约两秒后返回HOME，并显示“由于发生错误，软件已关闭”，因此该消息没有区分性；但正常的Pia离开流程（`Session type 3`）有区分性：

-
-

因此，在零售版上，当折叠值越过ROM缓冲区末尾时，记录解析器的存储会触及实时包装层对象，应用在该处中止；同样的存储若保持在加入端可见内存内则不会如此。压入函数主体所需栈帧的载荷，在零售版上同样可以从该位置返回。

植入后的分发来自应用下一条`bkpt #0x52`。游戏在两处产生它们：STWI驱动的IWRAM副本在连接期间每秒约60次（实时读取其命中计数测得），以及游戏自身在该位置调用`Sio32IDMain`（实时读取记录1得到12次命中）。当虚函数表低字节为`0x80`时，该分发进入`main + 0x5492C`，它在植入后的指针上重新读取`[component] + 0x98`并递归，直到线程栈超出所属区域；主机返回HOME且不发送`Session type 3`。若载荷用卡带自身的原始指令覆盖IWRAM副本中的`bkpt #0x52`，并撤销卡带副本的两处加载时补丁（包含两处位置的4 KB块，通过`swi 0x48`处理），就会去除两个来源：主机随后显示游戏自身的通信错误，发送`Session type 3`后离开LDN，提交网络报告并继续运行。在此状态下，植入只是未被触发，并未修复：没有代码会恢复虚函数表。撤销补丁后的卡带副本状态也持续至进程结束：此后无线菜单报告适配器未连接，完全重新启动应用才会重新应用包装层的加载时补丁。

### 当前边界所在

本页检查的加入端路径包括一次越过区域后备内存的存储：即解析器中的`0x8001`strh，位于`fold + 0xA`；植入指针的使用方从`main`自身静态地址的数据中读取目标（[一次写入可实现的所有植入位置](#every-placement-a-one-write-plant-can-make)）。该处列出了四种读取实时内存的放置，以及其余所有放置会留下的内容；在会话中，将低字节植入为`80`之后，组件的使用方是`main + 0x5492C`，来自`bkpt #0x52`钩子链。单次写入分析没有发现任何由加入端字节提供的调用目标；但它不能确定每一种写入序列的结果。去除该链的两个加入端来源后，观测到的分发不再发生。系统调用对组件的写入及其读取方见[其余系统调用](#the-remaining-syscalls)；`main + 0x1C36C8`类的字段由自身构造函数和自身代码写入（[ROM缓冲区之后是什么](#what-follows-the-rom-buffer-the-sloop-component)）。第三处加载时补丁替换了等待循环。屏蔽词过滤器的两个缓冲区都在分发器自身的栈帧内受长度约束（[屏蔽词过滤器](#the-bad-word-filter)）；闪存扇区路径的边界检查见[闪存扇区路径](#the-flash-sector-path).

Pia侧的两端都已解码：加入端的`RfuGameData`及用户名被重新打包进广播记录，并以base85编码（[广播记录](#the-advertisement-record)）；对端的`NetworkInfo`字节原样进入候选列表（[包装层自身的扫描流水线](#the-wrappers-own-scan-pipeline)）；对端会话消息先通过按类型设定的边界检查，处理程序才读取它们（[Pia会话消息分发器](#the-pia-session-message-dispatcher)）。后面的[线上数据解析章节](#the-pia-librarys-own-wire-parsing)追踪了静态链接的`PiaCommon-6_42_1`从UDP套接字到会话队列的路径；该追踪并非对其长度检查或全部消息处理程序的穷尽验证。

#### 其余系统调用

处理程序地址为`main + 0x05706C + entry * 4`，取自位于`main + 0x17D7F6`的跳转表。最后一列展示使用`sloop-svc`从神秘礼物客户端单次发起调用时的观察结果。

| swi | 处理程序、被调用方 | 作用 | 单次发起时的观察结果 |
| --- | --- | --- | --- |
| 0x40, 0x41 | `main + 0x05706C` | 适配器电源开关：将`r0 == 0x40`存入`[component + 0x40] -> [+0xA8] + 0x170` | 在神秘礼物菜单中发起swi 0x41会触发连接错误并离开LDN（[见上文](#what-follows-the-rom-buffer-the-sloop-component)) |
| 0x42 | 模式切换`main + 0x0588A0` | `rfu_REQ_startSearchChild`[sloopsvc.c:49]；将网络管理器设为模式2 | 以连接错误结束会话；未开启接入点 |
| 0x43 | `main + 0x0570EC` -> `main + 0x058AD0` | `rfu_REQ_startConnectParent`，16位PID位于`r0`[sloopsvc.c:91]；相同的模式切换 | 缓冲区脚本有响应，但关闭时显示“连接错误” |
| 0x44 | `main + 0x057100` -> `main + 0x058B0C` | `rfu_REQ_stopMode`，无参数[sloopsvc.c:102] | 在0x43之后调用，无可见变化 |
| 0x45 | `main + 0x057110` -> `main + 0x058900` | `rfu_REQ_startSearchParent`, `rfu_STC_readParentCandidateList`，参数为`&gRfuLinkStatus`[sloopsvc.c:67-75]；将包装层的扫描结果通过区域表复制到`struct RfuLinkStatus`, `findParentCount`[include/librfu.h]，首先写入偏移8处 | 220个已清零字节仍然为零（礼物会话中不搜索父端） |
| 0x46 | 跳转表条目`0x147` | 直接落入分发器退出路径：该系统调用无操作 |  |
| 0x47 | `main + 0x05715C` -> `main + 0x058680` | `rfu_REQ_configGameData`, `r0`指向`struct RfuGameData`（16字节）及用户名（8字节，`RFU_USER_NAME_LENGTH`）[sloopsvc.c:34-46; include/link_rfu.h:103-115,232]；将全部24字节复制到`component + 0x6050D8`，并将`activity`（第二个64位字的位16-22）复制到`component + 0x605360`，仅在发生变化时执行 | `activity`0x30逐字节写入两处 |
| 0x48, 0x56 | `main + 0x057084` | 闪存扇区复制：目标扇区为加入端的`r0`，源为`fold(guest r1)`，经过同一区域表，并根据区域大小检查边界，最多4 KB | [闪存扇区路径](#the-flash-sector-path) |
| 0x49 | `main + 0x0571A8` -> `main + 0x0588D0` | 调用`main + 0x0588D0`，作用于`component + 0xD0`对象；不接受加入端参数 | 返回0 |
| 0x4A | `main + 0x0571B8` -> `main + 0x058AB8` | 对以下对象执行相同形式的操作：`component + 0xD0` | 返回0 |
| 0x4B | `main + 0x0572C4` | 无参数；位1使`RfuMain1`使用`gHostRfuGameData->compatibility.playerTrainerId`重新设置随机数生成器种子，位0清除使`SpawnGroupLeaderAndMembers`在领队端提前退出[sloopsvc.c:132-145] | 0 |
| 0x4C | `main + 0x0571CC` | 调用`main + 0x05D930`，作用于`[component + 0xE8] + 0xA0`，返回0时再对全局指针调用`main + 0x049D28`；加入端数据不会传入任何一处 | 返回0 |
| 0x4D | `main + 0x0571FC` | 屏蔽词过滤器：解析`r0`，并从以下位置读取最多256字节：`fold(r0)`, [见下文](#the-bad-word-filter) |  |
| 0x4E | 跳转表条目`0x147` | 直接落入分发器退出路径：该系统调用无操作 |  |
| 0x4F | `main + 0x057248` -> `main + 0x058B54` | 在自身栈上构建`{u16 tag 0x4757; u32 value = r0}`；带标签属性分发器`main + 0x4EBD0`及设置器`main + 0x058BB4`不经验证便将该值存入`component + 0x6052A0` | 分别写入3和`0x7FFFFFFF`，每次之后都调用0x49和0x4A，没有观察到变化 |
| 0x50 | 读取器`main + 0x058BA4` | 回读同一个4字节计数值 |  |
| 0x51 | `main + 0x057270` -> `main + 0x0511BC` | 读取`component + 0x3404`到输出参数并将其清零；输出参数始终为分发器自身的栈槽 |  |
| 0x52 | `main + 0x05728C` | 将加入端的`r0`通过总线对象的区域表折叠（`[component + 0xE0] + 0x50`），并调用该区域的`+0x48`折叠函数。加入端的非零`r1`还会运行指针解析器`main + 0x562CC`：它读取`[[bus] + 0x50 + (r1 >> 24) * 8]`，索引不受0..255范围约束，将该值的`+0x48`作为虚函数调用，然后在`backing + offset`时返回`offset < size`。该处理程序是解析器唯一的调用方，会丢弃其结果并返回`r0 = 0`，因此加入端的`r1`回读为0。实时读取的256个条目是main自身的方法指针、负值和零，没有任何一个是具有`+0x48`方法的对象 |  |
| 0x53 | `main + 0x0572D4` | 返回`component + 0x2770 == 0`（通过`[component + 0xD0]`) |  |
| 0x54 | `main + 0x0572EC` | `svc_CommsAllowedByParentalControls`[sloopsvc.c:182] | 返回1 |
| 0x55 | `main + 0x057304` | 将`r0`存入`component + 0xE1BC`，将存入的字通过区域表折叠，并回读一个字节（[游玩报告由哪些内容构成](#what-the-play-reports-are-built-from)) |  |
| 0x57 | `main + 0x057330` | `MonsSelect`，写入位于以下位置的报告副本：`component + 0x140` |  |
| 0x58到0x60 | 跳转表条目`0x147` | 直接落入分发器退出路径：该系统调用无操作 |  |
| 0x61 | `main + 0x057340` -> `main + 0x058B2C` | `svc_SetActivity`；将`r0`写入`component + 0x605360`，仅接受0x41到0x48，即联盟交谊厅活动代码 | 0x45：在被调用方的`ret` (`main + 0x058B50`）处设断点，读得`w1`，该字段为0x45；正常关闭 |
| 0x62 | `main + 0x057354` | 将`component + 0xE1B0`加1，即下次报告中的`CommsError` |  |

响应经由`main + 0x2209C`返回：加入端的`r0`在编号大于0x2A时为1，加入端的`r1`等于处理程序的响应字。没有任何处理程序的响应包含包装层地址。

`component + 0x6052A0`共16字节：4字节计数、4字节未使用、8字节指针，指向`main`。刚启动时：计数1，指针为`main + 0x1E8D20`，它是一个指针数组，唯一已填充槽之后有两个空指针。

带标签属性分发器`main + 0x4EBD0`遍历组件上的监听器列表：条目大小为`0xd0`，位于`component + 0x10`，计数位于`+0x688`，启用字节位于`+0x690`；对于首字为2的每个条目，它都会调用组件虚函数表的槽`+0x50`，参数为位于`entry - 8`的8字节及带标签条目。设置器`main + 0x058BB4`是`0x4757`监听器。`0x59`监听器位于`main + 0x50618`，将位于`[tagged entry + 4]`的值写入`component + 0x3324 + index * 4`，索引从`[x2]`读取，并由`main + 0x4DB0C`限制在0..7。没有系统调用会构建`0x59`条目或提供那个第三参数，分发器的十二处调用都根据包装层内部字段构建条目。由`0x4757`监听器存入`component + 0x6052A0`的计数，除读取器`main + 0x058BA4` (`swi 0x50`）外没有其他读取方：映像中其他所有形成偏移`0x6052A0`或`0x6052A8`的代码位置，都只在初始化时写入它或其旁边的指针。由`0x4F`调用方提供的值不会产生作用。

主机自身搜索神秘礼物时，在任何缓冲区脚本之前都会发起`swi 0x47`，广播`activity`0x15（`ACTIVITY_WONDER_CARD`[include/constants/union_room.h:46]）；载荷调用会覆盖该值。在`main + 0x0586B4`处设置断点，可读取`component + 0x605360`到`x8 + 0x280`。游戏数据对象（虚函数表`main + 0x1C3B30`）与CPU/总线对象是同级对象，后者由`bkpt #0x52`的钩子表解析得到（虚函数表`main + 0x1C3878`、区域表、系统调用0x45、0x48、0x52、0x55、0x62）；实时地址相差`0x100000000`.

0x45写入的每个候选项布局尚未确定：复制循环的字节数与`sizeof(struct RfuTgtData)`不匹配；依赖它之前应先实时读取。

`component + 0x6050D8`，即由`swi 0x47`复制的24字节（[main + 0x058694]，从加入端的`r0`缓冲区执行前变址存储），由同一处理程序回读，并重新打包为广播记录。`component + 0x605360`的读取方是活动差异检查`main + 0x058698`（通过`component + 0x6050E0`）以及`svc_SetActivity`的设置器`main + 0x058B40`；两者均比较或存储活动代码。

#### 广播记录

该`swi 0x47`处理程序根据加入端自身的`RfuGameData`（16字节）和`gHostRfuUsername`（8字节）组装广播所携带的24字节RFU记录[include/link_rfu.h:103-115, src/sloopsvc.c:34-46]：

| 记录 | 来源 |
| --- | --- |
| `[0:2]` | `RfuGameData[2:4]`，训练家ID（`compatibility.playerTrainerId`) |
| `[2:10]` | 用户名 |
| `[10:12]` | 包装层的RFU会话ID，`main + 0x3F2E0([component + 0x6050D0])` |
| `[12:16]` | `RfuGameData[4:8]`, `partnerInfo` |
| `[16:20]` | 搜索字，由以下内容打包：`RfuGameData[0:2]`和`[8:12]` |
| `[22:24]` | `RfuGameData[8:10]`, `tradeSpecies` |

搜索字的各位来自两个源字：0-6为活动（`RfuGameData`的位16-22），7为性别（位24），8-10为版本（`RfuGameData[0:2]`的位10-12），11-14为语言（位0-3），15为`startedActivity`（位23），16为`canLinkNationally`（位7），17为`hasNationalDex`（位8），18-23为`tradeType`（位10-15），24为`gameClear`（位9），25-31为`tradeLevel`（位25-31）。`hasNews`和`hasCard`（位4和5）不被复制。位于`[20:22]`的两个字节保留栈帧原有内容。

编码器`main + 0x2A90`每组4字节写出五个字符，低位数字在前，字符表从`0x23`向上排列，跳过`0x5C`；若输出会超过给定容量，就会拒绝。处理程序调用它时，为24字节提供`0x20`的容量，因此30个字符可以容纳，并将文本存入`component + 0x6C0`，其`strlen`位于`component + 0x700` (`main + 0x15FAE0`和`main + 0x15FB20`，即`strlen`/`memcpy`PLT桩）。

主机端信标克隆的已捕获应用数据（`pokeldn/frlg/link/host_beacon.py`）共122字节：`0x5C`的Pia系统头，以及30个字符，解码得到训练家ID`0x1050`、姓名`GREEN`、RFU会话ID`0xac65`及搜索字`0x1584`（活动4、版本5、语言2、位7已设置）。

记录文本进入处理程序临时构建的广播数据构建器（类虚函数表`main + 0x1CB8C8`，构造函数`main + 0x87514`）：一个`0x180`字节的Pia广播区域位于`+0x1C`，已用大小位于`+0x18`，从`0x5C`头部开始计算，应用数据指针为`main + 0xA2C70` = `+0x78`，应用数据大小`main + 0xA2C90`= 已用大小减去`0x5C`，上限为`0x124`（槽`+0x28`, `main + 0x875AC`；头部偏移`0x5C`为槽`+0x30`, `main + 0x875A4`). `main + 0xA3480`通过其在以下位置持有的缓冲区对象，将30个字符追加到应用数据偏移处：`+8`（其容量由缓冲区虚函数表槽`+0x28`取得，已用大小位于缓冲区的`+0x18`，追加操作会设置缓冲区的`+8`的位1）；唯一调用方是该处理程序（`main + 0x58838`）。处理程序随后在以下位置传递该构建器：`main + 0x58854`: `x0 = [component + 0x3528]`, `main + 0xB1304`。该方法对`[session + 0xD0]`调用一个方法，将它继续作为参数传入，将位于`+0xD8`的u32清零，并调用`main + 0xD4DD0(x0 = [session + 0x70], x1 = [session + 0xD0], x2 = [session + 0x30], x3 = the builder)`。传递操作取得`X = [session + 0x30]`并调用`X`的虚函数表槽`+0xA8`，调用形式为`(X, [session + 0x70] + 0x90, builder)`，之前先检查`X`的槽`+0xD8`（必须返回true）及`+0xE8`（必须返回false）。会话的`+0x30`由`main + 0xAF760`根据`[[session + 8] + 0xB8]`设置，即会话所有者的`+0xB8`.

`X`具有外观类的结构：`nn::pia::local::LocalFacade`（虚函数表`main + 0x1CB548`）和`nn::pia::net::NetFacade` (`main + 0x1CBE60`）共用实现，其槽为`+0xA8` = `main + 0x8D4AC`, `+0xD8` = `main + 0x8D84C`（外观对象的`+0x28`已设置且其`+0x30`非空时为true）、`+0xE8` = `main + 0x8D920`（当`[[facade + 0x30] + 0x12D8]`非零时为true）。外观对象的`main + 0x8D4AC`通过`main + 0x8C6FC`验证，锁定管理器（`[facade + 0x30] + 0x2B8`经由`main + 0x94B78`，所以外观对象在`+0x30`处持有管理器），取出构建器的`+8` (`main + 0xA3710`）处的值并交给管理器的`main + 0x99C3C`，然后将传输对象记录到`[facade + 0x48]`，并在`[facade + 0x40]`记录状态8。管理器将缓冲区传给作业的接收半部（见下文），作业的发布半部则通过管理器的二进制块构建器进入`nn::ldn::SetAdvertiseData`。

组件保存在`[component + 0x3528]`处的对象是一个`nn::pia::session::Session`：该类的方法分布于`main + 0xAF4E0`到`0xB23xx`（主虚函数表`main + 0x1CE300`，第二张位于`main + 0x1CE330`，构造函数`main + 0xAF4E0`，它初始化从`+0x10`开始的字段，并将`+0xD8`视为u32）。其方法设置`+0x30` (`main + 0xAF760`), `+0x70`（由`main + 0xAF9F0`设置；实时状态下它持有`UpdateSessionPropertyJob`单例，其`+0x10`处的u16由设置器维护）以及`+0xD0` (`main + 0xAFA94`），并在`main + 0xAFB44`清除它们；传递调用方读取`+0x150`, `+0x528`, `+0x70`, `+0x30`, `+0xD0`和`+0xD8`，均为Session字段。组件在`main + 0x528F8`处选取它，来源是其嵌入于`+0x34A0`的对象（第一个字），或位于已重定位槽`main + 0x1D1AB0`的全局对象（该槽指向映像外部的`0x41FB1C8`），并用`main + 0xB14E0`打开它，该方法将回调`main + 0x52BB4`存入`+0x88`，并将组件存入`+0x90`。Session构造函数在映像中没有调用方，其虚函数表指针槽仅由该构造函数和析构函数加载，因此实例来自本模块外部。实时结构（模拟法语版《火红》，神秘礼物会话；使用相同的`main`二进制文件）：这一层是一组bss单例：`Session`位于`main + 0x1029950`, `SessionProtocol`位于`main + 0x1032000`，所有者位于`main + 0x9E1798`，该`LocalFacade`位于`main + 0x9E15B8`，另有三个会话作业单例位于`main + 0x103FBB0`, `+0x103FCE8`和`+0x1040180` (`LeaveMeshWithHostMigrationJob`, `ProcessHostMigrationJob`, `KickoutManageJob`）。实时会话期间，`[component + 0x3528]`恰好就是该`Session`，其中component = `[session + 0x90]`，即系统调用分发器接收的对象（其位于`+0x6050D8`的RFU影子副本保存最近的记录：活动`0x15`、用户名字节）。`[session + 8]`（所有者；同时也是`[protocol + 8]`，对所有协议均如此，以及`[reader + 0x60]`）没有虚函数表：`+0xB8`持有外观对象，`+0xC8`持有协议管理器。`[session + 0x30]`= 该`LocalFacade`（已用typeinfo验证）。会话作业的`+0x80`为`[SessionProtocol + 0x130]`= Session，其`+0x88`为SessionProtocol（其构造函数`main + 0xCB0D0`: `stp x9, x19, [x20, #0x80]`, `x9 = [x19 + 0x130]`).

广播机制属于另一个对象，即`nn::pia::local::LdnBackgroundProcessJob`（类虚函数表`main + 0x1CAC48`, `0xA60`字节，工厂函数`main + 0x7EED8`= 管理器的虚函数表槽`+0x278`，构造函数`main + 0x83A88`），它派生自`nn::pia::net::NetBackgroundProcessJob`（虚函数表`main + 0x1CB928`），并在`nn::pia::common::StepSequenceJob::Step`处嵌入一个`+0xD8`（虚函数表`main + 0x1C9770`），并在`nn::pia::local::LocalConnectNetworkSetting`处嵌入一个`+0x320`（虚函数表`main + 0x1CA2D0`）。其基类构造函数`main + 0x875BC`将网络管理器存入`+0xA8`并构建子对象；其构造函数在`+0x8C0` (`main + 0x87514`处构建广播数据构建器）。作业的方法`main + 0x84260`（虚函数表槽`+0x60`）是接收半部：它锁定管理器（`+0x2B8`），访问持有者（`main + 0x87374`作用于`[manager + 0x200] + 0xA8`和`[manager + 0x2D8]`），通过`main + 0x8885C`验证传入缓冲区（缓冲区大小`main + 0xA2C90`位于管理器槽`+0x100`给出的上限内，缓冲区的`+0x8`的位1已设置，`[manager + 0x12D8]`为零，`main + 0x879C0`使用`w2 = 8`检查，时间戳位于`[job + 0xA0]`），将缓冲区的`0x180`字节广播区域（`+0x1C`）复制到作业中位于`+0x8C0` (`main + 0x87578`的构建器），并将作业的下一步设为槽`0x130`。它通过作业虚函数表被调用：管理器的`main + 0x99C3C`将缓冲区交给保存在`+0x250`的对象（一个`StepSequenceJob::Step`派生的委托，构造函数`main + 0xA2824`, `0x98`字节，一个`0x38`字节的辅助对象位于`+0x88`，管理器位于`+0x90`），其`main + 0xA28E4`调用作业的槽`+0x60`，调用形式为`(job, helper, buffer)`。发布半部是作业的`+0x130` (`main + 0x84360`），它将作业构建器`+0x8C0`传入管理器的槽`+0xD0`，位于`main + 0x8445C`。Pia自身会话作业的步骤中有八处调用位置（`main + 0xCB0CC`-`0xCC738`; `nn::pia::session::LeaveMeshWithHostMigrationJob`，虚函数表`main + 0x1CEB70`, `nn::pia::session::ProcessHostMigrationJob`, `main + 0x1CEBA0`, `nn::pia::session::KickoutManageJob`，以及构造槽位于`main + 0x1D26F8`-`0x1D2728`的类），每处都由作业位于`+0x90`的状态字节控制，读取位于`+0x80`的持有者（其为`[SessionProtocol + 0x130]`，即`Session`；已实时验证），并调用`[holder + 0x30]`的虚函数表槽`+0x130`; `[holder + 0x30]`是该`LocalFacade`（实时typeinfo验证），其`+0x130`条目为`main + 0x8E0B4`.

该链受包装层网络状态控制，属于领队端路径。该`swi 0x47`主体仅在会话非空、位于`component + 0x690`的字节已设置、`component + 0x2770`至少为10且会话判断函数`main + 0xB06BC`返回false时才传递（`main + 0x5879C`-`0x587DC`）。位于`+0x690`的字节是监听器列表的启用标志：它在`main + 0x53A58`被设置，仅在`[component + 0x6A0] == [component + 0x6A4]`时如此（包装层的扫描与加入这对操作），并由带标签属性分发器的遍历过程清除（`main + 0x4EBB0`，模式`-2`），也由将`-1`写入两处的拆除过程清除。传递操作自身的条件检查随后比较管理器内两个Pia地址结构体：`X`的槽`+0xD8`尾调用`main + 0x95C90`，要求`[manager + 0x1268]`和`[manager + 0x1288]`均通过`main + 0x74BE0`（地址有效），并在`main + 0x74C18`中比较相等（先比较以下位置的u16：`+0x18`，再比较以下位置的0x10字节：`+8`）；槽`+0xE8`要求`[manager + 0x12D8]`为零。这两个结构体保存包装层本地地址（模拟器上为`127.0.0.1`）及对端地址（主机端IP），因此只有主机是当前网络领队时，该链才运行。加入网络的主机，其记录保留在影子副本中；游戏数据仍通过会话传到父端。

已在模拟器上实时确认，单帧内全部八跳均完成，使用一个`swi 0x47`，携带版本5、语言2、训练家ID`0x1234`、活动`0x45`及用户名`PKLDNTST`：处理程序影子副本接收24字节；手动设置条件字节，并令地址对相等后，会话的`main + 0xB1304`运行，外观对象的`main + 0x8D4AC`接收栈上的构建器（其应用数据包含30字符记录文本`Z8J4;Vk.+>\`.uN;###########`），管理器的`main + 0x99C3C`及其`+0x250`委托的`main + 0xA28E4`继续传递，作业的`+0x60`验证它并将`0x180`字节区域复制到作业中位于`+0x8C0` (`main + 0x87578`的构建器），作业的`+0x130`由状态机运行，管理器的二进制块构建器`main + 0x80C3C`接收包含同样记录文本的作业构建器。作业自身以状态机方式运行：其`+0x38`/`+0x40`保存当前步骤（带一位虚调用标志的虚函数表槽，或直接函数），基类方法`main + 0x6EAA0`（“ExecuteCore”，作业的槽`+0x20`）负责分发；观察到的步骤包括虚函数表槽`0xB8`, `0xC8`, `0xD8`, `0xE8`, `0xF8`, `0x108`, `0x118`, `0x138`, `0x148`以及直接函数，例如`main + 0x891F0`.

管理器类（`nn::pia::local::LdnProtocol`；虚函数表`main + 0x1CA5B0`，指针在`main + 0x7E244`处根据已重定位槽`main + 0x1D1E98`生成）保存自身的`NetworkInfo`，位于`[manager + 0x2D8] + 0xB8`：广播大小为`NetworkInfo + 0x26A` (`+0x322`），二进制块`NetworkInfo + 0x26C` (`+0x324`), `NetworkInfo + 0x282`位于`+0x33A`。其方法`main + 0x80C3C`（构建器应用数据的唯一使用方；`main + 0xA2C70`只有这一个调用方）清零`+0x380` (`NetworkInfo + 0x2C8`），将应用数据复制到该处，将大小设为应用数据大小加`0x5C`，存入`+0x322`，将`0x5C`字节Pia系统头写入`+0x324`，使用持有者自身方法（其虚函数表槽`+0x68`），并调用`nn::ldn::SetAdvertiseData(holder + 0x324, size)`（PLT为`main + 0x160A90`，GOT为`0x1d3800`）。另有两个管理器方法广播第二个对象的数据（`main + 0x7F990`, `0x81140`: `[object + 0x18]`，大小为其虚函数表槽`+0x38`加`main + 0x8AC20`），而`main + 0x80EBC`会在广播前根据`[manager + 0x128]`重建持有者。

`component + 0x2770`（经由`[component + 0xD0]`）由`swi 0x53`（布尔值）以及`main + 0x0511CC`和`main + 0x0511F4`读取，后两者无法由任何系统调用进入。`main + 0x0511F4`将它与10比较，达到或超过时原子加载位于`component + 0x2790`的标志；标志已设置时，进入`main + 0x057250`的后续代码，它检查第三参数是否为空。其调用方尚未确定。

该`bkpt #0x52`组件还拥有分发器（其虚函数表槽21）以及2324个种类名称，每个名称包含六种语言，使用djb2计算哈希（`main + 0x056540`，字符串位于`main + 0x1C4470`）。分发器栈帧由所有处理程序共用，包含`0x40`字节保存的寄存器，另加`0x310`.

`bkpt #0xFF`从载荷中调用它会关闭游戏：包装层提交会话的游玩报告、结束LDN、停止音频、提交根据存档构建的报告、提交存档并退出。主机端收不到响应。Ryujinx的`prepo`打印出的报告如下：

| 报告类别 | 字段 |
| --- | --- |
| `network`，每个连接会话一份 | `Flavor` 66, `Trainer`（32位训练家ID）、`Zone`（连接活动，神秘礼物为21，`ACTIVITY_WONDER_CARD`）、`Duration`, `Players`, `Slot`, `Rtt` |
| `game`，退出时提交 | `Flavor`, `TimeStamp`, `Trainer`, `Gender`, `Duration`, `Badges`（位掩码）、`TotalBadges`, `HallOfFame`, `TotalHallOfFame`, `CompleteRegionalPokedex`, `RegionalPokedexCnt`, `RegionalPokedexCap`, `CompleteNationalPokedex`, `NationalPokedexCnt`, `NationalPokedexCap`, `Distributed`, `LinkExchange`, `LinkBattle`, `MonsNo1..5`和`MonsNoNLevel`, `Money`, `CommsError` |

### 游玩报告由哪些内容构成

游戏报告从闪存映像解析。`main + 0x05A280`根据扇区尾部信息寻找最新槽（签名`0x08012025`），将其14个扇区（0xE000字节）复制到`component + 0x140 + 0x70`，然后`main + 0x05A370`使用各游戏对应的描述表遍历：徽章标志位、名人堂和图鉴标志、与存档密钥异或的金钱。每个偏移及位索引都来自静态表；复制后的存档只提供一个计数，`playerPartyCount`（一个字节），它约束位于`main + 0x05AAE0`的队伍遍历，255个0x64字节条目仍处于0xE000副本以内。`swi 0x57`填充`MonsSelect`（最初的伙伴，通过位于`main + 0x17DA8C`的内部编号到全国编号表转换）；打印的JSON仅包含表中固定子集，并省略`MonsSelect`. `swi 0x62`递增`component + 0xE1B0`，后者成为`CommsError`：每次调用都会让`CommsError`在下次由Ryujinx的`ServicePrepo ProcessPlayReport`打印到主机端日志的报告中加1。SaveBlock2指针由`swi 0x55`存入`component + 0xE1BC`，其唯一读取方是`main + 0x0577D8`，它检查`optionsButtonMode == 2`（L=A）。存储位置就是处理程序自身，`main + 0x057308`：分发器设置`x8 = component + 0xE1B0`，位于`main + 0x057058`，处理程序将加入端原始的`r0`存入`[x8 + 0xC]`。读取方将保存的字通过区域表折叠，检查边界并读取一个字节，`+0x13`深入折叠后的区域：两者均相对于加入端，并接受边界检查。

`main + 0x059CE4`根据游戏代码选择表；应用包含全部五张表：

| 游戏代码 | 表 | `Flavor`基数 |
| --- | --- | --- |
| `AXV?` | 《红宝石》 | 0x10 |
| `AXP?` | 《蓝宝石》 | 0x20 |
| `BPE?` | 《绿宝石》 | 0x30 |
| `BPR?` | 《火红》 | 0x40 |
| `BPG?` | 《叶绿》 | 0x50 |

`Flavor`加上该语言在`JEFIDS`中的索引，因此法语版《火红》报告为`0x42` (66).

该表按ID顺序寻址14个扇区，每个0x1000字节：字节偏移`o`对应SaveBlock1偏移`((o >> 12) - 1) * 0xF80 + (o & 0xFFF)`。一个标志是一对`(bit, byte)`；位号大于7表示不存在。对照三个反编译项目解码如下：

| 字段 | 《红宝石》/《蓝宝石》 | 《绿宝石》 | 《火红》/《叶绿》 |
| --- | --- | --- | --- |
| 徽章，8个标志，起始于 | 字节`0x23A0`位7，`FLAG_BADGE01_GET`0x807 | `0x23FC`位7，0x867 | `0x2064`位0，0x820 |
| `HallOfFame` | `0x23A0`位4，`FLAG_SYS_GAME_CLEAR`0x804 | `0x23FC`位4，0x864 | `0x2065`位4，0x82C |
| `Money` | `0x1490`（SaveBlock1 + 0x490），无密钥 | `0x1490`，异或`0x00AC`（SaveBlock2 `encryptionKey`) | `0x1290`（+0x290），异或`0x0F20` |
| 队伍数量、队伍 | `0x1234`, `0x1238` | `0x1234`, `0x1238` | `0x1034`, `0x1038` |
| `TotalHallOfFame` | `0x25E8`, `GAME_STAT_ENTERED_HOF` | `0x2644` | `0x22A8` |
| `LinkExchange` | `0x2614`, `GAME_STAT_POKEMON_TRADES` | `0x2670` | `0x22D4` |
| `LinkBattle`，以下各项之和： | `0x261C..0x2624`、连接对战胜场、负场、平局 | `0x2678..0x2680` | `0x22DC..0x22E4` |
| 地区图鉴大小 | 202 | 202 | 151 |

如果游戏有金钱密钥，游戏统计数据也使用该密钥异或。

`Distributed`共四个位，每一位都是开启前往凭票专属岛屿渡轮的标志：

| 位 | 标志 | 《红宝石》/《蓝宝石》 | 《绿宝石》 | 《火红》/《叶绿》 |
| --- | --- | --- | --- | --- |
| 0 | 肚脐岩（神秘船票） | 不存在 | `0x240C`位0，`FLAG_ENABLE_SHIP_NAVEL_ROCK`0x8E0 | `0x2069`位2，0x84A |
| 1 | 诞生之岛（极光船票） | 不存在 | 不存在 | `0x2069`位3，0x84B |
| 2 | 南方孤岛（无限船票） | `0x23AA`位3，`FLAG_SYS_HAS_EON_TICKET`0x853 | `0x2406`位3，`FLAG_ENABLE_SHIP_SOUTHERN_ISLAND`0x8B3 | 不存在 |
| 3 | 遥远的孤岛（古航海图） | 不存在 | `0x240A`位6，`FLAG_ENABLE_SHIP_FARAWAY_ISLAND`0x8D6 | 不存在 |

在《火红》和《叶绿》中，这两个标志都由船票的神秘事件脚本[mystery_event_msg.s:222,281]以及Switch版本的名人堂发放逻辑[post_battle_event_funcs.c:58]设置；若继承的存档已经进入过名人堂，则报告为0。

### 屏蔽词过滤器

`swi 0x4D`，处理程序为`main + 0x0571FC`，将`r0`解析为GBA地址，要求其后至少有256字节，将ASCII字符串转换为UTF-16，执行平台的粗俗用语检查，然后原地重写字符串。`r1`非零时选择游戏从不使用的第二种模式（`r1`= 1时遮蔽效果相同）。游戏通过`svc_BadWordCheck`调用它，将名称转换为ASCII后再转换回来[sloopsvc.c:211]。命名画面只有在它返回0时才保存输入名称[naming_screen.c:686]。

| 发送的字符串 | `r0` | 处理后的字符串 |
| --- | --- | --- |
| `hello world` | 0 | `hello world` |
| `hello fuck` | 1 | `hello `，后接四个`0xA1`字节 |
| `POKELDN` | 0 | 未变化 |
| `ASSASSIN` | 0 | 未变化 |
| `NINTENDO` | 0 | 未变化 |

路径[main + 0x0571FC -> main + 0x057458]：处理程序折叠`r0`，要求折叠位置之后有`0x100`字节，并将字符串复制到一个`0x100`字节的栈缓冲区，位于栈帧`-0x100`（位于`main + 0x85645F0`的复制操作受其`w1 = 0x100`参数限制）。UTF-16转换从该缓冲区读取，输出到一个`0x200`字节缓冲区，位于`sp + 0x10`（[main + 0x855F100]，`w2 = 0x200`），粗俗用语检查通过全局指针运行[main + 0x574AC，被调用方`main + 0x86664C0`]，遮蔽后的字符串复制回加入端折叠地址。两个缓冲区均结束于分发器自身的`0x310`字节栈帧内（`sp + 0x210`和`sp + 0x310`）；复制既不会触及保存的寄存器，也不会超出栈帧。替换字节是常量`0xA1`.

### 包装层自身的扫描流水线

包装层使用`nn::ldn::Scan`通过自身PLT扫描网络（`main + 0x160B70`; `ScanPrivate`位于`main + 0x160B60`），由管理器对象`x23`在调用位置`main + 0x80944`/`0x8095C`发起，参数为`w2 = 0x18`个网络，写入位于`manager + 0x14C0`的内联数组，24个条目，每个`0x480`（初始化时清零一次，`main + 0x7E290`）。模拟器自身的ldn服务将线上`ScanResponse`消息体直接转换为`NetworkInfo`，不检查长度，因此另一端的字段值会原样到达包装层。

一个消费循环（`main + 0x80A20..0x80B9C`）遍历数组：先清零一个`0x480`字节记录，位于`sp + 0x128` (`main + 0x874A0`），再将条目转换进去（`main + 0x87374`：先通过一次memcpy将整个`0x480`复制到`record + 0xB8`，再精确按位读取字段：源`+0xA`, `+0x11`（15字节整数解析，`main + 0xA9830`，支持十六/八/十/二进制及`b`/`x`前缀，每次推进均检查边界）、`+0x26A`（广播数据大小）、`+0x281`/`+0x282`, `+0x11A..0x11F`；存入记录`+0x90`, `+0xA0`, `+0xA2`, `+0xA4`, `+0xA6`, `+0xB0`），随后将记录交给过滤虚函数及接受虚函数（`main + 0x80A88..0x80A94`).

被接受的网络进入父端候选列表：16个槽，每个`0x1A`字节，位于`owner + 0x6050F2`，写入索引位于`owner + 0x605294`，最大为15（`cmp w8, #0xf; b.le`[main + 0x58C3C]）；数组结束于`+0x605292`，紧邻索引。填充操作对应所有者类（虚函数表`main + 0x1C3B30`）的槽`+0xA0`, `main + 0x58BF8`，由`main + 0x536A4`针对每个扫描结果中的站点调用；站点名称长度来自站点自身虚函数[槽`+0x50`]，并且`sub w8, w0, #1; cmp w8, #0x3f; b.hi`[main + 0x5364C]在调用前丢弃`x6 > 0x40`。填充函数内部，一个`0x41`字节栈缓冲区位于`sp + 7`，接收`memcpy(sp + 7, x5, x6)`，当`x6 > 0x40`时跳过清零尾部的memset[main + 0x58C68]：对于`x6 > 0x40`，复制会触及栈帧保存的`x29`/`x30`（缓冲区偏移`0x59`/`0x61`）。已解码的唯一调用方会先限制长度，因此经该调用方传入的长度最多为`0x40`；映像中有八处加载类的槽`+0xA0`, `main + 0x536A4`，其中只有此处已确认在该类上分发。

在模拟主机上测得，一个主机端正在广播时：计数1，槽0逐字节等于主机端广播：16字节游戏数据（活动`0x15`）、8字节显示名称、父端ID u16（`0x59f1`).

在`main`中，列表仅通过填充函数族写入（`main + 0x58BB4`, `0x58BE4`, `0x58BF8`），均为虚调用；映像中其他以组件为基准的访问全部是读取。所有者类的虚函数表指针`main + 0x1C3B30`在`main`中通过加载已重定位槽`main + 0x1D1B38`（值为`main + 0x1C3B20`）并加上`0x10`: `main + 0x58558`在清零位于`component + 0x6050F0`的候选列表时存入它，以及`main + 0x58FD8`/`0x59054`，位于两个组件初始化函数中。同样写法也用于生成管理器类指针（槽`main + 0x1D1E98`; `main + 0x7E244`, `0x7E4D0`）及会话类指针（槽`main + 0x1D2770`; `main + 0xB7D24`, `0xB7E78`).

### Pia会话消息分发器

包装层的原生Pia会话接收逻辑是在`main + 0xB9FC0`处按类型执行switch。它遍历节点链：`[node + 0x10]`是消息体，首字节为类型，而节点自身开头的三个字节是用作队列键的协议地址。当管理器对象的`[x0 + 0xA0]`非零且类型不大于`0x11`时分发节点，switch为`adr x8, main + 0xB9FD0` (`main + 0xB9FCC`), `ldrb w9, [main + 0x180FC9 + type]` (`main + 0xB9FC4`; `adr x27, main + 0x180FC9`，位于`main + 0xB9EFC`), `add x8, x8, w9, lsl #2`, `br x8`。位于`main + 0x180FC9`的字节表每种类型对应一个条目；十八个case代码块位于`main + 0xB9FD0 + index * 4`，每个均以无条件的`b main + 0xB9F80`结束，且各自调用处理程序（`main + 0xBCB60`, `main + 0xBE438`, `main + 0xBE8BC`, …).

每个处理程序在访问消息之前，都根据消息长度检查读取边界：类型1处理程序`main + 0xBE438`以`cmp w2, #0x15; b.ne`开头（只有`0x15`字节的消息才会进入复制），审计解码的各类型检查分别为：类型2`>= 4`、类型3`== 0x16 or 0x22`、类型4`== 0xf`、类型6`>= 0xf`、类型9`== 0x1e or 0x2a`、类型10及12`== 0x15`、类型11`>= 0xe`、类型13`== 0xa`、类型14`>= 0x4d`、类型17`>= 0xd`。变长读取器`main + 0xC0D90`根据位数计算字节数，与声明长度比较，不足时拒绝。在这组处理程序中，没有发现将消息控制的长度用于复制到固定缓冲区的情况。

这些类型是Pia会话协议自身的消息类型；主机端会话层（`pokeldn/ldn/pia_connect.py`）编号如下：0加入请求、1加入确认、2加入响应、3离开请求、4离开响应、5更新、6更新确认、7开始主机端迁移、8迁移确认。类型1处理程序`main + 0xBE438`将21字节消息读取为`[0]`类型、`[1:9]`和`[9:0xB]`为源站点的固定ID及可变ID，`[0xB:0x13]`和`[0x13:0x15]`为目标站点的对应ID；若目标ID对不匹配传输对象自身的ID对（[transport + 0x1B8]，`+0x1C0`）则拒绝，然后查找源站点并对其调用`main + 0xC9B4C`。类型2处理程序`main + 0xBE8BC`接受至少4字节的数据，根据管理器状态字节进行条件检查（`+0x30 == 0xFD`），并对消息字节3在3到0x10范围内执行switch。

接收路径的所有者是会话类（`nn::pia::session::SessionProtocol`；虚函数表基址`main + 0x1CE8E0`；其虚函数表指针在`main + 0xB7D24`/`0xB7E78`处根据已重定位槽`main + 0x1D2770`生成，构造函数为`main + 0xB7E70`）。消息泵是该类的虚函数表槽`+0x50`, `main + 0xB9CA0`，它调用遍历器`main + 0xB9DB0`；链挂在位于`[protocol + 0xF8]`的对象（会话数据包读取器，由协议管理器挂接）的`+0x70`表上（`main + 0xD6D68`返回该地址）。消息对象由`main + 0xD4430`构造（其虚函数表指针来自已重定位槽`main + 0x1D27B0`）。Pia库自身静态链接在`main`中（映像包含`SDK MW+Nintendo+PiaCommon-6_42_1-Release`及会话作业名称）。

### Pia库自身的线上数据解析

`main`链接了整个Pia 6.42.1协议栈（映像包含`SDK MW+Nintendo+...`发布字符串，针对`PiaCommon`, `PiaLocal`, `PiaNet`, `PiaSession`, `PiaTransport`和`Pia_ZStandard`，以及修饰后的类名）。上文仅以虚函数表描述的类如下：

| 前文称呼 | 类（虚函数表typeinfo中的修饰名称） | 虚函数表 |
| --- | --- | --- |
| 网络管理器 | `nn::pia::local::LdnProtocol` | `main + 0x1CA5B0` |
| 会话对象（构建器位于`+0x8C0`) | `nn::pia::local::LdnBackgroundProcessJob` | `main + 0x1CAC48` |
| 会话类（接收路径） | `nn::pia::session::SessionProtocol` | `main + 0x1CE8E0` |
| 数据包对象 | `nn::pia::common::Packet::Header` | `main + 0x1CA100` |
| 本地接收流 | `nn::pia::local::LocalInputStream` | `main + 0x1CA540` |
| 网络接收流 | `nn::pia::net::NetInputStream` | `main + 0x1CC1D0` |

传输类的虚函数表为`PacketReader` `main + 0x1CF1A8`（第二张位于`main + 0x1CE7E8`), `PacketWriter` `main + 0x1CF258`, `ProtocolManager` `main + 0x1CF3A0`, `ProtocolMessageReader` `main + 0x1CF458`, `ProtocolMessageWriter` `main + 0x1CF490`, `ReliableProtocol` `main + 0x1CF4C8`, `Station` `main + 0x1CF8C8`, `StationManager` `main + 0x1CF938`, `ReceiveThreadStream` `main + 0x1CFB20`, `SendThreadStream` `main + 0x1CFB68`；会话类的虚函数表为`Session` `main + 0x1CE300`, `SessionPacketReader` `main + 0x1CE748`, `SessionPacketWriter` `main + 0x1CE7F8`, `SessionStation` `main + 0x1CED20`；本地类的虚函数表为`LocalProtocol` `main + 0x1CA9B0`, `LocalService` `main + 0x1CB460`, `LocalFacade` `main + 0x1CB548`.

**数据包。**数据包对象大小为`0x1D18`字节：解析后的头部位于`+8`到`+0x24`，数据报缓冲区位于`+0x30`（容量为`0x1C5C`，即追加辅助函数`main + 0x75664`和`main + 0x75694`中的上限，后者在`+0x14`处记录尾部大小），接收大小位于`+0x1C90`（本地接收路径在`main + 0x7DE40`处保存它，此前执行`0x5AC`字节接收并检查该上限）。其解析函数（`main + 0x752D4`，虚函数表槽`+0x18`；入口`main + 0x752C8`提供对象自身缓冲区及常量`0x1C5C`）要求大于`0x1C`字节，并读取`0x1D`字节头部：

| 位置 | 大小 | 含义 | 存入位置 |
| --- | --- | --- | --- |
| 0x00 | 4 | 魔数`0x32AB9864`，大端序 | `+0x08` |
| 0x04 | 1 | 位0-6为版本，加密标志为`0x80` | `+0x0C` |
| 0x05 | 1 | 一个字节，保留发送时原值 | `+0x0D` |
| 0x06 | 2 | 目标可变ID，大端序 | `+0x0E` |
| 0x08 | 2 | 源可变ID，大端序 | `+0x10` |
| 0x0A | 2 | 数据包ID，大端序 | `+0x12` |
| 0x0C | 1 | 尾部大小 | `+0x14` |
| 0x0D | 8 | 随机数，保留发送时原值 | `+0x15` |
| 0x15 | 8 | GCM标签，保留发送时原值 | `+0x1D` |

此应用使用的协议版本为`0x10`（16）：有效性检查`main + 0x75610`要求魔数、`([+0xC] & 0x7F) == 0x10`以及`size - 0x1D > 2) > 0x716`时返回空指针。该容量检查允许`t`到`0x1C5B`；消息遍历器会另行根据接收大小减去头部及尾部检查（`main + 0xDE278`).

**套接字与接收流。**套接字是一个小型持有对象（构造函数`main + 0x6D93C`：fd为`-1`，位于`+0`，计数位于`+4`，地址族位于`+8`，协议位于`+0xC`); `main + 0x6D95C`打开它（`nn::socket::Socket`，PLT为`main + 0x160940`), `main + 0x6DBF4`关闭它（`main + 0x160950`), `main + 0x6DCD0`绑定它（`main + 0x160960`），而`main + 0x6DE6C`, `0x6DF44`, `0x6E00C`, `0x6E0F0`设置选项（`main + 0x160970`）。数据报调用为`main + 0x6E1D0` (`nn::socket::RecvFrom`，PLT为`main + 0x160980`，标志为`0x80`，源地址由`main + 0x6E9D0`转换回来）以及`main + 0x6E538` (`nn::socket::SendTo`, `main + 0x160990`）。本地接收流（可变ID位于`+0x88`，锁位于`+0x68`，套接字持有对象指针位于`+0x18`）运行消息泵`main + 0x7DD10`（虚函数表槽`+0x10`）：它接收数据到数据包缓冲区，并将头部解析进该对象（`main + 0x7DDEC`; `main + 0x6E1C8`是跳板）；数据包过滤器`main + 0x91280`（槽`+0x20`）首先要求数据包有效。当版本至少为7、尾部非空且目标可变ID不大于1时，尾部必须包含至少两个字节，且流自身ID（`+0x88`）必须非零，并出现在其大端序u16接收方ID列表中（`footer_size >> 1`个条目）。另外，当`([+0xC] & 0x7E) >= 6`且目标不小于2时，必须等于流自身的`+0x88`.

过滤器将接收方指针构造为`packet + (size - footer) + 0x30`，此前在`sub w8, w8, w9`处执行`main + 0x912EC`；消息遍历器`main + 0xD6460`与解析器`main + 0xDE278`将遍历边界构造为`size - footer - 0x1d` (`main + 0xD651C`, `main + 0xDE298`）。这两处减法都没有先检查尾部大小是否能容纳在数据报内。尾部大小字节位于数据报偏移12，在明文头部中，因此对端可自由设置。尾部大小超过数据报大小时，过滤器并未发生故障：六个31字节数据报，尾部设为`0x40`，均到达套接字，会话继续运行（在模拟器上测得）。

**线程。**传输层接收和发送循环为`nn::os`线程，名称分别为“Pia ReceiveThreadStream”（启动于`main + 0xE9020`，名称通过`adr`在`main + 0xE9034`处设置）及“Pia SendThreadStream”（`main + 0xEA758`），通过`main + 0xF6010` (`nn::os::CreateThread`创建，PLT为`main + 0x15FDF0`，以及`StartThread`, `main + 0x15FE00`).

**从线上数据到会话处理程序。**接收到的会话消息由会话数据包读取器解析，并放入按地址组织的表中，会话协议在每次更新时遍历该表。

`nn::pia::session::SessionPacketReader`（虚函数表`main + 0x1CE748`）继承自`nn::pia::transport::PacketReader`（虚函数表`main + 0x1CF1A8`）。读取器的`+0x30`方法（`main + 0xD5DE0`）处理接收的数据包，并调用`main + 0xD6460(reader, packet)`遍历其中消息。遍历器从数据报偏移`0x1D`开始，在`packet_size - footer_size` (`main + 0xDE278`, `0xD6510`-`0xD6538`）之前停止；尾部紧随载荷。它使用`main + 0x74EA8`解析每条消息，通过读取器的`+0x78`虚函数（`main + 0xD6D0C`：消息中位于`+0x2C`的u16，加上位于`+0x2E`的字节作为高位）取得用作队列键的协议地址，并调用`main + 0xD6944(table, address, message)`.

该表嵌入于`reader + 0x70`：u32桶数量位于`+0`，桶数组指针位于`+8`（每桶0x18字节，链头位于`+0`，链尾位于`+8`），可选哈希回调位于`+0x40`. `main + 0xD6944`先加载数组指针，再加上`index * 0x18`；桶并非内联于表中。桶索引为`callback(address) % count`，若未设置回调则为`(address[0] + address[1] + address[2]) % count`。`main + 0xD71F0(bucket, address, message)`取出一个节点，将消息复制进去（三个地址字节位于`+0`，消息体指针位于`+0x10`，ID位于`+0x18`，其他字段位于`+0x20`到`+0x30`，其余字段直到`main + 0x74C54`），并将其追加到桶的双向链表（next位于`+0x78`，previous位于`+0x80`).

协议侧：`nn::pia::session::SessionProtocol`的`+0x50`虚函数（`main + 0xB9CA0`）在每次更新时运行`main + 0xB9DB0`。它读取`[protocol + 0xF8]`（读取器，按下文方式挂接），取得读取器位于`+0x70`的表，根据协议自身的三字节地址计算桶（位于`+0x120`的u16及位于`+0x122`的字节，由`+0x18`虚函数`main + 0x828E4`读取；该地址对是一个`nn::pia::transport::Protocol`字段，由`main + 0xDA614`设置），遍历链，并按位于`[node + 0x10]`的消息体首字节经跳转表分发到处理程序（`main + 0xBCB60`, `main + 0xBE438`, `main + 0xBE8BC`, `main + 0xBF2D4`等等），传入`(protocol, node, id)`.

挂接：协议管理器（嵌入在其所有者的`+0xC8`处，协议表位于`+0x18`）遍历自身表，并根据所有者的`+0xF0`和`+0xF8`设置每个协议的`+0xF8`和`+0x100`（设置器为`main + 0xDA8C8`和`main + 0xDA8D0`，广播函数为`main + 0xDB740`，在`main + 0xEC0E4`处传入该地址对；任一参数为零时都会拒绝）。该`+0xF8`对象就是读取器，因此遍历器使用的表正是读取器的`+0x70`.

实时运行时，管理器位于`[session + 8] + 0xC8`（上文的所有者），其位于`[manager + 0x18]`的表具有位于`+0`的u32桶数量及位于`+8`的桶数组指针。每桶大小为`0x18`字节：`+0`是节点，节点的`+8`是协议，节点的`+0x30`链接下一个节点。在模拟会话中，该表计数为`19`，恰好有六个协议，每种一个，以协议地址为键（u16；位于`+0x122`的字节为零，每个协议的`+0x108`保存网络的Pia可变ID，`0x8fa2`/`0x0766`): `0xfd01` `nn::pia::local::LdnProtocol`, `0xfd03` `nn::pia::transport::RttProtocol`, `0xfd05` `nn::pia::transport::UnreliableProtocol`, `0xfd0a` `nn::pia::transport::ReliableProtocol`, `0xfd0d` `nn::pia::session::SessionProtocol`, `0xfd0f` `nn::pia::transport::MonitoringDataProtocol`。协议是每种一个，而非每个站点一个：`SessionProtocol`的消息泵在8次追踪中全部进入同一个实例，读取器表节点则归档在协议地址下（`0xfd0a`，消息ID为`0x60`）。实例由`main + 0xB1F60`创建并注册（分配 `0xD8E8` 字节，调用位置为 `main + 0xDB114`，构造函数为`main + 0xB7D0C`，以地址对为键插入管理器映射）；Session构造函数调用它一次，并将返回地址存入`+0x12`/`+0x14`.

该`nn::pia::transport::Protocol`基类（虚函数表`main + 0x1CF308`，构造函数`main + 0xDA548`，虚函数表指针来自已重定位槽`main + 0x1D2808`）在`+0x120`/`+0x122`处保存三字节地址，锁位于`+0xC8`，挂接的地址对位于`+0xF0`/`+0xF8`，两个已配置的8字节加u16值位于`+0x100`/`+0x108`和`+0x110`/`+0x118`，状态字节位于`+0x123`，标志位于`+0xD8`.

## 重定向主机的传出消息

`r0`是`&client->param`，因此`struct MysteryGiftClient`[include/mystery_gift_client.h:71]相对它位于固定偏移：

| 字段 | 相对于`r0` |
| --- | --- |
| `client->sendBuffer` | 0x10 |
| `client->link.sendSize` | 0x34 |
| `client->link.sendBuffer` | 0x3C |

`MysteryGiftLink_InitSend`保存传入的指针[mystery_gift_link.c:59]；发送时从`link->sendBuffer`起，对`link->sendSize`字节计算CRC[:166]。载荷若在InitSend与实际发送之间运行，就能将主机的传出消息指向任意地址：

```
CLI_RECV -> CLI_LOAD_TOSS_RESPONSE -> CLI_RUN_BUFFER_SCRIPT -> CLI_SEND_LOADED
```

若顺序相反，InitSend会覆盖载荷的修补。

切勿转储在CRC计算帧与发送帧之间会变化的区域：

```
case 0:  header.crc = CalcCRC16WithTable(link->sendBuffer, link->sendSize);   // one frame
case 1:  SendBlock(0, link->sendBuffer + blocksize, ...);                     // the next
case 2:  if (CalcCRC16WithTable(...) != link->sendCRC) LinkRfu_FatalError();  // the one after
```

[mystery_gift_link.c:155]。`gRngValue`（0x03004220）每帧前进两步；转储覆盖它时，消息体CRC会失败，主机报告“连接错误”。`buffer_script.build_memory_dump`拒绝任何与它重叠的范围；请绕开它转储，或使用`rng-trace`，后者通过4字节通道返回它。其他易变区域也必须用同样方式找出。

## 载荷

### `trainer-id-probe`

24字节，只读。主机早在数秒前就已通过`playerTrainerId`发送自己的`MysteryGiftLinkGameData`[mystery_gift.c:337]，因此响应值已知。

```arm
    ldrh    r3, [r1, #0x0A]         @ SaveBlock2.playerTrainerId[0..1]
    ldrh    ip, [r1, #0x0C]         @ SaveBlock2.playerTrainerId[2..3]
    orr     r3, r3, ip, lsl #16
    str     r3, [r0]                @ *param
    mov     r0, #1
    bx      lr
```

匹配意味着它在ARM状态下，使用反编译项目中的参数，访问真实的`gSaveBlock2Ptr`并返回1；值不同意味着参数或偏移错误；没有`Buffer script status:`日志行意味着客户端脚本结构错误，或根本没有到达调用。7字符玩家名称的结束符会覆盖游戏数据中的`playerTrainerId[0]`[mystery_gift.c:364]；此时主机端比较最高三个字节。

### `save-dump`和`memory-dump`

`memory-dump`接受绝对地址。`save-dump`通过r1和r2读取任一存档块的任意偏移，适用于所有构建。每次最多1024字节；`MGL_Receive`拒绝更大长度[mystery_gift_link.c:102]。

```
HOST --buffer-script save-dump --dump-block sav2 --dump-size 256 --version firered
HOST --buffer-script memory-dump --dump-address 0x0201C000 --version firered
```

它们可以访问`SaveBlock1.playerParty`，位于0x0038；`money`，位于0x0290，与`SaveBlock2.encryptionKey`（位于0xF20）异或；还可访问背包、标志、变量以及IWRAM（`gRngValue`).

### `memory-dump-multi`和`memory-dump-scatter`

`MG_LINK_BUFFER_SIZE`限制的是单条消息，而非整个会话。客户端从其1024字节接收缓冲区运行命令脚本[mystery_gift_client.c:140]，其中转储三元组

```
CLI_LOAD_TOSS_RESPONSE -> CLI_RUN_BUFFER_SCRIPT -> CLI_SEND_LOADED
```

只要容得下就可重复：每条命令8字节，循环前后另有三条固定命令，可执行41轮。`mg_script.MAX_DUMP_BLOCKS`将其限制为32轮，因为会话中断会丢失所有数据块。通过ESP32无线模块转储16 KB约耗时57秒，块间隔约2.5秒。

`CLI_RUN_BUFFER_SCRIPT`每轮重新复制映像[:238]，因此游标保存在`client->param`中：每轮发送`base + index * 1024`，并传递下一个索引。一个`param`若高半部没有`0x5A5A0000`，则表示第零轮。

`memory-dump-scatter`则改为索引基址表：

```
adr     r3, .Ltable
ldr     r3, [r3, r1, lsl #2]    @ this block's own base
str     r3, [r0, #0x3C]         @ client->link.sendBuffer
```

`adr`是PC相对寻址。全部32个槽均已填充，未用槽填入最后一个地址，因此多执行一轮只会重发已有数据块，而不会将消息指向0。相比连续块，离散块每次加入可覆盖的短函数主体约多四倍；对于跨越一兆字节的166个尚未读取函数主体：

| 一次加入，从线上接收16 KB | 覆盖的函数主体数量 |
| --- | --- |
| `memory-dump-multi`，从最佳基址起的十六个连续块 | 22 |
| `memory-dump-scatter`，最密集的十六个千字节区域 | 83 |
| `memory-dump-scatter`，32个块 | 166个中的119个 |

可读性保护检查每个离散块。各块首尾相接写入同一个文件；`--dump-scatter A,B,C`让`script_read.dumps`将每块放入各自基址，并标记为`[0]`, `[1]`, … `--dump-blocks 1`返回`CLIENT_SCRIPT_DUMP_MEMORY`，逐字节一致。

### `anchors`

将十一个字写入`client->sendBuffer`，并将`link->sendSize`扩展为44；无需重定向，因为`CLI_LOAD_TOSS_RESPONSE`已经将`link->sendBuffer`指向那里[`MysteryGiftClient_InitSendWord`，mystery_gift_client.c:91]。

| 字 | 含义 | 某次启动 |
| --- | --- | --- |
| 0 | `sub ip, pc, #8`：主机放置代码的位置 | 0x0201C000 |
| 1 | `lr`：调用之后的ROM地址[mystery_gift_client.c:276]，位0已设置，因为调用方为THUMB | 0x08148C75 |
| 2 | `sp` | 0x03007DB8 |
| 3 | `r0` = `&client->param`，也就是`AllocZeroed`在`gHeap` | 0x020020D4 |
| 4-5 | gSaveBlock2Ptr, gSaveBlock1Ptr | 0x02024598, 0x0202553C |
| 6-9 | 四个AllocZeroed缓冲区：send、recv、script、msg | 0x02006510 .. 0x02007140 |
| 10 | `link->sendBuffer`保持InitSend留下的值；必须等于第6个字 | 0x02006510 |

第4-5个字在每次战斗及加载时变化[load_save.c:75]；第3个及第6-9个字取决于堆状态。第1个字锚定反编译项目中的调用位置；第10个字等于第6个字可确认结构体偏移。缓冲区间隔0x410（1024字节加16字节块头），符合`malloc.c`中的描述。`buffer_script.describe_anchors`打印全部十一个字及其一致性检查。

### `save-write`

将载荷尾部复制到存档块，然后将`link->sendBuffer`指向目标，因此响应就是存档当前保存的内容。会话以`CLI_MSG_BUFFER_SUCCESS`结束，随后进入`MG_STATE_SAVE_LOAD_GIFT`并将写入提交到闪存；从标题画面重新加载后仍然保留。

```
HOST --buffer-script save-write --dump-block sav2 --dump-offset 0xB20 \
    --write-text "some text" --version firered
```

一个载荷携带936字节。更长数据分为每片936字节，每片一个载荷，在会话中依次运行；客户端根据命令列表逐个接收并运行[mystery_gift_client.c:145, 236]。响应为最后一片所覆盖位置的存档内容。

`build_save_write`拒绝超出以下区域的任何范围：`filler_90[8]`位于0x090，以及`filler_B20[0x400]`位于0xB20，均在`struct SaveBlock2`[global.h:345,357]中，`src/`没有任何代码引用它们。在`filler_B20`之后四字节处是`encryptionKey`，金钱使用它异或。`--write-unsafe`可覆盖此限制。该块在闪存中的落点轮换变化（[ID所在的位置](#where-an-id-lives-and-which-sector-carries-the-slots-counter)).

一次`save-write`仅改变指定范围：一次256字节写入改变SaveBlock2中196字节，全部位于指定范围内，SaveBlock1则无变化。游戏没有任何代码写入`filler_B20`：该处写入经过保存（测量了十代）、神秘事件、神秘卡片、软重置及游玩仍然保留（游玩一分钟后256字节均未变化，而期间SaveBlock1中有1456字节改变）。

### `memory-scan`

接受一个32位目标值及范围。每次调用扫描其预算内的32字节块，将游标写回自身映像并返回0；到达末尾的那次调用将`link->sendBuffer`重定向到结果并返回1。映像开头是一条跳过参数的分支：

| 偏移 |  |
| --- | --- |
| 0x000 | `b .Lcode` |
| 0x004 | 游标：起始地址，由载荷推进 |
| 0x008 | 结束位置 |
| 0x00C | 目标值 |
| 0x010 | 每次调用的块数 |
| 0x014 | max_calls，看门狗上限 |
| 0x018 | 结果：找到的匹配数、最终游标、已用调用次数、已存储匹配数 |
| 0x028 | 结果：64 ×（地址，值） |
| 0x228 | 代码 |

预算用于保护需要逐帧运行的RFU连接。内循环为一次`ldmia`加载八个字，再串接八条`cmpne`，每八个字约14条指令；默认512个块在unicorn下每次调用执行7703条指令，从EWRAM运行约耗60000周期，而每帧有280896周期（16位总线，ARM取指约6周期）。16 MB卡带需要1024次调用，约17秒。`--scan-blocks`负责设置；全过程主机端每秒约读取60个子端帧。

`max_calls`默认设为扫描范围所需次数再加二；看门狗停止时，响应中较短的游标说明应从何处继续。响应始终为528字节，因此`len(dump) == buffer_dump_size`可证明重定向成功。`found`统计所有匹配，`hits`保存前64个。`ldmia`只能发现字对齐的匹配：若目标值按真实步长从不出现在字对齐位置，就会返回零。

### `table-scan`

根据形态寻找表：找出每个由`runlen`个字构成的极大连续序列，每个字恰好比前一个大`delta`，返回序列起点及首值。`gSpecialVars`[data/event_scripts.s:51]列出`gSpecialVar_0x8000`到`0x800B`，共十二个连续的`u16`[event_data.c:16]，因此其前十二个字以2递增，首值为`&gSpecialVar_0x8000`.

```
HOST --buffer-script table-scan --table-delta 2 --table-runlen 12 \
    --table-start 0x08140000 --table-end 0x08400000 --version firered
```

条目12是`gSpecialVar_Facing`，声明在`Result`和`LastTalked`之后，相比条目11增加6，因此序列恰好十二项，要求13项就找不到。

形态测试每字约7条指令，而值测试约1.75条，因此`TABLE_SCAN_DEFAULT_BLOCKS`设为192个16字节块，与`memory-scan`的512个32字节块负载相同。`run`, `runstart`和`expect`保存在0x22C..0x234，位于游标旁，每次让出执行时都会保存，因为一个连续序列可能跨越`ldmia`和帧边界。`expect`初始为0，因此首字为零时会被计入一个尚未写入`runstart`; `read_table_scan`会丢弃范围外的命中。

相同形态也可找出实时的`struct ScriptContext`: `InitScriptContext`在+0x5C及+0x60处保存命令表及其末尾[include/script.h]，17条目表的两者相差68，因此`--table-delta 0x44 --table-runlen 2`扫描EWRAM会返回上下文地址及表地址。脚本运行之前上下文全为零，因此必须在同一次启动中先接收神秘事件礼物，再进行扫描。`--table-delta 0x358`（214个条目）可找到场景脚本上下文，其`cmdTable`就是已知的`gScriptCmdTable`.

### `rom-checksum`

将范围分为最多128个块分别求和，每块一个和值，使主机端能够标出卡带中与其ROM映像不同的块；随后对单块使用更小分块再运行一次即可缩小范围。逐帧循环、预算、看门狗及重定向发送均采用`memory-scan`的实现。每块按地址递增顺序从0开始累加各字：

```
acc = w + ror(acc, 31)          one `add r0, rN, r0, ror #31` per word, mod 2^32
```

`rom_checksum_reference`从ROM文件计算相同结果。异或会相互抵消（重复字得到0；相隔32个字的相同变化也会抵消）。超出参考文件末尾的块按和值标记为：全零、全0xFF、开放总线（每个半字等于自身地址除以二）、镜像或CONTENT。

| 偏移 |  |
| --- | --- |
| 0x000 | `b .Lcode` |
| 0x004 | 游标：起始地址，由载荷推进 |
| 0x008 | 结束位置 |
| 0x00C | 起始位置 |
| 0x010 | 每次调用的32字节小块数 |
| 0x014 | max_calls，看门狗上限 |
| 0x018 | 位移量：块大小的log2，范围5到25 |
| 0x01C | 当前块的累计和，跨调用保留 |
| 0x020 | 结果：最终游标、已用调用次数、已保存和值数、原样返回的位移量 |
| 0x030 | 结果：128 × u32块和值 |
| 0x230 | 代码 |

响应从0x020开始，共528字节。构建器拒绝起点未按块对齐、范围不是整数个块、超过128个块，以及块大小不是至少32字节的二次幂的情况。每八个字执行13条指令；512个小块每次调用执行6688条指令。默认扫描0x08000000..0x09000000，以128 KiB分块，共1024次调用，约17秒。

```
HOST --buffer-script rom-checksum --version firered
HOST --buffer-script rom-checksum --sum-start 0x08120000 --sum-end 0x08140000 \
    --sum-block 0x400 --version firered
```

主机端记录每块范围、两边和值以及`SAME`或`DIFF`，然后记录`rom-checksum: N of M blocks differ from `。映像为`config.REFERENCE_ROMS[game code]`，或对所有构建使用`--sum-reference`。超出映像的块会列出，但不计入统计。

### `rng-trace`

每帧采样一个字，并在每次采样的两次读取之间调用一个ROM函数（`--trace-call 0`使其变为普通采样器）。

```
HOST --buffer-script rng-trace --trace-address 0x03004220 --trace-call 0x080486B1 \
    --trace-samples 96 --version firered
```

调用为`mov lr, pc; bx r2`：读取pc得到`bx`之后的指令地址，位0清除，因此被调用方返回到ARM状态。在零售版《火红》上，每个`Random`轨迹样本均遵循LCG（实测轨迹中96个样本全部符合）。结果见[随机数生成器](frlg_rng.md).

### `string-gather`

给定第一个指针的地址、步长及数量，将各指针指向的字符串复制到同一个响应，包含0xFF结束符，并报告下次运行的继续位置。

```
HOST --buffer-script string-gather --gather-address 0x083E0D54 --gather-count 69 \
    --gather-stride 12 --version firered
```

`--gather-stride`对于`struct EasyChatWordInfo` (`text`位于0）时为12；对于一个`const u8 *`数组则为4。响应共776字节：四个头部字及最多760字节字符串。绝不截断：某字符串容不下时就结束本轮，并由`next`标明该字符串。`--gather-maxlen`（默认64）限制非字符串指针的读取范围。

### `create-mon`

```
void CreateMon(struct Pokemon *mon, u16 species, u8 level, u8 fixedIV,
               u8 hasFixedPersonality, u32 fixedPersonality, u8 otIdType, u32 fixedOtId)
```

四个参数位于`r0..r3`，另四个位于栈上。`asm/create-mon.s`遵循主机自身的函数序言：

```
08041150  push {r4,r5,r6,r7,lr}    ; sp -= 20
08041152  mov  r7, r8
08041154  push {r7}                ; sp -= 4
08041156  sub  sp, #28             ; sp -= 28, so entry sp is now sp + 52
0804115c  ldr  r4, [sp, #52]       -> entry sp +  0   hasFixedPersonality  (masked to u8)
0804115e  ldr  r7, [sp, #56]       -> entry sp +  4   fixedPersonality     (NOT masked: u32)
08041160  ldr  r5, [sp, #60]       -> entry sp +  8   otIdType             (masked to u8)
08041184  ldr  r0, [sp, #64]       -> entry sp + 12   fixedOtId            (u32)
```

四个参数以完整字写入`sp+0..sp+12`，并由载荷自行弹出。宝可梦在载荷自身映像中构建，代码前有32字节保护区；`--create-mon-destination ADDR`继续复制它，并需要`--write-unsafe`.

```
HOST --buffer-script create-mon \
    --create-mon-species 151 --create-mon-level 30 --create-mon-iv 31 \
    --create-mon-personality 0x3ADE0000 --version firered
```

`--create-mon-call`默认取`CreateMon | 1`，来自`rom_map.py`; `0`不调用任何函数，返回已清零缓冲区。响应共116字节（四个头部字及100字节的`struct Pokemon`），而`*param`是性格值。

子结构使用`personality ^ otId`加密并计算校验和，因此有效校验和可证明这两个字正确。`check_create_mon`检查种类、等级和个体值；`scratchpad/verify_create_mon.py`预测十三个派生字段：经验值来自`gExperienceTables[growthRate][level]`，亲密度及特性槽来自`gSpeciesInfo`，招式及PP来自可学招式表，六项能力值来自`CalculateMonStats`。昵称来自`gSpeciesNames`[pokemon.c:1810]，即卡带的法语名称表，只能读取，不进行预测。有三个字段用于测量主机：

| 字段 | 值 | 所说明的情况 |
| --- | --- | --- |
| `language` | 3 | `gGameLanguage`为LANGUAGE_FRENCH[global.h:22] |
| `metGame` | 4 | `gGameVersion`为VERSION_FIRE_RED[global.h:11] |
| `metLocation` | 91 | `GetCurrentRegionMapSectionId()`[overworld.c:1265]，即玩家当时站立的位置 |

`buffer_script.shiny_personality(tid, sid)`生成一只异色的`fixedPersonality`。离线桩用于`CreateMon`: `CREATE_MON_ARG_MODEL`将八个参数写入目标，`create_mon_copy_model(source)`复制100字节预备数据。

#### `--create-mon-append`

它写入的是`gPlayerParty`，而不是存档块中的队伍：

```
void SavePlayerParty(void)
{
    gSaveBlock1Ptr->playerPartyCount = gPlayerPartyCount;
    for (i = 0; i < PARTY_SIZE; i++)
        gSaveBlock1Ptr->playerParty[i] = gPlayerParty[i];
}
```

向存档块追加会报告成功，但下次保存时就会丢失[load_save.c:160,196]。它写入`slot == playerPartyCount`并增加数量，与捕获流程相同；绝不触及已占用槽，队伍已满时不写入。第五个响应字报告`countBefore | slot << 8 | status << 16`（0未请求、1已追加、2队伍已满、3试运行）。使用绝对`--create-mon-destination`或使用`--create-mon-call 0`进行追加都会被拒绝。

```
# dry run first: the same code with the two stores left out
HOST --buffer-script create-mon --create-mon-append-dry-run \
    --create-mon-species 59 --create-mon-level 30 --version firered
HOST --buffer-script create-mon --create-mon-append \
    --write-unsafe --create-mon-species 59 --create-mon-level 30 --version firered
```

试运行报告数量、目标地址及该槽当前100字节，可发现与队伍不一致的`playerPartyCount`。空槽并非全零：`ZeroMonData`最后执行`SetMonData(mon, MON_DATA_MAIL, &MAIL_NONE)`[pokemon.c:1737]，因此偏移0x55为`0xFF` (`buffer_script.EMPTY_PARTY_SLOT`, `is_empty_party_slot`).

|  | 是否移动？ | 因此 |
| --- | --- | --- |
| `gSaveBlock1Ptr` | 是，每次战斗和加载时重新生成一个随机的4字节对齐偏移[`SetSaveBlocksPointers`，load_save.c:75] | 每次调用均从`r1`/`r2`取得 |
| `gPlayerParty` | 否，链接时确定的EWRAM全局变量 | 可使用固定地址 |

`gPlayerParty`为0x02024280，而`gPlayerPartyCount`为0x02024025：这是EWRAM转储中唯一一个4字节对齐且能解码为具有有效校验和的`struct Pokemon`的窗口。

### `call`

一个地址、最多八个参数字、返回的`r0`，以及调用前后各读取一次的地址。

```
HOST --buffer-script call \
    --call-address 0x080486D1 --call-arg 0xC0DE --call-watch 0x03004220 --version firered

0x000  b .Lcode
0x004  function    THUMB pointer (bit 0 set), or 0 to call nothing
0x008  argc        how many of the eight words below are meant
0x00C  args[0..7]  r0, r1, r2, r3, then [sp+0], [sp+4], [sp+8], [sp+12]
0x02C  watch       a word to read before and after the call, or 0
0x030  result      calls used, function, argc, r0, *watch before, *watch after
```

`asm/call.s`始终压入十六个栈字节；被调用方从不弹出它们。`SeedRng`无返回值（`gRngValue = seed`[random.c:15]），因此观察字才是证据。只调用已经读出并确认为代码的地址。`tests/test_buffer_script.py`在unicorn下通过该载荷运行主机自身的`SeedRng`字节，并使用二次幂测试八参数路径。

### `flash-write`

在EWRAM中组装一个4 KB扇区，再用[`swi 0x48`](#the-flash-sector-path)写入闪存，绕过游戏的保存代码。暂存区为`gDecompressionBuffer + 0x400`，比载荷自身映像高0x400。

```
--flash-sector N            the sector, 0..31; 0..27 are the save bands and need --write-unsafe
--flash-fill-base WORD      word[i] = base + i * step, the data pattern
--flash-footer              compose a well-formed sector instead of a raw pattern
--flash-id N                the sector id at +0xFF4
--flash-derive              read the save globals and place it where that id actually lives
--flash-position N          aim at band position N and derive the id from it instead
--flash-counter-bias N      added to gSaveCounter for the footer
```

`--flash-footer`像游戏一样，从模式末尾到`+0xFF4`清零，计算游戏校验和，并写入ID、校验和、签名及计数器。状态字高半部为物理扇区，低半部为校验和。`--flash-derive`在写入时读取`gLastWrittenSector`和`gSaveCounter`：两者在每次保存时都会前进，而以成功消息结束的礼物会话会保存[mystery_gift_menu.c:1379]。

### `sloop-svc`

一次会话最多执行八个Sloop系统调用，操作数由主机端选择，通过结果块返回响应。

```
IP_HOST --buffer-script sloop-svc --svc-number 0x4d --svc-text "hello fuck" \
    --svc-data-in r0 --version firered

0x000  b .Lcode
0x004  flags       bit 0: r0 = &copy, bit 1: r1 = &copy
0x008  r0..r3
0x018  scratch     gDecompressionBuffer + 0x400
0x01C  length      of the data, at most 256
0x020  thunk       swi N ; bx lr (THUMB), or bkpt N ; bx lr with --svc-bkpt
0x024  count       1..8
0x028  numbers     eight bytes, one per call
0x030  data
```

每次调用前，载荷重新复制数据，并将编号写入跳板的低字节。结果块包括：标记`0x53565331`、计数、标记`0x53565332`、长度、八条20字节记录（跳板字、`r0..r3`的调用后值），以及最后一次调用留下的数据。仅处理值的编号（0x46、0x49..0x4B、0x4D、0x4E、0x50..0x54、0x58..0x60）原样调用；0x48、0x56、0x4C及0x55被拒绝；其余编号以及`--svc-bkpt`需要`--write-unsafe`; `--svc-bkpt`拒绝`#0x52`.

### `install-resident`

将常驻THUMB钩子复制到`0x0203FC00`，并安装到`gIntrTable[4]`，在一次会话中完成。它每帧运行，经过“继续游戏”及大地图仍然有效，直到软重置。

```
IP_HOST --buffer-script install-resident --resident turbo \
    --resident-param extra=4 --resident-param field=1 --resident-param battle=1 \
    --resident-param overlay=0x03004220 --resident-param hold=0x100 \
    --resident-param budget=228 --write-unsafe --version firered

0x000  b .Lcode
0x004  dest          0x0203FC00
0x008  length        of the hook, whole words
0x00C  table         &gIntrTable[4], 0x03002730
0x010  entry_off     the hook's entry inside it
0x014  original_off  its p_original word
0x018  blob_off      where the hook starts in this image, after the installer's code
```

THUMB安装程序为148字节，剩余876字节供钩子使用；其数据（`p_frames`, `p_ring`, `p_state`）不得与代码重叠，也不得超出`0x02040000`。复制及写表期间清除REG_IME。首次安装将被替换的处理程序保存在`0x0203FBFC`；后续安装串接到该字，该字为空时以`0xBAD0BAD0`拒绝。响应为找到的处理程序：`0x0800071D`，对应干净状态下的安装。同一时间只常驻一个钩子；全部共用位于以下位置的1 KB：`0x0203FC00`.

#### `turbo`

`asm/resident/turbo.s`运行`VBlankIntr`，然后在空闲帧中额外执行大地图回调`field`次、战斗回调`battle`次，以及`RunTextPrinters` (`0x08002D51`) `extra`次。只有当`callback1`/`callback2`恰好为`CB1_Overworld` (`0x08059E49`) / `CB2_Overworld` (`0x08059EC9`）或`BattleMainCB1` (`0x08015B6D`，由战斗初始化存入`0x08013FDE`) / `BattleMainCB2` (`0x08014889`）时才执行一轮，两次调用之间重新检查。`newKeys`和`newAndRepeatedKeys`先清零，使一次按键只处理一次。

当`gPaletteFade.active` (`0x02037AB4`）被设置时不执行任何一轮：硬件渐变结束的条件是`UpdatePaletteFade`设置一位的`hardwareFadeFinishing`，并由下一次垂直消隐观察到[palette.c:701, 743]；同帧第二次更新会将该位回绕至0，随后`CompleteWhenChoseItem`会在战斗关闭背包后永久等待。另有两个条件：

-
-

模拟器实测：每秒60帧，97%空闲，文本每帧五个字形；`field=1`使大地图速度翻倍，`battle=1`使战斗及其菜单速度翻倍。

`hold=MASK`仅当`gMain.heldKeys` (`gMain + 0x2C`）中掩码指定的所有按键都按住时才执行额外回调；额外文本处理则始终运行。使用`hold=0x100`（R）时，钩子每帧向`gHelpSystemToggleWithRButtonDisabled` (`0x0203F171`存入1，即`0x0813F6FC`中位于`RunHelpSystemCallback`, `0x0813F65C`的字面量），因此R不会打开帮助系统[help_system_util.c:50]；L仍可打开。

`budget=LINES`按时间限制轮数。Switch模拟器在每帧代码运行期间推进`REG_VCOUNT`（0到227，从160开始为垂直消隐）；只有自垂直消隐以来的行数，加上上次执行耗时的两倍，仍不超过`LINES`时，才开始一轮。上次耗时位于计数器`+0x0C`，延后执行的轮数计于`+0x10`；每次延后都会将保留的耗时估计缩减八分之一。

模拟器实测：

| 设置，按住R | 每帧额外轮数 | 说明 |
| --- | --- | --- |
| `field=2 battle=2` | 目标2轮，实际1.70到1.90轮 | 约2.9倍，无可见卡顿 |
| `field=3 battle=3` | 目标3轮，最多2.38轮 | 约四分之一帧卡顿；有可见顿挫 |
| `field=3 battle=3 budget=228` | 最高2.48轮 | 流畅；行走时每轮耗36到42行，战斗时100到108行 |

`overlay=ADDRESS`将位于`ADDRESS`的字绘制为八位十六进制数字，显示在大地图右上角（`0x03004220`为`gRngValue`）。条目写入`gMain.oamBuffer[120..127]` (`0x030026C8`），两种颜色写入`gPlttBufferFaded` (`0x020375F4`）及`gPlttBufferUnfaded` (`0x020371F4`）的OBJ调色板15，发生在`VBlankIntr`的`LoadOam`和`TransferPlttBuffer`之前（若在其后，顶部几行会落后一帧）。一个128字节1bpp字体（十六个3×5数字，像素位于第1到5行的第2到4列，`asm/resident/overlay.inc`）会在两个哨兵字不同时展开到OBJ图块1008到1023。叠加层会覆盖游戏保存在调色板15及这些图块中的内容。

`ring=ADDRESS`（140字节；`0x0203FF74`结束于EWRAM顶端）将`gRngValue`保存为`VBlankIntr`发现它时的值，每帧一个字，共32帧，并在`watch` (`gEnemyParty[0]`的性格值，即`0x02024028`）变化时冻结。草丛遭遇的性格值可由每个保留种子推导。在模拟器中于草丛行走时测得：每帧调用两次`Random`，从上一帧种子开始，性格抽取是第五次调用（`VBlankIntr`的调用[main.c:412]、本帧自身调用、槽位、等级、性格）。

#### `shiny`, `ivs`, `noencounter`

`shiny` (`asm/resident/shiny.s`）倒计时显示距离下一次异色野生抽取还有多久。`VBlankIntr`每帧调用`Random`一次[main.c:412]；野生宝可梦先抽取`Random() % 25`决定性格，再抽取`Random() | Random() << 16`直到性格匹配[wild_encounter.c:233, pokemon.c:1864]；`method=1`取第一对（脚本化的`CreateMon`）。异色条件为`TID ^ SID ^ high ^ low < 8`，TID和SID来自`gSaveBlock2Ptr` (`0x0300422C`) `+0x0A`。钩子逐帧跟踪`gRngValue`（最多64步，超过则重新开始），每个空闲帧搜索`search`个候选值，并显示目标性格及`target - current - offset`，使用十进制（`offset=4`，草丛情形），或者显示`FF`及搜索距离。按住`slow`（R）时，每帧额外等待`slow_frames`次垂直消隐：`IntrMain`在处理程序中保持VCount启用[crt0.s]，因此`m4aSoundVSync`会运行，钩子调用`m4aSoundMain` (`0x081DF53D`, `gPcmDmaCounter` `0x03002F68`，从`gSoundInfo` `0x03005F80`）取得每次等待的垂直消隐，并在`REG_IF`中清除它。状态共36字节，位于`0x0203FF80`.

`ivs` (`asm/resident/ivs.s`）用两行显示首位宝可梦的个体值（`OVERLAY_TWO_ROWS`，第二行位于`gMain.oamBuffer[112..117]`，y为10）：HP、攻击、防御、速度，随后是特攻、特防和`personality % 25`. `GetMonData(mon, MON_DATA_IVS)` (66, `0x080432E5`）返回六个五位个体值，HP位于最低位[pokemon.c:3250]；`GetBoxMonData`原地解密后再加密[pokemon.c:2992, 3327]，因此只在空闲的大地图帧中调用。

`noencounter` (`asm/resident/noencounter.s`）每帧将1存入`sWildEncountersDisabled` (`0x020386D8`），而`StandardWildEncounter` (`0x08086528`）首先检查它[wild_encounter.c:360]；`DisableWildEncounters` (`0x08085FAC`）是唯一其他写入方。草丛、水面及游走宝可梦遭遇会停止；钓鱼及甜甜香气走独立路径。

#### `noclip`

`noclip` (`asm/resident/noclip.s`，304字节）允许玩家穿墙，条件是按住`hold`（默认`0x100`，R）中的所有按键。每个空闲大地图帧（`gMain.intrCheck`位0清除，`callback2` `CB2_Overworld`）都会重写玩家`currentCoords`周围的四个地图网格块，`VMap.map` (`gBackupMapData`, `0x02031DF8`），将碰撞设为0、高度设为15，保留组合图块ID。`VMap`为`{s32 Xsize, s32 Ysize, u16 *map}`，位于`0x03004260`（法语版）或`0x03004310`（英语版），即`MapGridGetCollisionAt`中的字面量。一个块为`metatile | collision << 10 | elevation << 12`[global.fieldmap.h:7]；`GetCollisionAtCoords`先根据碰撞位阻挡，再检查`IsElevationMismatchAt`，后者允许高度15通过，而`ObjectEventUpdateElevation`在高度15图块上保持玩家自身高度不变[event_object_movement.c:4830, 8346, 8400]。

下一空闲帧恢复每个块，但只在`gMapHeader.mapLayout` (`0x02036DF8`）仍是被修改的布局，且该块仍保留原组合图块ID、高度15、碰撞0时恢复：如果发生传送或游戏重写了组合图块，则保留新块。等于`MAPGRID_UNDEFINED` (`0x3FF`）的块保持不变，否则玩家会走出地图。对象事件仍会阻挡（`DoesObjectCollideWithObjectAt`），台阶仍会触发跳跃，玩家旁边游走的对象事件也可能走进已开放的块。按住R本会打开帮助系统，因此钩子每帧向`0x0203F171`存入1（见`turbo`）。状态共24字节，位于`0x0203FF80`：布局、计数及四个`{u16 index, u16 block}`.

`tests/test_noclip.py`通过各卡带自身客户端安装它，并使用卡带自身的`MapGridGetCollisionAt`和`MapGridGetElevationAt`读取结果。mGBA上使用法语卡带在真新镇实测：向南走，不按R时玩家被围栏挡住，按住R则可穿过六个格子；对象事件仍会阻挡。

#### `follower`

`asm/resident/follower.s`将首位宝可梦作为真实对象事件放在玩家后一格跟随，使用游戏自身移动动作，因此游戏负责绘制行走、奔跑、跳台阶（弧线、影子、落地尘土）、门口渐变及精灵优先级。设计参考GB-Link的`cards/follow.s`（GPL-3.0）。它有984字节，超过单次`install-resident`会话容量，因此从存档安装（[保存在存档中的常驻钩子](#a-resident-hook-kept-in-the-save)).

在每个空闲大地图帧（`gMain.intrCheck`位0清除，`callback2` `CB2_Overworld`），在`VBlankIntr`:

| 步骤 | 钩子的操作 |
| --- | --- |
| 查找对象 | 查找局部ID为`0xF0`的活动对象事件，该局部ID没有任何地图使用；加载地图后不存在该对象 |
| 生成 | `SpawnSpecialObjectEventParameterized(gfx, MOVEMENT_TYPE_NONE, 0xF0, x, y, elevation)`在玩家格子上生成，直到玩家迈出第一步之前都隐藏 |
| 每帧 | 将其当前高度设为14，没有图块使用此高度：玩家可反向穿过它，任何对象都不会与它交谈[event_object_movement.c:4899]；`fixedPriority`在场景锁定时设置，因此加载会保持该高度 |
| 玩家迈步 | 玩家离开的格子成为其目标；相距一格时，使用玩家自身的动作族（奔跑变为`WALK_FAST`），不在同一直线上时则用`MoveObjectEventToMapCoords` |
| 台阶 | 玩家的`JUMP_2`移动两次坐标：第一次让跟随者来到边缘，第二次让它留在那里；玩家下一步时，跟随者自行执行`JUMP_2`，跳过两格；若同一直线上相距两格且无待跳台阶，则用`WALK_FASTER`（0x35）一次一格跟上 |
| 菜单 | `sLockFieldControls` (`0x0300109C`）设置时，使用`sGlobalScriptContextStatus` (`0x03000FA8`），在`CONTEXT_SHUTDOWN`: `RemoveObjectEvent`处处理，因此存档不会保存它；之后重新生成 |
| 骑车、冲浪、潜水 | 隐藏在玩家格子上 |
| 更换首位 | 移除并重新生成 |
| 碰撞 | 玩家在高度0图块上撞到它时，将它放回玩家格子 |

| 首位宝可梦 | 对象 |
| --- | --- |
| 42种有大地图精灵的宝可梦之一（`OBJ_EVENT_GFX_SNORLAX`109到`DEOXYS_N`；代欧奇希斯使用该版本的形态，构建器的`deoxys=`) | 使用其自身图形ID |
| 其他任意种类、蛋，以及按字母区分的未知图腾 | 卡比兽的32×32帧（109，`sAnimTable_Standard`）；其精灵的`images`指向九个`SpriteFrameImage`，位于`0x0203FBB4`（站立0..2使用图标帧0，行走3..8使用帧1，每帧0x200字节，来自`GetMonIconPtr`），使用OBJ调色板15 |

图标调色板在每个空闲帧写入`gPlttBufferUnfaded`的OBJ调色板15（`0x020375D4`），并仅在混合`gPlttBufferFaded` (`0x020379D4`）时写入`y` (`gPaletteFade + 4`，位6..10）为0时如此。进门淡出会将`BeginNormalPaletteFade`推进到`y`16，然后清除`active`，但画面仍为黑色[field_weather.c:740, palette.c]；在mGBA进入门口时实测，`active`保持设置21帧，随后`y`为16且`active`清除，持续四帧，之后`callback2`离开大地图。

在场景中按A，且玩家面前格子为跟随者、场景未锁定时（游戏自身的A处理、脚本或菜单会优先占用该帧）：`gSelectedObjectEvent`设为它，并运行`ScriptContext_SetupScript`，其中写入种类（`SPECIES_EGG`为412，没有叫声，因此省略）：

```
6A                lock
A1 SPEC 0000      playmoncry SPECIES, CRY_MODE_NORMAL
5A                faceplayer
4F F000 PTR       applymovement 0xF0: 66 FE (MOVEMENT_ACTION_EMOTE_SMILE, step_end)
51 0000           waitmovement 0
C5                waitmoncry
7F 00 0000        bufferpartymonnick STR_VAR_1, 0
67 PTR            message: "{STR_VAR_1} saute\nde joie !" (French), "{STR_VAR_1} jumps\nfor joy!" (English)
66 6D 6C 02       waitmessage, waitbuttonpress, release, end
```

状态共17字节，位于`0x0203FFDC` (`state=`): `+0`为其对象事件或`0xFF`, `+1`为待执行一步，`+2`为显示图标，`+3`为移动动作族，`+4`为最近观察到的玩家坐标，`+8`为目标，`+12`为首位宝可梦种类，`+14`为生成时所用种类，`+16`为待跳台阶。图标帧表共72字节，位于`0x0203FBB4` (`images=`），在安装程序保存于以下位置的处理程序下方：`0x0203FBFC`.

| 卡带 | `SpawnSpecialObjectEventParameterized` | `ObjectEventSetHeldMovement` | `ObjectEventClearHeldMovement` | `MoveObjectEventToMapCoords` | `RemoveObjectEvent` | `ScriptContext_SetupScript` | `gSelectedObjectEvent` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BPRF, BPGF | `0x08062130` | `0x080675A4` | `0x08067634` | `0x08063024` | `0x08061DB4` | `0x0806D3D4` | `0x03004294` |
| BPRE, BPGE | `0x08061FD4` | `0x08067448` | `0x080674D8` | `0x08062EC8` | `0x08061C58` | `0x0806D270` | `0x03004344` |

| 卡带 | `gMonIconPaletteIndices` | `gMonIconPalettes` | `GetMonIconPtr` |
| --- | --- | --- | --- |
| BPRF | `0x083CBEE8` | `0x083CB7A8` | `0x0809AA74` |
| BPGF | `0x083CBD24` | `0x083CB5E4` | `0x0809AA48` |
| BPRE | `0x083D197C` | `0x083D123C` | `0x0809A7B8` |
| BPGE | `0x083D17B8` | `0x083D1078` | `0x0809A78C` |

英语版数值来自`pokefirered_switch.elf`；法语版则是在各映像中找到的相同字节。`tests/test_follower.py`按照`install-kept`在各映像上安装的方式运行钩子，并为对象函数提供替身：生成、行走一步、图标帧及调色板、台阶等待及单次跳跃、对话脚本、菜单打开时移除。

`AddSpritesToOamBuffer`使用`gDummyOamData`填充未用OAM条目，但只填到`gOamLimit`[sprite.c:487]，该值由`ResetSpriteData`设为64[sprite.c:297]，在大地图中读得也是64（`0x02021B44`）：钩子写入编号大于64的条目后，它会一直留在画面上，直到某个画面重置精灵。

#### 已验证

| 钩子 | 零售版法语《火红》，ESP32无线模块（每次安装返回`0x0800071D`) | 模拟器 |
| --- | --- | --- |
| `turbo` `extra=4 field=3 battle=3 hold=0x100 budget=228` | 按住R可快进 |  |
| `overlay` | 绘制八位数字，每帧变化 | 在选择“继续游戏”后的回顾期间绘制 |
| `shiny` | 草丛中倒计时；R使其减速 | 跟踪的种子与`gRngValue`匹配；Python模型对异色判断也一致 |
| `ivs` | 首位宝可梦的个体值字及`personality % 25`与一个`save-dump`相匹配，来自`SaveBlock1 + 0x34` | 匹配`gPlayerParty` (`0x02024280`) |
| `noencounter` | 在草丛行走时没有野生遭遇 | 没有遭遇；软重置后恢复 |
| `turbo-lite+noclip+noencounter`, `turbo-lite.field=2 battle=2 hold=0x2`, `noclip.hold=0x100` | 一次会话返回`0x0800071D`；按住B快进，按住R穿墙，没有草丛遭遇，同时按两个键可快速穿墙 |  |
| `follower` | 在后一格跟随，在台阶边缘等待，玩家离开落地点后才跳跃，使用游戏自身影子及尘土；奔跑和跑跳台阶均无闪烁；面对它按A：叫声、笑脸、台词；开始菜单及门口行为正常；一次会话将其写入存档并安装 | mGBA上使用吉利蛋精灵及水箭龟图标，结果相同 |

尚未解决：模拟器中，叠加层在选择“继续游戏”后的回顾期间绘制，但在可交互游玩时不显示，而`field`仍然会加速游戏。

每个钩子在《叶绿》上只需修改一个地址即可运行：`m4aSoundMain`为`0x081DF518`（即`bl`，在其`VBlankIntr`中，位于`0x08000772`）；其他所有常量均可通过《火红》自身引用映射到相同位置。`follower`还会读取位置发生变化的ROM表及函数，已列在其章节中。构建器接受`version=`，主机端接受`--version leafgreen`。已在模拟《叶绿》上验证：加速及`shiny`，音乐保持正常。

### 同时运行多个钩子

每个钩子都将它替换的处理程序作为函数调用（`bl`跳转到一个`bx r3`，位于`p_original`），并通过自身压栈的`lr`返回，因此钩子的`p_original`可指向另一个钩子。`--resident turbo-lite+noclip+noencounter`从`0x0203FC00`开始将钩子首尾相接排列，把每个钩子的`p_original`写为下一个钩子入口（设置Thumb位），并交给安装程序一个二进制块，其入口是首个钩子入口，而其`p_original`属于最后一个钩子。`install-resident`, `install-kept`和MOM加载器保持不变。设置项需注明所属钩子：`--resident-param turbo-lite.hold=2`.

| 规则 | 原因 |
| --- | --- |
| 顺序为turbo、noclip、shiny、ivs、noencounter | turbo的额外回调在其他钩子完成本帧处理后运行 |
| 每个钩子的数据放在`0x0203FBB4..0x0203FBFC`，然后放到代码上方 | 默认位置重叠：`shiny`, `ivs`和`noclip`都在以下位置保存状态：`0x0203FF80` |
| 以下项目最多启用一个：`shiny`, `ivs`以及turbo的`overlay` | 各自都绘制到`gMain.oamBuffer[120..127]`及OBJ调色板15 |
| `follower`单独运行 | 984字节：与任何其他钩子组合都会超出存档可容纳的1004字节 |
| 代码必须能容纳在`0x0203FC00..0x02040000` | 1024字节；超过876字节则整组通过存档安装，超过1004字节则无法存放 |

`turbo-lite` (`asm/resident/turbo-lite.s`）是`turbo.s`在汇编时设置`TURBO_LITE`得到的版本：执行相同轮数、条件检查、按键保持及预算逻辑，但没有叠加层和随机数历史，占356字节而非696字节。所有turbo帧测试均在其上运行（`tests/test_turbo_lite.py`）；链中的一帧会运行每个钩子，并运行`VBlankIntr`一次（`tests/test_resident_chain.py`).

### `install-kept`

`asm/install-kept.s`，192字节，安装保存在`filler_B20`中的钩子，方式类似于`install-resident`安装自身钩子：它读取`gSaveBlock2Ptr`（该块每次加载都会移动），检查魔数、长度是否使校验和仍处于`filler_B20`内，以及和值；然后清除REG_IME，将游戏处理程序保存在`0x0203FBFC`，复制钩子，写入其`p_original`，并将`gIntrTable[4]`指向它。响应为在表中找到的处理程序，若未安装任何内容则为`0xBAD0BAD0`。+0处ARM入口属于缓冲区脚本；MOM的RAM脚本运行+8处THUMB入口，该入口将响应指向映像中的一个字。最后两个字按卡带修补：`&gSaveBlock2Ptr`和`&gIntrTable[4]`.

```
IP_HOST --buffer-script install-kept --version firered
```

### 保存在存档中的常驻钩子

任何常驻钩子都可保存在`filler_B20`中，并在启动后与MOM交谈重新安装，无需连接，也无需主机端。需要两次礼物会话完成设置：

```
IP_HOST --buffer-script save-write --resident follower --version firered
IP_HOST --gift resident-save --version firered
```

第一次将以下二进制块写入`SaveBlock2 + 0xB20`，并在同一会话中从该块安装钩子：

```
+0x00  magic     0x32524B50, "PKR2"
+0x04  length    the hook's bytes, whole words
+0x08  dest      0x0203FC00
+0x0C  entry     u16 offset of the hook's entry
+0x0E  original  u16 offset of its p_original word
+0x10  the hook
+len   checksum  the sum of every word before it
```

若二进制块超过单个`save-write`（936字节），则用两个载荷写入。会话先执行所有写入，再运行[`install-kept`](#install-kept)，每步均为独立载荷：客户端按照命令列表依次接收并运行缓冲区脚本[mystery_gift_client.c:145, 236]，仅最后一个响应会传回。

```
client  RECV RUN  RECV RUN  RECV RUN LOAD_TOSS_RESPONSE SEND_LOADED  RECV COPY_RECV
host    script    write 1   write 2  install-kept   <- the handler found
```

会话以`CLI_MSG_BUFFER_SUCCESS`结束，这会保存，因此`filler_B20`被写入闪存。

第二次将RAM脚本绑定到MOM，该脚本暂存36字节的[ram-jump跳板](#a-payload-larger-than-a-script-body)，然后跳入`install-kept`的THUMB入口；它们逐字节携带在脚本主体中（占995字节中的428字节）。与MOM交谈会安装钩子；第二次访问会串接到保留的处理程序，软重置会移除钩子，直到再次与MOM交谈。

| 钩子 | 二进制块 | `save-write`载荷 |
| --- | --- | --- |
| `noencounter` | 48 | 1 |
| `ivs` | 520 | 1 |
| `turbo-lite` | 376 | 1 |
| `turbo` | 716 | 1 |
| `shiny` | 888 | 1 |
| `follower` | 1004 | 2 |

`tests/test_resident_save.py`运行主机端与模拟客户端之间的完整会话，并在启动后的主机上运行MOM主体脚本：字节翻转、缺失第二次写入、长度超出`filler_B20`时都不会安装任何内容。零售版《火红》可从其`PKR2`二进制块安装跟随者。

新神秘卡片会取消绑定：`SaveWonderCard`调用`ClearSavedWonderCardAndRelated`，后者调用`ClearRamScript`[mystery_gift.c:172, 160]。`filler_B20`仍保持写入后的内容。

### `call-chain`

在一帧中依次执行最多十六步，每步返回一个响应字。

```
HOST --buffer-script call-chain \
    --chain-step call:FlagGet,0x828 \
    --chain-step call:FlagSet,0x828 \
    --chain-step call:FlagGet,0x828 --version firered
```

每步24字节（操作、目标、四个参数），写为`OP:TARGET[,ARG]...`，操作包括`call`, `read32/16/8`, `write32/16/8`。调用目标可以是一个`rom_map.CALLABLE`名称（绝不是反编译项目中的地址）。

一步的目标或首个参数可取自前一步结果，`prev`:

```
--chain-step call:GetVarPointer,0x4024      prev = the address the GAME computed
--chain-step read16+keep:prev               the value before, prev untouched
--chain-step write16:prev,7                 the store, read back by the payload itself
--chain-step read16:prev                    the value after
```

`ScrCmd_setvar`通过`GetVarPointer`的返回值写入[scrcmd.c:472]；没有任何ScrCmd工作函数属于`VarSet` ([ROM映射](frlg_rom_map.md)）。写入不会成为`prev`；读取则会，除非带有`+keep`。每次写入都会回读到响应中。

```
0x000  b .Lcode
0x004  count       how many steps are meant, 0..16
0x010  steps[16]   {op, target, a0, a1, a2, a3}, 24 bytes each
0x190  result      calls, count, steps executed, the op word that stopped it
0x1A0  values[16]  one word per step, in order
```

未知操作码会停止运行，并在响应中标明；ARM代码也会限制步骤数量。构建器拒绝空链、超过十六步、调用ARM指针或卡带范围之外、使用来自`prev`的调用目标（错误目标会卡住菜单）、未对齐或不可达的读取、超过四个参数，以及任何没有`--write-unsafe`的写入（随后主机会提交存档）。

```
call GetVarPointer(0x4024)   -> 0x020265B4
read16 [prev] keep           -> 0
write16 [prev] = 3           -> 3        the store, read back by the payload
read16 [prev]                -> 3
call VarGet(0x4024)          -> 3        the game's own reader, same frame
```

即使`gSaveBlock1Ptr`改变基址，该变量仍读为3。金钱为`*moneyPtr ^ gSaveBlock2Ptr->encryptionKey`[money.c:14]：

```
read32 [0x03004228]              -> 0x02025554     gSaveBlock1Ptr
read32 [prev + 0x290] keep       -> 0x5A5A198C     the ciphertext, before
call GetMoney(prev + 0x290) keep -> 0x00000BB8     3000, the plaintext
call AddMoney(prev + 0x290, 1234) keep
call GetMoney(prev + 0x290) keep -> 0x0000108A     4234, exactly +1234
read32 [prev + 0x290]            -> 0x5A5A02BE     the ciphertext, after
```

（示例数值。）两组异或对均得到密钥，此处为0x5A5A1234，即SaveBlock2 + 0xF20处的字（`rom_map.SAV1_MONEY`, `SAV2_ENCRYPTION_KEY`）。特殊函数从特殊变量读取操作数：将`gSpecialVar_Result`设为`GET_CARD_BATTLES_WON`后，特殊函数390返回卡片的`battlesWon`，即`SaveBlock1 + 0x3434`在同一帧所保存的值。

切勿从缓冲区脚本调用传送或消息工作函数：神秘礼物菜单中没有大地图。它们应放在[场景桩程序](frlg_rng.md#the-payload-in-the-script-body).

## 写入游戏会加载的扇区

以下内容均在模拟器上测得。

### 校验和覆盖该ID的数据块

`CalculateChecksum(data, size)`将`size`字节视为小端序u32字求和，并将`(sum >> 16) + sum`折叠为u16[decomp:src/save.c]。`size`是该ID自身的数据块，来自`sSaveSlotLayout`，共14个{u16 offset, u16 size}条目，在法语卡带上位于`0x083F58C4`：

| id | 大小 | id | 大小 |
| --- | --- | --- | --- |
| 0 | 3876 | 4 | 3816 |
| 1-3 | 3968 | 5-12 | 3968 |
| 13 | 2000 |  |  |

`HandleWriteSector`在复制数据块之前清零整个扇区缓冲区[save.c:181-183]，因此游戏写入的扇区在数据块之后全为零，对全部3968字节求和会得到相同校验和；若自行组装的扇区在数据块之后存在数据，则会被拒绝。只填充数据块。当ID由主机决定时，最多填充2000字节，即最小数据块大小：这样同一个校验和对任何ID都有效。

### ID所在位置，以及哪个扇区承载槽计数器

一个槽有14个扇区；游戏交替使用两个槽，并轮换ID位置[decomp:src/save.c:174]：

```
physical = ((gLastWrittenSector + id) % 14) + 14 * (gSaveCounter % 2)
```

`gLastWrittenSector`每次完整保存加一，到14时回绕[:147]。正常游玩时它与计数器同步，但某次写入被标为损坏时两者会分离：游戏从`gLastKnownGoodSector`恢复它[save.c:159]，而`Save_ResetSaveCounters`[:104]会独立重置它。`gLastKnownGoodSector`和`gLastSaveCounter`在实时值对前进之前读取它们，因此精确描述上一代。必须通过解析扇区尾部查找扇区，绝不要依赖固定文件偏移。

`GetSaveValidStatus`只在扇区签名为`0x08012025`且覆盖`locations[id].size`的校验和匹配时计入该扇区，ID取自扇区自身尾部：

-
-

因此，若一个完整扇区组的最后扇区计数器更高，它就会胜过所有扇区计数器都较低的另一组（十三个129加一个131，胜过十四个130）。

| 地址 | 符号 | 宽度 |
| --- | --- | --- |
| `0x030045A0` | `gLastWrittenSector` | u16 |
| `0x030045A4` | `gLastSaveCounter` | u32 |
| `0x030045A8` | `gLastKnownGoodSector` | u16 |
| `0x030045AC` | `gDamagedSaveSectors` | u32 |
| `0x030045B0` | `gSaveCounter` | u32 |

IWRAM，法语构建。加载后，`gLastWrittenSector`描述被采用的槽。

### 会话自身保存不会写入的扇区组

完整保存先赋值上一对值，再递增`gLastWrittenSector`和`gSaveCounter`，然后写入递增后计数器选定的扇区组[save.c:144-153]。礼物会话若以成功消息结束就会保存[mystery_gift_menu.c:1379]；其他结果则直接返回菜单，不保存。若会话将成功结束，应写入当前由`gSaveCounter % 2`选定的扇区组：会话保存会写另一组。若要被加载器采用，应将一个扇区放在组内位置13，计数器为`gSaveCounter + 2`，比会话的`gSaveCounter + 1`高一。位置13的ID为`(13 - gLastWrittenSector) % 14`，在主机上推导得到。

### 根据RAM快照组装扇区

保存例程在保存时进行序列化，因此SaveBlock2的实时内容与实际会写出的内容不同。以下两种情形中，所有校验和均通过，且`gDamagedSaveSectors`都保持为0：

-
-

正常保存一次写入全部十四个扇区，因此密钥与密文同步变化；部分写入必须保持这种一致性。

### 读取闪存：128 KiB芯片上的64 KiB窗口

`swi 0x48`线性寻址芯片。加入端加载看到的是位于`0x0E000000`的64 KiB窗口，1 Mbit芯片通过两个存储体访问：

```
sector N is bank N / 16 at 0x0E000000 + (N % 16) * 0x1000
```

窗口以上的地址会形成别名：`0x0E01E000`（扇区30）读取的是`0x0E00E000`，即所选存储体的扇区14，通常全零。应根据扇区计算存储体和窗口。选择存储体使用游戏自身的四次存储[decomp:src/agb_flash.c SwitchFlashBank，`0x081E0C74`，七条指令，无循环，无`REG_WAITCNT`]，将其内联后，载荷无需调用ROM函数：

```
strb 0xAA -> 0x0E005555 ; strb 0x55 -> 0x0E002AAA ; strb 0xB0 -> 0x0E005555 ; strb bank -> 0x0E000000
```

读取宽度为字节；闪存总线为8位。

`ReadFlash`唯一的持久影响是`REG_WAITCNT`的SRAM字段设为3（`WAITCNT_SRAM_8`[decomp:src/agb_flash.c:149]），启动后本就已设置：`AgbMain`清除它[main.c:143]，启动加载存档时调用`ReadFlash`[intro.c:1006]，每个闪存例程都会写入3（`gFlash->wait[0]`[agb_flash_mx.c:28, agb_flash_le.c:28]）。

绝不要将传出消息指向闪存。头部和消息体以不同宽度读取窗口：

| 步骤 | 代码 | 加载方式 | 读取内容 |
| --- | --- | --- | --- |
| 头部CRC | `CalcCRC16WithTable`[mystery_gift_link.c:166] | `ldrb` | 闪存：`0xDEC2`是物理位置的CRC，`0x1BC00..0x1BFFF`, `0x5907`，属于`0x1E000..0x1E0FB`（已选存储体1） |
| 消息体 | `Rfu_InitBlockSend`将每个不超过252字节的小块复制到`gBlockSendBuffer`[link_rfu_2.c:1357]，使用`memcpy` `0x081E44F4` | `ldm`，一次一个字，条件是源及目标均字对齐且剩余至少16字节 | 其他字节：重复的字节对`01 cb`, `10 3a`及`04 3a`，对于`0x0E01BC00`和`0x0E01E000` |

消息体CRC失败，主机端丢弃它，礼物菜单在RFU连接仍建立时卡住。消息体字节来自何处尚不清楚。`build_memory_dump`及其两个同类实现拒绝任何接触以下区域的范围：`0x0E000000..0x0FFFFFFF`. `flash-read`使用`ldrb`将扇区复制到EWRAM后发送副本，可准确返回扇区内容。

### 修改真实存档的单个字段

`flash-patch`读取真实保存流程写出的扇区，修改一个字段并写回，因此密钥和地图视图保持一致。一次编辑涉及两个扇区：

```
A   the target id's sector: patch the field, recompute the checksum over the id's own chunk,
    set the counter to gSaveCounter + 2
B   the sector at band position 13: set its counter to gSaveCounter + 2 and nothing else, not
    even the checksum, because +0xFFC is outside the summed data area
```

加载器会采用该扇区组（十二个扇区为旧计数器，两个为新计数器），因为十四个ID均有效，且最后有效扇区带有更高计数器。一次`flash-patch`修改玩家名称时，只改变扇区A的字段与校验和，以及扇区B的计数器；加载时采用该组，校验和均无误，金钱和大地图不变，密钥副本及地图视图均保留游戏写出的内容。

### 端到端完整链路

模拟主机实测：缓冲区脚本根据实时全局变量组装一个扇区，`swi 0x48`写入它，游戏下次保存提交映像，下次加载采用该组，且`gDamagedSaveSectors`状态正常。发送的模式（不同于加载器预先测试的模式，后者在任何位置均未出现）可从EWRAM回读，在两处各出现连续500个字。

# 读取存档

一次神秘礼物会话可读取实时存档：秘密ID，以及队伍中每只宝可梦的PID、个体值和性格。不会写入任何内容，也不会传递卡片。主机端日志将一次`save-dump`解码为：从偏移0读取SaveBlock2（姓名、性别、TID、SID、游玩时间），或读取覆盖0x38的SaveBlock1（每只队伍宝可梦的性格、个体值及基础点数），通过`pokeldn.frlg.save.readout`完成；一个`trainer-id-probe`响应则解码为TID和SID。

## 训练家ID与秘密ID

SaveBlock2偏移0处保存玩家姓名、性别、32位训练家ID及游玩时间[global.h:327]。低半部是训练家卡上的TID；高半部是秘密ID，不会在任何地方显示，也不会通过任何连接消息发送。

```
POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/frlg_mg_host.py --live --keys PROD_KEYS \
    --buffer-script save-dump --dump-block sav2 --dump-size 64 --dump-file dump.bin

./.venv/bin/python tools/frlg/dump_read.py dump.bin --block sav2

dump.bin: 64 bytes from sav2 + 0x0
  playerName    'PLAYER'
  gender        boy
  trainerId     0x12345678  TID 22136  SID 4660
  playTime      12h 34m 56s
```

若TID与训练家卡不符，说明读取有误。

## 队伍

SaveBlock1的0x34处为`playerPartyCount`，随后是`playerParty[6]`，位于0x38，每个100字节[global.h:772]：六只共需604字节。

```
POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/frlg_mg_host.py --live --keys PROD_KEYS \
    --buffer-script save-dump --dump-block sav1 --dump-offset 0x34 \
    --dump-size 608 --dump-file party.bin

./.venv/bin/python tools/frlg/dump_read.py party.bin --block sav1 --offset 0x34

party.bin: 608 bytes from sav1 + 0x34
  playerPartyCount 5
  slot 1: PIKACHU   Lv25 nick='PIKACHU' OT='PLAYER' PID=0x00000019 Hardy   IVs=[10,20,30,15,5,25] checksum ok
  slot 2: ...
```

（示例数值。）

个体值顺序为HP、ATK、DEF、SPE、SPA、SPD。异色列将每只宝可梦的PID与它自身的OTID比较。`checksum ok`每个槽都显示该结果，意味着是真实队伍。队伍宝可梦以一个`.pk3`/`.ek3`存储它们的方式保存（`pokeldn.frlg.save.mon`）：0x20处的48字节与`PID ^ OTID`异或，四个子结构按以下顺序排列：`PID % 24`.

SaveBlock1保存的是上次保存时的队伍（`SavePlayerParty`[load_save.c:160]，参见`--create-mon-append`）。若要转储实时队伍，请读取`gPlayerParty`，两张实测卡带上均为0x02024280：

```
--buffer-script memory-dump --dump-address 0x02024280 --dump-size 600
```

绝不要在多次运行之间沿用绝对存档块地址；`save-dump`每次重新取得指针。IWRAM及`gRngValue`见[随机数生成器](frlg_rng.md).
