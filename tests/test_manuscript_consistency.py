"""Bind the manuscript and README prose to ground truth.

The manuscript has no ``{{TOKEN}}`` injection, so every number in it is typed by
hand. A RedTeam pass found the headline test count stale (``596`` vs an actual
``609``+), the paper-demo duration contradicting itself, and benchmark figures
unbound to ``data/benchmarks.json``. These tests are the missing oracle: they
fail when prose numbers drift from the live suite, the recorded benchmarks, or
the package version — so the published figures stay honest by construction.

Real subprocess collection, real files, no mocks.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
import tomllib

import democreate

ROOT = Path(__file__).resolve().parent.parent
MANUSCRIPT = ROOT / "manuscript"
README = ROOT / "README.md"


def _manuscript_prose() -> dict[Path, str]:
    """Markdown chapters + the top-level README (the human-facing claims)."""
    files = sorted(MANUSCRIPT.glob("[0-9]*.md")) + [README]
    return {p: p.read_text(encoding="utf-8") for p in files}


@pytest.fixture(scope="module")
def collected_test_count() -> int:
    """Number of tests pytest collects in this repo (passing + skipped)."""
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    out = proc.stdout + proc.stderr
    match = re.search(r"(\d+)\s+tests?\s+collected", out)
    assert match, f"could not parse collected count from pytest output:\n{out[-2000:]}"
    return int(match.group(1))


def test_stated_test_count_matches_suite(collected_test_count: int) -> None:
    """The manuscript's "N passing tests (M skipped)" must equal what pytest
    actually collects. This is the negative control for the stale-596 defect."""
    abstract = (MANUSCRIPT / "00_abstract.md").read_text(encoding="utf-8")
    m = re.search(r"([\d,]+)\s+passing tests\s*\((\d+)\s+skipped\)", abstract)
    assert m, "abstract must state 'N passing tests (M skipped)'"
    passing = int(m.group(1).replace(",", ""))
    skipped = int(m.group(2))
    assert passing + skipped == collected_test_count, (
        f"abstract claims {passing} passing + {skipped} skipped = "
        f"{passing + skipped}, but pytest collects {collected_test_count}. "
        "Update the manuscript/README test counts (and re-render the stat-card "
        "figures) to match the suite."
    )


def test_passing_count_is_consistent_across_prose() -> None:
    """Every 'N passing tests' / 'N-test suite' / 'N tests ·' figure across the
    manuscript and README must cite the same number — no split-brain counts."""
    patterns = [
        r"([\d,]+)\s+passing tests",
        r"([\d,]+)-test suite",
        r"\b([\d,]+)\s+tests\s+·",
        r"\(([\d,]+)\s+tests\b",
    ]
    found: dict[str, list[str]] = {}
    for path, text in _manuscript_prose().items():
        for pat in patterns:
            for raw in re.findall(pat, text):
                found.setdefault(raw.replace(",", ""), []).append(path.name)
    # Also bind the figure-generator stat literals (e.g. the cover's "625 tests ·")
    # so those .py strings cannot drift from the prose (RedTeam graphical_abstract
    # finding). Folded into this test — not a new one — so it does not change the
    # suite size and desync the rendered stat-card videos.
    for rel in ("manuscript/figures/graphical_abstract.py",):
        for raw in re.findall(r"(\d+)\s+tests\b", (ROOT / rel).read_text(encoding="utf-8")):
            found.setdefault(raw, []).append(Path(rel).name)
    assert found, "no test-count figures found in prose (regex drift?)"
    assert len(found) == 1, (
        "inconsistent test counts across prose: "
        + "; ".join(f"{n} in {sorted(set(files))}" for n, files in found.items())
    )


def test_benchmark_numbers_match_recorded_json() -> None:
    """The evaluation chapter's measured figures must match data/benchmarks.json
    exactly, so prose and the data file cannot diverge."""
    benchmarks = json.loads((ROOT / "data" / "benchmarks.json").read_text(encoding="utf-8"))
    evaluation = (MANUSCRIPT / "07_evaluation.md").read_text(encoding="utf-8")
    expected = {
        "build median_ms": str(benchmarks["build"]["median_ms"]),
        "render ms_per_output_second": str(benchmarks["render"]["ms_per_output_second"]),
        "render animation_fps": str(benchmarks["render"]["animation_fps"]),
    }
    missing = {k: v for k, v in expected.items() if v not in evaluation}
    assert not missing, (
        "07_evaluation.md does not quote these data/benchmarks.json values: "
        f"{missing}. Regenerate the benchmark and update the prose together."
    )


def test_paper_demo_duration_is_single_valued() -> None:
    """The paper demo has one duration; prose must not contradict itself.

    Negative control for the 196.4s-vs-~211s-vs-~160s defect.
    """
    durations: dict[str, list[str]] = {}
    for path, text in _manuscript_prose().items():
        # Durations attached to the paper_demo artifact or 'paper' render prose.
        for m in re.finditer(r"[~]?\s?(\d{2,3}(?:\.\d)?)\s*s\b", text):
            ctx = text[max(0, m.start() - 80) : m.start()].lower()
            if "paper_demo" in ctx or "research-paper" in ctx or "paper demo" in ctx:
                durations.setdefault(m.group(1), []).append(path.name)
    # All paper-demo durations should round to the same canonical value (188).
    canon = {round(float(d)) for d in durations}
    assert len(canon) <= 1, (
        "paper-demo duration is inconsistent across prose: "
        + "; ".join(f"{d}s in {sorted(set(f))}" for d, f in durations.items())
    )


def test_version_strings_agree() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version = pyproject["project"]["version"]
    assert democreate.__version__ == version
    # The manuscript references the package version in its provenance prose.
    abstract = (MANUSCRIPT / "00_abstract.md").read_text(encoding="utf-8")
    config = (MANUSCRIPT / "config.yaml").read_text(encoding="utf-8")
    assert version in (abstract + config), (
        f"manuscript does not reference the current version {version}"
    )

