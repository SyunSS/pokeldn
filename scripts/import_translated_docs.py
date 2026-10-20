#!/usr/bin/env python3
"""Turn the translated offline docs site into the Markdown pages a language pack ships.

The pack's `documents` folder holds a page per docs/*.md file, and the app's reader keeps the English
page's heading anchors when a translation has as many headings (docs/plugins.md, Additional
resources). This reads each page's <main> from the offline build and converts its block elements back
to Markdown: headings, paragraphs, lists (including the code blocks the docs nest inside a list item),
tables, preformatted blocks and quotes.

    python scripts/import_translated_docs.py <offline-site> pokeldn/app/data/languages/zh-hans/docs
"""
import argparse
import html
import json
import re
import sys
from pathlib import Path

MAIN = re.compile(r"<main>(.*?)</main>", re.S)
TITLE = re.compile(r"<title>(.*?)\s*\|.*?</title>", re.S)
# The heading's own anchor link, an <svg>: it says nothing in Markdown.
ANCHOR = re.compile(r'<a[^>]*class="anchor-heading"[^>]*>.*?</a>', re.S)
CODE = re.compile(r"<pre[^>]*>(.*?)</pre>", re.S)
TAG = re.compile(r"<[^>]+>")
# The block elements a page is made of, in document order.
BLOCK = re.compile(r"<(h[1-6]|p|ul|ol|table|pre|blockquote)\b([^>]*)>(.*?)</\1>", re.S)
LIST_ITEM = re.compile(r"<li\b[^>]*>(.*?)</li>", re.S)


def unescape(text: str) -> str:
    return html.unescape(TAG.sub("", text))


def inline(text: str) -> str:
    """Inline Markdown: code spans, links, emphasis; whitespace collapses as HTML collapses it."""
    text = ANCHOR.sub("", text)
    text = re.sub(r"<code[^>]*>(.*?)</code>",
                  lambda m: "`" + unescape(m.group(1)).replace("`", "\\`") + "`", text, flags=re.S)
    text = re.sub(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                  lambda m: f"[{inline(m.group(2))}]({link(m.group(1))})", text, flags=re.S)
    text = re.sub(r"<(strong|b)>(.*?)</\1>", r"**\2**", text, flags=re.S)
    text = re.sub(r"<(em|i)>(.*?)</\1>", r"*\2*", text, flags=re.S)
    text = re.sub(r"<br\s*/?>", "  \n", text)
    text = re.sub(r"\s+", " ", html.unescape(TAG.sub("", text))).strip()
    # A literal <name> in prose would open an HTML tag; the English page escapes the angle bracket.
    return re.sub(r"(?<!\\)<(?=[A-Za-z/])", r"\\<", text)


