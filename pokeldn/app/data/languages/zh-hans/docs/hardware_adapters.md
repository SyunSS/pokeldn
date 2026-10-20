---
title: Wi-Fi 适配器
parent: Hardware and setup
nav_order: 3
---

# Wi-Fi 适配器

Linux 主机端可以以 root 身份直接驱动支持 AP 模式的 Wi-Fi 网卡，以替代 [ESP32 无线模块](hardware_esp32.md)。这是一条旧版实现路径，不再继续开发。

| 症状 | 原因 |
| --- | --- |
| 启动 AP 时出现虚拟机管理程序所见的 USB 断开连接 | USB 模式切换（见下文） |
| 主机端无响应 | `accept_decrypted_ccmp` 未设置 |
| `failed to get tx report from firmware`，位于 `dmesg` | 主机端自身的清理流程 |

## Windows 通过 ldnrs 使用 USB Wi-Fi

Windows 可以通过 [ldnrs 0.0.3](https://github.com/unlimitedcoder2/ldnrs/releases/tag/0.0.3) 使用外置 USB Wi-Fi 适配器。请单独安装 ldnrs，完成其适配器向导，并保持其守护进程运行。在 pokeldn 中打开“**插件**”，然后选择“**USB Wi-Fi（Windows，ldnrs）**”，该选项位于“**无线模块**”下。Switch 密钥仍从 pokeldn 的“设置”中获取。

ldnrs 向导会将选定的适配器绑定到 WinUSB，并下载所需的 Linux 驱动固件。WinUSB 接管该适配器期间，它将不再提供普通的 Windows Wi-Fi 功能。请通过另一条连接访问互联网。若要让该适配器重新用于 Windows 网络，请在设备管理器中恢复其原始驱动。兼容性取决于 ldnrs 中该适配器的驱动和固件；下文的 Linux 网卡测试结果不能证明其 Windows 兼容性。

在 PowerShell 中，运行任何游戏的常规启动器之前，先选择后端：

```
$env:POKELDN_RADIO = 'ldnrs:'
python bin/swsh_gift_host.py --keys C:\Switch\prod.keys --species 25 --level 25
```

参数为空时选择本地管道 `\\.\pipe\ldnd`。冒号后可以指定其他本地管道。守护进程通过该本地管道接收选定的密钥。它负责无线模块、LDN 关联和加密；pokeldn 通过其现有的用户空间 IPv4 协议栈传输以太网帧。扫描、加入、主机端创建会话及广播信息更新均使用 [守护进程协议 7](https://github.com/unlimitedcoder2/ldnrs/blob/0.0.3/docs/daemon-protocol.md)。如果守护进程缺失、适配器尚未就绪或协议版本不同，操作将失败并报错。

关联操作在守护进程中允许耗时 70 秒，在启动器中至少允许耗时 90 秒：上游的 [RTL8822BU 测试结果](https://github.com/unlimitedcoder2/ldnrs/blob/0.0.3/clients/python/ldnd/compat.py) 表明，两次驱动重新配置各需约 14.5 秒。关联完成后才开始游戏握手。每个守护进程一次只能承载一个会话。会话结束时，pokeldn 会关闭其原始通道和网络，但会让外部守护进程继续运行。抓包中仍会保留游戏 UDP 流量；ESP32 计数器和内置库的 Wi-Fi 管理钩子不适用于此后端。

离线检查会将扫描、加入和主机端创建会话请求与 ldnrs 0.0.3 的 Python 客户端生成的测试向量进行比较，并通过其原始以太网通道与脚本模拟的守护进程交换 UDP 数据。目前尚未使用 Windows 适配器和零售版主机测试此后端。

## 已测试的网卡

| 型号 | 类型 | 驱动 | 在已测试主机端上的结果 |
| --- | --- | --- | --- |
| TP-Link Archer T3U（`2357:012d`) | 外置 USB | `rtw88_8822bu` | 可靠；作为参考适配器 |
| ALFA AWUS036ACHM | 外置 USB | `mt76x0u` | 可靠 |
| Realtek RTL8821CE | 内置 PCIe | `rtw88_8821ce` | 可靠 |
| AMD RZ616 | 内置 M.2 | `mt7921e` | 速度约为一半，有时会在退出前死锁 |
| MT7601U | 外置 USB | `mt7601u` | 系统自带驱动不支持 AP 模式；需要固定版本的 `mt7601u-ap` DKMS 模块（[树莓派主机端](hardware_raspberry_pi.md)) |
| Intel AX200 | 内置 M.2 | `iwlwifi` | 失败：无法分配 IP |
| Atheros AR9271 | 外置 USB | `ath9k_htc` | 失败：通常无法分配 IP |

## 主机端模式

`--skip-encryption` 会跳过 LDN 的 Python CCMP 处理步骤，使 mac80211 或硬件只应用一次 CCMP；空中传输的流量仍保持加密。Archer T3U（`skip_encryption = true`，位于 `config/host.toml`）和 ALFA AWUS036ACHM 需要此设置。

`--accept-decrypted-ccmp` 适用于在硬件解密后的明文两侧保留 CCMP 头和 MIC 的监听模式驱动，Archer T3U 的 `rtw88_8822bu` 就是如此；该设置会在将明文转发给 `ldn-tap` 之前去除 MIC。ALFA 提供的是标准帧，因此应关闭此设置。

| 适配器 | 主机端配置 |
| --- | --- |
| TP-Link Archer T3U | 仓库跟踪的 `config/host.toml` 配置方案；不设置 Wi-Fi 标志 |
| ALFA AWUS036ACHM | `--phy phyN --skip-encryption --no-accept-decrypted-ccmp` |

`phy = "auto"` 仅会解析唯一一个 `rtw88_8822bu` USB `2357:012d` 设备，未找到或找到多个时均会失败。显式指定的 `--phy phyN` 始终优先；由于每次重新枚举时编号都会变化，仅建议在临时调试时使用。启动时会输出检测到的配置方案、发送与接收模式，并在标志与已验证的配置方案不一致时发出警告。

## TP-Link Archer T3U

`rtw88_8822bu` 自内核 6.11 起已进入主线，并列出了此 USB ID。请确认内核已将其绑定：

```
modinfo rtw88_8822bu | grep -i 2357
lsusb | grep -i 2357
iw dev
```

### 不让 NetworkManager 接管适配器本身

NetworkManager 会接管适配器热插拔后出现的接口（`wlx...`）并启动后台扫描；接口出现后不久，信道切换就会使无线模块停止工作（实测为 11 秒）：

```
rtw88_8822bu 3-1:1.0: write register 0x81c failed with -71
usb 3-1: USB disconnect, device number 2
```

排除该适配器和 LDN 接口：

```
# /etc/NetworkManager/conf.d/zz-ldn-unmanaged.conf
[keyfile]
unmanaged-devices=interface-name:ldnclient;interface-name:ldn;interface-name:ldn-mon;interface-name:ldn-tap;interface-name:wlx*;interface-name:wlan*
```

该文件必须排在最后（`zz-`）：某些发行版附带了排序更靠后、设置了 `unmanaged-devices=none` 的文件。重新加载 NetworkManager；`nmcli device status` 必须显示该适配器为 `unmanaged`，而 `NetworkManager --print-config | grep unmanaged` 必须显示该列表。如果其中不包含 `ldnclient`，NetworkManager 就会接管加入操作创建的接口，并让 wpa_supplicant 使用它，导致加入操作失败并报错 `[Errno 114] Match already configured`.

### 禁用驱动的 USB 3 模式切换

`rtw88_usb` 默认值为 `switch_usb_mode=Y`，这会在驱动加载后将适配器重新枚举为 USB 3 模式。对该设备进行直通的虚拟机管理程序会检测到断开连接，LDN 接口随之消失，主机端在创建会话初期便终止（实测约 1 秒），此前没有任何驱动错误：

```
RuntimeError: 802.11 beacon injector stopped: [Errno 100] Network is down
```

该参数自身的说明指出，USB 3 模式可能会干扰 LDN 使用的 2.4 GHz 频段。

```
# /etc/modprobe.d/rtw88-ldn.conf
options rtw88_usb switch_usb_mode=N
options rtw88_core disable_lps_deep=Y
```

之后请拔插适配器：在断电之前，它会一直保持 USB 3 模式。随后它只会以高速模式连接一次（启用切换时，会枚举两次，先是高速，再是 SuperSpeed）：

```
cat /sys/bus/usb/devices/*/speed     # 480, not 5000
cat /sys/bus/usb/devices/*/version   # 2.10, not 3.00
```

### 每次运行前先关闭适配器接口

处于启用状态的受管接口会占用无线模块的信道。`transport.free_radio()` 会将其关闭；仅执行 `tools/ldn/ldn_scan.py` 则不会：

```
OSError: [Errno 16] Device or resource busy
```

```
sudo ip link set wlxXXXXXXXXXXXX down
```

如果终止脚本重新启用了基础接口，下次启动就会因该错误而失败。任何为了内核 `iw scan` 而启用该接口的操作，都必须在移交控制权前再次将其关闭。

### 验证

`./scripts/preflight_pi.sh` 可在任何 Linux 主机端运行。
