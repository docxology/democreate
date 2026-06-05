# Audio: voice and voiceover assembly

A render's audio is **ground truth** for timing: narration is synthesized per
chunk, each clip's duration is measured, and the frames are held to those
measured durations (see [video.md](video.md)). This doc covers how the per-chunk
clips become one clean voiceover track.

The assembly primitives live in `assembly/audio.py`; the orchestration is
`pipeline._build_voiceover()`. All pacing is governed by
[`AudioConfig`](config.md).

## The system voice (zero pip)

The default real voice — `SystemTTSBackend` — uses the OS speech binary:
**macOS `say`** or **Linux `espeak` / `espeak-ng`**. It needs no `pip`/`uv`
install at all, just a binary that is usually already present. Select it with:

```bash
democreate render demo.json --tts system --voice Samantha
```

On macOS, list available voices with `say -v '?'` (e.g. `Samantha`, `Daniel`).
Because it is a *platform* backend (not portable), it is never the `auto`
default — but it turns the silent default into genuine spoken narration for
free. Other backends: `silent` (deterministic silent clips, the core default),
and the optional `kokoro` / `chatterbox` neural voices (extra `tts`). See
[backends.md](backends.md).

## Voiceover assembly: gaps, lead, trail

`concat_with_gaps()` concatenates the per-chunk clips in order, inserting
silence to give the narration breathing room. It is **pure standard library**
(the `wave` module) — import-safe, deterministic, and testable with no external
binary. Silence is generated at the clips' own `(channels, sampwidth,
framerate)`, so concatenation never resamples; mismatched clip formats raise a
`ValueError`.

| Pad | `AudioConfig` field | Default | Where |
|-----|--------------------|---------|-------|
| Lead silence | `lead_silence_ms` | `300` | Before the first clip. |
| Inter-chunk gap | `gap_ms` | `220` | Between consecutive clips. |
| Trail silence | `trail_silence_ms` | `600` | After the last clip. |

These same lead/gap/trail values are fed to the animator's `chunk_timing()` so
the frame timeline matches the padded audio exactly — no drift.

Canonical audio is 16-bit mono PCM. `measure_duration_ms()` reads the true
duration from the WAV header (frame count ÷ frame rate).

## Normalization and fade (ffmpeg, guarded)

When `normalize` is set **and** `ffmpeg` is on `PATH`, the raw voiceover is
post-processed:

1. **`normalize_audio()`** — ffmpeg `loudnorm` filter, targeting integrated
   loudness `I = −16 LUFS`, true-peak `TP = −1.5 dBTP`, loudness range
   `LRA = 11 LU`. This is why a verified render lands near −16 dB mean volume.
2. **`apply_fade()`** — a fade-in and fade-out of `fade_ms` (default 180 ms)
   each, via ffmpeg `afade`. The fade-out start is computed from the true clip
   duration.

Both are **guarded**: if `ffmpeg` is absent they raise
`BackendUnavailableError(extra="video")`, and `_build_voiceover()` catches that
(plus `RenderError` / `OSError`) and gracefully falls back to the raw, un-faded
track — the render still completes. The pure concat path never needs ffmpeg.

## Settings summary

| Field | Default | Meaning |
|-------|---------|---------|
| `backend` | `system` | `system` / `silent` / `kokoro` / `chatterbox`. |
| `voice` | `Samantha` | Voice id for voiced backends. |
| `rate_wpm` | `None` | Optional speaking-rate override. |
| `lead_silence_ms` | `300` | Silence before the first clip. |
| `gap_ms` | `220` | Silence between chunks. |
| `trail_silence_ms` | `600` | Silence after the last clip. |
| `normalize` | `True` | Apply `loudnorm` (needs ffmpeg). |
| `fade_ms` | `180` | Fade in/out duration (needs ffmpeg). |

## See also

- [config.md](config.md) — `AudioConfig` reference and YAML sample.
- [video.md](video.md) — how measured clip durations drive frame timing.
- [backends.md](backends.md) — TTS backends and the zero-pip system voice.
- [cli.md](cli.md) — `render` `--tts` / `--voice` options.
