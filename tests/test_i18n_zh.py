"""The languages shipped with pokeldn: discovery, the Settings choice, and the full-key translation.

A built-in pack is data only, like an installed one (docs/plugins.md, Language packs), so these tests
read it through the same loader and the same string lookups the app uses.
"""
import re
import string
from pathlib import Path
from types import SimpleNamespace

import pytest

from pokeldn import plugins
from pokeldn.app import i18n, paths, settings
from scripts.extract_strings import extract

ROOT = Path(__file__).resolve().parents[1]
PACK = i18n.LANGUAGES / "zh-hans"

# Translations that read the same in both languages: names, game codes, units, technical labels,
# shell commands and strings that are pure placeholders.
SAME_AS_ENGLISH = {
    "boards.wi_fi_mac_2fce70",                 # Wi-Fi MAC: the address, not a sentence
    "boards.sudo_usermod_ag_dialout_user_227ed4",   # a command to paste
    "pokemon.garchomp_choice_scarf_ability_rough_skin_evs_252_atk_4__556d7f",   # a Showdown set
}


@pytest.fixture(autouse=True)
def english(tmp_path, monkeypatch):
    """Each test starts in English with no plugins, then leaves the module as it found it."""
    monkeypatch.setattr(paths, "DATA", tmp_path / "data")
    monkeypatch.setenv("POKELDN_PLUGINS", "")
    plugins._reset()
    i18n.select()
    yield
    plugins._reset()
    i18n.select()


def translations() -> dict[str, str]:
    import tomllib
    return tomllib.loads((PACK / "strings.toml").read_text(encoding="utf-8"))


# Discovery

def test_the_pack_ships_beside_the_english_defaults():
    assert PACK.parent == i18n.LANGUAGES and PACK.name == "zh-hans"
    assert (PACK / "plugin.toml").is_file() and (PACK / "strings.toml").is_file()
    assert (i18n.LANGUAGES.parent / "strings.en.toml").is_file()


def test_a_language_shipped_with_the_app_is_found_without_installing_it():
    import tomllib
    meta = tomllib.loads((PACK / "plugin.toml").read_text(encoding="utf-8"))
    assert meta["name"] == "简体中文" and meta["locale"] == "zh-Hans"
    [found] = [p for p in i18n.bundled() if p.id == "zh-hans"]
    assert found.locale == "zh-Hans" and found.name == "简体中文" and not found.error
    assert found.version == meta["version"]
    assert len(found.translations) == len(extract())


def test_settings_offers_english_then_the_shipped_languages():
    offered = [(p.id, p.name) for p in i18n.language_packs()]
    assert ("zh-hans", "简体中文") in offered
    assert all(plugin_id and name for plugin_id, name in offered)


def test_choosing_a_shipped_language_needs_no_plugin():
    i18n.select("zh-hans")
    assert i18n.locale() == "zh-Hans"
    assert i18n.t("bank.bank_676c47", "Bank") == translations()["bank.bank_676c47"]
    i18n.select()
    assert i18n.locale() == "en" and i18n.t("bank.bank_676c47", "Bank") == "Bank"


def test_a_missing_key_or_placeholder_still_shows_english():
    i18n.select("zh-hans")
    assert i18n.t("no.such.key", "Hello {name}", name="Red") == "Hello Red"
    assert i18n.t("no.such.key", "Plain") == "Plain"
    # A translation whose placeholders cannot be formatted falls back to the English default.
    keys = translations()
    assert i18n.t("bank.edit_44b87f", "Edit {value0}", value0="Pikachu") == keys["bank.edit_44b87f"].format(
        value0="Pikachu")


def test_english_is_the_default_and_the_system_language_is_not_read(tmp_path, monkeypatch):
    """A new profile starts in English; the app never switches language on its own."""
    monkeypatch.setattr(settings, "PATH", tmp_path / "settings.json")
    assert settings.Settings().app_language == ""
    assert settings.load().app_language == ""
    assert i18n.locale() == "en"


