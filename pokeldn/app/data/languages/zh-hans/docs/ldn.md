---
title: 无线层
nav_order: 2
has_children: true
---

# 无线层

Switch 通过**LDN**（任天堂的本地无线通信）与附近主机通信，并在其上使用[Pia](pia.md)（任天堂的点对点会话中间件）。两者均为系统库；各游戏的区别在于 Pia 版本和载荷。

## 两个秘密值

LDN 口令用于验证 802.11 关联：长度为 16–64 字节（由`nn::pia::local::LdnBackgroundProcessJob`检查），按原值使用；晶灿钻石将 ASCII 字符串直接传给`nn::ldn::CreateNetwork`。16 字节的 Pia 游戏密钥用于派生会话密钥，以加密每个数据报。

| 游戏 | LDN 口令 | Pia 游戏密钥 |
| --- | --- | --- |
| 晶灿钻石／明亮珍珠 | `WirelessStrongCryptoKey2021`（27 字节，原始值） | 派生自`cryptoKeyDataSeed`；参见[BDSP](bdsp_session.md) |
| 剑／盾 | `W3GoSMEn7RIIUQ89rzqBHGhGferRNb7K18ZBq2aNuj8Us9RO9Q9JYyGOZlLy8MYL`（64 字节，原始值） | `p1frXqxmeCZWFv0X` |

朱／紫和传说 阿尔宙斯使用剑／盾的口令及游戏密钥（[朱和紫](sv.md), [传说 阿尔宙斯](pla.md)）；NintendoClients 维基中为阿尔宙斯写出的`HGHG`是错误拼写。

## 发现

读取广播通告只需要`prod.keys`: `tools/ldn/ldn_scan.py`会显示任意会话的`local_communication_id`, `scene_id`、版本、信道、接纳策略、参与者数量和应用数据。游戏只能看到与自身 LDN 协议相同的广播通告（1：使用以下密钥的 AES-CTR：`master_key_00`；3：使用以下密钥的 AES-GCM：`master_key_12`），因此主机端会采用与游戏相同的协议（`HostTransport(protocol=...)`).

| 游戏 | 协议 | 广播通告格式 |
| --- | --- | --- |
| GBA 应用（火红、叶绿），通信 ID 为`0x01006fa0233f8000` | 3 | 3，AES-GCM |
| 剑的神秘礼物界面，通信 ID 为`0x0100abf008968000` | 1 | 2，AES-CTR |
| 传说 阿尔宙斯本地交换，通信 ID 为`0x01001f5010dfa000` | 1 | 4 |

作为主机端的主机以 11 Mbit/s DSSS 发送信标，并以 HT MCS 3、20 MHz（OFDM）发送广播通告动作帧；朱的连接交换搜索和剑的神秘礼物界面均如此。仅支持 DSSS 的接收器会漏掉动作帧。

## 广播通告的应用数据

来自明亮珍珠的 Pia 5 布局：

```
+0x00  4  network id                     random per session
+0x04  4  CRC32 of the user password     0 when the room has no password
+0x08  1  system communication version
+0x09  1  header size                    16
+0x0a  2  padding
+0x0c  4  session parameter              random per session; seeds the Pia session key
+0x10     application data
```

抓包只能用其自身会话的广播通告解密；使用其他会话的广播通告会静默失败。

Pia 6.16 到 6.41 使用系统属性块，并从 SSID 派生会话密钥和网络 ID：

```
+0x00  2  system property data size      0x5C
+0x02  1  system communication version   21 for 6.16-6.30, 22 for 6.39-6.41
+0x03  2  application communication version
+0x05  16 user password
+0x15  1  is player limit enabled
+0x16  1  number of players
+0x17  4  player name size
+0x1b  1  player name encoding           1 = UTF-8, 2 = UTF-16
+0x1c  64 player name
+0x5c     application data
```

