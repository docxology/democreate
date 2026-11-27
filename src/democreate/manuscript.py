"""Build the DemoCreate manuscript PDF from its declarative ``config.yaml``.

The reproducible front door for the academic write-up under
``docs/manuscript/`` (run via ``scripts/build_manuscript.py``). It reads the
chapter order, metadata, bibliography, and build gates from
``docs/manuscript/config.yaml`` (the single source of truth) and drives Pandoc
— with ``pandoc-crossref`` for ``@fig:``/``@sec:`` cross-references and
``--citeproc`` for ``[@key]`` citations — through a XeLaTeX-class engine
(:data:`PDF_ENGINES`, ``tectonic`` by default) to a single PDF.

Two build gates protect "properly rendering":

* **Citation gate** (``fail_on_missing`` in the config): every ``[@key]`` used
  in a chapter must resolve to an entry in ``references.bib``; an unresolved key
  is a hard failure, not a silent ``[?]``.
* **Figure gate**: every ``![...](figures/x.png){#fig:x}`` insertion in the
  chapters must survive into the generated LaTeX as an ``\\includegraphics`` —
  this catches the markdown defects (e.g. a code fence closed on the same line
  as following prose) that silently drop figures from the concatenated build.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

__all__ = [
    "PDF_ENGINES",
    "build_manuscript",
    "defined_bib_keys",
    "extract_preamble",
    "figure_insertions",
    "load_config",
    "pick_engine",
    "stage_template_inputs",
    "used_citation_keys",
]

# Engines that understand the Unicode glyphs + fontspec the preamble relies on,
# in preference order. The first one found on PATH is used.
PDF_ENGINES = ("tectonic", "xelatex", "lualatex")


def load_config(path: Path) -> dict[str, Any]:
    """Load the manuscript ``config.yaml``."""
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def extract_preamble(preamble_md: Path, out_tex: Path) -> Path:
    """Strip the ```latex fence from ``preamble.md`` into a raw ``.tex`` header."""
    lines = preamble_md.read_text(encoding="utf-8").splitlines()
    if lines and lines[0].lstrip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].lstrip().startswith("```"):
        lines = lines[:-1]
    out_tex.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_tex


def defined_bib_keys(bib: Path) -> set[str]:
    """Return the citation keys defined by a BibTeX ``references.bib``."""
    return set(re.findall(r"^@\w+\{\s*([^,\s]+)", bib.read_text(encoding="utf-8"), re.M))


def used_citation_keys(chapters: list[Path]) -> set[str]:
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


def figure_insertions(chapters: list[Path]) -> list[str]:
    """The ``figures/x.png`` paths inserted as images across the chapters."""
    found: list[str] = []
    for ch in chapters:
        # Match the ](figures/x.png) tail; alt text may itself contain ] (e.g. [@sec:x]).
        found += re.findall(r"\]\((figures/[^)]+)\)", ch.read_text(encoding="utf-8"))
    return found


_FIGURE_LINK = re.compile(
    r"!\[(?P<alt>[^\n]+?)\]\(figures/(?P<name>[\w.-]+\.png)\)"
    r"\{#(?P<label>fig:[\w-]+)\}"
)


