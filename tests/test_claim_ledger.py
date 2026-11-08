"""Validate structured claim/evidence references without testing copied prose."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
VALID_STATUS = {"asserted", "estimate", "verified", "historical", "planned"}


@pytest.fixture(scope="module")
def ledger() -> dict:
    return yaml.safe_load((ROOT / "data/claim_ledger.yaml").read_text())


def test_claim_records_are_complete_and_unique(ledger: dict) -> None:
    claims = ledger["claims"]
    assert claims
    ids = [claim["id"] for claim in claims]
    assert len(ids) == len(set(ids))
    for claim in claims:
        for key in (
            "id", "claim", "value", "unit", "direction",
            "backed_by", "source", "status",
        ):
            assert key in claim
            assert claim[key] is not None
            assert claim[key] != ""
        assert claim["status"] in VALID_STATUS
        if claim["status"] == "historical":
            assert claim.get("evidence_note")
        if claim["status"] == "verified":
            assert claim.get("receipt"), "Verified claims require a specific run receipt"


def test_declared_evidence_anchors_resolve(ledger: dict) -> None:
    """Check referenced gate, hypothesis, condition and metric IDs structurally."""
    for claim in ledger["claims"]:
        ref = claim["backed_by"]
        match = re.search(r"([\w/]+\.yaml):([\w]+)#([\w]+)", ref)
        if not match:
            continue
        filename, section, anchor = match.groups()
        document = yaml.safe_load((ROOT / filename).read_text())
        target = document[section]
        if isinstance(target, list):
            assert anchor in {item["id"] for item in target}
        elif isinstance(target, dict):
            assert target.get("id") == anchor or anchor in target
        condition = re.search(r"condition=([\w]+)", ref)
        if condition:
            assert condition.group(1) in {item["id"] for item in document["conditions"]}


def test_evidence_source_paths_resolve(ledger: dict) -> None:
    bases = (ROOT, ROOT / "src/democreate")
    for claim in ledger["claims"]:
        cited = claim["backed_by"] + " " + claim["source"]
        for token in re.findall(r"[\w./-]+\.(?:py|yaml|toml|json)", cited):
            if token.startswith("output/"):
                continue  # Historical/generated artifacts are not shipped receipts.
            assert any((base / token).is_file() for base in bases), token


def test_current_metadata_versions_agree(ledger: dict) -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    citation = yaml.safe_load((ROOT / "CITATION.cff").read_text())
    codemeta = json.loads((ROOT / "codemeta.json").read_text())
    zenodo = json.loads((ROOT / ".zenodo.json").read_text())
    experiment = yaml.safe_load((ROOT / "experiment_plan.yaml").read_text())
    manuscript = yaml.safe_load((ROOT / "docs/manuscript/config.yaml").read_text())
    versions = {
        ledger["version"], citation["version"],
        citation["preferred-citation"]["version"], codemeta["version"],
        zenodo["version"], experiment["version"], manuscript["paper"]["version"],
    }
    assert versions == {project["version"]}
    assert (
        citation["title"] == codemeta["name"]
        == zenodo["title"] == ledger["title"]
    )
    assert (
        set(citation["keywords"]) == set(codemeta["keywords"])
        == set(zenodo["keywords"])
    )
