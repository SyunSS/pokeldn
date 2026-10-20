---
title: 控制器开发板
parent: Hardware and setup
nav_order: 5
---

# 控制器开发板

控制器开发板可以是 ESP32-S3，由 Switch 通过 USB-C 端口识别为有线控制器；也可以是经典 ESP32，通过经典蓝牙与其配对为 Pro 控制器。主机端可操作主机按键，并加载由开发板按自身时钟执行的宏。固件：`firmware/pad`，主机端：`pokeldn.pad`，应用页面：[控制器](gui.md#the-controller)，命令行：`tools/switch/pad.py`.

## 可使用哪些开发板

| 芯片 | 控制器 | 原因 |
| --- | --- | --- |
| ESP32-S3 | 通过 USB 连接的有线控制器 | 其 USB-OTG 模块可以实现任意 USB 设备 |
| 经典 ESP32 | 通过经典蓝牙连接的无线 Pro 控制器；主机端连接其 USB 转串口端口 | 本身没有 USB 设备功能；但具有经典蓝牙，即 Pro 控制器采用的传输方式 |
| ESP32-C3、ESP32-C6 | 不支持 | USB Serial/JTAG 功能固定，且其蓝牙仅支持 LE |

## USB 侧

开发板会枚举为 HORI 宝可拳控制器，`0f0d:0092`，具有一个 HID 接口，包含一个中断 IN 端点和一个中断 OUT 端点。Switch 会将此 ID 识别为普通 HID 手柄，无需 Pro 控制器握手。在固件 23.0.1 的零售版 Switch Lite 上，无需更改任何设置，即可在 HOME 菜单中枚举该设备，并根据开发板上报的报告移动光标。

输入报告为 8 字节，只要 USB 主机端准备好接收，就每毫秒发送一次：

| 偏移量 | 大小 | 字段 |
| --- | --- | --- |
| 0 | 2 | 按键，小端序 |
| 2 | 1 | 方向帽：0 为上，然后顺时针排列至 7 为左上；8 为居中 |
| 3 | 4 | LX、LY、RX、RY；128 为居中，0 为左或上 |
| 7 | 1 | 厂商自定义字节；固件会在此放入蓝牙状态 |

| 位 | 按键 | 位 | 按键 |
| --- | --- | --- | --- |
| 0x0001 | Y | 0x0100 | 减号键 |
| 0x0002 | B | 0x0200 | 加号键 |
| 0x0004 | A | 0x0400 | 按下左摇杆 |
| 0x0008 | X | 0x0800 | 按下右摇杆 |
| 0x0010 | L | 0x1000 | HOME |
| 0x0020 | R | 0x2000 | 截图键 |
| 0x0040 | ZL |  |  |
| 0x0080 | ZR |  |  |

厂商自定义字节：1 表示已同步，2 表示正在广播，3 表示已连接；`0x80 | step` 表示该步骤失败。

## 接线

使用 USB-C 转 USB-C 线缆连接开发板和主机。主机提供电源并充当 USB 主机端；开发板从中取电。当 USB 主机端已配置该设备时，XIAO ESP32S3 的 LED（GPIO21）会亮起。

Switch Lite 通过 C 转 C 线缆连接 Mac 时，自身作为电源，不会枚举任何设备。若通过 Mac 的 USB-A 端口连接，并打开“通过 USB 连接复制到电脑”，则会枚举为 `057e:201d`，包含一个 MTP 接口、一个只读的“相册”存储区以及十项只读操作（`0x1001`-`0x100a`).

## 蓝牙侧

开发板以 `POKELDN-PAD` 为名称进行广播，仅提供一个服务：`7a1e0001-5d2c-4c3e-9f4b-504f4b454c44`:

| 特征 | 访问方式 | 内容 |
| --- | --- | --- |
| `...0002` | 写入、无响应写入 | 8 字节输入报告，原样发送；宏执行期间会被忽略 |
| `...0003` | 读取 | 状态，见下文 |
| `...0004` | 写入 | 命令，见下文 |

