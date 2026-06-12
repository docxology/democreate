"""Bind ``data/claim_ledger.yaml`` to reality.

The claim ledger is the project's register of every falsifiable number. Its
header promises that "claims are NOT facts until their backing check passes" and
that "the publish pipeline cross-checks this ledger" — but until this module
existed, nothing actually verified that the ledger's ``source``/``backed_by``
files resolve or that its numeric values agree with the code they cite. A
RedTeam pass found C1 citing a ``tests/test_sync.py`` that does not exist. These
tests are that missing cross-check: they run with the core dependencies only, no
mocks, against the real repository tree.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import tomllib
import yaml

import democreate

ROOT = Path(__file__).resolve().parent.parent
LEDGER_PATH = ROOT / "data" / "claim_ledger.yaml"

# Bases a ledger ``source``/``backed_by`` path token may be relative to.
_PATH_BASES = (ROOT, ROOT / "src" / "democreate")
# File tokens we resolve. Render artifacts under ``output/`` are gitignored and
# legitimately absent on a clean checkout, so they are not required to exist.
_FILE_TOKEN = re.compile(r"[\w./-]+\.(?:py|yaml|toml|json)")
_VALID_STATUS = {"asserted", "estimate", "verified"}


@pytest.fixture(scope="module")
def ledger() -> dict:
    return yaml.safe_load(LEDGER_PATH.read_text(encoding="utf-8"))


def _claims(ledger: dict) -> list[dict]:
    claims = ledger.get("claims")
    assert claims, "claim_ledger.yaml has no claims"
    return claims


def test_every_claim_has_required_fields(ledger: dict) -> None:
    for claim in _claims(ledger):
        for key in ("id", "claim", "status"):
            assert key in claim, f"claim missing '{key}': {claim!r}"
        assert claim["status"] in _VALID_STATUS, (
            f"{claim['id']} has invalid status {claim['status']!r}; "
            f"expected one of {sorted(_VALID_STATUS)}"
        )


def test_claim_ids_are_unique(ledger: dict) -> None:
    ids = [c["id"] for c in _claims(ledger)]
    assert len(ids) == len(set(ids)), f"duplicate claim ids in ledger: {ids}"


def test_ledger_source_files_resolve(ledger: dict) -> None:
    """Every ``.py``/``.yaml``/``.toml``/``.json`` cited in a claim must exist.

    This is the negative control for the C1 defect: a ``source`` pointing at a
    nonexistent ``tests/test_sync.py`` (the real file is
    ``tests/test_narration_sync.py``).
    """
    missing: list[str] = []
    for claim in _claims(ledger):
        cited = f"{claim.get('backed_by', '')} {claim.get('source', '')}"
        for token in _FILE_TOKEN.findall(cited):
            path = token.split(":", 1)[0]  # drop any ``file.yaml:anchor`` suffix
            if path.startswith("output/"):
                continue  # gitignored, regeneratable render artifact
            if not any((base / path).exists() for base in _PATH_BASES):
                missing.append(f"{claim['id']}: cited path does not exist -> {path}")
    assert not missing, "claim_ledger.yaml cites nonexistent files:\n" + "\n".join(missing)


def test_ledger_version_matches_package(ledger: dict) -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert ledger["version"] == democreate.__version__ == pyproject["project"]["version"], (
        f"version skew: ledger={ledger['version']!r} "
        f"package={democreate.__version__!r} pyproject={pyproject['project']['version']!r}"
    )
    experiment = yaml.safe_load((ROOT / "experiment_plan.yaml").read_text(encoding="utf-8"))
    assert experiment["version"] == ledger["version"], (
        f"experiment_plan.yaml version {experiment['version']!r} does not match "
        f"claim ledger {ledger['version']!r}"
    )
    for rel in ("data/README.md", "data/AGENTS.md"):
        assert ledger["version"] in (ROOT / rel).read_text(encoding="utf-8"), (
            f"{rel} does not reference the current ledger version {ledger['version']}"
        )


def _claim_value(ledger: dict, claim_id: str):
    for claim in _claims(ledger):
        if claim["id"] == claim_id:
            return claim["value"]
    raise AssertionError(f"claim {claim_id} not found in ledger")


def test_claim_values_match_code(ledger: dict) -> None:
    """Numeric claims must equal the code/config defaults they assert."""
    from democreate.config import THEMES, VideoConfig
    from democreate.schema import DEFAULT_WPM

    # C5: default narration speaking rate.
    assert _claim_value(ledger, "C5") == DEFAULT_WPM == 150
    # C16: builtin theme presets (>= 5).
    assert _claim_value(ledger, "C16") <= len(THEMES)
    assert len(THEMES) >= 5
    # C21: default near-visually-lossless CRF.
    assert _claim_value(ledger, "C21") == VideoConfig().crf == 18


def test_fps_claim_matches_benchmark(ledger: dict) -> None:
    """C13's animation fps must match both the config default and the recorded
    benchmark, so the prose-cited frame rate cannot silently diverge from the
    shipped default (the RedTeam 15-vs-12 finding)."""
    from democreate.config import VideoConfig

    benchmarks = json.loads((ROOT / "data" / "benchmarks.json").read_text(encoding="utf-8"))
    bench_fps = benchmarks["render"]["animation_fps"]
    assert _claim_value(ledger, "C13") == VideoConfig().animation_fps == bench_fps
