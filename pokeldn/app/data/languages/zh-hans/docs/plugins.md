---
title: 插件
---

# 插件

插件无需修改 pokeldn，就能为其添加工具、游戏和无线电后端，也能自行加入或创建 LDN 网络。插件是一个包含 Python 文件及 `plugin.toml` 的文件夹，打包为一个 `.pokeplugin` 文件，玩家可在应用的“插件”页面添加。项目不分发、审查或支持第三方插件。

代码：`pokeldn/plugins.py`（加载器和 API）、`pokeldn/app/plugin_store.py`（软件包）、`pokeldn/ldn/radios.py`（无线电后端查找）、`gui/views/plugins.py`（页面）。

可以从以下两个示例入手：`examples/plugins/hello` 是最小插件，仅用两个文件提供一个工具；`examples/plugins/test_kit` 使用了 API 的所有部分。

## 安装插件

1.
2.
3.

插件工具会立即出现在“游戏”页面，并带有插头标记和“插件：…”字样。每个插件卡片都有启用／停用开关，以及用于打开其工具、从较新文件更新、显示文件夹、访问插件页面和移除插件的菜单。每次安装和更新都会再次显示风险界面。手动复制到插件文件夹的插件会显示“手动添加”，首次启用时也要求作出同样的确认。

若插件在启动时导致应用关闭或卡死，下次启动时会将其停用，并指出其名称。移除插件时会询问是否一并删除其保存的数据。

插件以 Python 代码形式运行于 pokeldn 内部，拥有与应用相同的文件、密钥、网络和开发板访问权限。软件包在安装并启用之前，不会运行其中任何内容。

### 来源

来源是由他人发布的插件 JSON 列表。“插件”页面的“**来源**”选项卡用于关注来源；“**浏览**”列出这些来源中的全部插件，并显示“**安装**, **更新至 N**”或“**已安装**”，以及移除按钮。应用初始就关注 `Decryptu/pokeldn-decrypt-plugins`，且此来源无法移除。移除其他来源不会卸载从该来源安装的插件。

| 在“来源”中输入的内容 | 读取的列表 |
| --- | --- |
| `OWNER/REPO` 或 `https://github.com/OWNER/REPO` | `https://raw.githubusercontent.com/OWNER/REPO/HEAD/pokeldn-source.json` |
| HTTPS 地址，结尾为 `.json` | 该文件 |
| 任何其他 HTTPS 地址 | `pokeldn-source.json`，位于该文件夹中 |

```
{
  "schema": 1,
  "name": "My plugins",
  "homepage": "https://github.com/me/my-plugins",
  "plugins": [
    {"id": "my-plugin", "name": "My plugin", "version": "1.0.0", "api": "1.6",
     "description": "...", "author": "me",
     "download": "https://github.com/me/my-plugins/releases/download/my-plugin-1.0.0/my-plugin-1.0.0.pokeplugin",
     "sha256": "64 hex digits", "size": 46302,
     "icon": "https://.../icon.png", "homepage": "https://..."}
  ]
}
```

`id`, `version`、一个使用 HTTPS 的 `download` 以及软件包的 `sha256` 为必填项；缺少其中一项或 ID 重复的条目会被忽略。若列表使用其他 `schema`，则会被拒绝。下载文件的 SHA-256 若与列表不同，会在读取前被拒绝；软件包 ID 若与条目 ID 不同，会在风险界面出现前被拒绝。列表无法证明作者身份：风险界面和签名检查与从文件安装时相同。

应用会在启动时（已在“设置”中开启“更新”时）以及刷新页面时读取全部已关注来源，并将最近一次列表保存在 `plugins/.source-cache/`，来源无响应时显示该缓存。已关注列表位于 `plugins/.sources.json`。已安装插件会记录其来源，并从该来源获取更新；从文件安装的插件会从首个列出它的来源获取更新，其次才使用自身的 `updates` 地址。

`scripts/plugin_source.py` 从软件包生成列表，并按与应用相同的方式读取各包：

```
python scripts/plugin_source.py my-plugin-1.0.0.pokeplugin -o pokeldn-source.json --name "My plugins" \
    --download "https://github.com/me/my-plugins/releases/download/{id}-{version}/{file}"
```

已列出且版本更高的条目会保留。

### 防护措施

两项检查用于阻止明显的有害行为。两者都不是沙箱：专门设计为绕过它们的插件仍能绕过。

安装界面读取软件包的 Python 文件，并列出其行为：使用网络、启动其他程序、删除文件、调用原生代码（`ctypes`, `cffi`）、运行动态生成的代码（`exec`, `eval`, `compile`, `marshal`）、引用 `prod.keys`，或者包含无法通过源码阅读检查的编译文件。列表为空仅表示未发现这些行为，不代表插件安全。

只要调用栈上存在插件代码，无论在应用内还是每次运行中，审计钩子（`pokeldn/plugin_guard.py`）都会通过 `PermissionError`:

| 拒绝 | 允许 |
| --- | --- |
| 删除、清空、移动或覆盖插件各文件夹之外的文件 | 在其插件文件夹、数据文件夹、文件库、会话文件夹、日志文件夹和临时文件夹内进行相同操作 |
| 启动 `rm`, `del`, `rd`, `Remove-Item`, `shred`, `dd`, `format`, `mkfs`, `diskutil`, `diskpart`, `sudo`, `su` 等程序，无论直接启动还是通过 shell 命令启动；或执行任何包含 `-delete` 或 `--no-preserve-root` | 启动任何其他程序 |
|  | 在任意位置创建新文件 |

调用栈上没有插件的代码（包括 pokeldn 自身代码）不会被拒绝；由插件调用的 pokeldn 代码则会受到限制。若插件需要执行被拒绝的操作，应请玩家自行执行。

## 制作插件

### 文件夹

```
my-plugin/
    plugin.toml        what the plugin is
    plugin.py          register(api): what it adds
    hello.py           a tool's script
    icon.png           optional, shown on the Plugins page and the Games page
    mylib_common.py    optional, any module the scripts share
```

### plugin.toml

