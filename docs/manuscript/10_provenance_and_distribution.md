# Unsigned Attribution, Digest Scope, and Distribution {#sec:provenance}

DemoCreate exposes three attribution carriers: visible metadata bars, editable MP4 container tags, and a JSON record embedded in a lossless PNG poster. These are **unsigned association records**, not authentication or digital signatures.

## Visible Labels and Editable Container Tags

`MetadataConfig` supplies author, source, URL and watermark text. Header/footer overlays render selected values into frames; container tags expose selected attribution to players and `ffprobe`. The PNG record includes an unsigned content digest and its own selected labels. These outputs share some inputs, not an identical field set or authenticated identity: for example, container tags can use a configured title override while the record derives its title from the Demo, and watermark/clock text is not the same payload as the poster digest. Anyone able to edit media can change or copy these values. They cannot establish who produced an artifact.

## Selected-Content Digest Scope and Adversarial Limits

`export/stego.py` encodes JSON in image-channel least-significant bits. `verify_provenance` compares its `content_sha256` to a recomputed selected-content Demo digest. The digest covers Demo title, geometry, fps, voice, scene identity/kind/context, chunk identity/text/voice and action type/params/trigger words. It excludes audio paths, chunk/action timing and durations, and does not hash external asset bytes, rendered frames, audio or MP4 bytes. Thus a matching digest can coexist with changed timing or changed files at an unchanged asset reference. The renderer computes the association from the workspace-relative resolved Demo; use the emitted `demos/demo.json` with matching geometry and path representation rather than assuming an authored artifact is identical.

A matching digest is a **consistency check only**. No private key, signature verification, trusted author identity, cover-pixel identity or MP4-byte binding is supplied. An adversary can replace the attribution, copy the payload into another cover or recompute it after edits. A source/reference path is not authentication of asset bytes. H.264 re-encoding does not preserve PNG LSB payloads.

When enabled and successful, the MP4 provenance stage writes `poster.png`, `poster_signed.png` (a historical filename, **not** a cryptographic signature) and `provenance.json`. Optional metadata/sidecar failures can be logged and skipped, so inspect actual outputs. The pipeline does not emit or transmit PNG bookends, nor does it authenticate bars, tags and posters as equivalent carriers.

![Three distinct metadata surfaces share selected configuration inputs: visible overlay labels, editable MP4 container tags and an unsigned poster payload. The schematic illustrates overlapping but different field sets, not equivalent authenticated identities. A selected-content digest does not bind rendered pixels, audio or MP4 bytes.](figures/provenance.png){#fig:provenance}

## Checking Resolved-Demo Consistency Before Distribution

```bash
democreate stego output/provenance/poster_signed.png --demo output/demos/demo.json
```

This illustrative command extracts a record and checks digest consistency; it is not an executed receipt and success does not authenticate a poster, video or author. `CITATION.cff`, `codemeta.json` and `.zenodo.json` describe candidate 0.8.0. Publication, a final version archive DOI and release date remain pending; the concept DOI is not a newly minted version DOI. Metadata files, digest matches and media property checks do not satisfy the still-blocking voiced acoustic study or establish publication readiness.
