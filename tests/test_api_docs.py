"""Tests for :mod:`democreate.api_docs` — the deterministic API reference generator."""

from __future__ import annotations

import subprocess
import sys
import types
from pathlib import Path

import typer

from democreate import api_docs
from democreate import errors as errors_mod


def test_summary_returns_first_nonempty_line_or_placeholder() -> None:
    def documented() -> None:
        """First line here.

        Rest ignored.
        """

    class NoDoc:
        pass

    assert api_docs.summary(documented) == "First line here."
    assert api_docs.summary(NoDoc()) == "_(no docstring)_"


def test_is_public() -> None:
    assert api_docs.is_public("Demo")
    assert not api_docs.is_public("_private")


def test_signature_of_cleans_typer_sentinel_default() -> None:
    def cmd(name: str = typer.Option("world", help="Greeting target")) -> None:
        """Greet."""

    sig = api_docs.signature_of(cmd)
    assert "OptionInfo" not in sig
    assert "0x" not in sig
    assert "world" in sig
    assert sig == api_docs.signature_of(cmd)


def test_signature_of_typer_required_param_stays_required() -> None:
    def cmd(name: str = typer.Option(..., help="Who to greet")) -> None:
        """Greet."""

    sig = api_docs.signature_of(cmd)
    assert "OptionInfo" not in sig
    assert "0x" not in sig
    # A required parameter renders without a default value.
    assert "name" in sig


def test_module_anchor() -> None:
    assert api_docs.module_anchor("democreate.narration.tts") == "democreatenarrationtts"


def test_members_regular_module_keeps_only_local_public() -> None:
    mod = types.ModuleType("fake_mod")

    def local() -> None:
        """Local."""

    def foreign() -> None:
        """Foreign."""

    local.__module__ = "fake_mod"
    foreign.__module__ = "somewhere_else"
    mod.local = local  # type: ignore[attr-defined]
    mod.foreign = foreign  # type: ignore[attr-defined]
    mod._private = local  # type: ignore[attr-defined]

    assert api_docs.members(mod, "function") == [("local", local)]


def test_members_facade_keeps_only_exported_names() -> None:
    mod = types.ModuleType("democreate")

    def exported() -> None:
        """Exported."""

    def hidden() -> None:
        """Hidden."""

    mod.exported = exported  # type: ignore[attr-defined]
    mod.hidden = hidden  # type: ignore[attr-defined]
    mod.__all__ = ["exported"]  # type: ignore[attr-defined]

    assert api_docs.members(mod, "function") == [("exported", exported)]


def test_members_real_module_lists_defined_public_classes() -> None:
    names = [name for name, _ in api_docs.members(errors_mod, "class")]
    assert "DemoCreateError" in names
    assert all(not n.startswith("_") for n in names)
    assert names == sorted(names)


def test_generated_reference_is_identical_across_processes(tmp_path: Path) -> None:
    """Fresh interpreters must publish the same callable-default representation."""
    outputs = [tmp_path / "api1.md", tmp_path / "api2.md"]
    script = (
        "import sys; from pathlib import Path; "
        "from democreate.api_docs import generate; generate(Path(sys.argv[1]))"
    )
    for output in outputs:
        subprocess.run(
            [sys.executable, "-B", "-c", script, str(output)],
            check=True,
            stdin=subprocess.DEVNULL,
            timeout=60,
        )
    assert outputs[0].read_bytes() == outputs[1].read_bytes()


def test_generated_reference_links_resolve_in_commonmark(tmp_path: Path) -> None:
    """Module navigation must work without a Pandoc-only heading extension."""
    import re
    from html.parser import HTMLParser

    from markdown_it import MarkdownIt

    class Headings(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.collecting = False
            self.text = ""
            self.anchors: set[str] = set()

        def handle_starttag(self, tag, attrs) -> None:
            if tag == "h2":
                self.collecting = True
                self.text = ""

        def handle_data(self, data) -> None:
            if self.collecting:
                self.text += data

        def handle_endtag(self, tag) -> None:
            if tag == "h2":
                self.anchors.add(
                    re.sub(r"[^a-z0-9_-]", "", self.text.lower().replace(" ", "-"))
                )
                self.collecting = False

    path = tmp_path / "api.md"
    api_docs.generate(path)
    html = MarkdownIt("commonmark").render(path.read_text())
    headings = Headings()
    headings.feed(html)
    targets = set(re.findall(r'href="#([^"]+)"', html))
    assert targets - headings.anchors == set()


def test_reference_includes_public_demo_factory_methods() -> None:
    """Consumers need the constructors used to load persisted Demo artifacts."""
    from markdown_it import MarkdownIt

    tokens = MarkdownIt("commonmark").parse(api_docs.render_module("democreate.schema"))
    names = {
        child.content.split("(", 1)[0]
        for token in tokens
        for child in token.children or []
        if child.type == "code_inline"
    }
    assert {"from_dict", "from_json"} <= names