def external_map(site: Path) -> dict[str, str]:
    """The offline build saves an outside page beside the site and links it by a local file; the app
    shows the original address instead, which opens in a browser (the build's external-map.json)."""
    try:
        saved = json.loads((site / "external-map.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    # The page links a saved copy relatively, so match on its name, with or without "./".
    return {local.removeprefix("./"): original for original, local in saved.items() if isinstance(local, str)}


EXTERNAL: dict[str, str] = {}
# A link the build could not fetch joins the reading report instead of the page it names. The English
# page's own address for that spot is filled in afterwards, from `fallback_external()`.
OFFLINE = "https://pokeldn.invalid/unavailable"


def link(href: str) -> str:
    """The site's own pages are the .md pages the app's reader resolves: a relative address, and the
    absolute form the site links back to itself with. Another site keeps its address untouched."""
    href = html.unescape(href)
    saved = EXTERNAL.get(href.removeprefix("./"))   # a saved copy of a page on another site
    if saved:
        return saved
    # The build's own pages that the pack does not ship: the reading report, and its copies of the
    # repository files, which the docs link by path.
    if href.startswith("assets/source/"):
        return "../" + href.removeprefix("assets/source/")
    if href.startswith("offline-report."):
        return OFFLINE
    if href.startswith("/pokeldn/"):
        return re.sub(r"\.html(#|$)", r".md\1", href.removeprefix("/pokeldn/"))
    if href.startswith("#"):
        return href
    site = re.match(r"^(?:https://decryptu\.github\.io)?/pokeldn/(.+)$", href)
    if site:
        return re.sub(r"\.html(#|$)", r".md\1", site.group(1))
    if re.match(r"^[a-z]+://", href):
        return href
    return re.sub(r"\.html(#|$)", r".md\1", href)


def code_block(block: str) -> str:
    """A fenced block; the site marks every one `language-plaintext` unless a language was asked for."""
    code = re.search(r"<code[^>]*>(.*?)</code>", block, re.S)
    body = unescape(code.group(1) if code else re.sub(r"</?pre[^>]*>", "", block))
    cls = re.search(r'class="[^"]*language-([\w+-]+)', block)
    language = cls.group(1) if cls else ""
    language = "" if language in ("plaintext", "highlighter-rouge") else language
    return f"```{language}\n{body.rstrip()}\n```"


def table(block: str) -> str:
    rows = [[inline(cell) for cell in re.findall(r"<t[hd]\b[^>]*>(.*?)</t[hd]>", row, re.S)]
            for row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", block, re.S)]
    rows = [row for row in rows if row]
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    rows = [row + [""] * (width - len(row)) for row in rows]
    lines = ["| " + " | ".join(rows[0]) + " |", "|" + "|".join(" --- " for _ in range(width)) + "|"]
    lines += ["| " + " | ".join(row) + " |" for row in rows[1:]]
    return "\n".join(lines)


def blocks(source: str, depth: int = 0) -> list[str]:
    """The Markdown for each block element in `source`, in order."""
    out = []
    for match in BLOCK.finditer(source):
        tag, attrs, body = match.group(1), match.group(2), match.group(3)
        if tag.startswith("h"):
            title = inline(body)
            if title:
                out.append("#" * int(tag[1]) + " " + title)
        elif tag == "p":
            text = inline(body)
            if text:
                out.append(text)
        elif tag in ("ul", "ol"):
            text = listing(body, tag == "ol", depth)
            if text:
                out.append(text)
        elif tag == "table":
            text = table(match.group(0))
            if text:
                out.append(text)
        elif tag == "pre":
            out.append(code_block(match.group(0)))
        elif tag == "blockquote":
            text = "\n".join("> " + line for line in inline(body).splitlines())
            if text.strip("> "):
                out.append(text)
    return out


def listing(body: str, ordered: bool, depth: int = 0) -> str:
    """A list's Markdown. An item may hold paragraphs and code blocks of its own, which the docs use
    for the command that produces a measurement, so those keep their lines under the marker."""
    indent = "  " * depth
    out = []
    for number, item in enumerate(LIST_ITEM.findall(body), 1):
        marker = f"{number}." if ordered else "-"
        parts = blocks(item, depth + 1)
        head, rest = "", []
        for part in parts:
            if not head and not part.startswith("```") and not part.startswith("|"):
                head = " ".join(part.splitlines())
            else:
                rest.append(part)
        out.append(f"{indent}{marker} {head}".rstrip())
        for part in rest:
            for line in part.splitlines():
                out.append(f"{indent}  {line}" if line else "")
    return "\n".join(out)


# A section page's child list ("目录") is generated from the navigation, not written in the page;
# the reader builds its own tree, so the copied list would add a heading the English page lacks.
CONTENTS = re.compile(r'<hr\s*/?>\s*<h[1-6][^>]*class="text-delta"[^>]*>.*?</h[1-6]>\s*<ul\b.*?</ul>', re.S)


def convert(main_html: str, english: str = "") -> str:
    """The page's Markdown; `english` supplies the address of a link the build could not fetch."""
    global OFFLINE
    markdown = "\n\n".join(blocks(CONTENTS.sub("", main_html))) + "\n"
    if OFFLINE in markdown:
        found = [u for u in re.findall(r"\]\((https?://[^)\s]+)\)", english)
                 if "silabs.com" in u or "silicon" in u.lower()]
        markdown = markdown.replace(OFFLINE, found[0] if found else "https://decryptu.github.io/pokeldn/")
    return markdown


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", help="the offline build's folder")
    parser.add_argument("out", help="the folder to write the Markdown pages into")
    parser.add_argument("--docs", default="docs", help="the English docs folder, for the front matter")
    args = parser.parse_args()
    site, out, docs = Path(args.site), Path(args.out), Path(args.docs)
    EXTERNAL.update(external_map(site))
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for page in sorted(site.glob("*.html")):
        english = docs / f"{page.stem}.md"
        if not english.is_file():          # index, the report, and a page the pack does not ship
            continue
        text = page.read_text(encoding="utf-8")
        main_html = MAIN.search(text)
        if not main_html:
            print(f"{page.name}: no <main>", file=sys.stderr)
            continue
        title = TITLE.search(text)
        front = english.read_text(encoding="utf-8").split("\n---\n")[0]
        if title:
            front = re.sub(r"(?m)^title:.*$", f"title: {title.group(1).strip()}", front)
        (out / page.stem).with_suffix(".md").write_text(
            f"{front}\n---\n\n" + convert(main_html.group(1), english.read_text(encoding="utf-8")),
            encoding="utf-8")
        written.append(page.stem)
    print(f"wrote {len(written)} pages into {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
