---
title: 神秘礼物文件
---

# 神秘礼物文件

一个 `.pokegift` 文件可保存《火红／叶绿》或《剑／盾》的一次完整神秘礼物分发，或一份 FRLG ARM 主机载荷，并包含目标游戏和原生记录。

## 桌面应用

在“游戏”中，每款游戏的“神秘礼物”都是一个工具，提供三种选择礼物的方式，《剑／盾》则有四种。两款游戏共用一个构建器；各游戏模块提供自身预设和表单（`pokeldn/frlg/gift/builder.py`, `pokeldn/swsh/gift_builder.py`，在 `pokeldn/app/gift_builder.py`).

| 模式 | 发送内容 |
| --- | --- |
| 使用预设 | 内置礼物；FRLG 神奇卡片、神奇新闻和主机代码以标志形式传给启动器 |
| 官方活动 | 真正的《剑／盾》活动卡片（[官方活动卡片](swsh_gift.md#official-event-cards)），按与自建礼物相同的方式编译 |
| 自行构建 | 表单内容，在“开始”时编译为 `session/gifts/.pokegift`，并以 `--gift-file` |
| 打开文件 | 共享的 `.pokegift`，或 `.wc8`，后者适用于《剑／盾》 |

FRLG 的“游戏增强”是常驻钩子（[`install-resident`](frlg_rom.md#install-resident)）。可以同时勾选多个，它们会作为一条链运行（[同时使用多个钩子](frlg_rom.md#several-hooks-at-once)）。每项均带设置，并转换为启动器的 `--resident-param` 标志；面板还会显示已勾选集合占用主机可用 1024 字节中的多少字节。

| 增强功能 | 设置 | 参数 |
| --- | --- | --- |
| 加快游戏（`turbo-lite`) | 速度 x1 到 x4；地图、对战或两者；始终开启，或按住 R、B、Select 时开启；加快文本 | `field` 和 `battle` = 速度 - 1，`budget=228` 从 x3 起，`hold`, `extra=4` |
| 穿墙 | R、B 或 Select | `hold` |
| 异色倒计时 | 减速按钮；减慢至 1/2、1/4 或 1/8 速度 | `slow`, `slow_frames` 为 1、3 或 7 |
| 不遇野生宝可梦、在屏幕显示首位宝可梦个体值、宝可梦跟随 | 无 |  |

不提供 L：只有 R 的帮助系统切换有可被钩子屏蔽的标志。“保存增强功能供以后使用”会发送 `save-write --resident`，替代 `install-resident`：所选集合写入 `filler_B20`，并在同一会话中安装。超过一次 `install-resident` 会话容量（876 字节）的集合以及跟随功能，始终经由存档处理。“妈妈恢复你的增强功能”会绑定妈妈的加载器，每次启动后与妈妈交谈即可安装存档保存的集合。再次发送增强功能会替换当前运行的集合。应用会在保存选项旁和“发送之前”中显示恢复步骤，必须保存的集合也会显示。预设名称和说明自动换行，确保操作指引保持可见。`tests/test_gift_builder.py` 会针对全部十二种卡带，将所有增强组合及每项的全部设置通过启动器进行测试。

“读取存档”可读取训练家 ID（TID）和秘密 ID（SID）、训练家详情、游戏时间，以及上次保存队伍的性格、个体值和基础点数。结果显示在会话日志中；两个转储预设还会把读取数据写入 Received。该组说明了通常隐藏的 SID、由六项 0 到 31 的独立数值组成的个体值，以及作为训练点数的基础点数。这些读取操作不会改变存档和神奇卡片（[读取存档](frlg_rom.md#reading-the-save)).

原生 `.wc3` 和 `.wc8` 扩展名会在检测 JSON 之前选择游戏二进制读取器。WC8 的二进制封装可能以 `{` 开头；它仍然是原生记录。`.pokegift` 文件使用 JSON 读取器，未知扩展名的文件若以 JSON 左花括号开头，也仍可包含共享礼物。

“自定义”将预设复制到表单。FRLG 卡片预设只有在表单能够表达每个步骤时才提供该功能：无条件的宝可梦、道具、蛋、野生对战和消息阶段，不含事件脚本，也不含来访训练家。每个《剑／盾》预设都是一个表单状态。

FRLG 表单可构建神奇卡片、神奇新闻或主机代码。

| 部分 | 内容 |
| --- | --- |
| 卡片 | 标题、副标题、四行文本、图标物种、1000 到 1019 的卡片 ID、可重复接收、可分享 |
| 发放者 | 任意宝可梦中心的配送员、玩家家中的妈妈，或真新镇南部的男子 |
| 步骤 | 宝可梦（物种、等级、携带道具、四个招式）、道具及数量、蛋、野生对战、消息 |
| 新闻 | 标题、最多十行文本、新闻 ID |
| 主机代码 | ARM 源码或预先构建的 `.bin`、构建所针对的卡带、预期应答、返回字节数 |

每个步骤都是独立发放阶段，因此队伍或背包满时会停在该步骤，玩家只需重试剩余部分。配送员以外的人物通过一个 `initramscript` 绑定持有这些步骤；绑定期间不显示卡片。绑定脚本不带领取标志：在另一份礼物替换绑定之前，该人物每次都会执行发放步骤。物种采用卡带内部编号（`pokeldn/frlg/save/species_names.py`）。卡片和新闻针对全部四种卡带编译；主机代码可针对全部四种或选定的一种编译。

主机代码使用 `arm-none-eabi-as` 汇编，只要它位于 PATH、Homebrew 文件夹或 Arm 的 Windows 安装文件夹中；没有汇编器时，表单接受预先构建的 `.bin`，并显示适用于当前系统的汇编器安装命令：

| 系统 | 命令 |
| --- | --- |
| macOS | `brew install arm-none-eabi-binutils` |
| Fedora | `sudo dnf install arm-none-eabi-binutils-cs` |
| Debian、Ubuntu 及其衍生发行版 | `sudo apt install binutils-arm-none-eabi` |
| Windows | `winget install Arm.ArmGnuToolchain` |

其他 Linux 发行版会提供 Arm 下载页面。Fedora 44 和 Ubuntu 24.04 的软件包可将默认模板汇编为 `01 00 a0 e3 1e ff 2f e1`。“离线检查”会在模拟主机上运行一次代码（`pokeldn/frlg/rom/custom_code.py`），并显示应答和字节内容。“开始”和保存文件之前也会执行同样检查：出错或始终不返回 1 的代码会被拒绝。

《剑／盾》表单可构建宝可梦（指定或随机性格，可选超极巨化能力）、蛋、最多六种背包道具、官方服装、对战点数或金钱，并附带卡片 ID。宝可梦、蛋、道具、服装和对战点数类型写入的字节格式，来自零售版《剑》曾列出并领取的记录（[《剑／盾》神秘礼物](swsh_gift.md#a-card-delivered-to-a-retail-console)）；皮卡丘预设与启动器自身默认记录逐字节相同。服装来自官方服装卡片中的成对条目（[服装](swsh_gift.md#clothing)），每种玩家性别最多六件。若物种没有超极巨化形态，PKHeX 会拒绝为其设置超极巨化标志。

“发送之前”列出主机将收到什么、何时运行，以及礼物支持的卡带。“保存礼物文件”把选中礼物写为 `.pokegift`，无需开发板或 Switch 密钥。FRLG 预设使用启动器自身的构建器，因此文件包含其构建出的全部卡带变体。主机游戏代码在礼物握手期间选择变体；文件中不存在的卡带会在发送礼物数据前被拒绝。预设卡片 ID 位于“高级”选项卡（`--flag-id`，1000 到 1019）。

应用不会在导入时修改礼物文件。文件保留在所选路径。

已在零售版主机上通过打开文件完成发放：法语《火红》上的时拉比卡片和主机代码文件，《剑》上的皮卡丘卡片。表单构建的主机代码返回了存档训练家 ID。

## 命令行

两个礼物启动器均接受 `--gift-file FILE`。《剑／盾》保留 `--record` 作为别名。`--export-gift FILE` 保存选中礼物，并在使用无线电后端之前退出。

```
./.venv/bin/python bin/frlg_mg_host.py --gift celebi --export-gift celebi.pokegift
./.venv/bin/python bin/frlg_mg_host.py --news berry --export-gift news.pokegift
./.venv/bin/python bin/swsh_gift_host.py --species 25 --level 25 --export-gift pikachu.pokegift
./.venv/bin/python -m pokeldn.gifts inspect celebi.pokegift
```

FRLG 礼物文件一并定义卡片标志 ID、脚本、问卷和拒绝消息。与文件同时使用 `--flag-id`, `--questionnaire` 和 `--hunt-*` 等载荷覆盖选项会被拒绝。无线电后端、训练家身份和卡带选择选项仍属于会话设置。

### 主机代码

导出内置载荷，包含配置的字节内容及响应设置：

```
./.venv/bin/python bin/frlg_mg_host.py --buffer-script save-dump --dump-size 64 \
  --export-gift save-dump.pokegift
```

作者可以将自身原始 ARM 代码打包，并明确指定目标卡带：

```
arm-none-eabi-as -march=armv4t -mcpu=arm7tdmi -o payload.o payload.s
arm-none-eabi-objcopy -O binary -j .text payload.o payload.bin
./.venv/bin/python -m pokeldn.gifts import --game frlg --code payload.bin \
  --build BPRF --name "Custom payload" --expect 66 -o custom.pokegift
```

一个最小的 `payload.s` 向响应参数写入 66，并在一次调用中完成：

```asm
.syntax unified
.arm
.text
.global _start
_start:
    mov r3, #66
    str r3, [r0]
    mov r0, #1
    bx lr
```

代码必须为与位置无关、按字对齐的 ARMv4T，最多 1024 字节。主机传入 `r0 = ¶m`, `r1 = gSaveBlock2Ptr` 和 `r2 = gSaveBlock1Ptr`；它每帧调用一次载荷，直到返回 1。执行约定见 [主机代码](frlg_rom.md)。没有 `--expect` 时，接受任意返回参数。将响应重定向至字节缓冲区的载荷在打包时使用 `--dump-size N`。

分享该 `.pokegift` 文件。接收者在“FRLG → 神秘礼物”中打开，或使用 `--gift-file custom.pokegift`. `--dump-file PATH` 选择主机端写入返回转储的位置。卡带变体约束在发送代码前执行。打包只验证结构和大小；作者在实际运行前必须使用 `buffer_script.emulate_repeating` 离线执行新载荷。文件哈希并不能证明原生代码会返回，或不会破坏存档。

### 原生格式

转换器可导入《剑／盾》WC8 记录、FRLG `.wc3` 文件，以及 `pokemon-gen3-mysterygift-tool` 使用的成对 FRLG 文件。一个 `.wc3` 或 `.wc8` 也可直接打开，入口为应用的“打开文件”及 `--gift-file`.

若 FRLG 脚本的可达代码不包含绝对地址，就能服务所有采用相同卡片布局的卡带：其跳转和文本采用 `vgoto`/`vmessage` 操作数，相对于自身的 `setvaddress` [scrcmd.c:171]，道具则通过 `callstd` 获取。含有 `goto`, `call`, `message`, `callnative` 或其他绝对指针的脚本只属于一种卡带，需要 `--build`；此类 `.wc3` 在直接打开时会被拒绝。

```
./.venv/bin/python -m pokeldn.gifts import --game swsh --record event.wc8 -o event.pokegift
./.venv/bin/python -m pokeldn.gifts import --game frlg --wc3 "FL - Item AuroraTicket (FRE).wc3" -o aurora.pokegift
./.venv/bin/python -m pokeldn.gifts import --game frlg --card WonderCard.bin \
  --script Script.bin --name "Event gift" -o event.pokegift
./.venv/bin/python -m pokeldn.gifts export celebi.pokegift --build BPRF --out-dir native-gift
./.venv/bin/python -m pokeldn.gifts export celebi.pokegift --wc3 --build BPRJ --out-dir native-gift
./.venv/bin/python bin/frlg_mg_host.py --gift celebi --console-build BPRJ --export-gift celebi.wc3
```

保存到以 `.wc3` 或 `.wc8` 结尾的路径时，将写入对应原生文件，而不是 `.pokegift`：适用于 `--export-gift`、“保存礼物文件”及 `pokeldn.gifts.save`。一个 `.wc3` 包含一种卡带的卡片和脚本；若未指定 `--build`，礼物所有变体的字节内容必须相同。变体不同时，GUI 会询问导出哪种卡带。`.pokegift` 保留所有语言变体。`.wc3` 元数据块除图标外全部写零；图标重复使用卡片中的值。游戏接受的每个国际版图鉴库文件，经过导入再导出后，卡片、脚本和图标字节均保持相同。

国际版 `.wc3` 为 1420 字节（`0x58C`):

| 偏移量 | 大小 | 内容 |
| --- | --- | --- |
| `0x000` | 336 | 卡片 CRC16、2 个填充字节、332 字节的 `struct WonderCard` |
| `0x150` | 80 | 存档侧卡片元数据；不读取 |
| `0x1A0` | 1004 | CRC16、2 个填充字节、`struct RamScriptData`（魔数 51、地图组、地图编号、对象 ID、995 字节脚本）、1 个填充字节 |

Project Pokémon 的 EventsGallery 中全部 54 个国际版文件，其脚本 CRC 都覆盖 1000 字节，包含填充字节；游戏自身则覆盖 999 字节 [script.c:488]。导入两种均接受。`--icon N` 导入选项，或应用“打开文件”下的“卡片图标”，可将卡片的 `iconSpecies`（卡片偏移量 2）设为 0 到 411 的内部物种 ID；0 表示不绘制图标 [mystery_gift_show_card.c:466]。

日版 `.wc3` 文件为 1252 字节（`0x4E4`）：卡片结构为 164 字节，其 CRC 包装结构为 168 字节，元数据起于 `0x0A8`，1004 字节 RAM 脚本结构起于 `0x0F8`。直接导入时，日版文件面向 `BPRJ` 和 `BPGJ`；国际版文件面向十种拉丁文字卡带。显式指定的 `--build` 必须与卡片布局一致。图鉴库中标志 ID 为 4 到 8 的调试卡片会被拒绝：配送员只为标志 ID 1000 到 1019 发放礼物 [mystery_gift.c:241]。已首次进入名人堂的存档中，极光船票和神秘船票不会产生任何效果（[极光船票和神秘船票](frlg_gift.md#the-aurora-and-mystic-tickets)).

FRLG 文件对包含 336 字节国际版或 168 字节日版卡片，以及 1004 字节 RAM 脚本结构。导入会验证两个 CRC，以及脚本未绑定的神秘礼物头部。原生文件对无法携带印章、来访训练家、神秘事件脚本、问卷门槛或神奇新闻。包含这些附加内容的分发无法导出为该文件对。`.pokegift` 可将它们一起保留。

## 版本 2

文件采用 UTF-8 JSON，有五个必填字段：

| 字段 | 值 |
| --- | --- |
| `format` | `pokeldn.gift` |
| `version` | 整数 `2` |
| `game` | `frlg` 或 `swsh` |
| `name` | 非空显示名称，最多 180 个字符 |
| `variants` | 将目标代码映射至原生数据和选项的对象 |

每个变体都包含 `data` 和 `options` 对象。位于 `data` 的组件包含 `hex`，即以十六进制编码的原生字节，以及 `sha256`，即其小写 SHA-256 摘要。JSON 字段顺序没有含义。导出会对字段排序，确保文件输出确定。

| 游戏 | 变体键 | 数据组件 | 选项 |
| --- | --- | --- | --- |
| FRLG 礼物 | 支持的卡带代码 | `card`, `ram_script`, `stamp`, `activation_script`, `install_activation_script`, `trainer`, `news`, `mevent` | `questionnaire`, `denied_message` |
| FRLG 主机代码 | 支持的卡带代码 | `buffer_code`, `buffer_lead_1`.. | 下文的响应设置 |
| 剑／盾 | `swsh` | `wc8` | 无 |

FRLG 卡片变体使用相同标志 ID 和礼物类型。神奇新闻和主机代码均单独传输。抓包、密钥、文件系统路径和会话计时不属于此格式。

FRLG 主机代码变体恰有一个 `buffer_code` 组件，同一会话中可先运行最多八个载荷，使用 `buffer_lead_1`, `buffer_lead_2` 及后续连续编号，不得有空缺（保存在存档中的常驻钩子会将 `filler_B20` 与它们一同写入，随后安装）。其可选响应设置为 `buffer_expect`（32 位无符号整数或 `trainer-id`), `buffer_dump_size`, `buffer_dump_blocks`, `buffer_dump_address`, `buffer_dump_addresses` 和 `buffer_decode`。转储每块大小为 1 到 1024 字节，最多 32 块；分散转储为每块指定一个地址。解码器名称来自现有响应解码器。转储输出路径和本地 ROM 比较路径保留在主机端，不包含在共享文件中。

读取器也接受包含卡片、新闻或 WC8 的版本 1 文件。导出使用版本 2，它新增主机代码和整数响应设置。版本 1 读取器会拒绝版本 2 文件。

读取器拒绝未知版本、字段和目标代码、重复 JSON 字段、无效哈希、大于 256 KiB 的文件、无效原生大小及无效组件组合。FRLG 验证还会检查卡片字段、训练家校验和及神秘事件终止条件。《剑／盾》发放在打开无线电后端前，仍须通过共用的 PKHeX 礼物验证。

哈希可检测损坏字节，但不能验证分发者身份，也不能证明导入的 FRLG 脚本可安全执行。原生脚本导入保留原指令，并要求明确指定目标卡带。

## 实现

`pokeldn.gifts` 负责封装格式、验证分派、读取器、写入器和转换器。游戏专用编解码器位于 `pokeldn.frlg.gift.file` 和 `pokeldn.swsh.gift_file`。共用应用适配器调用启动器自身的构建器；GUI 为两款游戏使用同一个选择器和导出控件。

FRLG 文件适配器构建现有的 `MysteryGiftDistribution`，包括其卡带选择和拒绝路径。《剑／盾》适配器向现有 WC8 广播通告构建器提供数据。无线协议和载荷布局均不变。