状态采用小端序：挂载状态 u8、报告写入次数 u32、播放状态 u8、已完成循环次数 u32、条目索引 u16、条目数量 u16、文本形式的固件版本，随后是 NUL、复位原因 u8（`esp_reset_reason`）、上次启动到达的阶段 u8，以及通电以来的启动次数 u16。1.0.0 之前的固件仅发送前五个字节。

| 命令 | 正文 | 效果 |
| --- | --- | --- |
| `0x10` 加载 | 数量 u16、循环起点 u16、循环次数 u32 | 停止宏并设置程序大小；循环次数为 0 时持续执行，直到被停止 |
| `0x11` 数据 | 首个条目索引 u16，随后为各条目 | 每个条目由一份报告和一个以毫秒计的保持时长 u16 组成，共 10 字节 |
| `0x12` 播放 |  | 启动程序 |
| `0x13` 停止 |  | 停止程序并松开所有按键 |
| `0xB0` 下载 |  | 将芯片重启至 ROM 加载器 |

程序最多容纳 8192 个条目。循环起点之前的条目仅执行一次，其余条目重复执行。播放器使用 `vTaskDelayUntil` 按 1 kHz 节拍等待，因此各段保持时长可累加而不产生漂移：在 Mac 的 USB 侧测试中，一个循环 10 次的宏每轮都精确耗时 500 毫秒。

在 macOS 上通过 bleak 执行无响应写入时，如果 CoreBluetooth 队列已满，写入就会丢失，而 bleak 从不读取 `canSendWriteWithoutResponse`：连续发送 300 份中性报告时，开发板写入计数器只记录到 67 次；间隔为 20 毫秒或更长时，40 份全部到达。`pokeldn.pad.link` 会在每次写入报告前等待该标志；如果该标志不存在，或持续一秒为假，则改用有响应写入。

| 报告写入方式 | 连续发送时每份报告耗时 | 到达开发板的数量 |
| --- | --- | --- |
| 无响应，不限速 | 0.1 毫秒 | 300 份中的 67 份 |
| 有响应 | 60 毫秒，在连接的前 25 秒内保持稳定 | 300 份中的 300 份 |
| 无响应，通过标志控制发送节奏 | 2.4 毫秒 | 200 份中的 200 份 |

固件 1.2.0 会在连接时请求 15 到 30 毫秒的连接间隔；但有响应写入仍耗时 63 毫秒，尚不清楚 macOS 是否批准了该请求。

断开连接会将报告恢复为中性状态，因此主机端消失后不会留下任何按住的按键；正在执行的宏仍会继续。

## 串口侧

经典 ESP32 始终连接电脑的 USB：UART0 以 921600 波特率双向传输帧（`firmware/pad/main/uart_link.c`, `pokeldn/pad/serial_link.py`），且控制台输出已关闭。关闭控制台后，没有其他配置会将 UART0 路由到 GPIO1 和 GPIO3，因此固件会自行设置这些引脚；否则开发板不会回应任何请求。

```
A5 5A | length u16 (type and payload) | type u8 | payload | sum of type and payload mod 256
```

| 类型 | 方向 | 载荷 |
| --- | --- | --- |
| `0x01` | 发往开发板 | 8 字节报告；通过以下消息回应：`0x81` |
| `0x02` | 发往开发板 | 无；通过以下消息回应：`0x82`，其中携带状态记录 |
| `0x03` | 发往开发板 | 命令，与控制特征中的命令相同；通过以下消息回应：`0x81` |
| `0x81` | 发往主机端 | 结果 i8：0，-1 表示长度错误，-2 表示拒绝 |
| `0x82` | 发往主机端 | 状态记录；mounted 表示 Switch 已设置玩家指示灯 |

主机端打开串口时会将 DTR 和 RTS 置低。但在 macOS 上，DevKit 的 CP2102 仍会在打开端口时重启开发板，启动期间发送的请求会丢失；因此主机端会持续重试状态请求，最长 3 秒。服务会先逐个尝试所有并非 S3 原生 USB 的 USB 串口，再扫描蓝牙 LE。请让一个进程持续持有该端口：每次重新打开都会重启开发板并断开其蓝牙连接。

