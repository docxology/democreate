"""Tests for :mod:`democreate.manuscript` — the manuscript build gates and helpers."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from democreate.manuscript import (
    build_manuscript,
    defined_bib_keys,
    extract_preamble,
    figure_insertions,
    pick_engine,
    used_citation_keys,
)


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_extract_preamble_strips_latex_fence(tmp_path: Path) -> None:
    preamble = _write(tmp_path / "preamble.md", "```latex\n\\usepackage{fontspec}\n```")
    out = tmp_path / "preamble.tex"
    extract_preamble(preamble, out)
    assert out.read_text(encoding="utf-8") == "\\usepackage{fontspec}\n"


def test_extract_preamble_passes_unfenced_through(tmp_path: Path) -> None:
    preamble = _write(tmp_path / "preamble.md", "\\usepackage{fontspec}\n")
    out = extract_preamble(preamble, tmp_path / "preamble.tex")
    assert out == tmp_path / "preamble.tex"
    assert out.read_text(encoding="utf-8") == "\\usepackage{fontspec}\n"


def test_defined_bib_keys(tmp_path: Path) -> None:
    bib = _write(
        tmp_path / "references.bib",
        "@article{smith2024,\n  title={X},\n}\n\n@inproceedings{ jones25 ,\n}\n",
    )
    assert defined_bib_keys(bib) == {"smith2024", "jones25"}


def test_used_citation_keys_excludes_crossrefs_and_code(tmp_path: Path) -> None:
    ch = _write(
        tmp_path / "01_ch.md",
        "Prose cites [@smith2024] and @jones25 inline; see @fig:one and [@sec:two].\n"
        "Fenced LaTeX does not count:\n```latex\n\\cite{fenced}\n```\n"
        "Inline `@coderef` neither.\n",
    )
    assert used_citation_keys([ch]) == {"smith2024", "jones25"}


def test_figure_insertions_matches_paths_with_bracketed_alt(tmp_path: Path) -> None:
    a = _write(tmp_path / "a.md", "![Alt [@sec:x] text](figures/one.png){#fig:one}\n")
    b = _write(tmp_path / "b.md", "![two](figures/sub/two.png)\nno figure here\n")
    assert figure_insertions([a, b]) == ["figures/one.png", "figures/sub/two.png"]


def test_pick_engine_prefers_first_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        shutil, "which", lambda name: None if name == "tectonic" else f"/usr/bin/{name}"
    )
    assert pick_engine() == "xelatex"


def test_pick_engine_raises_when_none_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda name: None)
    with pytest.raises(SystemExit, match="no PDF engine found"):
        pick_engine()


def test_build_manuscript_requires_pandoc(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(shutil, "which", lambda name: None)
    with pytest.raises(SystemExit, match="pandoc not found on PATH"):
        build_manuscript(
            config=tmp_path / "config.yaml",
            manuscript_dir=tmp_path,
            output=tmp_path / "out.pdf",
        )


def test_build_manuscript_fails_on_missing_chapter(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/bin/{name}")
    cfg = _write(
        tmp_path / "config.yaml",
        "chapters: [00_absent.md]\nbibliography: references.bib\n",
    )
    with pytest.raises(SystemExit, match="missing chapter files"):
        build_manuscript(config=cfg, manuscript_dir=tmp_path, output=tmp_path / "out.pdf")


def test_build_manuscript_citation_gate_hard_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/bin/{name}")
    _write(tmp_path / "00_ch.md", "Cites [@ghost2024].\n")
    _write(tmp_path / "references.bib", "@article{real2024,\n}\n")
    cfg = _write(tmp_path / "config.yaml",
                 "chapters: [00_ch.md]\nbibliography: references.bib\n")
    with pytest.raises(SystemExit, match="unresolved citation keys"):
        build_manuscript(config=cfg, manuscript_dir=tmp_path, output=tmp_path / "out.pdf")


PANDOC = shutil.which("pandoc") is not None and shutil.which("pandoc-crossref") is not None


@pytest.mark.backend
@pytest.mark.skipif(not PANDOC, reason="pandoc + pandoc-crossref not on PATH")
def test_build_manuscript_gates_pass_and_check_skips_pdf(tmp_path: Path) -> None:
    _write(
        tmp_path / "00_ch.md",
        "Intro [@real2024].\n\n![Alt text](figures/one.png){#fig:one}\n",
    )
    _write(tmp_path / "references.bib", "@article{real2024,\n  title={T},\n}\n")
    _write(tmp_path / "preamble.md", "```latex\n\\usepackage{fontspec}\n```\n")
    cfg = _write(
        tmp_path / "config.yaml",
        "chapters: [00_ch.md]\nbibliography: references.bib\npreamble: preamble.md\n"
        "paper:\n  title: T\nauthors:\n  - name: A\n",
    )
    rc = build_manuscript(
        config=cfg, manuscript_dir=tmp_path, output=tmp_path / "out" / "m.pdf", check=True
    )
    assert rc == 0
    assert (tmp_path / "out" / "preamble.tex").read_text(encoding="utf-8") == (
        "\\usepackage{fontspec}\n"
    )


@pytest.mark.backend
@pytest.mark.skipif(not PANDOC, reason="pandoc + pandoc-crossref not on PATH")
def test_build_manuscript_figure_gate_catches_dropped_figure(tmp_path: Path) -> None:
    # The markdown defect the gate exists for: the image sits inside a fenced
    # code block, so Pandoc never emits an \includegraphics for it.
    _write(tmp_path / "00_ch.md", "```\n![Alt](figures/gone.png){#fig:one}\n```\n")
    _write(tmp_path / "references.bib", "@article{real2024,\n}\n")
    _write(tmp_path / "preamble.md", "```latex\n\\usepackage{fontspec}\n```\n")
    cfg = _write(tmp_path / "config.yaml",
                 "chapters: [00_ch.md]\nbibliography: references.bib\n")
    with pytest.raises(SystemExit, match="figure gate"):
        build_manuscript(
            config=cfg, manuscript_dir=tmp_path, output=tmp_path / "out" / "m.pdf",
            check=True,
        )