def test_an_installed_pack_of_the_same_id_wins_over_the_shipped_one(tmp_path, monkeypatch):
    folder = tmp_path / "mine"
    folder.mkdir()
    (folder / "plugin.toml").write_text(
        'id = "zh-hans"\nname = "简体中文（我的）"\napi = "1.5"\nlocale = "zh-Hans"\nstrings = "strings.toml"\n',
        encoding="utf-8")
    (folder / "strings.toml").write_text('"bank.bank_676c47" = "我的银行"', encoding="utf-8")
    monkeypatch.setenv("POKELDN_PLUGINS", str(folder))
    i18n.select("zh-hans")
    assert i18n.t("bank.bank_676c47", "Bank") == "我的银行"
    assert i18n.locale() == "zh-Hans"


def test_a_broken_shipped_pack_falls_back_to_english(tmp_path, monkeypatch):
    folder = tmp_path / "languages"
    broken = folder / "zh-hans"
    broken.mkdir(parents=True)
    (broken / "plugin.toml").write_text(
        'id = "zh-hans"\napi = "1.5"\nlocale = "zh-Hans"\nstrings = "strings.toml"\n', encoding="utf-8")
    (broken / "strings.toml").write_text('"hello" = "你好 {missing"', encoding="utf-8")
    monkeypatch.setattr(i18n, "LANGUAGES", folder)
    monkeypatch.setattr(i18n, "_bundled_cache", ((), []))
    [found] = i18n.bundled()
    assert found.error and i18n.language_packs() == []
    i18n.select("zh-hans")
    assert i18n.locale() == "en" and i18n.t("hello", "Hello") == "Hello"
    monkeypatch.setattr(i18n, "_bundled_cache", ((), []))


# Coverage

def test_every_english_string_has_a_translation():
    english = extract()
    assert set(translations()) == set(english), (
        f"missing: {sorted(set(english) - set(translations()))[:5]}, "
        f"extra: {sorted(set(translations()) - set(english))[:5]}")


def test_translations_keep_every_placeholder_and_format_specification():
    english, chinese = extract(), translations()

    def fields(text):
        # Only named fields matter: literal text is the translation's own, including its spacing.
        return [(name, spec, conversion) for _, name, spec, conversion in string.Formatter().parse(text)
                if name is not None]

    problems = [key for key in english if fields(english[key]) != fields(chinese[key])]
    assert not problems, problems[:10]


def test_format_specifications_survive_translation():
    """Numbers, percentages and times keep the format the English asks for, so the value renders the
    same; only the words around them change."""
    english, chinese = extract(), translations()
    specs = {key: re.findall(r"\{[^}]*:[^}]*\}", value) for key, value in english.items()}
    specs = {key: found for key, found in specs.items() if found}
    assert len(specs) >= 15, "the English strings format numbers, percentages and times"
    for key, wanted in specs.items():
        assert re.findall(r"\{[^}]*:[^}]*\}", chinese[key]) == wanted, key


def test_the_pack_is_translated_rather_than_copied_english():
    """Every sentence is Chinese; only names, game codes, units and pure placeholders read the same."""
    english, chinese = extract(), translations()

    def prose(value: str) -> bool:
        """Three or more English words outside the placeholders: a sentence, not a name, a code, a
        shell command or a technical label."""
        literal = re.sub(r"\{[^}]*\}", "", value)
        if re.match(r"^\s*(sudo|apt|pip|python|git|brew|dnf|pacman|choco)\b", literal):
            return False
        return len(re.findall(r"[A-Za-z]{2,}", literal)) >= 3

    copied = [key for key, value in english.items()
              if prose(value) and chinese[key] == value and key not in SAME_AS_ENGLISH]
    assert not copied, f"{len(copied)} sentences are still English: {copied[:10]}"
    # And the great majority of entries carry Chinese characters.
    translated = sum(1 for value in chinese.values() if re.search(r"[\u4e00-\u9fff]", value))
    assert translated >= len(chinese) * 0.95, f"only {translated} of {len(chinese)} entries are Chinese"


def test_the_separators_read_naturally_in_chinese():
    chinese = translations()
    assert chinese["presentation.list_separator"] == "、"
    assert chinese["presentation.date_time_format"].startswith("%Y")