## 经典蓝牙侧

`firmware/pad/main/bt_esp32.c` 会注册一个 Bluedroid HID 设备：170 字节的 Pro 控制器报告描述符、服务“Wireless Gamepad”、提供方“Nintendo”、子类 0x08、设备类别 0x002508、名称“Pro Controller”、无输入无输出的 SSP，并关闭调制解调器睡眠。它按 ID 回应 0x01 子命令：0x02 为设备信息（固件 4.00、类型 0x03、其蓝牙地址），0x10 为 SPI 读取，0x03 为报告模式，0x04 为扳机时间，0x21 为 MCU 配置，其余命令返回普通 ACK；0x30（玩家指示灯）标记该控制器已被接管。回复会优先于任何 0x30 报告发出。

从连接建立开始，按键或摇杆发生变化时立即发送 0x30 报告，否则每 100 毫秒发送一次；测试中，如果开发板不发送此报告，Switch Lite 虽然会连接，却始终不开始握手。连接建立后，开发板等待 1 秒；切换到 sniff 模式后等待 250 毫秒；发送因拥塞被拒绝（原因 8）后等待 45 毫秒。这些值来自 friendmaker 的 Switch Lite 配置（`classic_bt_controller_transport.cpp`, `SWITCH_LITE`).

| 0x30 发送节奏 | 零售版 Switch Lite |
| --- | --- |
| 在 0x03 模式切换后每 15 毫秒发送一次 | 握手完成至玩家指示灯阶段，随后 Bluedroid 切换 sniff 模式，发送因拥塞失败，Switch 在指示灯亮起后 2 到 20 秒断开连接（HCI 0x13）；没有任何按键输入到达界面 |
| 变化时发送，否则每 100 毫秒发送，并使用上述等待时间 | 连接保持稳定，501 次发送无一失败；按键可在“更改握法／顺序”和“控制器”菜单中移动光标 |

Switch 的握手顺序为：0x02、0x08、0x10（地址 0x6000 和 0x6050）、0x03（0x30）、0x04、0x10（地址 0x6080、0x6098、0x8010、0x603D、0x6020）、0x40、0x30（0）、0x48、0x21、0x30（玩家 1）。

已绑定的开发板会在启动时重新连接其 Switch。刷入合并镜像会覆盖 NVS 分区，连同绑定信息一起清除：请从“更改握法／顺序”重新配对。

`pro_report.c` 会将共用报告映射到 Pro 控制器的各字节（dekuNukem 的 `bluetooth_hid_notes.md`）：摇杆静止时为 0x800，向任一方向的偏移量为 0x700，与其在 0x603D 返回的出厂校准一致；序列号和用户校准区域返回空白闪存值（0xFF）。`tests/test_pad_pro.py` 会在主机端编译该实现，并检查每个按键位及校准数据。

## 宏

宏是扩展名为以下值的 JSON 文件：`.pokemacro` (`pokeldn.pad.macro`):

```
{
  "format": "pokeldn-macro", "version": 1,
  "name": "Soft reset", "description": "", "author": "", "game": "",
  "press_ms": 100, "gap_ms": 150,
  "setup": [{"press": "HOME"}, {"wait": 1000}],
  "loop": [
    {"press": ["A", "B"], "ms": 500, "after": 2000, "note": "skip the intro"},
    {"repeat": 3, "steps": [{"press": "A"}]},
    {"press": [], "left": [0, 1], "ms": 300},
    {"wait": 5000}
  ],
  "loops": 0
}
```