def stage_template_inputs(config: Path, manuscript_dir: Path, output: Path) -> Path:
    """Copy the checked manuscript and PNGs to Template's render layout.

    The standalone builder reads the authored image paths. Template consumes
    a derived tree with each image rebased to the generated figure directory.
    """
    cfg = load_config(config)
    manuscripts = output / "manuscript"
    figures = output / "figures"
    chapter_names = cfg["chapters"]
    auxiliaries = (cfg["bibliography"], cfg.get("preamble", "preamble.md"))
    for name in (*chapter_names, *auxiliaries):
        if Path(name).name != name or name in {"", ".", ".."}:
            raise ValueError(f"Template inputs must be manuscript filenames: {name!r}")
    chapter_paths = [manuscript_dir / name for name in chapter_names]
    chapters = {path.name: path.read_text(encoding="utf-8") for path in chapter_paths}
    registry = []
    for body in chapters.values():
        for match in _FIGURE_LINK.finditer(body):
            name = match["name"]
            registry.append(
                {
                    "label": match["label"],
                    "filename": name,
                    "caption": match["alt"],
                    "alt_text": match["alt"],
                    "generated_by": "scripts/build_manuscript.py --stage-template",
                }
            )
    if len(registry) != len(figure_insertions(chapter_paths)):
        raise ValueError("Template staging requires labelled PNGs and alt text")

    manuscripts.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    for name, body in chapters.items():
        rebased = _FIGURE_LINK.sub(
            lambda match: match[0].replace("](figures/", "](../../output/figures/", 1),
            body,
        )
        (manuscripts / name).write_text(rebased, encoding="utf-8")
    for name in auxiliaries:
        shutil.copyfile(manuscript_dir / name, manuscripts / name)
    shutil.copyfile(config, manuscripts / "config.yaml")
    for item in registry:
        name = item["filename"]
        shutil.copyfile(manuscript_dir / "figures" / name, figures / name)
    path = figures / "figure_registry.json"
    path.write_text(
        json.dumps({"schema_version": 1, "figures": registry}, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def pick_engine() -> str:
    """Return the first available XeLaTeX-class PDF engine on ``PATH``."""
    for eng in PDF_ENGINES:
        if shutil.which(eng):
            return eng
    raise SystemExit(
        f"no PDF engine found (looked for {', '.join(PDF_ENGINES)}); install tectonic"
    )


def build_manuscript(
    config: Path,
    manuscript_dir: Path,
    output: Path,
    check: bool = False,
) -> int:
    """Run the citation + figure gates and, unless ``check``, build the PDF.

    Args:
        config: Path to the manuscript ``config.yaml``.
        manuscript_dir: Root of the manuscript tree; chapter, bibliography, and
            preamble paths from the config resolve against it and Pandoc runs
            with it as the working directory. Relative roots use the caller's cwd.
        output: Target PDF path, relative to the caller's cwd; the extracted
            ``preamble.tex`` is written next to it.
        check: Run the gates only and skip the PDF build.

    Returns:
        ``0`` on success.

    Raises:
        SystemExit: On a missing Pandoc toolchain, missing chapter files, an
            unresolved citation key, or a figure dropped from the LaTeX.
    """
    cfg = load_config(config)
    manuscript_dir = manuscript_dir.resolve()
    output = output.resolve()
    chapters = [manuscript_dir / c for c in cfg["chapters"]]
    missing_files = [c for c in chapters if not c.is_file()]
    if missing_files:
        raise SystemExit(f"missing chapter files: {[str(c) for c in missing_files]}")
    bib = manuscript_dir / cfg["bibliography"]

    # --- Citation gate -----------------------------------------------------
    used = used_citation_keys(chapters)
    defined = defined_bib_keys(bib)
    unresolved = sorted(used - defined)
    if unresolved and cfg.get("fail_on_missing", True):
        raise SystemExit(f"unresolved citation keys (not in {bib.name}): {unresolved}")
    print(f"citations: {len(used)} used, {len(defined)} defined, {len(unresolved)} unresolved")
    inserted = figure_insertions(chapters)
    missing_assets = [p for p in inserted if not (manuscript_dir / p).is_file()]
    if missing_assets:
        raise SystemExit(f"figure gate: missing image assets: {missing_assets}")
    if not shutil.which("pandoc"):
        raise SystemExit("pandoc not found on PATH")
    if not shutil.which("pandoc-crossref"):
        raise SystemExit("pandoc-crossref not found on PATH (needed for @fig/@sec refs)")

    # --- Build the LaTeX once so the figure gate inspects the real output --
    paper = cfg.get("paper", {})
    authors = ", ".join(a["name"] for a in cfg.get("authors", []))
    output.parent.mkdir(parents=True, exist_ok=True)
    preamble = extract_preamble(
        manuscript_dir / cfg.get("preamble", "preamble.md"),
        output.parent / "preamble.tex",
    )

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

    proc = subprocess.run([*common, "-t", "latex"], cwd=manuscript_dir,
                          capture_output=True, text=True, check=True,
                          stdin=subprocess.DEVNULL)
    tex = proc.stdout or ""
    emitted = re.findall(
        r"\\includegraphics(?:\[[\s\S]*?\])?\s*\{(figures/[^{}\n]+\.\w+)\}", tex
    )
    expected = Counter((manuscript_dir / p).resolve() for p in inserted)
    rendered = Counter((manuscript_dir / p).resolve() for p in emitted)
    dropped = list((expected - rendered).elements())
    if dropped:
        raise SystemExit(
            f"figure gate: {len(dropped)} inserted figure(s) dropped from the LaTeX "
            f"(markdown defect — check for a code fence closed on the same line as "
            f"following prose): {dropped}")
    print(f"figures: {len(inserted)} inserted, {len(emitted)} rendered (all present)")

    if check:
        print("✓ checks passed (no PDF built)")
        return 0

    engine = pick_engine()
    print(f"building {output.name} via {engine} …")
    subprocess.run(
        [*common, "-H", str(preamble), f"--pdf-engine={engine}", "--toc", "-N",
         "-o", str(output)],
        cwd=manuscript_dir, check=True, stdin=subprocess.DEVNULL)
    size_kb = output.stat().st_size // 1024
    print(f"✓ wrote {output} ({size_kb} KB)")
    return 0
