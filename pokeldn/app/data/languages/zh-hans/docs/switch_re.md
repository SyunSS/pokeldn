---
title: Switch 游戏逆向工程
nav_order: 3
---

# Switch 游戏逆向工程

无需完整解包即可阅读零售版 Switch 游戏代码，示例包括 Unity/IL2CPP 游戏（BDSP，7.3 GB 的 NSP 文件）和原生 C++ 游戏（剑／盾，13.3 GB 的 XCI 文件）。

## 工作顺序

1. 用手头已有的常量搜索公开来源。代码搜索可以查到 NintendoClients 维基内部，包括汇总表未链接的各游戏专属页面：
  ```
  gh search code "<a constant, a field name, a class name>" --limit 20
  gh api repos/kinnay/NintendoClientsWiki/contents --jq '.[].name'
  gh api repos/kinnay/NintendoClientsWiki/contents/<Page>.md --jq .content | base64 -d
  ```
  汇总表提供派生值；各游戏、Pia 版本和应用数据页面提供计算规则。
2.
3.
4.
5.

解密使用 Pia LDN 的游戏需要其口令、`cryptoKeyDataSeed`、本地通信版本、广播通告以及每个发送方的 MAC（[Pia 层](pia.md)).

## 提取可执行文件

### 从 NSP 提取

NSP 是包含 NCA 的 PFS0 归档；可执行文件位于一个数 GB 大小的 NCA 的末尾附近。

1.
2.
3.

### 从 XCI 提取

`tools/switch/xci_read.py`遍历 HFS0 分区（或 NSP 的 PFS0），原位解密 NCA 头部（使用以下密钥进行 AES-128-XTS 加密：`header_key`，扇区微调值采用大端序），并打印游戏 ID、内容类型、密钥代数，以及每个节的偏移、计数器和密钥：

```
./.venv/bin/python tools/switch/xci_read.py <the.xci> --keys prod.keys --type Program
```

卡带 NCA 的权限 ID 为零，且没有票据：主体密钥位于使用以下密钥解密的密钥区槽位 2：`key_area_key_application_`。更新的 exefs 位于其 Program NCA 的第 0 节，是普通的 CTR PartitionFS：

```
./.venv/bin/python tools/switch/xci_read.py <the.xci> --nca <id> --exefs 0 --extract main
```

易错点：FS 头部的`fs_type`位于 +0x2，哈希类型位于 +0x3（hactool 的结构体将名称对调了）；8 字节的节计数器需要反序使用。

### 从 RomFS 提取

NCA 各节使用游戏密钥进行 AES-128-CTR 加密（计数器由该节的 CTR 值及以下值组成：`offset >> 4`，采用大端序），因此任意范围均可单独解密。`tools/switch/romfs_read.py`可直接在容器中的 4.2 GB RomFS 上遍历、搜索和提取内容；若头部大小字段不等于`0x50`则抛出异常，密钥、偏移或计数器错误最先会在这里显现。hactool 遇到含 34 位十六进制数字的`prod.keys`行时会中止，而对缺少表的稀疏文件执行`--listromfs`时会发生段错误。

## 先为所有内容命名

零售版 Unity 游戏具有两个独立的命名层：

-
-

所属类（`LocalProtocol`或`LanProtocol`）可用于区分 LDN 会话密钥派生逻辑与几乎相同的局域网派生逻辑。带有空洞的虚函数表属于多重继承组：这些空洞是下一个子对象的 offset-to-top 和 typeinfo。

## 只存在于元数据中的常量

一个常量`byte[]`默认值，如果属于普通的`[Serializable]`C# 类（而不是`ScriptableObject`），就会由其构造函数使用`RuntimeHelpers.InitializeArray`，基于以下类型的静态字段写入：``，其字节只存在于`global-metadata.dat`的字段默认值表中。构造函数的 ADRP/LDR 指令对指定一个元数据使用槽位，该槽位解析为`Field$.`，即数据的 SHA-1；按字段名读取值，并通过计算哈希验证。BDSP 的 16 字节游戏密钥种子就是这样存储的。原生 C++ 常量位于 rodata，可通过交叉引用查找。

