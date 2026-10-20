---
title: 树莓派 4 神秘礼物主机端
parent: Hardware and setup
nav_order: 4
---

# 树莓派 4 神秘礼物主机端

搭配 TP-Link Archer T3U / AC1300（`2357:012d`, `rtw88_8822bu`）的 64 位树莓派 4 可以充当神秘礼物主机端。打过补丁的 LDN 实现位于 `vendor/LDN`；切勿在树莓派上安装未经修补的 PyPI 包。适配器的内核配置见 [适配器](hardware_adapters.md).

部署过程通过 SSH 别名，将已提交的 Git 对象推送到树莓派上的裸仓库，不经过 GitHub，不使用 `rsync`，也不包含被忽略的文件（参考仓库、`.venv`、抓包、宝可梦文件、Switch 密钥）。

## 首次部署

在桌面计算机上，使用 SSH 别名和树莓派登录用户执行：

```
git add -A
git commit -m "Prepare Raspberry Pi deployment"
./scripts/deploy_pi.sh --host pi-ldn --user PI_USER
```

`deploy_pi.sh` 会拒绝工作区有未提交修改的桌面端检出目录，运行配置和文档测试，按需创建 `/home/PI_USER/repos/pokeldn.git`，将当前提交推送到其 `deploy` 分支，并创建或快进更新 `/home/PI_USER/pokeldn`。它绝不会强制重置，也会拒绝包含未提交文件的树莓派检出目录。如果 SSH 别名已经指定了远程用户，请提供路径：

```
./scripts/deploy_pi.sh --host pi-ldn \
  --path /home/PI_USER/pokeldn \
  --repo /home/PI_USER/repos/pokeldn.git
```

然后初始化树莓派环境：

```
ssh pi-ldn
cd ~/pokeldn
./scripts/setup_pi.sh
```

`setup_pi.sh` 需要 64 位 Raspberry Pi OS（`aarch64`）以及 Python 3.11 或更新版本（Bookworm 为 3.11，Trixie 为 3.13）。它会根据 `requirements.txt` 构建虚拟环境，安装系统工具（`--no-apt` 可跳过），并将 `ldnclient`, `ldn`, `ldn-mon` 和 `ldn-tap` 排除在 NetworkManager 管理范围之外（`--no-networkmanager` 可跳过）。请通过以太网或内置 Wi-Fi 保持 SSH 连接：主机端创建会话时会独占 TP-Link 适配器。

## 配置与 Switch 密钥

仓库跟踪的 `config/host.toml` 是 TP-Link 实际运行配置方案：

```
[host]
live = true
skip_encryption = true
accept_decrypted_ccmp = true

[ldn]
phy = "auto"
```

被忽略的 `config/host.local.toml` 保存密钥的绝对路径（主机端以 `sudo` 身份运行）；有关如何安装 `prod.keys`，请参阅 [树莓派上的 Switch 密钥](hardware_switch_keys.md).

## 验证并运行

插入 TP-Link 适配器后执行：

```
cd ~/pokeldn
./scripts/preflight_pi.sh
./scripts/run_mystery_gift.sh
```

预检为只读操作。它会检查 Python 和随项目附带的 LDN 包，加载 `config/host.toml` 及可选的 `config/host.local.toml`，检查 TP-Link USB ID 和 `rtw88_8822bu`、AP 与监听模式支持、NetworkManager 排除设置，以及密钥文件的权限模式是否为 `0600`。如果 TP-Link 的调用禁用了 `skip_encryption` 或 `accept_decrypted_ccmp`，预检将拒绝执行，包括通过 `run_mystery_gift.sh` 传入的参数。它会自行添加 Debian 的 `sbin` 路径，因此在本地 shell 中和通过单行 SSH 命令执行时行为一致。

