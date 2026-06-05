#!/usr/bin/env python
"""Build the DemoCreate manuscript PDF from its declarative ``config.yaml``.

This is the reproducible front door for the academic write-up under
``manuscript/``. It reads the chapter order, metadata, bibliography, and build
gates from ``manuscript/config.yaml`` (the single source of truth) and drives
Pandoc — with ``pandoc-crossref`` for ``@fig:``/``@sec:`` cross-references and
``--citeproc`` for ``[@key]`` citations — through a XeLaTeX-class engine
(``tectonic`` by default) to a single PDF.

Two build gates protect "properly rendering":

* **Citation gate** (``fail_on_missing`` in the config): every ``[@key]`` used
  in a chapter must resolve to an entry in ``references.bib``; an unresolved key
  is a hard failure, not a silent ``[?]``.
* **Figure gate**: every ``![...](figures/x.png){#fig:x}`` insertion in the
  chapters must survive into the generated LaTeX as an ``\\includegraphics`` —
  this catches the markdown defects (e.g. a code fence closed on the same line
  as following prose) that silently drop figures from the concatenated build.

    uv run python scripts/build_manuscript.py            # build manuscript/output/*.pdf
    uv run python scripts/build_manuscript.py --check     # gates only, no PDF
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

_REPO = Path(__file__).resolve().parents[1]
_MANUSCRIPT = _REPO / "manuscript"

# Engines that understand the Unicode glyphs + fontspec the preamble relies on,
# in preference order. The first one found on PATH is used.
_PDF_ENGINES = ("tectonic", "xelatex", "lualatex")


def _load_config(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _extract_preamble(preamble_md: Path, out_tex: Path) -> Path:
    """Strip the ```latex fence from ``preamble.md`` into a raw ``.tex`` header."""
    lines = preamble_md.read_text(encoding="utf-8").splitlines()
    if lines and lines[0].lstrip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].lstrip().startswith("```"):
        lines = lines[:-1]
    out_tex.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_tex


def _defined_bib_keys(bib: Path) -> set[str]:
    return set(re.findall(r"^@\w+\{\s*([^,\s]+)", bib.read_text(encoding="utf-8"), re.M))


def _used_citation_keys(chapters: list[Path]) -> set[str]:
    """Citation keys actually used in prose (``[@key]`` / ``@key``), excluding
    cross-reference prefixes (``@fig:``/``@sec:``/``@tbl:``/``@eq:``)."""
    keys: set[str] = set()
    for ch in chapters:
        text = ch.read_text(encoding="utf-8")
        # Drop fenced code and inline code so LaTeX examples (\cite{key}) don't count.
        text = re.sub(r"```.*?```", "", text, flags=re.S)
        text = re.sub(r"`[^`]*`", "", text)
        for m in re.findall(r"(?<![\w@])@([A-Za-z][\w:+-]*)", text):
            if m.split(":", 1)[0] not in {"fig", "sec", "tbl", "eq"} or ":" not in m:
                if not m.startswith(("fig:", "sec:", "tbl:", "eq:")):
                    keys.add(m)
    return keys


def _figure_insertions(chapters: list[Path]) -> list[str]:
    """The ``figures/x.png`` paths inserted as images across the chapters."""
    found: list[str] = []
    for ch in chapters:
        # Match the ](figures/x.png) tail; alt text may itself contain ] (e.g. [@sec:x]).
        found += re.findall(r"\]\((figures/[^)]+)\)", ch.read_text(encoding="utf-8"))
    return found


def _pick_engine() -> str:
    for eng in _PDF_ENGINES:
        if shutil.which(eng):
            return eng
    raise SystemExit(
        f"no PDF engine found (looked for {', '.join(_PDF_ENGINES)}); install tectonic"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=Path, default=_MANUSCRIPT / "config.yaml")
    ap.add_argument("--check", action="store_true",
                    help="run the citation + figure gates only; do not build the PDF")
    ap.add_argument("-o", "--output", type=Path,
                    default=_MANUSCRIPT / "output" / "democreate_manuscript.pdf")
    args = ap.parse_args()

    if not shutil.which("pandoc"):
        raise SystemExit("pandoc not found on PATH")
    if not shutil.which("pandoc-crossref"):
        raise SystemExit("pandoc-crossref not found on PATH (needed for @fig/@sec refs)")

    cfg = _load_config(args.config)
    chapters = [_MANUSCRIPT / c for c in cfg["chapters"]]
    missing_files = [c for c in chapters if not c.is_file()]
    if missing_files:
        raise SystemExit(f"missing chapter files: {[str(c) for c in missing_files]}")
    bib = _MANUSCRIPT / cfg["bibliography"]

    # --- Citation gate -----------------------------------------------------
    used = _used_citation_keys(chapters)
    defined = _defined_bib_keys(bib)
    unresolved = sorted(used - defined)
    if unresolved and cfg.get("fail_on_missing", True):
        raise SystemExit(f"unresolved citation keys (not in {bib.name}): {unresolved}")
    print(f"citations: {len(used)} used, {len(defined)} defined, {len(unresolved)} unresolved")

    # --- Build the LaTeX once so the figure gate inspects the real output --
    paper = cfg.get("paper", {})
    authors = ", ".join(a["name"] for a in cfg.get("authors", []))
    preamble = _extract_preamble(_MANUSCRIPT / cfg.get("preamble", "preamble.md"),
                                 args.output.parent / "preamble.tex")
    args.output.parent.mkdir(parents=True, exist_ok=True)

    common = [
        "pandoc", *[str(c) for c in chapters],
        "--from", "markdown+tex_math_dollars+raw_tex",
        "--filter", "pandoc-crossref", "--citeproc",
        f"--bibliography={bib}",
        "-M", f"title={paper.get('title', 'DemoCreate')}",
        "-M", f"author={authors}",
        "-M", f"date={paper.get('date', '')}",
        "-M", f"reference-section-title={cfg.get('reference-section-title', 'References')}",
        "-M", "link-citations=true",
    ]

    inserted = _figure_insertions(chapters)
    tex = subprocess.run([*common, "-t", "latex"], cwd=_MANUSCRIPT,
                         capture_output=True, text=True, check=True).stdout
    # Pandoc emits \includegraphics[keepaspectratio,alt={<caption>}]{figures/x.png};
    # match the brace-wrapped figure path, not the alt-text caption.
    emitted = re.findall(r"\{(figures/[^{}]+\.\w+)\}", tex)
    emitted_names = {Path(p).name for p in emitted}
    dropped = [p for p in inserted if Path(p).name not in emitted_names]
    if dropped:
        raise SystemExit(
            f"figure gate: {len(dropped)} inserted figure(s) dropped from the LaTeX "
            f"(markdown defect — check for a code fence closed on the same line as "
            f"following prose): {dropped}")
    print(f"figures: {len(inserted)} inserted, {len(emitted)} rendered (all present)")

    if args.check:
        print("✓ checks passed (no PDF built)")
        return 0

    engine = _pick_engine()
    print(f"building {args.output.name} via {engine} …")
    subprocess.run(
        [*common, "-H", str(preamble), f"--pdf-engine={engine}", "--toc", "-N",
         "-o", str(args.output)],
        cwd=_MANUSCRIPT, check=True)
    size_kb = args.output.stat().st_size // 1024
    print(f"✓ wrote {args.output} ({size_kb} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
