"""Committed documentation must have resolvable local files and heading links."""
from __future__ import annotations

import re
import subprocess
import unicodedata
from pathlib import Path
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt


def _anchors(text: str) -> set[str]:
    tokens = MarkdownIt("commonmark").parse(text)
    result = set(re.findall(r'<a\s+(?:[^>]*\s)?(?:id|name)=[\"\']([^\"\']+)', text))
    counts: dict[str, int] = {}
    for index, token in enumerate(tokens):
        if token.type != "heading_open":
            continue
        title = tokens[index + 1].content.lower()
        slug = "".join(
            char for char in title
            if char in "_-" or char.isspace() or unicodedata.category(char)[0] in "LMN"
        ).replace(" ", "-")
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        result.add(slug if count == 0 else f"{slug}-{count}")
    return result


def test_documentation_local_navigation_resolves() -> None:
    root = Path(__file__).resolve().parent.parent
    names = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z", "*.md"],
        cwd=root, stdin=subprocess.DEVNULL, text=True,
    ).split("\0")
    failures: list[str] = []
    for name in filter(None, names):
        source = root / name
        if not source.is_file():
            continue
        for token in MarkdownIt("commonmark").parse(source.read_text(encoding="utf-8")):
            for child in token.children or []:
                if child.type not in {"link_open", "image"}:
                    continue
                target = child.attrGet("href" if child.type == "link_open" else "src")
                assert target is not None
                url = urlsplit(target)
                if url.scheme or url.netloc:
                    continue
                path = unquote(url.path)
                destination = root / path.lstrip("/") if path.startswith("/") else (
                    source.parent / path if path else source
                )
                if not destination.exists():
                    failures.append(f"{name}: missing file for {target}")
                elif url.fragment and destination.suffix == ".md":
                    if unquote(url.fragment) not in _anchors(destination.read_text(encoding="utf-8")):
                        failures.append(f"{name}: missing heading for {target}")
    assert failures == []
