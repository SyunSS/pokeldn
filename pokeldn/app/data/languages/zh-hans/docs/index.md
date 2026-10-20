---
title: pokeldn
nav_order: 1
---

# pokeldn

pokeldn 实现了 Nintendo Switch 本地无线通信（LDN），通过 ESP32 开发板作为无线收发器，与零售版 Switch 硬件上运行的宝可梦游戏通信：电脑或 Android 手机通过 USB 串口连接，iPhone 则通过蓝牙连接。这些页面记录了所涉及的协议，并附有反编译引用、反汇编地址和硬件测量结果。

请先阅读[应用设置](gui.md)或[命令行用法](usage.md). [代码组织](architecture.md)介绍了共享模块和测试。

## 支持的游戏

七款游戏均在零售版硬件上运行，均使用相同的 LDN 和 Pia 层：

|  | FRLG | LGPE | SwSh | BDSP | PLA | SV | PLZA |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 交换 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 神秘礼物 | ✓ | ∅ | ✓ | ∅ | ∅ | ∅ | ∅ |
| 活动宝可梦 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 连接对战 | ✓ | ✗ | ✗ | ✗ | ∅ | ✗ | ✗ |
| 在主机上执行代码、读取和写入存档 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |

✓ 可在零售版主机上使用 · ✗ 尚未实现 · ∅ 游戏不支持通过本地无线使用此功能 FRLG 火红／叶绿 · LGPE Let's Go! 皮卡丘／伊布 · SwSh 剑／盾 · BDSP 晶灿钻石／明亮珍珠 · PLA 传说 阿尔宙斯 · SV 朱／紫 · PLZA 传说 Z-A

火红和叶绿以原始 GBA ROM 的形式在 Switch 上的模拟器内运行，因此 ROM 自身的 GBA 连接协议叠加在主机的 LDN 和 Pia 之上。其余六款游戏直接在 Pia 上运行自身代码：晶灿钻石和明亮珍珠使用 Unity/IL2CPP；剑、盾和 Let's Go 使用 C++，并通过以下模块承载协议缓冲区：`gflnet3`；传说 阿尔宙斯、朱、紫和传说 Z-A 则使用静态链接 Pia 的 C++。

## 章节

| 章节 | 内容 |
| --- | --- |
| [无线层](ldn.md) | LDN 和 Pia：广播通告、关联、各版本的数据包格式、会话密钥派生。与具体游戏无关。 |
| [Switch 游戏逆向工程](switch_re.md) | 阅读零售版游戏自身的代码：原位提取 NCA/RomFS、IL2CPP 元数据、C++ RTTI。介绍通用方法。 |
| [火红和叶绿](frlg.md) | GBA 连接、神秘礼物、在主机上执行代码、随机数生成器以及两款卡带。 |
| [晶灿钻石和明亮珍珠](bdsp.md) | Pia 5.27–5.45、联盟交谊厅以及交换流程。 |
| [剑和盾](swsh.md) | Pia 4、同步框架、交换、主机端与加入端的极巨团体战、极巨大冒险，以及神秘礼物的本地通信分支。 |
| [Let's Go! 皮卡丘和伊布](lgpe.md) | Pia 3、连接密码以及交换流程。 |
| [传说 阿尔宙斯](pla.md) | Pia 头部版本 11、交换流程以及主机端组装的记录。 |
| [朱和紫](sv.md) | Pia 头部版本 11、可靠流、主机端执行的交换、主机端与加入端的太晶团体战，以及以加入端身份参与集友圈。 |
| [传说 Z-A](za.md) | Pia 头部版本 16、游戏的二十种交换消息，以及主机端与加入端的交换。 |
| [模拟神秘礼物](gift_simulated.md) | 由主机端向五款不支持本地神秘礼物的游戏交换官方礼物宝可梦，并针对接收方存档生成。 |
| [命令行用法](usage.md) | 源码环境设置和各游戏的命令。 |
| [桌面应用](gui.md) | 设置、宝可梦银行、控制器、更新和构建；Android 和 iOS 上也使用同一应用。 |
| [代码组织](architecture.md) | 共享模块、宝可梦准备与验证。 |
| [硬件与设置](hardware.md) | ESP32 无线收发器、Switch 密钥，以及旧版 Linux Wi-Fi 网卡。 |
| [代码签名政策](code_signing.md) | Windows 发行版签署哪些内容、团队角色以及隐私政策。 |

## 致谢

基于[kinnay 的 LDN 库](https://github.com/kinnay/LDN)和[NintendoClients 维基](https://github.com/kinnay/NintendoClients/wiki)构建，并参考了[pret/pokefirered](https://github.com/pret/pokefirered)，即火红／叶绿的反编译项目。
