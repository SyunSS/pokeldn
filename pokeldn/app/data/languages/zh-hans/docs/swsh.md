---
title: 剑和盾
nav_order: 6
has_children: true
---

# 剑和盾

宝可梦剑和盾以 C++ 运行游戏代码，使用协议缓冲区消息，通过通用的发布／订阅框架直接运行于 Pia 之上。

静态分析使用盾 1.3.2 欧洲版镜像（`01008db008c2c000`，更新 NCA，SDK 7.7.0.0）；测量使用法语版剑 1.3.2。两个版本共用网络代码；存在差异的地方会明确标注。

零售版剑已与 pokeldn 在两种角色下完成交换（[作为交换主机端](swsh_trade.md#hosting-a-trade)).

| 页面 | 内容 |
| --- | --- |
| [卡带与会话](swsh_session.md) | 密钥、镜像、Pia 4，以及从关联到首份应用数据的流程 |
| [同步框架](swsh_protocol.md) | 消息 ID、内容、持有者、路由、同行宝可梦载荷 |
| [交换](swsh_trade.md) | 交换界面、盒子状态机、逐步确认流程 |
| [神秘礼物](swsh_gift.md) | 神秘礼物菜单的本地无线通信分支 |
| [极巨团体战](swsh_raid.md) | 巢穴大厅及其广播通告、创建供一台或多台主机加入的团体战、加入端参与的战斗、极巨大冒险、离开流程 |

## 来源

除非章节明确注明某个客户端，否则 ID、偏移和地址均来自盾的`main`或无线通信抓包。`SYNC_ANSWERS`（位于`pokeldn/swsh/trade.py`中）是`andyjusa/nxldn-lab`对主机之间通信抓包的解读（消息 97 和 60000 与 pokeldn 的内容逐字节一致）。四个客户端支持从 Pia 站点握手开始的局域网模式：`kwsch/PokePiaSWSH`, `lincoln-lm/swsh-lan-client`, `andyjusa/nxldn-lab`, `Slashcash/PSD`；它们均未涵盖 LDN 或主机端迁移。

## 场景脚本

`bin/script/amx/*.amx`（1.3.2 中共 953 个）采用带 64 位单元的 Pawn 3.x：魔数为`0xF1E1`，版本为 10，标志为`0x1C`（紧凑代码、休眠、不检查）。紧凑编码每字节使用 7 位，高位组在前，首字节的第 6 位表示符号。非分支的单参数操作码也会打包为`(param << 32) | op`，按 3.x 顺序从 162 开始编号（`LOAD.pri` 162, `LOAD.S.pri` 164, `PUSH.C` 188, `PUSH.S` 190, `STACK` 191, `ADD.C` 197, `ZERO.S` 200, `EQ.C.pri` 201, `INC.S` 204, `HALT` 210, `PUSH.ADR` 212); `halt 0`位于偏移 0，可据此确定格式。

一个原生函数条目占十二字节，由`u64 0`和一个`u32`名称哈希组成，由以下函数解析：`amx_Register` (`0x0066d970`):

```
h = 0; for each byte c: h = (h * 0x83) ^ c        (32-bit)
```

绑定表是`(name, function)`配对，位于`.data`中，每个模块一张（获取函数例如`0x014aea00`）：共 777 个名称，覆盖已使用的 513 个哈希中的 512 个。物品相关函数：`ItemAdd` (`0x014acea0`), `ItemSub` (`0x014acf40`), `ItemGetNum`, `ItemAddCheck`, `ItemGetCategory`, `GetPocketNumberFromItemNumber_`。变量相关函数：`WorkGet`/`WorkSet`（经过哈希的 64 位键），`TempWorkGet`/`TempWorkSet`（由 UI 在脚本恢复前填入的索引）。调用时对每个参数从右到左执行`PUSH`，然后执行`SYSREQ.N native, bytes`.

## 尚未解决

-
-
-
-
