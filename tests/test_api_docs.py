"""Tests for :mod:`democreate.api_docs` — the deterministic API reference generator."""

from __future__ import annotations

import inspect
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


def test_signature_of_plain_function_is_verbatim() -> None:
    def f(a: int, b: str = "x") -> None: ...

    assert api_docs.signature_of(f) == str(inspect.signature(f))


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


def test_generate_is_deterministic_and_complete(tmp_path: Path) -> None:
    out1 = tmp_path / "api1.md"
    out2 = tmp_path / "api2.md"
    assert api_docs.generate(out1) == out1
    api_docs.generate(out2)

    text1 = out1.read_text(encoding="utf-8")
    assert text1 == out2.read_text(encoding="utf-8")
    assert text1.startswith("# API reference")
    assert "## `democreate.errors`" in text1
    assert "### Functions" in text1
    assert text1.endswith("\n")
