---
title: 命令行用法
---

# 命令行用法

请在仓库根目录运行命令。从源码运行工具需要 Python 3.11+、Switch 的 `prod.keys`（默认为 `~/.switch/prod.keys`，也可使用 `--keys PATH`）以及已刷入固件的 ESP32 开发板。请参阅 [支持的开发板](hardware_esp32.md#supported-boards) 和 [构建与刷写](hardware_esp32.md#building-and-flashing).

```
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
dotnet build -c Release services/pkhex
export POKELDN_RADIO=esp32:auto
python -m pokeldn --list
python -m pokeldn --radio esp32:auto swsh-host --offer-file offer.pk8
```

交换工具需要 .NET 10 SDK，以便运行 PKHeX 辅助程序。请通过 `requirements.txt` 安装随项目附带的 LDN 库；不要替换为 PyPI 上的 `ldn` 包。在 Windows 上，请在 PowerShell 中使用 `.venv\Scripts\Activate.ps1` 激活虚拟环境，并使用以下方式设置无线模块：`$env:POKELDN_RADIO = "esp32:auto"`.

`esp32:auto` 会选择当前唯一的 USB 串口；可使用 `esp32:PORT` 显式指定串口。请参阅 [无线模块设置与诊断](hardware_esp32.md#running)。配置文件和默认输出路径均相对于工作目录解析。每个入口点都接受 `--help`.

## 火红与叶绿

在主机上解锁直接交互区，并准备至少两只 `.pk3` 队伍成员。

```
./.venv/bin/python bin/frlg_trade_join.py --live -o output.pk3 PARTY1.pk3 PARTY2.pk3   # join the Switch's trade
./.venv/bin/python bin/frlg_trade_host.py -o output.pk3 PARTY1.pk3 PARTY2.pk3          # host a Direct Corner trade
```

主机端会广播群组并主导交换。默认情况下，它提供 `PARTY2.pk3`，并将接收到的内容写入 `output.pk3`。默认值依次来自 `config/host.toml` 和被忽略的 `config/host.local.toml`；命令行标志会覆盖这两层配置；`--print-effective-config` 会显示最终结果。

1.
2.
3.
4.

| 标志 | 用途 |
| --- | --- |
| `--keys PATH` | `prod.keys` 位置 |
| `--slot N` | 提供的队伍成员索引，从零开始 |
| `--capture FILE` | JSONL 诊断记录 |
| `--config` / `--local-config` / `--no-local-config` | 替换或禁用某一配置层 |
| `--ot NAME`, `--version firered\|leafgreen`, `--id TID[:SID]` | 单次运行的训练家覆盖值（每项范围为 0..65535；LinkPlayer ID 为 `(SID << 16) \| TID`) |
| `--verbose` | 逐数据包输出，在按帧计时的循环内同步写入日志；仅与 `--replay` 配合使用 |

`DEFAULT_TRAINER`，位于 [`pokeldn/config.py`](../config.py) 中，保存没有对应命令行标志的默认值（性别、语言、全国图鉴）。连接协议见 [连接协议](frlg_link.md).

**联盟交谊厅。** `--union-room` 会通过中间 NPC 的路径广播；保活等待结束后，主机才会显示已连接，约需 10 秒（[连接协议](frlg_link.md)）。每次联盟交谊厅连接只进行一次交换，随后主机返回场景（`union_room.c:1744`). `--board-type normal` 会将提供的宝可梦登记到交换公告板；`--union-room-chat` 配合 `--chat-message` / `--chat-file` 可聊天；`--union-room-battle --battle-fight` 可对战（主机需有两只不高于 30 级、且不是蛋的宝可梦）。

```
./.venv/bin/python bin/frlg_trade_host.py --union-room --union-room-keepalive 120 PARTY1.pk3 PARTY2.pk3
```

**神秘礼物。** `bin/frlg_mg_host.py` 会通过“朋友”路径广播，并发送一张神奇卡片及分发脚本。在 Switch 上：**神秘礼物 → 神奇卡片 → 朋友**，然后选择 pokeldn 的主机端；存档必须已解锁神秘礼物。`--make-artifact` 会写入所发送字节的 `.ram.lst` 清单。目录、创作系统以及“朋友”路径要求见 [神秘礼物](frlg_gift.md).

```
./.venv/bin/python -u bin/frlg_mg_host.py --gift beast-cutscene --flag-id 1005 --capture mystery-gift.jsonl
```

传说宝可梦由存档中的最初伙伴决定（妙蛙种子对应水君，杰尼龟对应炎帝，小火龙对应雷公）。共用的集章活动卡片为 `--gift solrock-stamp` 和 `--gift lunatone-stamp`，顺序不限。