def test_a_plural_marker_drops_out_where_chinese_has_no_plural():
    """The Views append `plural_suffix` for a count other than one; Chinese shows the same word for
    both, so the pack translates the marker to nothing and each sentence reads right either way."""
    assert translations()["plugins.plural_suffix"] == ""
    i18n.select("zh-hans")
    for count in (1, 3):
        suffix = i18n.t("plugins.plural_suffix", "s") * (count != 1)
        assert i18n.t("plugins.tool_d0d814", "{value0} · {value1} tool{value2}",
                      value0="火红／叶绿", value1=count, value2=suffix) == f"火红／叶绿 · {count} 个工具"
    empty = [key for key, value in translations().items()
             if not value.strip() and key != "plugins.plural_suffix"]
    assert not empty, f"only a plural marker may translate to nothing: {empty[:5]}"


def test_the_wireless_transport_keeps_one_name_throughout():
    """`radio` is the transport the board or a plugin provides; one wording names it everywhere, so
    the Games page, the Plugins page and the phone's own copy read consistently."""
    english, chinese = extract(), translations()
    radio = {key: value for key, value in chinese.items() if re.search(r"\bradio\b", english[key], re.I)}
    assert len(radio) >= 10, "the app names the radio in many places"
    stray = [key for key, value in radio.items() if "通信方式" in value]
    assert not stray, f"one wording, not several: {stray[:5]}"
    missed = [key for key, value in radio.items() if "无线电" not in value]
    assert not missed, f"these name the radio differently: {missed[:5]}"


def test_the_pack_passes_its_own_checker():
    from scripts.check_language_pack import check
    errors, warnings = check(PACK, extract())
    assert not errors, errors[:10]
    # The warnings are the names, game codes and units that read the same in both languages.
    assert len(warnings) <= 40, warnings[:10]


# The Settings page

def test_the_settings_dropdown_lists_the_shipped_language_and_does_not_turn_on_a_plugin(tmp_path, monkeypatch):
    pytest.importorskip("flet")
    import flet as ft
    from gui.views.settings import SettingsView
    from pokeldn.app import settings as settings_module

    monkeypatch.setattr(settings_module, "PATH", tmp_path / "settings.json")
    chosen = settings_module.Settings()
    app = SimpleNamespace(settings=chosen, update=None, update_state="", update_listeners=[],
                          picker=None, page=None, ui=lambda fn: fn())
    view = SettingsView(app)

    def options(control):
        if isinstance(control, ft.Dropdown):
            yield control
        for child in [*(getattr(control, "controls", None) or []), getattr(control, "content", None)]:
            if isinstance(child, ft.Control):
                yield from options(child)
            elif isinstance(child, list):
                for item in child:
                    if isinstance(item, ft.Control):
                        yield from options(item)

    language = next(drop for drop in options(view.column) if any(
        option.key == "zh-hans" for option in drop.options))
    assert [(option.key, option.text) for option in language.options][:2] == [("", "English"), ("zh-hans", "简体中文")]

    view.save = lambda key, value: (setattr(chosen, key, value), chosen.save())
    view._language("zh-hans")
    assert chosen.app_language == "zh-hans"
    assert "zh-hans" not in chosen.plugins, "a language shipped with the app is not a plugin to turn on"
    assert settings_module.load().app_language == "zh-hans"


def test_choosing_a_community_pack_still_turns_it_on(tmp_path, monkeypatch):
    pytest.importorskip("flet")
    from gui.views.settings import SettingsView
    from pokeldn.app import settings as settings_module

    monkeypatch.setattr(settings_module, "PATH", tmp_path / "settings.json")
    chosen = settings_module.Settings()
    view = SettingsView.__new__(SettingsView)
    view.app = SimpleNamespace(settings=chosen)
    view.save = lambda key, value: (setattr(chosen, key, value), chosen.save())
    view._language("community-zh-hant")
    assert chosen.app_language == "community-zh-hant" and "community-zh-hant" in chosen.plugins


# The display language other programs are asked for

def test_pkhex_is_asked_for_simplified_chinese_names(monkeypatch):
    from gui.localization import DisplayService
    from pokeldn import pokemon

    asked = []

    def reply(request):
        asked.append(request.get("display_language", "en"))
        return {"names": [{"id": 25, "name": "皮卡丘" if request.get("display_language") else "Pikachu"}]}

    monkeypatch.setattr(pokemon.SERVICE, "_ask", reply)
    i18n.select("zh-hans")
    service = DisplayService()
    assert service.names("sv", "species") == [{"id": 25, "name": "皮卡丘"}]
    assert asked == ["zh-Hans"]
    from gui.localization import flet_locale
    pytest.importorskip("flet")
    configuration = flet_locale()
    assert configuration.current_locale.language_code == "zh"
    assert configuration.current_locale.script_code == "Hans"