`run_mystery_gift.sh` 会执行一次预检，然后监管短时运行的 root 主机端进程；每个进程使用随机 TID/SID，在分发完成、尝试失败，或五分钟内没有 Switch 加入且没有 Pia/RFU 流量后重新启动。按一次 Ctrl-C 即可停止。它始终传入 `--end-on-success`（在分发后的关闭流程完成后结束）和 `--idle-timeout 300`（连续指定秒数没有 Switch 流量后结束），并自行管理 `--id`，因此已保存的 `--id` 无法重复使用旧身份。其余所有 `bin/frlg_mg_host.py` 选项都会被转发；`--help` 和 `--print-effective-config` 均不需要预检或 root 权限。

每次成功加入后的尝试都会追加到被忽略的每日记录文件 `logs/mystery-gift-attempts-YYYY-MM-DD.csv` 中，包含以下列：`attempt`, `received_result` (`true`，仅在发送了神奇卡片或印章时填写）、`time`, `trainer_name`, `trainer_ot`（来自 Switch 的 LinkPlayer 数据块中的名称和五位训练家 ID；如果尝试在此之前失败，则留空）。`bin/frlg_mg_host.py --attempt-log-dir logs` 也会写入相同的记录文件。

事件控制：`--gift`, `--flag-id`, `--verbose`, `--capture`, `--ot`, `--version`, `--id`. `--client-ready-idle-frames N` 是用于硬件测试的时序诊断选项；其他情况下请勿设置。`--make-artifact` 会写入确定性的 `.ram.lst` 清单，保存于 `artifacts/` (`--artifact-dir DIR`；该选项可重定向输出位置）：内容包括编译后的 RAM 脚本字节、解码后的指令、校验和、分支与消息目标，以及分发阶段摘要；`--no-make-artifact` 可在已保存的命令中禁用此功能。

```
./scripts/run_mystery_gift.sh --gift solrock-stamp --client-ready-idle-frames 45 \
  --capture solrock-45.jsonl
./scripts/run_mystery_gift.sh --gift worlds-xp --make-artifact
```

除非正在诊断其他硬件，否则请将 `--phy`, `--adapter`, `--skip-encryption` 和 `--accept-decrypted-ccmp` 保持为 TP-Link 默认值。对于 ALFA `mt76x0u`，请传入其当前 PHY（`iw dev`；拔插后会改变）和 `--no-accept-decrypted-ccmp`；随后预检会检查该 PHY 的 AP 和监听模式，以及 `mt76x0u` CCMP 配置方案。

### 使用自定义 AP 驱动的 MT7601U 适配器

系统自带的 `mt7601u` 驱动不支持 AP 模式。主机端创建会话需要固定版本的 `mt7601u-ap` DKMS 模块（`vendor/mt7601u-ap-1.0`），并在树莓派上针对其 ARM64 内核构建；切勿复制在桌面计算机上构建的 `.ko`。从桌面计算机执行：

```
./scripts/deploy_pi.sh --host pi-ldn --user PI_USER --install-mt7601u-ap
```

或在树莓派上执行：

```
cd ~/pokeldn
./scripts/setup_pi.sh --install-mt7601u-ap --no-networkmanager
```

这会安装 `dkms` 和 `linux-headers-rpi-v8`，并为每个已安装且具有匹配头文件的内核注册该模块（APT 可能在重启之前安装更新的内核）；如果当前运行的内核缺少匹配头文件，则会停止。重新插拔适配器（或重启），从 `iw dev` 读取其 PHY，并使用 `--phy phyN --no-accept-decrypted-ccmp` 运行。预检会确认已加载的 `mt7601u` 来自 `updates/dkms`，并支持 AP 和监听模式。

## 部署更改

在桌面计算机上提交更改，然后再次运行 `./scripts/deploy_pi.sh --host pi-ldn --user PI_USER`。它只会快进更新代码；当依赖文件或 `vendor/LDN` 发生变化时，树莓派会刷新其虚拟环境。`./scripts/update_pi.sh` 可在手动推送后于树莓派上执行更新。切勿在树莓派上编辑受跟踪文件；请让 `config/host.local.toml`、密钥和抓包文件仅保存在树莓派本地，并保持为被忽略状态。