**神奇新闻。** `--news` 对应主机神秘礼物的第二栏（**神秘礼物 → 神奇新闻 → 朋友**）：标题和正文共 444 字节，可在华蓝市领取树果奖励。主机只会保存与现有内容不同的新闻；`--news-id N` 可强制生成一条新新闻。

```
./.venv/bin/python -u bin/frlg_mg_host.py --news berry --news-id 7
```

**存档备份与恢复。** 同一“朋友”路径可以将完整的 128 KB 存档复制到 `.sav` 文件，或将 `.sav` 写回：先写在主机原有存档之外的位置，逐扇区回读校验，然后由游戏加载并保存；未完成全部流程时，主机存档将保持原样。在应用中，神秘礼物工具的“你的存档”选项卡可以保存并命名备份，导入和导出 `.sav` 文件，并通过 PKHeX 编辑训练家和队伍。零售版法语《火红》上备份约需四分钟；在零售版英语《火红》上恢复后，可通过“继续”加载，法语存档也已验证。[存档备份与恢复](frlg_gift.md#save-backup-and-restore).

```
./.venv/bin/python -u bin/frlg_mg_host.py --live --save-backup backup.sav --save-resume-dir partial
./.venv/bin/python -u bin/frlg_mg_host.py --live --save-restore backup.sav
```

**主机存档。** 神秘礼物会话会在主机上运行原生 ARM 代码。`save-dump` 会回读实时存档（秘密 ID，以及每只队伍宝可梦的 PID、个体值和性格）；不会写入任何内容。`flash-patch` 可编辑单个字段：读取存档扇区，仅修改指定字节，重新计算校验和，写回扇区，并递增计数器以使游戏加载它。这会修改真实存档；请先阅读 [从 RAM 快照构造扇区](frlg_rom.md#composing-a-sector-from-a-ram-snapshot)。载荷见：[主机上的代码](frlg_rom.md).

```
./.venv/bin/python -u bin/frlg_mg_host.py --buffer-script save-dump --dump-block sav2 --dump-size 64 --dump-file dump.bin
./.venv/bin/python tools/frlg/dump_read.py dump.bin --block sav2
./.venv/bin/python -u bin/frlg_mg_host.py --buffer-script flash-patch --flash-id 0 \
  --flash-patch-offset 0x00 --flash-patch-hex cac9c5bfc6bec8ff --write-unsafe
```

## Let's Go! 皮卡丘与伊布

交换界面会交替创建会话和扫描，因此 pokeldn 既可作为主机端，也可作为加入端。两者都会发送 kind-1 身份消息：加入端发送 `pokeldn.lgpe.reference` 附带的消息，主机端则回送主机自身的消息（`--first echo`）或使用文件。两者都会提供一个 232 字节的 PB7（`pokeldn.lgpe.pb7`; `--offer echo` 会返回主机自身的记录）。主机端的 `--next-offer` 和加入端重复指定的 `--offer` 可将记录加入队列，用于同一席位上的后续交换，每次一条。加入端的 `--leave-after S` 会在回应第一个交换步骤后 S 秒退出，行为与玩家离开交换界面相同；若不设置，席位会保持开放以便后续交换。

```
./.venv/bin/python bin/lgpe_host.py --seconds 600 --player-name POKELDN \
  --first echo --our-trainer 41234:12345 --offer offer.pb7
./.venv/bin/python bin/lgpe_join.py --connect --connect-seconds 300 \
  --ack-peer-clock --ack-re-announce \
  --our-trainer 41234:12345 --offer offer.pb7
```

主机操作：交流 → 本地联机 → 交换，暗号选择皮卡丘 ×3，然后停留在搜索界面等待。对于通过局域网连接的模拟主机，请使用 `lgpe_host.py --ip-host --our-ip IP`。请参阅 [Let's Go](lgpe.md).

## 剑与盾

主机操作：YY 通讯 → 连接交换 → 本地联机，在两条消息处均按 A，然后停留在搜索界面等待。

```
# join the console's session and trade: the console's own party snapshot is sent back, rewritten
POKELDN_RADIO=esp32:auto ./.venv/bin/python bin/swsh_connect.py --keys PROD_KEYS \
  --preset trade --offer-slot 1 [--offer-file your.pk8 --offer-file next.pk8 --fresh-pid] \
  --save-offered received.pk8

# or host, and let the console join: its snapshot is taken from this trade
POKELDN_RADIO=esp32:auto ./.venv/bin/python bin/swsh_host.py --keys PROD_KEYS \
  --offer-file your.pk8 --fresh-pid --received received.pk8 --channel 6 --seconds 900
```

主机端会构建自己的站点广播信息，并重写加入主机的实时快照。pokeldn 作为主机端时，主机通过 YY 通讯 → 连接交换 → 交换加入，并在随后两条消息处均按 A；`--received FILE` 会保存它发送的内容，`--code 12345678` 可创建供密码搜索加入的会话。`--advert` 和 `--snapshot` 仍接受已保存的记录以供比较。主机端和加入端均可重复指定 `--offer-file`，在同一会话中每次交换使用一条记录，玩家则再次从盒子中选择；第 N 次交换会使用 `-N` 写入收到的内容。详情见：[交换](swsh_trade.md).

神秘礼物无需建立会话；礼物界面会扫描，分发端则广播卡片。主机操作：神秘礼物 → 接收礼物 → 通过本地无线通信接收。

```
./.venv/bin/python bin/swsh_gift_host.py --species 25 --level 25 \
  --move1 84 --move2 45 --move3 86 --move4 98 --nickname POKELDN --ot POKELDN --seconds 300
./.venv/bin/python bin/swsh_gift_host.py --record card.wc8 --seconds 300
```

`--set FIELD=VALUE` 可设置任意记录字段（`shiny_type=3`, `ball=1`, `held_item=236`, `iv_hp=31`, `gigantamax=1`), `--ribbon N` 可添加奖章，`--dump FILE` 无需无线模块即可写入记录。道具 ID 会对照道具表进行检查；没有对应表项的 ID 也会被接受，但在显示其背包条目时会导致游戏中止。请参阅 [神秘礼物](swsh_gift.md).

## 晶灿钻石与明亮珍珠

pokeldn 会以角色身份加入主机的联盟交谊厅。主机操作：任意宝可梦中心 → 2F → 左侧接待员 → 普通的“是”（不是密码或群组选项），然后在联盟交谊厅内远离墙壁等待。

```
./.venv/bin/python tools/ldn/ldn_scan.py --channels 1,6,11 --dwell 0.8      # see the session
./.venv/bin/python bin/bdsp_connect.py --channels 1,6,11 --count 9 --connect 5 --join 6 \
  --hold 420 --reliable-ack --reliable-sweep 3 --room-walk 15 --room-pattern fixed \
  --room-walk-steps 0 --join-avatar 0 --answer-requests --state 0 --recruiting 0 \
  --answer-talk --can-talk 0 --initiate-talk --initiate-delay 3 \
  --after-approach 0x06:0001000000 --trade-reply --complete-trade \
  --trade-template offer.pb8 --trade-nickname POKELDN --src-var 0x2B7F4C12
```

关联可能失败（`Connect failed with status code 1`）；诊断前请先重试运行（[会话](bdsp_session.md)). `--room-pattern fixed` 会持续发送加入请求，直到主机请求角色状态，最多发送 `--room-walk` 次（上例为 15）。重复指定 `--trade-template` 可将宝可梦加入队列，用于会话中的每次交换；最后一只会被重复提供。每次运行都应使用新的 `--src-var`（主机会保留见过的 ID）；如果上次运行是手动停止的，玩家应先离开再重新进入房间。`--complete-trade` 允许主机写入存档；不设置时，交换会停在最后一次确认处。角色出现并走动结束后：Y → 交流菜单 → 交换宝可梦。

如果要改为主机端，请先启动主机端，然后玩家以同样方式进入房间并举起交换表情（Y → 交流菜单 → 交换宝可梦）：

```
./.venv/bin/python bin/bdsp_host.py --offer offer.pb8 --complete-trade --capture host.jsonl
```

`--offer` 必须是合法 PB8，且其 PID 不存在于该存档中；重复指定时，每次交换使用队列中的一只，最后一只重复提供。`--password 00000000` 会创建需要该密码才能进入的房间。请参阅 [晶灿钻石与明亮珍珠](bdsp.md).

## 传说 阿尔宙斯

充当交换主机端的主机会与加入的站点进行交换；如果对方加入较晚，则会将主机端角色移交给该站点（[传说 阿尔宙斯](pla.md)). `bin/pla_host.py` 创建会话，主机通过连接密码加入；`bin/pla_join.py` 会加入主机的搜索，每次交换使用重复指定的 `--offer` 中的一条，并在收到角色移交时接任主机端。