# Packaging

# The Advanced options page

def test_every_advanced_option_is_described_in_chinese():
    """Games, Options, Advanced shows one paragraph per command-line flag. That text is argparse
    `help=` in bin/*.py, looked up in the pack's `messages` table (i18n.help_text), not in
    strings.toml: a missing sentence leaves the option English."""
    from gui.views.games import flags_of
    from pokeldn.app.catalog import GAMES
    i18n.select("zh-hans")
    leftover = []
    total = 0
    for game in GAMES:
        for tool in game.tools:
            for flag in flags_of(tool.script):
                if not flag.help:
                    continue
                total += 1
                if i18n.help_text(tool.key, flag.option, flag.help) == " ".join(flag.help.split()):
                    leftover.append(f"{tool.key} {flag.option}")
    assert total > 1800, f"the tools publish {total} described options"
    assert not leftover, f"{len(leftover)} options still read English: {leftover[:5]}"


def test_the_messages_table_keeps_the_protocol_identifiers_it_meets():
    """A translated `messages` key is replaced wherever the whole displayed string equals it, so an
    identifier translated by mistake would also change a flag's own value."""
    import tomllib
    messages = tomllib.loads((PACK / "messages.toml").read_text(encoding="utf-8"))
    for identifier in ("save-dump", "memory-scan", "flash-write", "rng-trace", "table-scan",
                       "create-mon", "call-chain", "sloop-svc", "BPRE", "3star", "sav1",
                       "square", "line", "fixed", "move", "in-room", "raw", "ldn"):
        assert messages.get(identifier, identifier) == identifier, identifier


def test_help_text_falls_back_to_english_for_a_sentence_the_pack_does_not_have():
    i18n.select("zh-hans")
    assert i18n.help_text("frlg-trade-host", "--out", "received-mon output path") != "received-mon output path"
    assert i18n.help_text("no-such-tool", "--nope", "a sentence nobody translated") == "a sentence nobody translated"


def test_the_session_panel_translates_the_apps_own_log_lines():
    """app_log() strips the "[app] " prefix and looks the rest up, so the pack's keys carry no prefix;
    a tool's own output and the [done] lines stay English (docs/plugins.md)."""
    from gui.localization import app_log
    i18n.select("zh-hans")
    assert app_log("[app] This firmware uses a different radio protocol. Update it on the Board page.") == \
        "[app] 本固件使用了不同的无线电协议。请在「开发板」页面更新它。"
    assert app_log("[app] Could not open /dev/ttyUSB0: busy") == "[app] 无法打开 /dev/ttyUSB0：busy"
    assert app_log("[app] /dev/ttyUSB0 runs the controller firmware.") == "[app] /dev/ttyUSB0 运行的是控制器固件。"
    # A tool's output and the completion line the console reads are never translated.
    assert app_log("[done] trade 1 complete") == "[done] trade 1 complete"
    assert app_log("some tool output in English") == "some tool output in English"


def test_a_desktop_build_ships_the_language_pack():
    """scripts/pack_app.py copies every tracked file under `pokeldn/`, so the pack travels with the
    program; a file outside those folders would need its own --add-data line."""
    import importlib.util
    import sys
    path = ROOT / "scripts" / "pack_app.py"
    spec = importlib.util.spec_from_file_location("pack_app_language", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    relative = PACK.relative_to(ROOT).as_posix()
    assert relative.startswith("pokeldn/")
    files = module.runtime_files()
    assert "pokeldn/app/data/strings.en.toml" in files, "the folder holding the pack is packaged"
    source = path.read_text(encoding="utf-8")
    assert '"pokeldn/"' in source


def test_the_mobile_builds_stage_the_whole_package():
    """Android and iOS copy the `pokeldn` package, so the pack travels with it (examples/)."""
    for script in (ROOT / "examples/android/stage.py", ROOT / "examples/ios/build.py"):
        source = script.read_text(encoding="utf-8")
        assert "'pokeldn'" in source and "ls-files" in source
