---
title: 在 Raspberry Pi 上安装 Switch 密钥
parent: Hardware and setup
nav_order: 2
---

# 在 Raspberry Pi 上安装 Switch 密钥

`prod.keys`是你自己 Switch 的凭据，实时运行的 LDN 主机端需要它。切勿将其提交到仓库、粘贴到配置中、包含在抓包文件中，或将桌面端虚拟环境复制到 Pi；部署过程绝不会传输它。它应放在`/home/PI_USER/.switch/prod.keys`，Pi 上被版本控制忽略的`config/host.local.toml`应指定该绝对路径，因为主机端以`sudo`身份运行，而`~`不会解析为登录账户的路径：

```
[ldn]
keys_path = "/home/PI_USER/.switch/prod.keys"
```

## 在 Pi 上本地安装

以 Pi 的登录用户运行安装程序（在`sudo`下运行时，它会以`$SUDO_USER`身份重启）。它会创建`~/.switch`，权限模式为`0700`，并以以下权限模式安装文件：`0600`；它绝不会显示文件内容，再次运行时会保留内容相同的文件并修复权限。源文件必须是绝对路径指向的普通文件，且登录用户可读取：

```
cd ~/pokeldn
./scripts/install_switch_keys.sh --source /absolute/path/to/prod.keys
```

`--stdin`通过 SSH 以流的方式传输密钥，不创建暂存副本：

```
# On the desktop; pi-ldn is your SSH alias.
ssh pi-ldn 'cd ~/pokeldn && ./scripts/install_switch_keys.sh --stdin' < "$HOME/.switch/prod.keys"
```

## 通过 SSH 别名使用 SCP

在私有目录中暂存，绝不要使用以下共享目录：`/tmp`，并在完成后删除副本（`scp -p`会保留本地权限模式）：

```
# On the desktop.
ssh pi-ldn 'install -d -m 700 "$HOME/.frlg-ldn-provision"'
scp -p "$HOME/.switch/prod.keys" pi-ldn:.frlg-ldn-provision/prod.keys
ssh pi-ldn 'cd ~/pokeldn && \
  ./scripts/install_switch_keys.sh --source "$HOME/.frlg-ldn-provision/prod.keys" && \
  rm -f "$HOME/.frlg-ldn-provision/prod.keys" && \
  rmdir "$HOME/.frlg-ldn-provision"'
```

无论使用哪种方法，都应验证：

```
ssh pi-ldn 'stat -c "%a %U %n" "$HOME/.switch" "$HOME/.switch/prod.keys"'
# Expected: 700 PI_USER /home/PI_USER/.switch
#           600 PI_USER /home/PI_USER/.switch/prod.keys
```