```
./.venv/bin/python bin/pla_host.py --code 00000000 --channel 6 --seconds 1800 \
  --session-update --sustain --clock --data-exchange --data-exchange-name POKELDN \
  --data-exchange-id 11223344 --game-channel --trade-box --trade-box-record offer.pa8 \
  --offer-out received.pa8
./.venv/bin/python bin/pla_host.py --ip-host --our-ip 172.16.86.128 --code 00000000 ...   # emulated console, no radio
```

主机操作：祝庆村的佐雯 → 交换 → 附近的人 → 输入相同的八位密码，提供宝可梦并确认。主机端会在两次提供之间重新读取记录文件，并将主机交换来的记录写入 `--offer-out` (`-2`，后续交换依此类推）；`--trade-box-collect DIR` 会保留主机展示或提供的每条记录，包括光标位置。重复指定 `--trade-box-record` 可将记录加入队列，用于会话中的每次交换，最后一条重复提供。`pokeldn.pla.pokemon` 可以读取、写入记录，并通过 `build` 从 376 个零字节创建记录；`pokeldn.pla.stats` 可计算能力值和体型。请参阅 [传说 阿尔宙斯](pla.md).

## 朱与紫

离线连接交换搜索会交替扫描和创建会话，因此 pokeldn 可以作为主机端（`bin/sv_host.py`）或加入端（`bin/sv_join.py`).

