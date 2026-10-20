---
title: 桌面版构建
---

# 桌面版构建

发布的应用包含 PKHeX，以及适用于 ESP32、ESP32-S3、ESP32-C3 和 ESP32-C6 的合并无线模块固件。用户需自行提供 `prod.keys`.

打开应用，在“设置”中选择 `prod.keys`。在“开发板”页面，选择用作无线模块的 USB 开发板并安装“无线”固件。选择游戏和工具，准备宝可梦或选择文件，然后按照主机操作说明进行并按“开始”。收到的宝可梦会保存到“设置”中选定的文件夹；“输出”旁的文件夹按钮可以将其打开。安装时会检测芯片并选择内置镜像；从文件安装镜像时，会在写入前检查其是否与该芯片匹配。S3、C3 或 C6 请通过原生 USB Serial/JTAG 连接。不支持 S2 芯片。

神秘礼物工具共用一个构建器：可以使用预设、自行构建，或打开 `.pokegift` 文件；《剑／盾》还支持打开 `.wc8` 卡片。“保存礼物文件”无需连接开发板，即可将选定礼物导出为 `.pokegift`，或根据扩展名导出为 `.wc3`（《火红／叶绿》）或 `.wc8`（《剑／盾》）。[神秘礼物文件](gifts.md#desktop-app) 介绍了各种形式、卡带变体以及原生格式转换。

## 首次启动

棋盘格背景覆盖整个窗口，包括透明页头；导航栏像其他面板一样，以玻璃面板形式悬浮其上。页头不显示应用标题，支持拖动以及双击最大化或还原。macOS 保留原生窗口按钮；Windows 和 Linux 使用应用页头中的按钮。集成页头已在 macOS 上完成视觉检查；Windows 和 Linux 的窗口管理器行为尚未验证。

-
-
-

## Android 设置要求

该 [Android 应用](https://decryptu.github.io/examples/android/README.md) 将此界面带到手机上。其“开发板”页面遵循下表；插拔开发板、Android USB 提示关闭、以及玩家从“设置”返回时，都会重新读取 USB 状态。原生 USB 开发板（`303a:1001`）插入时会打开应用。在已测试的 OnePlus CPH2621 上，启用手机的 OTG 连接设置后，已连接的 ESP32C6 无需重新插拔线缆即可获得供电并完成枚举。

| 检测到的状态 | 所需引导 |
| --- | --- |
| 没有兼容的 USB 设备 | 检查支持数据传输的线缆及连接；显示该手机相关的 USB 主机或 OTG 设置说明，包括 OnePlus 的 OTG 连接开关。仅凭设备未出现，无法确定是哪项检查失败。 |
| 设备存在，但缺少 USB 权限或权限被拒绝 | 解释 Android USB 访问提示，并提供明确的重试操作。 |
| 已授权，但开发板握手失败 | 检查开发板连接及其是否运行受支持的无线模块固件；显示实际错误。 |
| 开发板回应握手 | 显示检测到的开发板和固件，然后允许继续游戏操作流程。 |
| 开发板断开连接，或用户从“设置”返回 | 刷新检测结果和权限状态，更新引导，并在开发板就绪后继续设置。 |

如果只能通过 CP210x、CH34x 或 FTDI 桥接芯片识别开发板（经典 ESP32），应用会明确说明手机应用无法驱动它。PKHeX 经 Android 编译后在手机上运行。接收的宝可梦通过 Android 文件选择器保存。

设置引导使用经过验证的厂商专属路径或可搜索的设置名称，并在 Android 支持时提供“设置”快捷入口。流程会显示当前相关的下一步操作，并持续展示设置进度。ADB 和无线调试等开发工具与用户设置流程保持分离。

在 Android 上，“打开文件夹”会将该文件夹打包为 ZIP，保存到玩家选择的位置；文件选择器使用 Android 原生界面。

## iOS 设置

该 [iOS 应用](https://decryptu.github.io/examples/ios/README.md) 通过 AltStore 或 SideStore 安装，将此界面带到 iPhone 或 iPad 上。iPhone 无法打开 USB 串口设备，因此应用通过蓝牙连接开发板：开发板运行 **蓝牙无线** 固件，需先在桌面应用的“开发板”页面安装一次（ESP32-C6 使用 `pokeldn-radio-ble-c6.bin`，经典 ESP32 使用 `pokeldn-radio-ble.bin`），此后 USB 仅用于供电。手机连接后，“开发板”页面会将其列为“蓝牙无线模块”；首次启动会请求蓝牙权限。手机占用开发板期间，开发板不会回应 USB 线缆上的任何请求：从电脑或 Android 手机使用开发板前，请先关闭 iOS 应用。文件选择器采用 iOS 原生界面，并将选定文件复制到应用内；应用文件位于“文件 → 我的 iPhone → pokeldn”。

## 手机

宽度小于 760 点时，应用通过底部标签栏展示各页面，每页面板一次仅显示一个，可通过上方的切换器选择：“游戏”页面包括“游戏”“选项”和“会话”；选择工具会切到其选项，按“开始”则会切到会话。对话框占满屏幕宽度。Android 和 iOS 不提供“控制”和“更新”页面。

## 应用语言

“设置 → 应用语言”列出英语和已安装的社区语言包。选择语言包即可启用，重启应用后生效。缺失的文本会回退为英语。训练家语言单独控制生成的宝可梦。[语言包](plugins.md#language-packs-15) 介绍了包格式和翻译模板。桌面应用仅附带默认英语。内置的 [Noto Sans CJK SC](https://github.com/notofonts/noto-cjk/tree/main/Sans/OTF/SimplifiedChinese) 回退字体可在离线状态下显示中日韩文字；其 SIL 开放字体许可证位于 `gui/assets/fonts/LICENSE`.

## 你的训练家

“设置 → 你的训练家”定义应用生成的每只宝可梦的初训家：名称、性别、语言以及两组 ID，均按游戏显示方式输入。《传说 Z-A》只有在初训家的性别、ID 和名称均匹配时，才会将收到的宝可梦视为玩家自己的（[收到的记录](za.md#what-the-trade-writes-into-a-received-record)）。《传说 阿尔宙斯》的数据交换记录携带该性别及与之匹配的外观（[记录](pla.md#the-games-reader-and-the-pre-handler-phase)）；零售版交换时，界面没有任何位置显示对方的性别。记录将训练家保存为 16 位 TID 和 16 位 SID，分别对应一个 32 位 ID 的低半部和高半部。

| 游戏 | 显示的 ID | 秘密 ID | 存储的 ID |
| --- | --- | --- | --- |
| 火红、叶绿 | TID，0 到 65535 | SID，0 到 65535 | `SID << 16 \| TID` |
| Let's Go、剑／盾、晶灿钻石／明亮珍珠、传说 阿尔宙斯、朱／紫、传说 Z-A | id mod 10^6，六位数 | id div 10^6，0 到 4294 | `secret * 10^6 + ID`，小于 2^32 |

Switch 的 ID 对会在 `pokeldn/app/settings.py` `Settings.ids` 中按各游戏转换。在引入 Switch ID 对之前保存的设置，会从第一组 ID 对推导出它，因此基于这些设置生成的记录仍保持相同的存储 ID。

每个与主机连接的工具都会将该训练家作为自己的玩家身份，替换录制消息中携带的名称（`tests/test_gui_catalog.py`）。ID 会传入支持它们的启动器：《火红》《叶绿》、Let's Go、《剑／盾》和《晶灿钻石／明亮珍珠》。《火红》和《叶绿》最多容纳七个第三世代字符；更长的名称会截为七个，不属于第三世代字符集的名称则变为 `POKELDN` (`Settings.name`).

## Windows USB 驱动

经典 ESP32 开发板通过 USB 转串口桥接芯片连接电脑，该芯片位于 USB 插座旁。只有安装桥接芯片的驱动后，Windows 才会为开发板分配 COM 端口；否则应用列表中不会出现该板，设备管理器则会显示警告（问题代码 28，未安装驱动）。使用原生 USB 端口的 ESP32-S3、C3 和 C6 开发板无需驱动。

| 桥接芯片 | USB ID | 驱动 | 安装方法 |
| --- | --- | --- | --- |
| Silicon Labs CP2102 / CP210x | `10c4:ea60` | [CP210x VCP 驱动](https://www.silabs.com/developer-tools/usb-to-uart-bridge-vcp-drivers)，即 CP210x Universal Windows Driver ZIP 压缩包 | 解压后，右键点击 `silabser.inf`，选择“安装”，然后拔下并重新插入开发板 |
| WCH CH340 | `1a86:7523` | [CH341SER.EXE](https://www.wch-ic.com/downloads/CH341SER_EXE.html) | 运行并选择“安装”，然后拔下并重新插入开发板 |

如果没有列出 COM 端口，“开发板”页面会每 2 秒向 Windows 查询设备管理器中存在问题的 USB 设备（`Get-CimInstance Win32_PnPEntity`, `ConfigManagerErrorCode <> 0`），识别找到的已知桥接芯片，并显示对应驱动的安装步骤（`gui/board.py` `bridges_without_driver`).

## Linux 串口

应用以当前用户身份打开开发板，不使用 root，也不使用内核网络功能。打开端口需要属于 `dialout` 用户组（Arch 上为 `uucp`）；如果用户无权打开某端口，操作会失败并返回 `EACCES`，此时“开发板”页面会提示所需用户组，而不是称端口被占用。

| 服务 | 开发板 | 影响 |
| --- | --- | --- |
| brltty 6.4（Ubuntu 22.04） | CH340 `1a86:7523` | 被 `85-brltty.rules` 接管；安装 brltty 时不会出现 `/dev/ttyUSB*`（[LP 1990357](https://bugs.launchpad.net/bugs/1990357)）。修复方法：`sudo apt remove brltty` |
| brltty 6.6（Ubuntu 24.04） | CP210x `10c4:ea60`、CH340 | CP210x 规则已被注释掉（[LP 1958224](https://bugs.launchpad.net/bugs/1958224)）；CH340 仅在连接于 `1a40:0101` 集线器之后时被接管 |
| ModemManager 1.23（Ubuntu 24.04） | 全部 | 没有针对 `10c4`, `1a86` 或 `303a` 的忽略规则；其严格过滤器仅在接口协议为 1 到 6 时允许 `cdc_acm` 端口通过（`mm-filter.c`) |

Linux 上没有列出串口时，“开发板”页面会读取 `/sys/bus/usb/devices`，识别其接口下没有 tty 的已知桥接芯片，并针对 CH340 显示 brltty 修复方法（`gui/board.py` `bridges_without_port`).

## 本地存储

“设置 → 存储”显示可回收本地文件占用的空间。“清理本地文件”会先请求确认，再移除检查中列出的文件，并报告释放了多少空间。清理前请保存缺陷报告所需的记录。

清理范围包括应用的 `session/` 工作文件（抓包、串口跟踪、临时提供文件及会话元数据）、`logs/`，以及 `pokemon/` 中未使用的已生成或已导入提供文件。生成不足一分钟的提供文件会保留，以便尚未完成的构建保存其选择。已保存工具设置和队列引用的提供文件也会保留。接收文件及其选定文件夹、宝可梦仓库、Switch 密钥、选定固件和设置均会保留，即使它们位于待清理文件夹内也是如此。除应用明确命名的临时提供文件以外的宝可梦记录和二进制转储，即便在更改接收文件夹后也会保留。生成的提供文件通过构建器的时间戳和随机后缀识别。符号链接会跳过；检查后发生变化的文件会保留。空子文件夹会被移除。

清理前请先完成所有正在进行的会话、刷写或开发板检查。清理在后台执行，完成前会阻止启动新会话和刷写。无法移除的文件会被报告，并可重试。宝可梦精灵图缓存有独立的“清除缓存”按钮，位于高级设置中。

## 你的存档

《火红》和《叶绿》神秘礼物工具的“你的存档”选项卡，可以通过“神奇卡片 → 朋友”路径备份主机存档，或将存档恢复回去（[存档备份与恢复](frlg_gift.md#save-backup-and-restore)）。存档保存在 `Documents/pokeldn/Saves` (`pokeldn.app.saves`），每个 `.sav` 旁都有一个 `.json`，保存其名称、来源及主机游戏代码。“清理本地文件”绝不会触碰此文件夹；设置 `POKELDN_DATA` 后，存档库则位于该文件夹中的 `Saves`。

| 操作 | 行为 |
| --- | --- |
| 从 Switch 备份 | 启动器写入 `backup-.sav` 及其 `.json`；因连接中断而未完成的备份会保存在 `Saves/.partial`，下次备份会从中断处继续 |
| 将存档写入 Switch | 选定的存档会传给 `--save-restore`；选择存档前，“开始”按钮保持禁用 |
| `+`，或将 `.sav` 拖放到卡片上 | 文件会被复制进来；16 字节的模拟器页脚会被去除，除此之外，任何非 128 KB 大小的文件都会被拒绝 |
| 重命名、导出 .sav、删除 | 名称仅用于显示，保存在 `.json` 中；“删除”仅会移除此电脑上的这两个文件 |
| 查看并编辑 | PKHeX 读取训练家、队伍和电脑盒子；见下文 |

运行期间，“会话”面板会将启动器输出的 `[save] backup N of 128 KB` 或 `[save] restore N of M sectors` 行显示为进度条，运行结束后刷新列表。

当存档没有完整副本，或 PKHeX 发现队伍中存在不合法的宝可梦时，会阻止恢复，直到开启“仍然恢复”。存档名称默认使用训练家和卡带信息，其中卡带信息只有备份才能获知。

编辑器可以修改训练家名称、性别、金钱和代币，以及队伍：重新排序、移除，或添加由 PKHeX 根据此存档自身训练家信息（名称、ID、秘密 ID 和语言）生成的宝可梦。每只队伍宝可梦都会显示 PKHeX 的判定；“检查合法性”会检查一个盒子，需数秒。“另存为新存档”会通过 PKHeX 写入结果，重新计算每个扇区的校验和，检查是否通过游戏自身的扇区测试，并将其作为新条目加入存档库；原始存档保持不变。

## 宝可梦仓库

“宝可梦仓库”页面会保存交换收到的每只宝可梦，并可将它交换到 HOME 允许转移至的任意游戏。记录保存在 `Documents/pokeldn/Bank` (`pokeldn.app.bank`），每条记录均使用对应游戏的原生格式（`.pk3`, `.pb7`, `.pk8`, `.pb8`, `.pa8`, `.pk9`, `.pa9`），旁边带有一个 `.json`。“清理本地文件”绝不会触碰此文件夹；设置 `POKELDN_DATA` 后，宝可梦仓库则位于该文件夹中的 `Bank`。

| 步骤 | 行为 |
| --- | --- |
| 一次交换完成 | 会话面板使用 PKHeX 读取每个接收文件，并将副本存入宝可梦仓库；接收文件仍保留；字节内容已存在于宝可梦仓库中的记录不会重复存入 |
| 宝可梦存入宝可梦仓库 | 其 `.json` 会保存种类、摘要、PKHeX 判定、源文件、字节内容的 SHA-256、位于“made”下用于转移的随机 63 位 HOME 追踪码，以及 `home_tracker`: `empty`, `made`，也可能为空 |
| 页面列出目标游戏 | 辅助程序的 `destinations` 命令会尝试转移至全部七款游戏，并报告各项拒绝原因 |
| 选择目标游戏的交换工具 | 辅助程序的 `move` 命令会转换记录，转换结果连同 `"bank": id` 一起加入该工具的提供队列，应用随即打开该工具 |
| 本次运行的第 N 次交换完成 | 该 `[done] trade N complete` 行会移除排为第 N 次交换的仓库宝可梦；运行结束时，其队列条目也会移除 |
| 运行在此之前失败或被停止 | 宝可梦仍保留在宝可梦仓库和队列中 |

转移会先经过 PKHeX 自身的 HOME 转换（`EntityConverter.ConvertToType`，通过 `PKH`），再执行 PKHeX 在目标游戏中的合法性检查；若在目标游戏中不合法，则拒绝转移并显示 PKHeX 原因，将逐招式信息合并为一条（“有 2 个招式不合法”），每个问题仅列一次。转移过程中：

-
-
-
-

| 拒绝条件 | 依据 |
| --- | --- |
| 任何宝可梦都不能转回《火红／叶绿》 | `EntityConverter.IsConvertibleToFormat` |
| 任何宝可梦都不能转入 Let's Go | HOME 只允许从中移出；仅使用转换器则可将 `PK3` 转为 `PB7`，因为 Let's Go 的格式编号（7）高于《火红》（3） |
| 蛋 | HOME 对《火红》和《叶绿》的筛选规则；转换器则会将其孵化 |
| 《火红／叶绿》中携带道具或掌握秘传招式的宝可梦 | HOME 对《火红》和《叶绿》的筛选规则 |
| 目标游戏不存在的种类或形态 | 目标游戏的种族数据表 |
| 没有转换路径 | PKHeX.Core 26.8.26 无法将任何《传说 Z-A》记录转换到其他游戏 |

“编辑”只修改玩家可在游戏内自行更改的内容：昵称（留空可恢复种类名称）、等级（只能提高）、招式和携带道具。辅助程序的 `check` 命令会应用这些字段并执行 PKHeX 合法性检查；如果编辑会让合法宝可梦变为不合法，则会拒绝并保持原记录不变。保存编辑会重写记录及其 `.json`（摘要、判定、SHA-256），并重新检查目标游戏。已加入交换队列的宝可梦不可编辑。

### HOME 追踪码设置

当宝可梦缺少所需的 HOME 追踪码时，PKHeX 会将其标记为无效（`HomeTrackerUtil.IsRequired`, `LegalityCheckResultCode.TransferTrackerMissing`，严重级别为 `HOMETransferTrackerNotPresent`）：包括已转移到其他游戏的宝可梦，以及只能通过 HOME 到达该游戏的活动礼物。HOME 3.1.0 及更新版本会拒绝并非由 HOME 签发的追踪码（错误 10015）。“设置 → 高级设置 → HOME 追踪码”用于选择应用在该字段中写入什么（`Settings.home_tracker`); `pokeldn.pokemon.Service` 会在每次辅助程序请求中将其作为 `home_tracker` 发送，运行时则通过以下变量继承该值：`POKELDN_HOME_TRACKER`.

| 设置 | 宝可梦仓库转移、导入，以及构建器的礼物修复 | 合法性 | 显示的警告 |
| --- | --- | --- | --- |
| `empty`（默认） | 追踪码保持未设置 | 若 PKHeX 判定该记录在带有追踪码时合法，则予以接受；存在其他问题则拒绝 | PKHeX 标记缺少 HOME 追踪码 |
| `made` | 随机 63 位追踪码；仓库宝可梦使用其仓库追踪码 | 不变 | 无法存入 HOME |

每个辅助程序回复都携带 `home_tracker` (`empty`, `made`，也可能为空），而 `destinations` 会按游戏提供该信息。警告会显示在生成或加载的提供记录、仓库条目、仓库目标游戏以及导入行上。PKHeX 26.8.26 的其他检查取决于是否存在追踪码：没有追踪码时，它不允许在另一个 HOME 游戏中发生任何进化（`EvolutionGroupHOME.CheckAllAdjacent`），因此在《朱》中以皮丘孵化的皮卡丘，在《剑／盾》中会被视为不可能的进化；《传说 Z-A》也只会在带追踪码的记录上保留 HOME 重新对齐后的特性（`AbilityVerifier.VerifyBirthAbility`，例如《黑 2》探探鼠在 `tests/data/bank_import.json` 中的隐藏特性）。在 `empty` 设置下，辅助程序会使用一份副本来判定此类记录；该副本包含追踪码，以及 HOME 对其处理过的宝可梦所做的更改（`ValidWithTracker`）；记录本身仍不保留追踪码。

“神秘礼物－模拟”也遵循此设置（[神秘礼物－模拟](#mystery-gift---simulated)）。在各类礼物中，PKHeX 只要求由 HOME 发放的礼物携带追踪码：在 `empty` 下，副本不带追踪码；在 `made` 下，则带有生成的追踪码（`MendGift`，位于 `services/pkhex/Program.cs`）。生成的追踪码还会配套应用 HOME 对其处理过的宝可梦所做的更改，因为 PKHeX 会要求带追踪码的记录满足这些条件 [HomeQuirks]：《朱／紫》宝可梦的身高设为其体型值，《传说 Z-A》的身高和体重也作相应处理，而《传说 Z-A》的头目宝可梦会带有头目标记（`HomeSeen`）。PKHeX.Core 26.8.26 收录了此类礼物：《剑／盾》16 个，《晶灿钻石／明亮珍珠》《传说 阿尔宙斯》和《传说 Z-A》各 4 个，《朱／紫》5 个；每个礼物在两种设置下均可通过检查。《剑／盾》神秘礼物会以社区卡片形式发送其中 16 个（“官方活动 → Pokémon HOME”）：宝可梦由主机生成，因此无论设置如何都不会带有追踪码（[Pokémon HOME](swsh_gift.md#pokemon-home)).

### 导入

通过“宝可梦仓库”页面的加号按钮，或将文件拖放到网格上，可以导入宝可梦文件或游戏存档。辅助程序的 `import` 命令使用 PKHeX 读取文件：先使用 `SaveUtil.TryGetSaveFile`，并借助文件名识别（3DS 存档是名为 `main` 且无扩展名的文件），然后使用 `FileUtil.TryGetPKM` 读取 PKHeX 支持的任意格式的单条记录（`.pk1` 到 `.pk9`, `.pb7`, `.pb8`, `.pa8`, `.pa9`, `.ck3`, `.xk3`, `.bk4`, `.rk4` 等）。对于存档，先提取每个非空队伍槽位，再提取每个非空盒子槽位。该文件仅被读取。

| 记录 | 宝可梦仓库保留的内容 |
| --- | --- |
| 来自宝可梦仓库支持的游戏（`PK3`, `PB7`, `PK8`, `PB8`, `PA8`, `PK9`, `PA9`) | 若 PKHeX 判定合法，则原样保留记录，包括携带道具和招式 |
| 其他任意格式 | 移除记录中的携带道具，因为宝可梦进入 HOME 时不会携带道具；对于第三或第四世代记录，还会遗忘秘传招式，因为伙伴公园和宝可传送会拒绝它们；若随后 PKHeX 判定合法，则按仓库转移方式转入首个接受它的游戏，顺序为《火红／叶绿》《朱／紫》《剑／盾》《晶灿钻石／明亮珍珠》《传说 阿尔宙斯》《传说 Z-A》 |

如果 PKHeX 判定记录在其原格式下不合法，则会拒绝并显示 PKHeX 原因；转移时建议的配招绝不会替代该记录原游戏本不允许的招式。校验和错误的记录、其他游戏的蛋，以及所有可达游戏均不支持的种类，也会被拒绝。导入宝可梦的 `.json` 中携带 `imported`：文件名、槽位、源格式及移除的内容。

`Bank/.imported` 为每条已导入记录保存一个键：在移除任何内容之前，对其解密后存储字节计算的 SHA-256。键已存在的记录不会再次导入，即使该宝可梦已通过交换离开仓库；字节内容已入库的记录也不会重复入库。游玩游戏后再次导入同一存档时，只会导入发生变化的记录。

从《火红》存档导入的一只百变怪，已通过“宝可梦仓库”页面交换到零售版《朱》；再次导入该存档时，其中 104 条记录无一重复入库。

一条从零售版《剑》收到并转移到《传说 Z-A》的记录，使用了仓库追踪码且保留其 PID，已在零售版 Z-A 的交换盒子中显示等级和初训家，并完成交换。

`tests/test_bank.py` 会通过真实辅助程序在六组游戏之间转移记录，检查目标启动器是否接受，并验证各项拒绝条件、被接受和被拒绝的编辑，以及交换后将宝可梦移出仓库的运行流程。它会导入《黑 2》存档，以及由 PKHeX 遭遇生成器构建的第四世代和第六世代文件（`tests/data/bank_import.json`）：携带道具和秘传招式被移除，非法记录被拒绝，第二次导入不会有任何记录入库。

### 尚未解决的问题

-
-
-
-

## GTS

“GTS”页面列出其他玩家公开中的挂单，可按提供或想要的种类筛选；玩家自己的挂单和报价位于“你的”区域。“寄放宝可梦”会使用一只合法且未排入交换队列的仓库宝可梦；挂单详情中会提供所有符合条件的仓库宝可梦供选择。挂单或报价期间，宝可梦位于 `Documents/pokeldn/GTS`，不在宝可梦仓库中。一旦存在挂单或报价，只要应用运行，无论当前处于哪个页面，都会回应报价。事件和规则见 [GTS](online.md#the-gts).

## 开发板与固件

“开发板”页面会列出插入此电脑的每块开发板。选中开发板的页头会显示其固件和版本，标明“已是最新”或“有可用更新”，并提供该状态所需的操作。“固件”卡片列出应用附带的每种固件（`gui.board.FIRMWARES`：先是“无线”，然后是“控制器”）；已安装的固件会被标记，芯片无法运行的固件会明确说明，其余固件在确认后即可安装。“从文件安装”接受 pokeldn 的 `.bin`，并通过其应用描述符中的项目名称识别。

| 开发板 | 页面如何发现它 | 版本来源 |
| --- | --- | --- |
| 无线固件 | 其串口 | HELLO 回复 |
| 控制器固件，经典 ESP32 | 无线模块检查失败后，通过其串口发现 | 端口上的状态帧 |
| 控制器固件，ESP32-S3 | USB 总线（macOS 使用 `0f0d:0092`: `ioreg`，Linux 使用 `/sys/bus/usb/devices`，Windows 使用 `Win32_PnPEntity`）；它没有串口 | 通过蓝牙读取的状态 |
| 未安装 pokeldn 固件 | 没有任何回应时，通过其串口发现 | 无 |

应用附带的版本取自镜像 ESP-IDF 应用描述符的 `version` 字段（魔数为 `0xABCD5432`，在合并镜像中的位置为 `0x10020`）。“有可用更新”表示该版本比开发板上的版本更新。在串口上安装时，会让 esptool 将芯片复位进入加载器；对于运行控制器固件的 S3，则会通过蓝牙发送下载命令，最多等待 20 秒让加载器端口出现，然后使用以下方式刷写：`--from-loader`.

## 控制器

“控制”页面通过运行控制器固件的开发板（[控制器开发板](hardware_pad.md)）操作 Switch 按键并执行宏。请从“开发板”页面安装“控制器”固件（ESP32-S3 或经典 ESP32）。ESP32-S3 插入 Switch 的 USB-C 端口，“连接”通过蓝牙 LE 连接它。经典 ESP32 则保持连接此电脑的 USB，并从 Switch 的“HOME → 控制器 → 更改握法／顺序”进行配对；“连接”通过串口连接它。重新安装固件会清除配对。

状态行会说明开发板连接在哪里：连接此电脑（出现在此电脑的 USB 总线上）、连接 Switch（USB 已配置但不在此电脑总线上），或两者都未连接。固件的 `mounted` 标志仅表示某个 USB 主机端已配置开发板。

| 部分 | 作用 |
| --- | --- |
| 屏幕控制器 | 按住按钮会在主机上持续按住对应按键；摇杆支持八个方向的满幅偏转，中心为 L3 和 R3 |
| 键盘 | 开启时，键盘按键会按宏的按压时长点按对应按钮：方向键对应十字键，X 对应 A，Z 对应 B，S 对应 X，A 对应 Y，Q 对应 L，W 对应 R，1 对应 ZL，2 对应 ZR，Enter 对应 +，Backspace 对应 -，H 对应 HOME，C 对应截图键 |
| 录制到宏 | 每次按压都会成为一个记录保持时长的步骤，下一次按压前的间隔会成为该步骤的暂停时长 |
| 宏编辑器 | 支持按下按键和操作摇杆的步骤、等待步骤，以及可嵌套的重复步骤；包含“运行一次”部分和按指定次数或持续至停止的“循环”部分 |
| 在开发板上播放 | 编译、加载并启动宏；开发板按自己的时钟执行，即使电脑休眠或断开连接也会继续 |

运行控制器固件的开发板插入此电脑时，会显示在“开发板”页面；[开发板与固件](#boards-and-firmware) 介绍了如何发现它及更换固件。未连接控制器时，“控制”页面会说明当前插入的设备，并提供“开发板”页面链接。

宏保存在 `Documents/pokeldn/Macros`（设置 `POKELDN_DATA` 后，位于该文件夹中的 `Macros`），每个宏对应一个 `.pokemacro` 文件，每次编辑都会写入。“导出”会写出用于分享的副本；“导入”会检查文件，并以未占用的名称复制进来。格式见 [控制器开发板：宏](hardware_pad.md#macros).

连接断开时（将开发板从电脑移到 Switch 导致其断电），页面会重新寻找开发板，直到它回应或按下“停止查找”。

页面与 `pokeldn.pad.service` 通信；它是一个通过 `127.0.0.1:47800` 维持蓝牙连接的子进程。在 macOS 上，除非应用声明了 `NSBluetoothAlwaysUsageDescription`，否则尝试打开蓝牙的进程会被停止；打包应用已声明，未声明时也只会停止该子进程。应用关闭子进程的 stdin 后，子进程会退出。

在 macOS 26 上，`bluetoothd` 会对签名身份为应用包主可执行文件的后台进程进行被动的“ThirdPartyApp scan”，无论是否设置服务 UUID 过滤器，都不会向其提供发现结果；独立签名的二进制文件（`Info.plist=not bound`）则会获得主动扫描。因此，打包应用从 `Contents/Helpers/pokeldn-bluetooth` 启动服务；这是其可执行文件的副本，使用该标识符签名，并将 `_internal` 链接到 `../Frameworks`；它使用应用的蓝牙权限运行。从主可执行文件扫描时发现 0 个设备；从辅助程序扫描时发现 19 个，其中包括开发板。如果应用发现正在运行的服务使用其他代码（状态回复中的 `code`），就会要求其退出并启动自己的服务。

## 宝可梦精灵图

宝可梦图像来自 [PokeAPI](https://github.com/PokeAPI/sprites)，按需下载。已下载的图像缓存在应用数据文件夹中的 `sprites/`，离线时仍可使用。

“设置 → 宝可梦精灵图”可禁用下载；缓存图像仍会显示。同一设置区域还提供清除精灵图缓存的按钮。

不可用的种类或形态会显示占位图。如果异色图像不可用，则显示同一形态的普通图像。缺少图像不会妨碍生成或交换宝可梦。

## 团体战活动

《朱／紫》的“太晶团体战（主机端）”工具中，“团体战活动”卡片可使用 Project Pokemon 的 [EventsGallery](https://github.com/projectpokemon/EventsGallery) ([活动团体战](sv_raid.md#event-raids)）中的活动创建团体战。应用会在自身数据文件夹内的 `EventsGallery/` 中保存该图库团体战活动的独立副本（`pokeldn.app.events_gallery`）；“清理本地文件”会保留它。

| 操作 | 行为 |
| --- | --- |
| 下载 | 向 `api.github.com` 查询 master 分支中最近一次修改 `Released/Gen 9/SV/Raid Events` 的提交，下载 `codeload.github.com/projectpokemon/EventsGallery/zip/`（2026 年 10 月为 22 MB），并解包每个活动最新补丁中的四张表，约 17 MB；`gallery.json` 保存提交及其日期 |
| 检查更新 | 仅请求一次该最新提交；与本地副本不同时才视为有更新。图库其他位置的变化不算更新 |
| 更新 | 重新执行下载 |

新副本只有在完整下载后才替换旧副本；下载失败或取消时会保留旧副本。活动文件夹名称最长达 152 个字符，因此在 Windows 上，应用使用 `\\?\` 路径打开文件。

活动列表包含副本中除 `000 Base Data`（游戏自身的表）以外的所有活动：截至 2026-09-06 共 152 个，默认最新在前，旁边的箭头可切换顺序。每项上方显示去掉编号的文件夹名称（若为轮次，则显示“活动 · 轮次”），下方显示首领；输入搜索时会同时筛选两者。选择一个活动后：

-
-
-

折叠卡片会暂时停用该活动（`#raid-event-folded`，位于工具值中，`GamesView.show_raid_event`）：团体战卡片、“查找团体战”和命令均恢复为普通团体战，页头显示“已关闭：活动”。展开后恢复活动。启动时若正在使用活动，该卡片会展开。本地副本缺少的活动（未下载，或更新后被移除）仍会保持选中：页头以红色显示“缺失：活动”，并在副本重新包含它或选择其他活动前拒绝运行（`pokeldn.app.command.code_error`).

## 主机端团体战奖励

“太晶团体战（主机端）”工具的“奖励”卡片提供培养道具、太晶碎块（包括星晶）、秘传调味料、宝物和精灵球模板。选择组合会替换当前奖励行。“每项数量”会将该组合内所有行的数量统一改为 1 到 999。编辑道具或单独的数量会切换为“自定义奖励”；可增删行，最多 45 行。未填完整的行或无效数量会阻止启动。已保存的选择会保留道具和数量。

“团体战自带奖励”会清除覆盖设置，并使用所选团体战的奖励表（[作为主机端](sv_raid.md#hosting); `gui/views/rewards.py`).

## 团体战 NPC 队友

“太晶团体战（主机端）”工具中，“加入的主机数”下方的“团体战 NPC 队友”卡片，可选择填补主机未占用槽位的 NPC 训练家：一台主机加入时有两名，两台时有一名，三台时没有（[队友](sv_raid.md#partners); `gui/views/raid_partners.py`）。未选择时不传入任何参数，主机端会像游戏主机一样，从剧情进度对应的池中抽取。

-
-

点击可让训练家入座，并按所占槽位编号；再次点击则将该槽位交还随机抽取。每个选择会依次传入 `--raid-partner`。提高“加入的主机数”会移除最后一个选择；如果所选阶段没有该训练家，也会移除（例如四星以下的 Dylan 或 Luke）。折叠仅隐藏卡片（`GamesView.show_raid_partners`）：选择仍会传给团体战，页头会显示所选名称。

## 联盟集友圈

《朱／紫》的两个联盟集友圈工具通过四位连接密码，加入主机创建的集友圈（[联盟集友圈](sv_union_circle.md)）。每次集友圈的密码都不同，因此每次启动时该字段都为空（`Field.remembered`).

-
-

内置运行的 `[panel]` 卡片（[状态卡片](plugins.md#status-cards-18)）仅在运行期间显示于对应工具选项的顶部（`GamesView.show_run_cards`）；运行结束即消失。遭遇运行通过这种方式显示区域搜索状态。

集友圈运行日志只保留用户需要关注的内容：加入、主机端总数、BP 完成情况、宝可梦生成或进入战斗，以及找到或丢失主机端所在区域。`--verbose-circle`（位于“高级”选项卡的“高级选项”中）会额外记录每条发送的集友圈消息以及区域搜索的每个步骤。

## 神秘礼物－模拟

Let's Go、《晶灿钻石／明亮珍珠》《传说 阿尔宙斯》《朱／紫》和《传说 Z-A》的“神秘礼物－模拟”工具卡片，会列出 PKHeX 活动表中该游戏的礼物宝可梦（[模拟神秘礼物](gift_simulated.md#the-gifts); `gui/views/event_gifts.py`）。每行两张卡片，最新在前：依次显示精灵图、卡片标题，以及宝可梦、所属训练家和发放时间；悬停可查看招式。一次显示 24 张，“显示更多”再增加同样数量；搜索可通过卡片显示的任意词语、精灵球、招式或卡片编号缩小范围。十张及以下时完整显示，更多时在独立区域内滚动（`event_gifts.FIT`).

点击会为“设置”中的训练家创建新副本，并将其添加到列表上方的队列中，显示合法性、招式和初训家。一次主机端会话中最多可按顺序交换六个礼物。同一活动可选择多次，每次都会创建独立副本。按“开始”前，可用关闭按钮移除队列中的礼物。队列满时会暂停接受新选择，直到有礼物被移除。副本保留生成时的训练家：更改训练家后，需要移除并重新选择该礼物。对于以接收者为训练家、但从未向该训练家语言的存档发放过的礼物，例如非中文训练家选择 Let's Go 的中文美录坦和美录梅塔，卡片会显示非法及原因；点击后也会提示原因，并保留当前提供内容（[卡片发放到的存档](gift_simulated.md#saves-a-card-reached)）。默认开启“为接收玩家生成”（“高级”选项卡）时，交换会针对主机自身存档重新生成以接收者为训练家的礼物（[为接收玩家生成](gift_simulated.md#made-for-the-receiving-player)）。具有卡片固定训练家的礼物会按生成时的样子发送。如果队列中所有礼物都按原样发送，该开关会关闭、禁用并淡化，下方说明会解释原因（`command.locked`）。此时启动不会传入 `--for-receiver`。当队列包含可使用接收者姓名的礼物时，开关会恢复之前的设置；主机端会将其应用于每张符合条件的卡片。

除 Let's Go 外，任意游戏中由 HOME 发放的礼物，其追踪码由 HOME 追踪码设置决定（[HOME 追踪码设置](#the-home-tracker-setting)）。其卡片会带琥珀色边框；选定副本会显示对应设置的警告：“PKHeX 标记缺少 HOME 追踪码”或“无法存入 HOME”。交换时仍像其他礼物一样提供（[交换所提供的副本](gift_simulated.md#the-copy-a-trade-offers)).

## 隐私日志

“设置 → 在日志中隐藏个人信息”（默认开启）会在应用显示和复制的会话日志及开发板日志中遮蔽以下内容（`pokeldn/app/redact.py`):

| 遮蔽内容 | 替代显示 | 保留内容 |
| --- | --- | --- |
| 路径中的用户主目录（`/Users/NAME`, `/home/NAME`, `C:\Users\NAME`) | `~` | 路径其余部分 |
| iOS 应用容器（`/var/mobile/Containers/Data/Application/UUID`) | `` |  |
| MAC 地址中标识设备的后半部分，有无冒号均可 | `**:**:**`, `******` | 标识厂商的前半部分（Nintendo、Espressif） |
| 带引号的值（`'…'`, `"…"`, `b'…'`），位于 `ot_name`, `ht_name`, `OT`, `nickname`, `trainer`, `player` 或 `name` | `***` | `POKELDN` 和 `PKLDN`，不区分大小写；程序自身的名称 |
| 以下标识之后的值：`TID`, `SID`, `tid`, `sid`, `trainer_id` | `***` |  |
| 运行中曾出现过一次的训练家名称，以及“设置”中的训练家名称，在后续任何位置再次以完整词语出现时均遮蔽 | `***` |  |

昵称只在其原位置遮蔽，不会在其他位置遮蔽：因为它往往就是种类名称。会话记录（`captures/`）包含原始消息，不做遮蔽。本地链路地址（`169.254.x.x`, `127.0.0.x`）无法识别任何人，因此保留。

## 弹窗

应用启动的运行、它的其他子进程，或应用自身的代码，都可以在当前任意页面上方显示弹窗（`pokeldn.popup`，自插件 API 1.2 起提供）。共有三种：

| 类型 | 按钮 | 回调 |
| --- | --- | --- |
| `acknowledge(title, text)` | 一个，`label`（确定） | `on_ack`：点击按钮、按 Esc 或点击外部时触发 |
| `confirm(title, text, agree, disagree)` | 同意和不同意，使用调用方提供的标签 | `on_agree`, `on_disagree` 或 `on_dismiss`；按 Esc 和点击外部会触发后者 |
| `choose(title, text, options)` (1.7) | 每个选项一个，共 2 到 8 个，按调用方顺序在文本下方全宽显示 | `on_choice(index)`，或 `on_dismiss`；按 Esc 和点击外部会触发后者 |

打开弹窗从不等待：会立即返回弹窗 ID，稍后通过回调传回答案。回调在读取应用答案的线程中运行，除非 `set_dispatcher(dispatch)` 将其交给程序自身的循环；在应用内则运行于工作线程，避免回调阻塞窗口。回调抛出异常时会打印回溯。

| 选项 | 作用 |
| --- | --- |
| `id` | 在程序自身的弹窗中标识此弹窗；使用仍未关闭弹窗的 ID 再次打开时，会原位替换它并丢弃原回调。未提供时会生成新 ID |
| `tone` | `info`, `warning` 或 `error`，用于选择图标 |

`cancel(id)` 可关闭弹窗；一旦 `cancel` 返回，其任何回调都不会再触发，但先前答案已交给分发器的回调除外。程序若已有 32 个未回答弹窗，将收到 `RuntimeError`。弹窗页头会显示打开它的程序：工具、开发板安装器或控制器服务；应用自身打开的弹窗则不显示名称。

程序退出时，其确认弹窗和选择弹窗会关闭，通知弹窗则保留，但不会再回传答案。没有应用界面时（`available()` 为假，例如终端中），弹窗只是一条输出中的 `[pop-up]` 行，不会有答案返回，也不计入 32 个的限制。

`runner.Process(..., popups=app.popups, label=...)` 会在子进程中设置 `POKELDN_POPUPS=1`。子进程将每个弹窗作为 stdout 上的一条 `[popup]` 行和一个 JSON 对象发送；应用不会将其写入日志，即使其他线程的打印让它出现在行内任意位置，也会识别出来；应用通过子进程 stdin 上的 `[popup] {"id", "n", "answer"}` 回答（选择题的答案是选项索引，从 `"0"` 到 `"7"`），由 `pokeldn.app.runner.child` 读取。`n` 用于区分弹窗及使用相同 ID 重新打开的弹窗，因此对已替换弹窗的迟到答案不会触发任何操作。应用内代码会直接访问管理器（`popup.attach`). `pokeldn.app.popups.Manager` 保存打开的弹窗；`gui.popups.Dialogs` 负责绘制。应用对话框的 `page.pop_dialog()` 只关闭应用自身最上层对话框，绝不会关闭在其上方打开的弹窗。

## 进度

运行会输出 `[progress] DONE TOTAL UNIT TITLE` (`pokeldn.progress.show`，插件 API 1.7；`UNIT` 为 `bytes` 或 `items`），以在“会话”面板中用进度条代替日志行：显示数量（`1.05 of 5.20 GB`）、最近 30 秒的速率以及剩余时间。`show` 对每个标题每秒最多输出四行，并始终输出最后一行。存档备份或恢复的 `[save]` 行也会绘制相同的进度条。

当原本为接收玩家生成的礼物改用“设置”中的训练家发送时，“神秘礼物－模拟”会发出警告并说明原因：存档没有训练家名称，或副本在卡片、PKHeX、提供内容检查或加载器阶段停止（[交换](gift_simulated.md#the-trade)）。每台主机各有一个警告（`receiver_gift.pop_up`），较新的原因会替换当前打开的原因。应用还会针对更新未安装成功、以及被停用的插件显示自己的警告。

## 更新

应用启动时，会在后台向 `api.github.com/repos/Decryptu/pokeldn/releases/latest` 查询最新稳定版本，超时为 5 秒。如果标签版本高于应用的 `pokeldn.__version__`，侧边栏会增加“更新”入口，打开后显示包含发行说明的对话框，以及“立即更新”或“下载”按钮。

立即更新（`pokeldn.app.update`）会原位安装该版本：

1.
2.
3.
4.
5.
6.

应用自行下载的文件不带隔离属性（macOS）或网络来源标记（Windows），因此 Gatekeeper 和 SmartScreen 都不会再次询问。`SHA256SUMS` 与压缩包来自同一个 GitHub 发行版：校验可发现下载损坏或截断，但不能验证发行版的真实性。

| 情况 | 行为 |
| --- | --- |
| 预发布版本、草稿，或标签不符合 `vX.Y.Z` | 不提供 |
| 无网络、HTTP 错误，或回复不是发行版 | 启动时不显示任何内容；“立即检查”会提示 GitHub 未回应 |
| 在“设置”中关闭“更新” | 启动时不发送请求；“立即检查”仍会发起查询 |
| 没有适用于此电脑的压缩包，或缺少 `SHA256SUMS` 于该发行版中 | “下载”会打开文件或发行版页面 |
| 源码检出目录、从“下载”运行的 macOS 应用（App Translocation），或用户不可写的 macOS／Linux 文件夹 | 显示“下载”并说明原因 |
| Windows 上用户不可写的文件夹（`C:\Program Files`) | 显示“立即更新”；辅助程序启动前，Windows 会请求管理员权限（UAC），拒绝时应用保持不变 |
| 会话、刷写或清理正在运行 | “立即更新”会要求先完成当前操作 |
| 校验和不匹配或下载失败 | 不做任何更改；对话框提供“下载” |

在 Windows 上仅管理员可修改的文件夹中，辅助程序通过 `ShellExecuteExW`，使用 `runas` 动词启动，并在解包副本旁读写操作结果（管理员辅助程序可能以其他用户身份运行），最后通过资源管理器打开新应用，使其按用户自身权限运行。`scripts/check_update.py ARCHIVE FOLDER` 会用 127.0.0.1 上提供的发行版测试打包应用自身的更新流程；“更新检查”工作流使用“发布”运行生成的压缩包，在 Windows（用户文件夹及 `C:\Program Files`）和 Linux 上执行此测试。

设置、密钥及收到的宝可梦保存在应用之外，因此会保留。辅助程序替换 `/Applications` 中的应用时，macOS 是否请求“应用管理”权限尚未测试；若被拒绝，会保留旧应用，并在对话框中显示错误。

请求不携带用户数据。GitHub 对每个地址每小时允许 60 次未经身份验证的请求。`POKELDN_UPDATE_URL` 可替换端点以便测试（`tests/test_app_update.py`).

## 文件拖放

从桌面拖来的文件可放到以下目标：

| 目标 | 接受内容 |
| --- | --- |
| 交换中的“要提供的宝可梦” | 宝可梦文件（按“或使用宝可梦文件”的方式导入），或包含 Showdown 配置的 `.txt`（按“导入粘贴内容”的方式读取）；后续文件会分配到之后的交换 |
| 添加交换 | 每个文件新增一次交换，优先填充末尾未改动的交换，直至达到会话上限 |
| 神秘礼物工具的“礼物”卡片 | 一个 `.pokegift`，或一张 `.wc8`（《剑／盾》）或 `.wc3`（《火红／叶绿》）卡片；会切换到“打开文件” |
| “开发板”页面的“固件”卡片 | pokeldn 的 `.bin`，确认后安装 |
| 任意路径字段、欢迎对话框 | 该字段要求的文件；文件夹字段会取拖入文件所在的文件夹 |

Flet 1.0.2 的桌面客户端不接受文件拖放。`scripts/build_client.py` 会检出与已安装版本相同的 Flet 源码，将 `gui/flet_drop`（基于 [desktop_drop](https://pub.dev/packages/desktop_drop) 封装的 Flet 扩展）加入其客户端，并构建到 `gui/client/`. `gui/drop.py` 声明对应的 `FileDrop` 控件。`gui/main.py` 在自定义客户端已构建时使用它，否则运行 Flet 自带客户端，此时不会显示拖放目标；冻结打包的应用始终附带已构建的客户端。该脚本需要 Flutter，版本由 `python -m flet_cli.cli --version --json` 指定（Flet 1.0.2 对应 3.44.8）。它将 macOS 客户端的部署目标从 11.0 提高到 12.0：Xcode 27 无法构建更老的目标。Linux 客户端采用 Flet 的轻量版本，与 Flet 自身 CI 的构建方式相同。

## 文档页面

“文档”页面显示应用指南，以及本站导航列出的每个页面。页面列表上方的搜索字段按章节匹配：搜索每个标题及其下正文，且查询中的每个词都必须匹配。标题或页面名称中的匹配排名优先。选择结果会打开页面并定位到该标题；指向 `page.md#heading` 的链接也会以相同方式滚动（`gui/views/docs.py`).

## 尚未发行的游戏

为 Switch 正式发行前预先准备的游戏，只有在应用从源码检出目录运行时，才会显示在“游戏”列表、“宝可梦仓库”和“文档”页面中（`pokeldn/app/preview.py`）。打包发行版已冻结，且不包含 `.git`，因此绝不会显示它们。`POKELDN_PREVIEW=1` 可在任何环境中显示它们；`POKELDN_PREVIEW=0` 可在源码检出目录中隐藏它们。对应文档页面会设置 `nav_exclude` 和 `search_exclude`.

## 从源码运行

进行源码开发时，请安装 Python 3.13 和 .NET 10 SDK：

```
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r gui/requirements.txt
dotnet build -c Release services/pkhex -warnaserror
python scripts/build_client.py    # optional: file drops; needs Flutter
python gui/main.py
```

源码检出目录不包含固件镜像（`gui/firmware` 是构建输出）。“开发板”页面的“下载固件”会从包含经典 ESP32 镜像及 `SHA256SUMS` 的最新非草稿发行版中取得所有已知镜像，对照该发行版的 `SHA256SUMS` 逐一校验，只有全部匹配才写入。如果某发行版早于某芯片的支持时间，就不包含该芯片的镜像。比源码检出版本更旧的发行版镜像可能使用较旧的串口协议，此时开发板检查会报告固件已过时。

## 构建桌面应用

要打包应用，请为 `esp32`, `esp32s3`, `esp32c3` 和 `esp32c6` 安装 ESP-IDF v6.1，并激活其环境。使用各自独立的配置构建四种无线模块镜像，以及控制器镜像（`firmware/pad`，它会通过组件管理器获取 `espressif/esp_tinyusb`）：

```
mkdir -p gui/firmware
POKELDN_IMAGES="$PWD/gui/firmware"
cd firmware/esp32
idf.py -B build/esp32 -D SDKCONFIG="$PWD/build/esp32/sdkconfig" set-target esp32
idf.py -B build/esp32 -D SDKCONFIG="$PWD/build/esp32/sdkconfig" build
idf.py -B build/esp32 merge-bin -o "$POKELDN_IMAGES/pokeldn-radio.bin"
idf.py -B build/esp32s3 -D SDKCONFIG="$PWD/build/esp32s3/sdkconfig" set-target esp32s3
idf.py -B build/esp32s3 -D SDKCONFIG="$PWD/build/esp32s3/sdkconfig" build
idf.py -B build/esp32s3 merge-bin -o "$POKELDN_IMAGES/pokeldn-radio-s3.bin"
idf.py -B build/esp32c3 -D SDKCONFIG="$PWD/build/esp32c3/sdkconfig" set-target esp32c3
idf.py -B build/esp32c3 -D SDKCONFIG="$PWD/build/esp32c3/sdkconfig" build
idf.py -B build/esp32c3 merge-bin -o "$POKELDN_IMAGES/pokeldn-radio-c3.bin"
idf.py -B build/esp32c6 -D SDKCONFIG="$PWD/build/esp32c6/sdkconfig" set-target esp32c6
idf.py -B build/esp32c6 -D SDKCONFIG="$PWD/build/esp32c6/sdkconfig" build
idf.py -B build/esp32c6 merge-bin -o "$POKELDN_IMAGES/pokeldn-radio-c6.bin"
export POKELDN_BLE=1   # the Bluetooth builds for the iOS app (hardware_esp32.md, Bluetooth)
BLE_DEFAULTS="sdkconfig.defaults;sdkconfig.defaults.ble"
idf.py -B build/ble -D SDKCONFIG="$PWD/build/ble/sdkconfig" -D SDKCONFIG_DEFAULTS="$BLE_DEFAULTS" set-target esp32
idf.py -B build/ble -D SDKCONFIG="$PWD/build/ble/sdkconfig" -D SDKCONFIG_DEFAULTS="$BLE_DEFAULTS" build
idf.py -B build/ble merge-bin -o "$POKELDN_IMAGES/pokeldn-radio-ble.bin"
idf.py -B build/ble-c6 -D SDKCONFIG="$PWD/build/ble-c6/sdkconfig" -D SDKCONFIG_DEFAULTS="$BLE_DEFAULTS" set-target esp32c6
idf.py -B build/ble-c6 -D SDKCONFIG="$PWD/build/ble-c6/sdkconfig" -D SDKCONFIG_DEFAULTS="$BLE_DEFAULTS" build
idf.py -B build/ble-c6 merge-bin -o "$POKELDN_IMAGES/pokeldn-radio-ble-c6.bin"
unset POKELDN_BLE
cd ../pad
idf.py -B build -D SDKCONFIG="$PWD/build/sdkconfig" set-target esp32s3
idf.py -B build -D SDKCONFIG="$PWD/build/sdkconfig" build
idf.py -B build merge-bin -o "$POKELDN_IMAGES/pokeldn-pad-s3.bin"
cd ../..
python scripts/build_client.py
python scripts/build_unicorn.py
python scripts/pack_app.py
```

绝对输出路径确保镜像保存在 `gui/firmware`。打包器要求提供无线模块、蓝牙无线模块和控制器镜像，来自 `scripts/build_client.py` 的客户端，以及来自 `scripts/build_unicorn.py` 的 Unicorn（需要 CMake）；冻结应用检查会验证这些内容均已包含，并确认内置客户端包含 `flet_drop`。发布工作流会分别构建每个目标，并向每个桌面打包器提供全部镜像。

应用版本为 `pokeldn.__version__`，会显示在“设置”以及 macOS 和 Windows 的包元数据中。准备发行版前，请同时更新它和 `.github/release-notes.md`。工作流会为三个桌面下载包和五个固件镜像生成 `SHA256SUMS`。手动运行工作流会生成构建产物；`v*` 标签会发布名为 `pokeldn vX.Y.Z` 的发行版，正文采用 `.github/release-notes.md`，其第一行必须为 `# pokeldn X.Y.Z`（工作流和 `tests/test_release.py` 会检查），并且每次都包含相同的九个文件。只有包含连字符的标签，例如 `v0.3.0-rc1`，才会被标记为预发布版本；GitHub 会在仓库侧边栏将其他发行版中的最新版本显示为“Latest”。

应用采用 PyInstaller 单文件夹构建：macOS 上为 `pokeldn.app`，而 Linux 和 Windows 上为一个 `pokeldn` 文件夹，其中包含 `pokeldn` 或 `pokeldn.exe` 以及 `_internal`。单文件版本每次启动都会将整个包（约 180 MB）解压到临时文件夹，而每次运行工具都是应用重新启动自身，因此又要支付一次解压开销。在 M4 上，单文件夹应用进入“游戏”页面仅需 0.7 秒，而非 2.9 秒；工具运行进程启动需 0.08 秒，而非 1.5 秒。Flet 打包器在 macOS 上拒绝 `--onedir`；`scripts/pack_app.py` 会在 Flet 自身的 `--onefile` 之后将其传给 PyInstaller，后面的标志优先。包内的 Python 进程从不向程序坞完成登记：作为前台应用时，它会显示第二个图标，持续弹跳直到应用退出。打包器会设置 `LSBackgroundOnly`，位置为其 `Info.plist`，因此只有查看器具有程序坞图标，与单文件引导程序下相同。

| 部分 | 大小 | 减小体积的方法 |
| --- | --- | --- |
| Flet 查看器（`scripts/build_client.py`) | 31 MB，macOS 压缩包为 9.4 MB | 不包含可选 Flet 扩展（视频、地图、相机、WebView 等；应用只绘制核心控件）；macOS 仅包含构建机器的架构，分离 Dart 符号（`--split-debug-info`），并在 macOS 上使用 xz 压缩包 |
| Unicorn（`scripts/build_unicorn.py`) | 3 MB | 从已安装版本的源码构建，仅启用 ARM 和 ARM64 引擎；wheel 中的库包含所有 CPU 家族（16 MB） |
| PKHeX 辅助程序（`services/pkhex`) | 16 MB | 完全裁剪：移除辅助程序不可达的框架与 PKHeX.Core 代码；关闭 EventSource、调试器和热重载支持 |
| Python | 8 MB 的模块 | 打包器排除 Flet 的 Web 服务器、身份验证和图像附加依赖（`flet_web`、FastAPI、Uvicorn、Pydantic、httpx、Pillow）、pytest、Pygments，以及 rich 的语法、Markdown 和回溯模块、`multiprocessing`, `_pydecimal`，并在 macOS 上排除东亚字符编解码器；macOS 库会去除本地符号（`strip -x`) |

裁剪会关闭 .NET 中基于反射的 JSON；辅助程序回复需要此功能，因此项目会重新启用它（`JsonSerializerIsReflectionEnabledByDefault`）。否则每条命令都会返回 `JsonTypeInfo metadata for type 'System.String' was not provided`。第三世代活动表是 PKHeX.Core 内部成员，通过名称读取；一个 `DynamicDependency` 特性会确保其在裁剪后保留。

macOS 打包器以 xz 格式写入查看器，但沿用 Flet 的文件名 `flet-macos.tar.gz`（9.4 MB，而不是 13.6 MB）；flet_desktop 1.0.2 使用 `r:gz` 模式打开该文件，因此冻结应用会向 flet_desktop 提供一个 `tarfile`，其 `open` 可自动检测压缩格式（`gui/flet_client.py`）。可执行文件和 PKHeX 辅助程序绝不会去除符号：两者都在 Mach-O 镜像之后附带归档。Flet 的 macOS 项目每次构建都会运行 `dart run rive_native:setup`；移除 Rive 后该步骤会失败，因此客户端构建将其替换为 `exit 0`.

查看器对每个构建只解包一次，位置为 `~/.flet/client/flet-desktop-full--`，而 Flet 从不移除较旧构建的文件夹。每次启动时，冻结应用都会使用 `pokeldn-drop` 标记自己的文件夹，并移除带有该标记的其他文件夹；对于较早的 macOS 构建，也会识别 `pokeldn.app` (`gui/flet_client.py`）；其他 Flet 应用的查看器会保留。

Flet 1.0.2 的打包器会重新签名 macOS 查看器，却不保留其已有的权限声明。位于 `scripts/pack_flet.py` 的打包封装会在查看器元数据变更后签名时保留这些权限。冻结检查会从内嵌查看器读取签名封存的 `com.apple.security.files.user-selected.read-write` 权限；没有它，选择 `prod.keys` 就会引发 `ENTITLEMENT_NOT_FOUND`.

Linux 引导程序会将 `LD_LIBRARY_PATH` 设置为包目录，其中带有构建机器的 `libstdc++.so.6`（Ubuntu 22.04）。该库优先加载后，会导致 Fedora 44 的 Mesa 没有 EGL 客户端扩展，Flet 查看器随即在 libepoxy 中中止（`No provider of eglGetPlatformDisplayEXT`). `pokeldn/app/paths.py` 会为应用启动的每个程序恢复用户的 `LD_LIBRARY_PATH`，并将 `FLET_LINUX_DISTRO` 设置为内置查看器的构建版本；否则 Flet 会按 glibc 选择查看器，并下载包内未附带的版本。冻结检查在 Linux 上会断言这两项。

应用内置 Unicorn，用于“离线检查”。它按名称加载架构模块，因此打包器会收集其子模块，并将仅支持 ARM 的库按 wheel 中的文件名直接加入 `unicorn/lib`；冻结检查会断言包含 ARM64 且不包含 x86。PyInstaller 的 Windows 引导程序链接了控制流保护（DllCharacteristics `0xC160`），而 Unicorn 会以 `0xC0000409` 终止启用 CFG 的进程，发生于首次调用 `uc_mem_map` ([unicorn#2281](https://github.com/unicorn-engine/unicorn/issues/2281)）；即使使用 64 MiB 线程栈也无济于事。打包器会清除 `GUARD_CF`，位于 `pokeldn.exe`，得到 `0x8160`，即 `python.exe` 的标志。冻结检查会在每个平台上使用 Unicorn 运行一个载荷。Unicorn 在这里会自行引发并处理访问冲突：冻结检查中切勿启用 `faulthandler`，否则会将该异常记录到 stderr，导致检查失败。