启用传输加密时，用户密码会用 0xFE 填充到十六字节，然后使用游戏密钥进行 AES-128-GCM 原位加密，丢弃认证标签，IV 为`key[1] key[8] key[7] key[2]`，再由块构造器复制进去（阿尔宙斯 1.1.1 的`0x6fac70`; [设置函数](pla.md#the-link-code-in-the-advertisement)）。单个 GCM 块相当于与由密钥确定的固定密钥流进行异或：仅凭游戏密钥即可读出密码。

## 为模拟器充当主机端

ldn_mitm 模式下，模拟器通过端口 11452 建立关联，然后通过局域网运行 Pia：不需要无线收发器、不需要`prod.keys`，也不需要 root 权限。`pokeldn/ldn/ldn_mitm.py`用于加入；`ldn_mitm_host.py`通过以下组件作为主机端运行：`IpHostTransport`，其中的`NEEDS_RADIO = False`选择`NullBeaconInjector`.

```
UDP  console -> host:11452   Scan          header only, unicast and broadcast
UDP  host    -> console      ScanResp      NetworkInfo, 0x480
TCP  console -> host:11452   Connect       NodeInfo, 0x40
TCP  host    -> console      SyncNetwork   NetworkInfo with the console seated, held open
```

`nn::ldn::NetworkInfo`，共 0x480 字节：

```
+0x000  NetworkId          IntentId 0x10 (u64 localCommunicationId, u16, u16 sceneId, u32) then SessionId 0x10
+0x020  CommonNetworkInfo  MAC 6, Ssid 0x22 (length byte then 0x21), s16 channel, u8 linkLevel, u8 networkType, u32
+0x050  LdnNetworkInfo     SecurityParameter 0x10, u16 securityMode, u8 acceptPolicy, ...
+0x066                     u8 nodeCountMax, u8 nodeCount
+0x068                     NodeInfo[8], 0x40 each: u32 IPv4 little-endian, MAC 6, u8 nodeId,
                           u8 isConnected, 0x20 name at 0x0C, u16 localCommunicationVersion at 0x2E
+0x26A                     u16 advertiseDataSize, then 0x180 bytes of advertise data
+0x478                     u64 authenticationId
```

节点使用真实局域网地址（Pia 不通过隧道传输）；节点 0 的地址必须可达，绝不能是链路本地地址：主机会向该地址发送 Pia 数据并建立 TCP 连接。模拟器根据节点地址派生其 MAC（`02:00:ac:10:56:01`对应 172.16.86.1）。游戏自身节点在 +0x2E 处存放 88（在 0x2C 处的字节后对齐），该值由其`ConnectImpl`传入，游戏会原样保留收到的 NetworkInfo。火红的扫描过滤器仅比较`localCommunicationId`和`networkType`（`sceneId`为 0xFFFF，`ssidLength` 0).

16 字节会话 ID 在三个位置必须是同一个值：`NetworkId.SessionId`、`Ssid`的十六进制文本，以及 Pia 会话密钥的明文`AES(game_key).encrypt(ssid)`，网络 ID 为`crc32(ssid[1:16])` [`pokeldn/ldn/crypto.py`:114]，与 LDN 库的实现一致 [vendor/LDN/ldn/**init**.py:1921, :1910]。广播一个值却使用另一个值加密，仍可建立关联，但主机会丢弃所有数据报并超时，不报任何错误。

## 站点的广播

已加入的主机将广播和组播直接发往 BSS（不设置 DS 位；地址依次为组地址、主机地址、BSSID；使用 CCMP 组密钥，密钥 ID 为 1），将单播以 to-DS 方式发送（使用成对密钥，密钥 ID 为 0）。火红最先发送的广播是查询主机端的 ARP 和 IPv6 组播。标准接入点会丢弃未设置 DS 位的帧，而不响应 ARP 的主机端会被以原因 3 解除认证。[ESP32](hardware_esp32.md)会完整转发这些帧（`vendor/LDN/ldn/__init__.py` `_process_data_frame`负责在旧版 Linux 路径中解密这些帧）。

## 信道

LDN 也允许使用 5 GHz 的 36/40/44/48 信道，而 ESP32 无法使用这些信道；火红／叶绿只扫描 2.4 GHz。重新成为主机端的主机可能更换信道；开发板扫描会打印该信道：

```
POKELDN_RADIO=esp32:auto ./.venv/bin/python tools/ldn/ldn_scan.py --keys PROD_KEYS --dwell 2.5
```

广播通告会泄漏到相邻信道：开发板在主机端所在信道的相邻信道上也能听到其广播通告，但数量少得多，RSSI 则相同。在相邻信道加入可以建立关联，但随后主机端在自身信道上发出的下一条广播通告会使连接因网络不兼容而断开；因此扫描会报告广播最繁忙的信道。
