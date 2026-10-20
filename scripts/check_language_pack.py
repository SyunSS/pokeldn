#!/usr/bin/env python3
"""Check a language pack against the English defaults it translates: keys, placeholders and format
specifications (docs/plugins.md, Language packs). A translation that cannot be formatted would fall
back to English one lookup at a time, so this catches it before the pack ships."""
import argparse
import json
import re
import string
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMPLATE = ROOT / "pokeldn/app/data/strings.en.toml"
BUILT_IN = ROOT / "pokeldn/app/data/languages"


def english() -> dict[str, str]:
    """The English defaults tests/extract_strings.py keeps, without importing the app."""
    from scripts.extract_strings import extract
    return extract(ROOT)


def _fields(text: str) -> list[tuple[str, str, str | None, str | None]]:
    """(literal, name, format specification, conversion) for every field of a format string."""
    return [(literal, name, spec, conversion) for literal, name, spec, conversion in
            string.Formatter().parse(text)]


def check(folder: str | Path, defaults: dict[str, str] | None = None) -> tuple[list[str], list[str]]:
    """(errors, warnings) for one pack folder. Errors stop a pack shipping; warnings ask a human."""
    folder = Path(folder).resolve()
    errors: list[str] = []
    warnings: list[str] = []
    try:
        meta = tomllib.loads((folder / "plugin.toml").read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return [f"{folder}: plugin.toml does not read: {error}"], warnings
    from pokeldn import plugins
    from pokeldn.app import i18n, plugin_store
    plugin_id, locale = str(meta.get("id", "")), str(meta.get("locale", ""))
    if not plugin_store.ID.fullmatch(plugin_id):
        errors.append(f"plugin.toml: id {plugin_id!r} needs lowercase letters, digits, dots, dashes or underscores.")
    if not re.fullmatch(r"[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*", locale):
        errors.append(f"plugin.toml: locale {locale!r} is not a language tag such as zh-Hans.")
    if not isinstance(meta.get("name"), str) or not meta["name"]:
        errors.append("plugin.toml: name is the display name in Settings, App language.")
    state, message = plugins.compatibility(plugins.parse_api(meta.get("api")))
    if state in ("newer", "older"):
        errors.append(f"plugin.toml: {message}")
    if "strings" not in meta:
        errors.append('plugin.toml: strings = "strings.toml" names the file holding the text.')
        return errors, warnings

    def read(name):
        resource = (folder / name).resolve()
        if not resource.is_relative_to(folder):
            raise ValueError("Language pack resources must remain inside the plugin folder.")
        return resource.read_bytes()

    try:
        strings = i18n.read_pack(meta, read)
    except (OSError, ValueError) as error:
        return [*errors, f"{meta.get('strings')}: {error}"], warnings

    source = english() if defaults is None else defaults
    missing, extra = sorted(set(source) - set(strings)), sorted(set(strings) - set(source))
    if missing:
        errors.append(f"{len(missing)} English key(s) have no translation, such as {missing[0]!r}.")
    if extra:
        errors.append(f"{len(extra)} key(s) are not in the English defaults, such as {extra[0]!r}.")

    for key in sorted(set(strings) & set(source)):
        default, value = source[key], strings[key]
        try:
            # Only named fields matter: literal text is the translation's own, including a leading or
            # trailing space the language needs.
            wanted = [(name, spec, conversion) for _, name, spec, conversion in _fields(default) if name is not None]
            got = [(name, spec, conversion) for _, name, spec, conversion in _fields(value) if name is not None]
        except ValueError as error:
            errors.append(f"{key}: the translation has an invalid format string: {error}")
            continue
        if [name for name, _, _ in wanted] != [name for name, _, _ in got]:
            errors.append(f"{key}: placeholders are {[n for n, _, _ in wanted]}, "
                          f"the translation has {[n for n, _, _ in got]}.")
        elif wanted != got:
            errors.append(f"{key}: a placeholder's format specification or conversion changed.")
        if not value.strip():
            # A plural marker, an article or a space a language does not need may go, but not a
            # sentence: the app would show nothing where the English shows text.
            if len(re.findall(r"[A-Za-z]{2,}", default)) >= 3:
                errors.append(f"{key}: the translation is empty; the app would show nothing for it.")
            else:
                warnings.append(f"{key}: translated to nothing, dropping the English {default!r}.")
        elif value == default and re.search(r"[A-Za-z]{3}", default):
            warnings.append(f"{key}: untranslated ({default[:60]!r}).")
    return errors, warnings


def report(folder: Path, errors: list[str], warnings: list[str]) -> None:
    print(f"{folder.name}: {len(errors)} error(s), {len(warnings)} warning(s)")
    for line in errors:
        print(f"  error: {line}")
    for line in warnings:
        print(f"  warning: {line}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folders", nargs="*", help="language pack folders to check")
    parser.add_argument("--all", action="store_true", help="every language shipped with pokeldn")
    parser.add_argument("--json", action="store_true", help="the counts as JSON, for a build step")
    args = parser.parse_args()
    folders = [Path(path) for path in args.folders] or (
        sorted(p for p in BUILT_IN.iterdir() if (p / "plugin.toml").is_file()) if args.all else [])
    if not folders:
        parser.error("name a language pack folder, or --all")
    defaults, failed, results = english(), False, {}
    for folder in folders:
        errors, warnings = check(folder, defaults)
        results[str(folder)] = {"errors": errors, "warnings": warnings}
        if not args.json:
            report(folder, errors, warnings)
        failed = failed or bool(errors)
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