## 检查导出的是哪个版本

游戏本体和更新分别位于不同的 NSP 中。BDSP 本体定义了 24 个网络消息类，1.3.0 则定义了 65 个；`PosData`从`Vector3 pos, short rotY`变为`ushort posX, ushort posZ, short rotY`（16 字节变为 6 字节），而`JoinData`新增两个字段并取消了对齐，因此用本体导出的布局解码抓包，会得到看似合理却毫无意义的结果。检查方法：

-
-

常量会保留（BDSP 本体元数据中的密钥种子能解密更新后主机抓包中的全部 674 个数据包）；凡是未经抓包确认的结构性内容，都要重新阅读核实。

## 读取游戏更新的 RomFS

更新的 RomFS 是修补游戏本体 RomFS 的 BKTR 节。其末尾有两张表，使用该节普通的 CTR 加密，以偏移量为键，按 0x4000 字节的桶组织（hactool 的`bktr.c`），共同决定每个字节：重定位表将虚拟范围映射到更新的节或本体 RomFS（`is_patch`）；子节表为更新的每个物理范围提供计数器值，用来替换节计数器的字节 4..8。`tools/switch/bktr_read.py`将两者组合成一个可寻址的节：

```
./.venv/bin/python tools/switch/bktr_read.py UPDATE.nsp --base BASE.nsp \
    --extract /Data/Managed/Metadata/global-metadata.dat
```

本体应是更新所属游戏的 Program NCA，且具有 CTR RomFS 节：XCI 的更新分区包含系统程序的 Program NCA，最先找到的 Program NCA 就是其中之一。

## 查找调用者

扫描镜像中的字，查找`bl` (`100101`加上有符号 26 位字偏移）以及尾调用`b` (`000101`），只有一行的 C# 转发器会编译成后者：BDSP 的`ANetData$$SendReliableData`和`ANetData$$SendReliableData`没有任何`bl`调用者，却有九个`b`调用者，位于联盟交谊厅的上下文菜单中。一个没有分支指向它的方法，可能是通过 ADRP/ADD 指令对注册为以下类型的委托：`Action`（`arm64_xref.py`），例如`TradeStateModel`的`WriteSaveData`, `FirstSave`和`SendTradeState`.

易错点：`arm64_xref.function_start`会向前穿过`udf`填充区回溯，可能把一次写入归到前一个函数（需检查函数序言）；以“入口后 N 字节”为函数边界会越过其`ret`进入下一个函数体；`mov w0, #0x80`在 ARM64 上是 ORR 立即数指令，字节模式扫描无法识别，因此应使用反汇编器解码常量。

## 调用 nnSdk

对 nnSdk 的调用会经过一个 GOT 槽位，该槽位由指定符号名的 JUMP_SLOT 重定位填充：交叉引用该槽位（`tools/switch/nso_imports.py`），然后统计其唯一 PLT 桩的调用者。

## 工具

读取器位于`pokeldn.switch`（容器和 NCA、RomFS、NSO、Trinity 包）；工具是其上的命令行接口，需要游戏自身文件的程序会通过它从用户导出内容中读取。除上文的`xci_read.py`, `romfs_read.py`, `bktr_read.py`和`rtti_names.py`之外，以下工具也全部离线运行：

```
tools/switch/nso_read.py     an NSO's three segments decompressed (pure-Python LZ4) at their
                             memory offsets: a file offset is an address
tools/switch/nso_relocs.py   MOD0 -> dynamic -> relative relocations, RELA and RELR. Vtable slots
                             fill at load time, so "who points here" is a relocation question;
                             modern titles use RELR, where a RELA-only reader finds nothing
tools/switch/arm64_xref.py   ADRP(+ADD|+LDR) cross-references, BL call graph, function starts
tools/switch/arm64_dis.py    capstone window disassembly
```