```
id = "my-plugin"            # required: lowercase letters, digits, dots, dashes, underscores
name = "My plugin"          # shown in the app
version = "1.0.0"           # compared on update: 1.2.0 updates 1.0.0
author = "Your name"
description = "One or two sentences shown on the install screen and the plugin's card."
homepage = "https://example.org/my-plugin"   # optional, opened from the plugin's menu
updates = "https://github.com/you/my-plugin" # optional, where newer versions are published (Updates)
api = "1.1"                 # required: the plugin API it needs (see Versions); 1 means 1.0
icon = "icon.png"           # optional; a square PNG, 96 x 96 looks sharp
library = "My files"        # optional (1.7): a folder the player sees, see A library
library_sort = "name"       # optional (1.8): its order until the player picks one, see A library
module = "plugin"           # optional; the module holding register()
exclude = ["tests"]         # optional; folders and files pack_plugin.py leaves out of the package
```

### plugin.py

`register(api)` 在插件启用时运行，既会在应用内运行，也会在应用启动的每次运行中执行。

```
from pokeldn.plugins import Field, Game, Tool


def register(api):
    api.add_tool("frlg", Tool(
        "my-hello",                                   # a key no other tool uses
        "Hello",                                      # the name on the Games page
        "hello.py",                                   # the script, relative to the plugin folder
        "Says hello.",                                # the line under the tool's name
        ("Nothing to do on the console.", "Press Start."),   # the console steps the app lists
        fields=(Field("--name", "Your name", default="Red"),),
        fixed=("--trainer", "{ot}"),                  # always passed; {ot} is the trainer name in Settings
    ))
```

### 工具脚本

应用先导入脚本，读取其选项以供“高级”选项卡使用，然后在会话文件夹中将其作为独立子进程运行。脚本定义 `build_parser()`，并在 `if __name__ == "__main__"` 下执行实际工作；顶层代码会在导入时运行，破坏“游戏”页面。

```
import argparse


def build_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name")
    parser.add_argument("--trainer")
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    print(f"Hello {args.name}, from {args.trainer}'s pokeldn.")
```

| 脚本 | 应用 |
| --- | --- |
| 打印一行 | 在会话输出中显示该行 |
| 打印 `[done] trade N complete` (`pokeldn.ldn.show_done()`) | 将队列中的一次交换标记为完成 |
| 以退出码 0 结束 | 将会话标记为已完成并结束 |
| 以其他退出码结束或抛出异常 | 将会话显示为失败，并在输出中显示回溯信息 |
| 接收 `KeyboardInterrupt` | 玩家按了“停止”；应在 15 s 内正常退出，否则进程会被终止 |
| 打开弹窗（`pokeldn.popup`, 1.2) | 无论应用当前显示哪个页面，都在其上方显示弹窗，并返回玩家的答复 |
| 请求从多个选项中选择一个（`pokeldn.popup.choose`, 1.7) | 每个选项显示一个按钮，并返回所按按钮的索引 |
| 报告进度（`pokeldn.progress.show(done, total, title, unit)`, 1.7) | 在“会话”面板中用进度条替代该行，显示速率和剩余时间（[进度](gui.md#progress)) |
| 显示状态卡片或标记文件库文件（`pokeldn.panel`, 1.8) | 在工具页面显示它，并在运行结束后保留（[状态卡片](#status-cards-18)) |

弹窗不会阻塞等待玩家：`acknowledge` 和 `confirm` 立即返回其 ID，答复稍后通过回调传入；回调可能随时在另一个线程上触发。脚本应维护自身状态，在答复到来时作出响应，而不是停下来一直等待：

```
import queue
from pokeldn import popup

answers = queue.Queue()
popup.set_dispatcher(answers.put)       # callbacks wait for the loop below instead of running on their own thread
asked = popup.confirm("Trade the shiny?", "Your partner offers a shiny Gholdengo.", "Trade", "Skip",
                      on_agree=lambda: print("trading"), on_disagree=lambda: print("skipping"),
                      tone="warning")
while not finished():                   # the script's own work goes on meanwhile
    try:
        answers.get(timeout=0.5)()
    except queue.Empty:
        pass
popup.cancel(asked)                     # no use for the answer any more: the pop-up closes, no callback fires
```

为共享模块取一个其他软件包未使用的名称（`mylib_common`，而不是 `utils`）：插件文件夹会加入 Python 搜索路径。

### 插件可以导入什么

正式发布的应用自带 Python 3.13，不包含 `pip`。插件可以导入：

| 内容 | 来源 |
| --- | --- |
| 标准库 | 随应用捆绑，但不包括 `multiprocessing`, `tkinter`, `curses`, `venv`, `ensurepip`, `profile`, `cProfile`, `pstats`, `trace`, `compileall`, `modulefinder`, `pyclbr`, `tabnanny` 和其他平台专属模块（`scripts/pack_app.py`, `PLUGIN_STDLIB`) |
| `trio`, `pycryptodome` (`Crypto`), `zstandard`, `pyserial` (`serial`), `websockets`, `certifi`, `bleak`, `unicorn`, `flet` | pokeldn 自身的依赖，版本见 `requirements.txt` |
| `ldn` 和 `pokeldn` | pokeldn 本身；只有下方 API 表中的部分是稳定接口 |
| 任意纯 Python 模块 | 随插件文件夹分发 |

包含编译代码的软件包（`numpy`, `Pillow`）只能在已安装该包、从源码运行的环境中使用。发布插件之前，应在正式发布的应用中测试：插件测试套件的自检在那里也以相同方式运行。

### 字段

一个 `Field` 对应工具“基本”选项卡中的一个输入项；应用在其标志之后传入该值。

| `kind` | 输入项 | 传入形式 |
| --- | --- | --- |
| `text`（默认） | 文本框 | `--flag VALUE` |
| `number` | 数字框 | `--flag VALUE` |
| `choice` | 下拉框，选项为 `choices=((value, label), ...)` | `--flag VALUE` |
| `switch` | 开关 | `--flag`，仅开启时传入 |
| `file` | 文件选择器，`exts=("bin",)` | `--flag PATH` |

