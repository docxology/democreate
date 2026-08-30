# AGENTS.md — .humos/

HumOS sidecar contract (see `README.md` here for the file table and bridges).
Agent notes:

- **No `humos.*` import dependency** — the coupling is declarative only
  (`sidecar.toml`, `bridges.toml`, `conformance.toml`). Never add a runtime
  import of HumOS code from `democreate`.
- `conformance.toml` pins the coverage floor, gate command, and required
  surfaces; if you change CI or coverage policy, reconcile it with this file.
- Bridge claims (`feeds` → hum-dashboard, `informs` ← hum-docxology) describe
  external repo relationships; verify against the sidecar repos before relying
  on them (unverified from this checkout).