```
./.venv/bin/python bin/sv_host.py --seconds 240 --player-name POKELDN \
  --rtt-probe --net-property --clock --net-stations 4 --scarlet-response \
  --record-delay 0.17 --announce --announce-delay 5.25 \
  --send-at 6.00:0x7c:1:b90101b902b90280800001 \
  --trade-offer offer.hex --offer-after-open 8
```

主机操作：X → 宝可入口站 → 连接交换 → 离线，不设置密码 → 搜索。重复指定 `--trade-offer` 可在同一席位上每次交换提供一条记录。线路协议层面的要求（身份消息顺序、确认应答 `lowest_pending`）见 [朱与紫](sv.md).

两种角色也都可参与本地太晶团体战。`--raid-seed` 会创建可由主机加入的团体战（宝可入口站 → 太晶团体战，连接密码 4970）：种子和四个上下文标志决定首领，`--raid-reward ITEM:QUANTITY` 可替换其奖励，而 `--raid-pokemon` 是 pokeldn 玩家带入的宝可梦。`--raid-event FOLDER` 则从宝可入口站新闻分发内容中获取首领和奖励，即 Project Pokemon 的 [EventsGallery](https://github.com/projectpokemon/EventsGallery) 中的一个活动；应用会按需下载和更新。`--raid-players N` 允许最多三台主机加入同一场团体战；当 N 台主机已进入大厅且都按下“准备”后，或大厅计时结束时，战斗便会开始。`--raid-partner TRAINER` 可为主机未占用的槽位选择填充用的 NPC 队友，每个空槽最多指定一次（只有一台主机时为空两槽）；否则主机会根据主机端的剧情进度选择这些队友。`bin/sv_join.py --raid-pokemon FILE` 会加入由主机创建的团体战。在两种情况下，pokeldn 的玩家都会在战斗开始时离开，其宝可梦则留下与主机的宝可梦并肩作战。应用中的两个太晶团体战工具均支持这些标志；请参阅 [太晶团体战](sv_raid.md).

## 传说 Z-A

连接交换搜索会交替创建会话和扫描，因此 pokeldn 可以加入或充当主机端。主机操作：连接交换 → 本地联机 → 使用密码 00000000 搜索。加入端会反复扫描，直到占据一个席位。

```
# host: start it first, then search on the console
POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/za_host.py --keys prod.keys --trade-offer offer.bin --capture zh.jsonl
# join
./.venv/bin/python bin/za_join.py --channels 1,6,11 --dwell 0.35 --seconds 900 \
  --hold 450 --quiet-seat 25 --connect-timeout 6 --game --trade-offer offer.bin --offer-delay 4
```

在交换盒子中选择一只宝可梦，待对方的宝可梦出现后确认。两种角色都能在同一会话内回应下一次提供；重复指定 `--trade-offer` 可将记录加入队列，每次交换使用一条。完成后按 B 退出；主机离开时，主机端会关闭会话。`--offer-out FILE` 会保留主机提供的内容。对于通过局域网连接的模拟主机，请使用 `za_host.py --ip-host --our-ip IP --comm-id ffffffffffffffff` 和 `za_join.py --ip-join --host-ip IP --our-ip IP --comm-id ffffffffffffffff`。提供文件共 354 字节（九字节头、344 字节记录、一个尾字节）；`pokeldn.gen9.build` 可构建该记录，因为 Z-A 的布局与《朱》相同。请参阅 [传说 Z-A](za.md).

## 诊断

-
-
-