### 插件保存什么

更新会替换插件文件夹。设置、缓存和其他需要持久保存的内容应放在 `api.data`，从 `register` 获取，或使用 `pokeldn.plugins.data_folder("my-plugin")` 从工具脚本获取：其路径是数据文件夹下的 `plugin-data/`，跨更新保留，只有玩家在移除时要求删除才会删除。

### 文件库（1.7）

插件若保存由玩家管理的文件（备份、下载等），应在 `plugin.toml`: `library = "My files"` 为 `Documents/pokeldn/My files`（数据文件夹中的 `My files`，位于 `POKELDN_DATA`). `api.library` 从 `register` 获取，或使用 `pokeldn.plugins.library_folder("my-plugin")` 从工具脚本获取，首次使用时创建并返回。

| 文件库 |  |
| --- | --- |
| 防护措施 | 允许在其中写入、替换、重命名和删除，与数据文件夹相同 |
| 安装界面 | 显示其名称 |
| 移除插件 | 保留文件库及其中全部文件 |
| “游戏”页面 | 在插件工具下方列出其中的文件；玩家可以通过按钮或拖放添加文件，也可以重命名和删除。以 `.` 开头或以 `.part` 结尾的名称不会显示：可以先用此类名称写入文件，写完后用完整文件替换 |
| 排序 | 玩家可选择按名称、日期或大小升序／降序排列，并按插件分别保存；未选择前使用 `plugin.toml` 的 `library_sort` (1.8: `name`, `name-desc`, `date`, `date-desc`, `size`, `size-desc`），否则使用 `date-desc`，最新文件优先。名称采用自然排序：连续数字按数值比较，并忽略大小写，因此 `v65536` 排在 `v131072` 之前，且 `20.5.0` 排在 `23.0.1` |
| 文件备注 | `pokeldn.panel.annotate` (1.8, [状态卡片](#status-cards-18)) |
| 名称 | 最多 40 个字符，可用字母、数字、空格、句点、连字符和下划线；拒绝使用 pokeldn 自身文件夹的名称（`Bank`, `Saves`, `Received`…）、Windows 设备名称，以及其他已加载插件的文件库名称 |

`help=` 在输入项下方添加说明行，`default=` 填充其值，而 `hidden=True` 将其移至“高级”选项卡。内置工具使用的字段，以及其余 `Field`，见 `pokeldn/app/catalog.py`。API 1.5 新增 `Field.identity`，为标签会被翻译的位置字段提供稳定的设置键。工具的 `fixed` 参数可以包含 `{ot}`, `{tid}`, `{sid}`, `{language}` 和 `{gender}`（“设置”中的训练家）、`{received}`（Received 文件夹）、`{stamp}`（运行开始时间），以及自 1.7 起的 `{keys}`（“设置”指定的 `prod.keys` 文件）。脚本的解析器若接受 `--keys`，即使不使用该令牌，也会收到该文件的路径。

### 状态卡片（1.8）

运行会在工具页面顶部、字段上方留下卡片，并为其文件库中的文件添加备注。`pokeldn.panel` 将它们打印为 `[panel]` 行，因此从源码运行和正式发布的应用中行为相同；运行结束后，应用将其保存在数据文件夹的 `plugin-panels/.json` 中，并随插件一起删除。在应用之外，仅打印该行，不执行其他操作。

```
from pokeldn import panel, plugins

icon = plugins.data_folder("my-plugin") / "icons" / "0100abcd.png"
panel.show("console", "Pokémon: Let's Go, Pikachu!", [
    "Group\tcapito27's Switch · 1 of 8 consoles",
    "System version\t23.0.1",
], image=icon, chips=[("Version", "1.0.2")], tone="ok")
panel.annotate("Game 1.0.2.nsp", state="ok", text="Every signature checks", image=icon)
```

| 调用 | 应用显示的内容 |
| --- | --- |
| `panel.show(id, title, lines=(), *, image=None, chips=(), tone="info")` | 卡片 `id`，替换此前相同 ID 下显示的卡片。每行可以是纯文本，或用 `labelvalue` 表示两列；标签块是一个 `(label, value)` 对；`tone` 可为 `info`, `ok`, `warning` 或 `error`，在标题旁显示图标 |
| `panel.clear(id)` | 移除卡片 |
| `panel.annotate(name, *, state="ok", text="", image=None)` | 标记文件库文件 `name`: `ok`, `bad` 或 `checking`，在其下显示一行文本，并用图像替换文件图标 |
| `panel.unannotate(name)` | 移除备注 |

| 限制 |  |
| --- | --- |
| 卡片 ID | 1 到 32 个字符，可用小写字母、数字、`-` 和 `_` |
| 每个插件的卡片数 | 8；超过后，新 ID 会被丢弃 |
| 一张卡片 | 标题最多 80 个字符，最多 12 行且每行最多 200 个字符，最多 6 个标签块且每侧最多 40 个字符 |
| 图像 | 插件数据文件夹或文件库中不超过 2 MB 的 PNG 或 JPEG；其他图像不会显示 |
| 备注 | 绑定文件名：重命名或删除文件会丢弃备注 |

超出这些限制的调用会在脚本中抛出 ValueError；应用无法读取的 `[panel]` 行会显示在会话输出中。

### 自定义游戏

```
api.add_game(Game("my-game", "My game", "Mine", "", (tool_one, tool_two)), icon="icon.png")
```

`Game(key, name, short, doc, tools)`；该游戏分区按顺序列出其工具，位于内置游戏下方。`api.add_tool("my-game", tool)` 可向其中继续添加工具。

### 无线电后端

无线电后端代替 ESP32 开发板传输无线消息。`api.add_radio(scheme, install, label)` 将它列在“插件”页面的“**无线电**”下；使用该后端启动的运行会在首次无线调用之前调用 `install(argument, log)`。

```
import contextlib
from ldn import wlan


def install(argument, log):
    @contextlib.asynccontextmanager
    async def factory():
        yield MyFactory()           # the interface of ldn.wlan.Factory
    wlan.set_factory(factory)


def register(api):
    api.add_radio("myradio", install, "My radio")
```

`pokeldn/ldn/esp32_wlan.py` 是开发板的工厂函数，也是无内核接口后端的参考实现。应用以 `POKELDN_RADIO=myradio:` 运行插件无线电后端，参数为空；在命令行中，参数则是冒号之后的内容。

### LDN 网络（1.7）

`pokeldn.ldn.network` 为插件加入或创建 LDN 网络，并向其提供无线电后端的 IPv4 协议栈。它需要不使用内核接口的无线电后端：ESP32 开发板或 ldnrs。

```
from pokeldn.ldn import network

with network.join(COMM_ID, keys=args.keys, password=PASSPHRASE, name="My game") as net:
    net.add_protocol(6, lambda src, dst, segment: segments.put((src, segment)))   # TCP, say
    while not net.send_ip(6, net.host_ip, first_segment):    # False until ARP finds the host
        time.sleep(0.1)
```

| 名称 | 含义 |
| --- | --- |
| `join(comm_id, *, keys, password, nickname, app_version, name, log, timeout)` | 扫描并加入通告 `comm_id` 的网络，不加入其他网络；`name` 是面向玩家的消息中使用的名称。抛出 `RuntimeError`，若没有网络应答 |
| `host(comm_id, *, keys, password, nickname, application_data, scene_id, app_version, max_participants, channel, protocol, log, timeout)` | 创建可供主机加入的网络 |
| `Network.ip`, `.mac`, `.host_ip`, `.broadcast`, `.ssid`, `.comm_id`, `.application_data` | 地址和广播通告：加入时为主机端的，作为主机端时为自身的 |
| `Network.participants` | 已在所创建网络中入座的站点，每项为 `.index`, `.ip`, `.mac`, `.name` |
| `Network.add_protocol(number, handler)`, `.remove_protocol(number)` | `handler(src_ip, dst_ip, payload)` 在无线电循环中接收发往本机、协议为 `number` 的每个重组后 IPv4 数据包：应将其入队并立即返回。UDP（17）仍由协议栈处理。处理函数的异常会被记录，并丢弃该包 |
| `Network.send_ip(protocol, dst_ip, payload)` | 一个 IPv4 数据包，以 1500 字节分片；`False`，并发送 ARP 请求，当 `dst_ip` 的地址未知时 |
| `Network.udp_socket(port)` | 网络上的 UDP 套接字：`sendto`, `recvfrom`, `setblocking`, `settimeout`, `fileno`, `close` |
| `Network.set_application_data(data)` | 所创建网络的新广播通告 |
| `Network.error`, `.close()` | 网络结束的原因（运行中为空）；离开网络。`Network` 是上下文管理器 |
| `pokeldn.ldn.radio_lost()` | 无线电后端退出进程的原因，或为空。随后运行以与玩家按“停止”相同的 `KeyboardInterrupt` 结束；此项用于区分两者 |

通过开发板传输时速率约为 0.5 MB/s；使用 `pokeldn.progress.show`.

### 对战服务器

对战服务器为主机端启动器运行团体战，使主机与程序的宝可梦共同参与同一场对战（[提供对战服务](sv_raid.md#serving-the-battle)）。目前只有《朱／紫》（`"sv"`）支持它。`api.add_battle_server(game, name, factory, label)` 用于注册；运行 `bin/sv_host.py --raid-serve NAME`（或仅使用 `--raid-serve`，选择首个已加载的服务器）时，会调用 `factory(bootstrap, partners)`，时机为主机发送对战引导数据之后，且不在网络循环中执行。`bootstrap` 是对战引导数据的字节内容，`partners` 是两个 NPC 伙伴的 0x158 字节队伍记录。返回对象如下：

| 成员 | 作用 |
| --- | --- |
| `start(now)` | 服务器在 `now` 秒时的第一帧；返回推动了对战的帧数 |
| `run(until)` | 按每秒 30 帧推进，直到 `until` 秒（至少一帧）；返回推动了对战的帧数 |
| `t` | 服务器时钟，以秒为单位 |
| `receive(slot, message)` | 站点消息，由 32 字节头部和消息体组成，来自对战槽位 `slot` |
| `sent(slot)` | 自上次调用以来，排队等待发给 `slot` 的消息，每条均为 32 字节头部加消息体 |

槽位 0 是程序的宝可梦，1 是首领，2 是主机，3 和 4 是伙伴。任一成员抛出异常都会停止对战服务；主机随后独立进行自己的对战。

```
def register(api):
    api.add_battle_server("sv", "mine", MyServer, "My raid battle")
```

### 打包与测试

```
python scripts/pack_plugin.py my-plugin --key ~/my-plugin-signing.pem
```

写入 `my-plugin-1.0.0.pokeplugin`，附带签名，并按与应用安装前相同的方式检查。隐藏文件和文件夹 `exclude = ["tests", "tools"]`，以及 `plugin.toml` 指定的名称都不会包含在软件包内。任何 zip 都可使用，只要 `plugin.toml` 位于顶层或某一个顶层文件夹中，且没有越出该文件夹的路径，也没有符号链接。

开发时可以跳过打包：在 `POKELDN_PLUGINS` 中指定文件夹，该进程及其启动的运行就会启用插件，无论“插件”页面如何显示。

```
POKELDN_PLUGINS=~/my-plugin python -m pokeldn --plugins
POKELDN_PLUGINS=~/my-plugin python -m pokeldn my-hello -- --name Blue
POKELDN_PLUGINS=~/my-plugin python gui/main.py
```

`--plugins` 列出找到的全部插件及加载失败原因。若插件在 `register` 中抛出异常、面向其他 API 版本或占用已被使用的键，则不会添加任何内容；其卡片显示错误，其他插件仍正常加载。插件也可以作为 Python 软件包分发，在 `pokeldn.plugins` 组中设置入口点，指定包含 `register`.

### 签名

`--key FILE` 使用作者的 Ed25519 密钥为软件包签名；密钥首次在 `FILE` 中创建，并打印其指纹（`ABCD-EFGH-IJKL-MNOP`）。软件包携带 `plugin.sig`：其中包含公钥，以及针对插件 ID、版本和其他每个文件 SHA-256 的签名。

| 应用检测到 | 显示或执行 |
| --- | --- |
| 签名与文件不匹配 | 拒绝文件：作者签名后内容被修改 |
| 此前未见过的已签名插件 | 显示指纹，并为该插件 ID 记住密钥 |
| 使用已记住密钥签名的更新 | “由同一作者签名” |
| 更新使用其他密钥签名，或旧版本有签名而更新无签名 | 显示红色警告，并要求第二次确认，之后才能安装 |
| 从未见过其签名版本的未签名插件 | “未签名” |

应保密并备份密钥文件：密钥丢失会让之后每个版本看起来都像来自他人，而任何持有密钥的人都能以作者身份签名。在插件页面公布指纹，供玩家与安装界面显示的指纹对比。首次安装无法证明作者身份；签名只能证明后续版本来自同一作者。

### 更新

`updates`，位于 `plugin.toml` 中，用于指定新版本的发布位置：

| `updates` | 应用读取的内容 |
| --- | --- |
| `https://github.com/OWNER/REPO` | 最新发行版：其标签（`v1.3.0` 或 `1.3.0`）及首个 `.pokeplugin` 资源文件 |
| 任何其他 HTTPS 地址 | JSON 文件 `{"version": "1.3.0", "url": "https://.../my-plugin-1.3.0.pokeplugin", "page": "..."}` |

在“设置”中开启“更新”后，应用会在启动时及按下“插件”页面刷新按钮时查询每个已安装插件的更新地址。若有新版本，“插件”菜单项会变绿，插件卡片上会显示“**更新至 1.3.0**”；点击后下载文件，并打开包含签名检查的安装界面。未经玩家确认，不会安装任何内容。仅对 `127.0.0.1` 和 `localhost` 接受 HTTP，以便在本地测试发行版。

## 语言包（1.5）

语言包是仅包含数据的文件夹插件。其 `name` 是“设置 → 应用语言”中的显示名称。其 `locale` 为语言标签；保存的选择通过以下值标识插件：`id`.

```
id = "community-zh-hans"
name = "简体中文"
version = "1.0.0"
api = "1.5"
locale = "zh-Hans"
strings = "strings.toml"
```

`strings.toml` 与 `plugin.toml` 位于同一目录。为每个带点的键加引号，让 TOML 将其读取为扁平表：

```
"bank.bank_676c47" = "宝可梦银行"
```

该文件只包含文本值。语言包不需要 Python 模块或 `register` 函数。安装、签名、作者密钥、移除和 `updates` 均与其他插件采用相同的软件包流程。无效 TOML、非文本值和无效格式语法会在安装前被拒绝。已安装语言包损坏时会显示加载错误，并回退为英语。

在“插件”页面安装语言包，再在“设置 → 应用语言”中选择它，并重启 pokeldn。选择语言包会启用其插件。英语始终可用。语言包缺失、停用或已移除时使用英语。训练家语言仍决定应用生成的宝可梦所用的语言。

每次查找都带有内联的英语默认值。缺少的键使用默认值；未使用的键没有影响。类似 `{value0}` 的命名占位符可在译文中调整位置。应保留其名称、转换标记和格式说明；`` 产生字面花括号。若译文中的占位符无法格式化，此次查找会使用英语默认值。

```
python scripts/extract_strings.py
python scripts/extract_strings.py --check
python scripts/pack_plugin.py examples/plugins/pseudo -o pseudo.pokeplugin
```

提取器写入 `pokeldn/app/data/strings.en.toml`，按键排序。测试会检查其是否与源码一致，并拒绝一个键对应两个英语默认值的情况。措辞变化时键保持不变。将模板复制到独立的插件仓库中，再翻译其值；省略的键无需维护。位于 `examples/plugins/pseudo` 的部分伪语言环境会为选定字符串加括号，其余保留，以测试回退逻辑。示例不包含在桌面软件包中。

### 附加资源（1.9）

API 1.9 的语言包可指定以下可选文件及文件夹，与 `plugin.toml` 位于同一目录。1.5 语言包仍然有效。安装、签名和更新对这些资源的处理方式与 `strings.toml` 相同，且所有路径都不得指向插件文件夹之外。

```
api = "1.9"
messages = "messages.toml"
templates = "templates.toml"
terms = "terms.toml"
help = "help.toml"
documents = "docs"
font_family = "Noto Sans CJK SC"
```

| 条目 | 键 | 值 |
| --- | --- | --- |
| `messages` | 模块的英语原文，逐字保留，花括号按字面含义处理 | 对应译文 |
| `templates` | 带命名字段的英语消息，`"Could not open {path}: {reason}"` | 包含相同字段的译文 |
| `terms` | 游戏术语（1 到 200 个字符，最多 10000 个术语），`"Squirtle"` | 对应译文 |
| `help` | `"TOOL-KEY:--option"`，某个工具的标志 | 该标志在“高级”选项卡中的说明 |
| `documents` | 一个文件夹，其中包含 `guide.md` 及 `docs/` 的各页面，并保留其名称 |  |
| `font_family` | 随应用捆绑或已安装的字体，最多 100 个字符 | 应用的文本字体；保留中日韩字体回退机制 |

`strings.toml` 仍通过 `t(key, English)` 提供应用自身控件的翻译。其他表翻译游戏模块、PKHeX 和插件生成并由控件显示的英语文本：标签、摘要、错误、礼物和团体战说明。消息先在 `messages` 中整条查找，再与 `templates` 匹配，然后逐句查找，最后在单词边界处替换每个 `terms` 条目。缺失条目会显示英语。

模板源文本最多 2048 个字符，包含 1 到 8 个简单命名字段，每个字段之后、下个字段之前必须有字面文本；不得包含转换标记、格式说明或属性访问。匹配不使用正则表达式，而按字面匹配，并优先匹配最长源文本，消息长度最多 4096 个字符。捕获值按原样显示，除非字段名以 `term`（按游戏术语及消息翻译）或 `message`（按消息翻译）开头，最大递归深度为 4。

若 PKHeX 支持语言包对应的语言，就会用该语言显示物种、招式、道具、特性、性格和球种名称（`ja`, `fr`, `it`, `de`, `es`, `ko`, `zh-Hans`, `zh-Hant`; `zh` 配合 `TW`, `HK` 或 `MO` 会读取 `zh-Hant`），并以该语言提供合法性报告。Flet 自带的对话框及文件选择器也遵循该语言环境。

文档阅读器和搜索在语言包提供对应页面时使用该页面，否则使用英语页面。若译文页面的标题数量与英语页面相同，就保留英语页面的标题锚点；否则在标题前使用一行 `` 指定锚点。前置元数据中的 `title` 用于修改侧边栏中的页面名称；目录树本身仍采用英语版本的结构。

供记录、文件或其他应用读取的内容保持英语：文件名、Bank 和队列摘要、GTS 列表、设置、会话日志（其中的 `[app]` 行在界面中显示为译文）、无线电脚本输出，以及 `[done]` 行。“设置”中的训练家语言仍决定应用生成的宝可梦所用的语言。

## 插件测试套件

`examples/plugins/test_kit`，使用 `scripts/pack_plugin.py` 打包，新增：

| 位置 | 工具 | 作用 |
| --- | --- | --- |
| 插件测试套件 | 自检 | 检查 API 版本、自身加载、导入内容、所有字段类型、训练家令牌、会话文件夹、数据文件夹（跨更新保留的运行计数器）、文件库及其中某文件的备注，以及无线电后端；逐项打印 PASS 或 FAIL，并在页面留下“上次自检”卡片 |
| 插件测试套件 | 模拟会话 | 打印交换步骤，并在每次交换时打印一行 `[done]`；按“停止”可正常结束 |
| 插件测试套件 | 故意失败 | 抛出异常，或以退出码 3 结束 |
| 火红与叶绿 | 来自插件的问候 | 与内置工具一同列出的插件工具 |
| 无线电 | 测试套件无线电后端 | 不安装也不传输任何内容；使用它启动的会话会说明这一点 |

## 版本

插件 API 包含主版本号和级别，写作 `1.1`。插件的 `api` 指定所需最低版本；应用会显示自身版本，位置为“插件”页面及 `python -m pokeldn --plugins`.

| API 变化 | 应用行为 |
| --- | --- |
| 新增功能 | 提高级别；需要更高级别的插件会被拒绝，并提示“请更新 pokeldn” |
| 移除功能或改变含义 | 提高主版本号 |
| 仍受支持的旧主版本 | `DEPRECATED`，位于 `pokeldn/plugins.py` 中，指定将停止支持它的发行版；插件仍可加载，其卡片和安装界面会说明此事 |
| 已停止支持的旧主版本 | `API_OLDEST` 超过其期限后，插件会被拒绝，并提示“请向作者索取较新版本” |

插件自身的 `version` 只与其已安装副本比较，用来显示更新、重新安装或降级。

| API | 新增内容 |
| --- | --- |
| 1.0 | `add_tool`, `add_game`, `add_radio`, `folder`, `version` |
| 1.1 | `api.data`, `api.level`, `pokeldn.plugins.data_folder(plugin_id)` |
| 1.2 | `pokeldn.popup` |
| 1.3 | 程序接口：构建器、礼物文件、PKHeX 和开发板 |
| 1.4 | Bank 导入、记录、目标游戏、出示内容和交换完成处理 |
| 1.5 | 语言包插件和字符串查找 |
| 1.6 | `add_battle_server` |
| 1.7 | `pokeldn.ldn.network`, `pokeldn.ldn.radio_lost`, `library` 和 `api.library`, `pokeldn.popup.choose`, `pokeldn.progress`，以及 `{keys}` 令牌 |
| 1.8 | `pokeldn.panel`, `library_sort` |
| 1.9 | 语言包消息、模板、术语、工具帮助、文档和字体偏好 |

## API，第 1 版

| 名称 | 含义 |
| --- | --- |
| `api.add_tool(game, tool)` | 添加一个 `Tool`，归入键为 `game`: `frlg`, `lgpe`, `swsh`, `bdsp`, `pla`, `sv`, `za` 的游戏，或插件添加的游戏 |
| `api.add_game(game, icon="")` | 添加包含工具的游戏分区 |
| `api.add_radio(scheme, install, label="")` | 添加无线电后端 |
| `api.add_battle_server(game, name, factory, label="")` | 添加团体战服务器（1.6） |
| `api.folder` | 插件文件夹（一个 `Path`）；Python 软件包则为 None |
| `api.version`, `api.level` | 应用运行的主版本号和级别，`1` 和 `8` |
| `api.data` | 跨更新保留的文件夹，首次使用时创建（1.1） |
| `pokeldn.plugins.data_folder(plugin_id)` | 从工具脚本中获取同一文件夹（1.1） |
| `api.library`, `pokeldn.plugins.library_folder(plugin_id)` | 玩家可见的文件夹，由 `plugin.toml` 的 `library` 指定，首次使用时创建（1.7，[文件库](#a-library-17)) |
| `Tool`, `Field`, `Game` | 应用的目录类型，导入来源为 `pokeldn.plugins` |
| `pokeldn.ldn.show_done()` | 打印将一次交换标记为完成的行 |
| `pokeldn.popup.acknowledge(title, text="", *, id, label="OK", on_ack, tone)` | 带一个按钮的弹窗；返回其 ID（1.2，[弹窗](gui.md#pop-ups)) |
| `pokeldn.popup.confirm(title, text, agree, disagree, *, id, on_agree, on_disagree, on_dismiss, tone)` | 带同意和不同意按钮的弹窗，按钮名称由调用方指定，Esc 或点击外部可关闭；返回其 ID（1.2） |
| `pokeldn.popup.choose(title, text, options, *, id, on_choice, on_dismiss, tone)` | 带 2 到 8 个选项按钮的弹窗；`on_choice(index)` 收到所按选项，Esc 或点击外部会触发 `on_dismiss`；返回其 ID（1.7） |
| `pokeldn.progress.show(done, total, title, unit="bytes")` | “会话”面板中的进度条；`unit` 可为 `bytes` 或 `items` (1.7) |
| `pokeldn.panel.show(id, title, lines=(), *, image, chips, tone)`, `clear(id)`, `annotate(name, *, state, text, image)`, `unannotate(name)` | 工具页面的状态卡片及文件库文件的备注（1.8，[状态卡片](#status-cards-18)) |
| `pokeldn.ldn.network` | 加入和创建 LDN 网络，并提供其 IPv4 协议栈（1.7，[LDN 网络](#ldn-networks-17)) |
| `pokeldn.ldn.radio_lost()` | 无线电后端退出运行的原因，或为空（1.7） |
| `pokeldn.popup.cancel(id)`, `available()`, `set_dispatcher(dispatch)` | 关闭弹窗并丢弃其回调；是否由应用显示弹窗；回调运行位置（1.2） |

本表及下一张表列出受支持的接口。插件从 pokeldn 导入的其他任何内容，都可能在任意发行版中改变。

## 程序接口（1.3；1.4 新增 Bank，1.5 新增语言包）

插件或基于 pokeldn 源码检出构建的独立程序（触屏前端、脚本），可以使用与应用相同的代码构建礼物和宝可梦，并管理开发板。在 API 主版本 1 内，这些名称保持其含义；`tests/test_plugin_surface.py` 会解析全部名称。

| 名称 | 含义 |
| --- | --- |
| `python -m pokeldn --list`, `python -m pokeldn TOOL -- ARGS` | 每个工具的键；并可运行其中一个工具，使用“设置”中的训练家及以下标记之后的参数：`--` |
| `pokeldn.app.i18n.t(key, default, **fmt)`, `select(plugin_id)` | 带内联英语默认值和命名格式化的字符串查找；通过插件 ID 选择已启用语言包，ID 为空则选择英语（1.5） |
| `pokeldn.app.catalog.GAMES` | 内置游戏，每个 `Game` 的 `.tools` 包含其 `Tool`：位于 `bin/` 下的脚本及其字段；应用传入的标志保持名称不变 |
| `pokeldn.pokemon.SERVICE.species(game)`, `.names(game, kind)` | 物种，以及游戏中的 `moves`, `items`, `bag`, `held` 或 `balls`，表示为 `{"id", "name"}` 列表 |
| `pokeldn.pokemon.SERVICE.options(game, species, trainer)` | 该物种的出示内容可以使用的形态、性格、特性、道具和球种 |
| `pokeldn.pokemon.SERVICE.make(game, species, trainer, level, shiny, nickname, version, options)` | 适用于该游戏的合法宝可梦；`options` 接受性格、特性、性别、携带道具、球种、亲密度、招式、个体值和基础点数；返回其各值及 `"file"`，即写入的路径 |
| `pokeldn.pokemon.SERVICE.paste(game, text, trainer)` | 位于 `text` 中的 Showdown 配置，每项表示为 `make` 的各值及其 `errors` |
| `pokeldn.pokemon.BuilderError` | PKHeX 拒绝或缺失时抛出，并附带面向玩家的说明句 |
| `pokeldn.pokemon.NATURES` | 按各记录保存的索引排列的 25 个性格名称 |
| `pokeldn.gifts.load(path, game=)`, `pokeldn.gifts.save(path, gift)` | 读取和写入一个 `.pokegift`, `.wc3` 或 `.wc8` ([神秘礼物文件](gifts.md)) |
| `pokeldn.swsh.gift_builder.KINDS`, `PRESETS`, `PRESET`, `OUTFITS` | 《剑／盾》构建器的礼物类型 `(key, label, icon)`、预设（`.key`, `.label`, `.group`, `.summary`, `.state`）和服装 |
| `pokeldn.swsh.gift_builder.blank(**changes)`, `record(state)`, `compile(state)`, `describe(state, name)` | 表单状态、其封装的 720 字节记录、其面向 `gifts.save` 的礼物，以及面向玩家的说明行；状态无效时抛出 `ValueError`，并指出字段。宝可梦状态接受 `nature`（0 到 24；未提供时由游戏随机生成） |
| `pokeldn.swsh.events.load()`, `by_key()`, `gift(key)` | 官方《剑／盾》活动卡片，以及由其中一张生成的礼物 |
| `pokeldn.frlg.gift.builder.KINDS`, `PRESETS`, `PRESET`, `GIVERS`, `CARTRIDGES` | 《火红／叶绿》构建器的类型、预设、发放卡片的人物，以及主机代码可作用的卡带 |
| `pokeldn.frlg.gift.builder.blank()`, `compile(state)`, `describe(state, name)` | 对神奇卡片、神奇新闻或主机代码提供相同功能 |
| `gui.board.ports()`, `identify(port, blink=)`, `detect_chip(port)` | 串口，以及开发板运行的内容：`.firmware`, `.firmware_version`, `.protocol`, `.current`（其协议与当前 pokeldn 相符） |
| `gui.board.download_firmware(say=)`, `image_for(kind, chip)`, `image_version(path)`, `flash(port, kind=)` | 发行版镜像及其 SHA-256 校验、芯片适用镜像、镜像版本，以及检查芯片后刷写镜像 |
| `pokeldn.app.bank.library()` | 默认 Bank 文件夹，表示为 `Path`；列出内容不会创建该文件夹（1.4） |
| `pokeldn.app.bank.Entry`, `Imported`, `ImportedPokemon` | 下文描述的 Bank 结果类型（1.4） |
| `pokeldn.app.bank.Imported.count(state)` | 处于该状态的导入结果数量（1.4） |
| `pokeldn.app.bank.entries(folder=)`, `find(entry_id, folder=)`, `data(entry)` | 按最新优先排列的记录、某条记录或 `None`，以及其原生字节内容（1.4） |
| `pokeldn.app.bank.import_file(path, trainers, folder=)` | 导入宝可梦文件或存档，不修改源文件；返回 `Imported` (1.4) |
| `pokeldn.app.bank.deposit(game, source, info, folder=)` | 将收到文件的副本及其 PKHeX 检查结果存入 Bank；返回 `Entry`，若该字节内容已入库则返回 `None`（1.4） |
| `pokeldn.pokemon.SERVICE.check(game, path)` | 使用 PKHeX 检查收到的原生记录；返回 `info` 字典，用于 `bank.deposit`，包括合法性判定（1.4） |
| `pokeldn.app.bank.destinations(entry, trainer)`, `offer(entry, game, trainer)` | 各游戏的转换可用性，以及转换为某个游戏格式的出示内容（1.4） |
| `pokeldn.app.bank.edit(entry, fields)`, `remove(entry_id, folder=)` | 编辑昵称、提升等级、招式或携带道具；返回更新后的 `Entry`；显式删除记录及其元数据（1.4） |
| `pokeldn.app.bank.TradeSession(offers, folder=)` | 为一次运行按顺序创建出示内容字典的快照，包括没有 Bank ID 的出示内容（1.4） |
| `pokeldn.app.bank.TradeSession.advance(count)` | 应用累计已确认交换次数；返回 `.completed`，即已处理的最大次数；重复或较旧的次数不会改动记录（1.4） |
| `pokeldn.app.received.trades_done(line)` | 启动器 `[done] trade N complete` 行中的累计次数，或 `None` (1.4) |

无论由应用还是 `python -m pokeldn` 启动，一次启动器运行都对应一个进程：应向其自身 PID 发送 SIGINT 停止，15 s 后再发送 SIGTERM。切勿按名称匹配启动器（`pkill -f`）：这也会终止其他程序启动的运行。

## Bank 集成（1.4）

外部 Python 前端使用 `pokeldn.app.bank`，与桌面版 Bank 使用同一模块。它自行管理出示队列及进程生命周期。应用设置、队列辅助功能和 Bank 元数据文件仍属于内部实现。转换使用现有 PKHeX 辅助程序；源码安装通过 `dotnet build -c Release services/pkhex`.

`Entry` 提供 `id`, `path`, `game`, `species_id`, `shiny`, `summary`, `legal`, `tracker`, `created`, `origin` 和 `home_tracker`. `game` 是目录键；`created` 是以秒为单位的 Unix 时间；`path` 是原生记录。`home_tracker` 为 `empty`, `made` 或空字符串，详见 [HOME tracker 设置](gui.md#the-home-tracker-setting).

`Imported` 提供 `name`, `save` 和 `pokemon`，以及 `count(state)`。每个 `ImportedPokemon` 包含 `where`, `species`, `species_id`, `shiny`, `state`, `game` 和 `detail`。状态为 `banked`, `already` 或 `refused`。拒绝按记录单独处理：某只宝可梦被拒绝，不影响存档中的其他记录导入。`trainers` 将游戏键映射为包含 `ot`, `tid`, `sid`, `language` 和 `gender` 的训练家字典，格式与宝可梦构建器接受的相同。导入会记住已导入的记录，包括之后被交换出去的记录。

`destinations` 返回以游戏为键的字典，每个值包含 `ok`, `reason` 和 `home_tracker`. `offer` 返回包含 `file`, `summary`, `species`, `shiny`, `legal`, `encounter`, `moves`, `report`, `home_tracker` 和 `bank`. `file` 指定已准备好的原生记录；`bank` 是源条目 ID。准备出示内容不会移除原始 Bank 记录。应保留出示文件，直到对应运行结束，并将它传给启动器的 `--offer-file` 参数。运行已入库的出示内容时不要使用 `--fresh-pid`，以保留其身份信息。桌面版命令构建器会自动处理；`python -m pokeldn TOOL` 只组装默认值，不接收 Bank 出示内容字典，因此启动 Bank 交换的前端应直接使用目录工具的脚本。

```
from pokeldn.app import bank, received

trainer = {"ot": "ASH", "tid": 1111, "sid": 2222, "language": 2, "gender": 0}
games = ("frlg", "lgpe", "swsh", "bdsp", "pla", "sv", "za")
result = bank.import_file("main", {game: trainer for game in games}, folder="tradebox-bank")
entry = next(iter(bank.entries(folder="tradebox-bank")), None)
if entry is None:
    raise ValueError("No Pokemon available in the Bank.")
routes = bank.destinations(entry, trainer)
if not routes["swsh"]["ok"]:
    raise ValueError(routes["swsh"]["reason"])
offer = bank.offer(entry, "swsh", trainer)
session = bank.TradeSession([offer], folder="tradebox-bank")

def on_launcher_line(line):
    count = received.trades_done(line)
    if count is not None:
        session.advance(count)
```

每次运行创建一个 `TradeSession`，严格遵循出示顺序，也包括不含 `bank` 键的生成内容。传入已确认的完成次数，切勿传入进程退出码或排队交换次数。失败或被停止的运行会将未完成记录保留在 Bank 中。累计次数允许跳过中间消息；超过快照出示内容数量的生成交换会计数，但不会移除额外记录。`advance` 对负数或非整数次数抛出 `ValueError`。每成功移除一条记录才会推进进度，因此发生 `OSError` 后可以用相同次数重试。

文件访问错误会抛出 `OSError`；PKHeX 失败、转换或编辑被拒绝时会抛出 `pokeldn.pokemon.BuilderError`. `deposit` 从 `pokeldn.pokemon.SERVICE.check` 获取检查数据，不再额外检查合法性；用户提供的存档和宝可梦文件通过 `import_file` 进入。带 `folder` 的方法接受路径，默认使用 `library()`。`data`, `edit`, `destinations` 和 `offer` 使用 `Entry` 携带的路径。在导入 pokeldn 之前设置 `POKELDN_DATA`，还可隔离辅助程序输出及前端的其他应用文件。

Bank 操作均为同步操作。应在前端 UI 线程之外执行 PKHeX 工作。同一时间一个 Bank 文件夹只能由一个写入方管理；不支持多个应用同时导入、编辑和交换。桌面应用处于活动状态时，TradeBox 应使用独立文件夹。外部队列自行丢弃已完成的出示内容；`TradeSession` 只修改 Bank。
