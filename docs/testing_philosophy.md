# Testing philosophy

DemoCreate's tests are a contract, not a courtesy. The same property that makes
the demos reproducible — determinism — makes the suite able to assert *exact*
output. Four principles govern every test.

## 1. No mocks

There is no mocking framework in this suite — no `unittest.mock`, no `MagicMock`,
no faked return values standing in for the deterministic core. Tests exercise the
real deterministic backends, real temp files (`tmp_path`), and real serialization
round-trips. The reasoning is simple: the deterministic defaults *are* the real
thing on core deps, so there is nothing to fake. If a behavior seems to require a
mock, the design is wrong — push the work into a deterministic default that does
it for real.

The one sanctioned exception is `monkeypatch`, used surgically for exactly two
things that cannot otherwise be reached deterministically: (a) simulating an
*absent* optional binary (`shutil.which` → `None`, `_has_ffmpeg` → `False`) so the
`BackendUnavailableError` guard path is testable even on a machine where the
binary is installed, and (b) forcing the core-only fallback branch (e.g.
`_resolve_render_frame` → `None`) or stubbing an external-process probe so the
verifier's degraded-input branches run without a real encoded video. These patch
*availability*, never the value a deterministic backend computes.

```python
def test_pipeline_writes_player(tmp_path):
    demo = Demo.from_json(STARTER_JSON)
    result = build_demo(demo, Workspace(tmp_path))
    assert result.player_path.exists()          # real file, real workspace
```

## 2. Deterministic

The default path has no RNG, no wall-clock, and no network, so output is
byte-for-byte stable. Tests assert exact frames, exact manifests, exact captions,
and exact round-trips — not loose tolerances.

```python
def test_demo_round_trips_losslessly():
    assert Demo.from_dict(demo.to_dict()) == demo
    assert Demo.from_json(demo.to_json()) == demo
```

Determinism invariants (stable renders, fixed synthetic timing) are explicitly
asserted; keep them green. Anything that would introduce nondeterminism into a
default backend is a bug.

## 3. Pure-core coverage gate (≥90%)

`pyproject.toml` enforces `fail_under = 90` with branch coverage on
`src/democreate`. The pure-Python spine and every deterministic default must be
fully exercised. Run the gate with:

```bash
.venv/bin/python -m pytest --cov
```

Coverage configuration excludes `tests/*` and `__init__.py` files, and the report
ignores `pragma: no cover`, `if __name__ == "__main__":`, `raise
NotImplementedError`, and `if TYPE_CHECKING:`.

## 4. Backend skip markers

Heavy backends (Kokoro, Whisper, mss, Playwright, Manim, MoviePy, pynput,
pyautogui, tree-sitter) are absent in CI by design. Two mechanisms keep the suite
green and honest:

- The `backend` pytest marker (declared in `pyproject.toml`:
  *"tests that exercise an optional heavy backend (skipped if absent)"*) marks
  tests that need a real extra; they skip cleanly when the dependency is missing.
- For the default path, tests assert the **`BackendUnavailableError`** contract —
  that requesting a real backend without its extra raises the right error
  carrying the right `extra` install hint. This tests the fallback boundary
  without installing anything heavy.

```python
@pytest.mark.backend
def test_real_whisper_transcribes(...):
    ...                                          # skipped unless whisper installed

def test_missing_extra_raises_with_hint():
    with pytest.raises(BackendUnavailableError) as exc:
        get_tts_backend("kokoro")                # absent in CI
    assert exc.value.extra == "tts"
```

Real-backend adapter code carries `# pragma: no cover` so it never counts against
the core coverage gate.

## Running the suite

```bash
.venv/bin/python -m pytest -q                    # full suite, fast
.venv/bin/python -m pytest tests/test_capture_*.py -q   # one subsystem (no --cov,
                                                 #   avoids .coverage races)
.venv/bin/python -m pytest --cov                 # the enforced ≥90% gate
ruff check . && mypy src                          # lint + types
```

Use `.venv/bin/python` explicitly — a bare `python` may be a shim that runs a
different interpreter and silently fakes a green suite. Scope subsystem runs
without `--cov` when working in parallel to avoid `.coverage` file races.