| 字段 | 含义 |
| --- | --- |
| `press_ms`, `gap_ms` | 当步骤未指定时，该步骤保持输入的时长及之后的暂停时长 |
| `setup` | 仅执行一次的步骤 |
| `loop` | 重复执行的步骤，共 `loops` 次；0 表示持续重复，直到停止 |
| 按压步骤 | `press`：单个按键名，或同时按住的按键列表（`A B X Y L R ZL ZR PLUS MINUS LSTICK RSTICK HOME CAPTURE UP DOWN LEFT RIGHT UPLEFT UPRIGHT DOWNLEFT DOWNRIGHT`); `left` 和 `right`：摇杆 `[x, y]`，取值 -1 到 1，向上为正；`ms` 为保持时长；`after` 为暂停时长；`note` |
| 等待步骤 | `wait`：松开全部按键并等待的毫秒数 |
| 重复步骤 | `repeat`：将 `steps` 重复 1 到 10000 次，最多嵌套 8 层 |

编译器会展开重复步骤，合并保持相同报告的相邻条目，并拆分超过 65535 毫秒的保持时长。展开后超过 8192 个条目的宏会被拒绝。`after: 0` 位于两次相同按压之间时，会将它们合并为一次连续保持。如果文件的 `version` 比读取程序支持的版本更新，该文件也会被拒绝。

## 主机端

`pokeldn.pad.service` 会维持蓝牙连接，并通过 `127.0.0.1:47800`: `status`, `connect`, `send`, `tap`, `play`, `stop`, `download`, `scan`, `disconnect` 每行接收一个 JSON 请求。应用会将其作为自身子进程启动；`tools/switch/pad.py` 会在没有运行实例时，在独立进程中启动它。

在 macOS 上，如果开发板在连接仍建立时断电（从 Switch 拔下），CoreBluetooth 可能让读取或写入一直挂起而不报错。服务会在限定时间内回应每个请求（`status` 为 5 秒，`play` 为 120 秒，`scan` 为 20 秒，其余为 40 秒，包括连接过程）。超时后，服务会关闭连接，让开发板重新广播，并回复错误。应用客户端会在 150 秒后停止等待。

```
./.venv/bin/python tools/switch/pad.py A
./.venv/bin/python tools/switch/pad.py HOME wait:1 'RIGHT*3' A
./.venv/bin/python tools/switch/pad.py hold:B:2 stick:L:-1:0:0.5
./.venv/bin/python tools/switch/pad.py --play soft_reset.pokemacro
./.venv/bin/python tools/switch/pad.py --stop --status
```

如果负责该进程的应用没有声明 `NSBluetoothAlwaysUsageDescription`，macOS 就会中止尝试打开蓝牙的进程；在其他应用内嵌的终端中会出现这种情况。`pad.py --make-app PATH` 会生成一个运行该服务的小型应用；请先用 `open` 打开一次并允许蓝牙访问，之后的 `pad.py` 调用以及源码检出目录中的应用都会使用它。

## 再次刷写

手柄占用了 USB 端口，因此 esptool 无法通过复位让它进入加载器。下载命令、“开发板”页面的安装操作以及 `pad.py --download` 会通过蓝牙完成这一过程；插入开发板时按住 BOOT，则无需固件配合。

-
-
-
-

无线模块切换到控制器、以及控制器切换回无线模块两个方向，都已通过以下方式完成刷写：`python -m gui.board --kind pad|radio`. `--from-loader` 可刷写已由下载命令置于加载器中的开发板：与控制器固件相同，它会等待、以不复位方式连接，再通过看门狗启动镜像。

注意事项：FreeRTOS 默认 100 Hz 下，USB 循环的延迟会变为零个节拍，导致 NimBLE 无法获得运行机会；因此固件按 1000 Hz 构建。

## 构建

```
. scratchpad/esp/env.sh
cd firmware/pad && idf.py -B BUILD_DIR -D SDKCONFIG=SDKCONFIG_PATH build
```

TinyUSB 来自组件管理器（`espressif/esp_tinyusb` 2.4.0）。发布流程会在无线模块镜像旁构建 `pokeldn-pad-s3.bin`。

## 尚未解决的问题

- Switch 2 是否能与经典 ESP32 固件配对；目前仅测试过 Switch Lite。
- Switch 2 是否同样接受 HORI ID；目前仅测试过 Switch Lite。
