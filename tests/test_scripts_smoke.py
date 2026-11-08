"""Behavioral regressions for project-owned diagnostic and generation scripts."""

from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = PROJECT_ROOT / "scripts"


def _load_script(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("linked_input", ["pdf", "src", "figure", "nested_source"])
def test_paper_showcase_rejects_escaped_inputs_before_staging(
    tmp_path: Path, linked_input: str,
) -> None:
    """Real external links must fail before even the first PDF is staged."""
    examples = tmp_path / "checkout" / "examples"
    examples.mkdir(parents=True)
    script = examples / "make_paper_showcase.py"
    shutil.copyfile(PROJECT_ROOT / "examples" / script.name, script)
    showcase = _load_script(script)
    root = tmp_path / "selected-paper"
    pdf = root / showcase._PDF_INPUT
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"internal PDF")
    source = root / "src"
    source.mkdir()
    figures = root / "output" / "figures"
    figures.mkdir()
    for name in showcase._FIGURE_INPUTS:
        (figures / name).write_bytes(b"internal figure")
    outside = tmp_path / "outside"
    outside.mkdir()
    external = outside / "external.py"
    external.write_text("value = 42\n", encoding="utf-8")
    if linked_input == "src":
        source.rmdir()
        source.symlink_to(outside, target_is_directory=True)
    elif linked_input == "nested_source":
        (source / "linked.py").symlink_to(external)
    else:
        target = pdf if linked_input == "pdf" else figures / showcase._FIGURE_INPUTS[-1]
        target.unlink()
        target.symlink_to(external)

    with pytest.raises(ValueError, match="escapes selected --paper-root"):
        showcase.build(root)
    assert not (examples / "assets").exists()


def test_benchmark_identity_tracks_resources_and_input_without_absolute_paths(
    tmp_path: Path,
) -> None:
    """Exercise the real hash routine against copied resources, not fake output."""
    benchmark = _load_script(SCRIPTS / "benchmark.py")
    root = tmp_path / "checkout"
    shutil.copytree(
        PROJECT_ROOT / "src" / "democreate", root / "src" / "democreate",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )
    for name in ("pyproject.toml", "uv.lock", "scripts/benchmark.py"):
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(PROJECT_ROOT / name, target)
    before = benchmark._source_identity(root, '{"input": 1}')
    template_name = "src/democreate/export/templates/player.html.j2"
    template = root / template_name
    template.write_bytes(template.read_bytes() + b"\n<!-- negative control -->\n")
    after = benchmark._source_identity(root, '{"input": 1}')
    assert before["source_sha256"] != after["source_sha256"]
    before_files = {item["path"]: item for item in before["source_manifest"]}
    after_files = {item["path"]: item for item in after["source_manifest"]}
    changed = {
        name for name in before_files if before_files[name] != after_files[name]
    }
    assert changed == {template_name}
    assert all(not Path(name).is_absolute() and ".." not in Path(name).parts
               for name in after_files)
    moved = tmp_path / "different-absolute-location"
    shutil.copytree(root, moved)
    assert benchmark._source_identity(moved, '{"input": 1}') == after
    assert benchmark._source_identity(root, '{"input": 2}')["source_sha256"] != (
        after["source_sha256"]
    )
