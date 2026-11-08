# Audio: measured WAV clips, pauses and optional processing

TTS produces one WAV per narration chunk. The pipeline measures clip duration
and uses configured lead/gap/trail windows for synchronization, captions,
voiceover assembly and frame holds. This shares a **nominal timebase**, not a
measurement of acoustic word onsets. Frame/codec rounding can change encoded
endpoints. See [video](video.md) for animated versus static playback.

## The system voice (zero pip)

Core `build` and library defaults synthesize **silence**; `render` defaults to
`system`. `SystemTTSBackend` uses usable macOS `say` or Linux
`espeak`/`espeak-ng`, then ffmpeg or macOS afconvert for canonical PCM WAV.
Availability includes a synthesis/transcode probe, not only executable presence.

```bash
democreate render demo.json --tts system
```

Choose an installed voice with `--voice`; macOS can list voices with `say -v '?'`.
Kokoro is implemented but requires a compatible voice environment, packages and
model/voices. ElevenLabs is a cloud adapter needing credentials/network.
Chatterbox is unwired and no published extra enables it. The
[backend reference](backends.md) owns provisioning and readiness details.

## Voiceover assembly: gaps, lead, trail

`assembly.audio.concat_with_gaps()` writes a new WAV using stdlib `wave`, with no
resampling. All inputs must share channels, sample width and sample rate;
mismatch raises `ValueError`. The high-level TTS paths use 16-bit mono PCM.
Files are numbered `chunk_0000.wav`, etc.; chunk IDs are labels, not paths.

[AudioConfig](config.md) defines the defaults: 300 ms
lead, 220 ms gaps and 600 ms trail. `measure_duration_ms()` reads actual frame
count/sample rate. Pauses do not extend subtitle cue windows. Static frame
holds keep the preceding still until the next spoken start; animated playback
can show the upcoming chunk during a gap. Neither silently speaks text in HTML.

## Normalization and fade (ffmpeg, guarded)

`pipeline._build_voiceover()` concatenates clips, then optionally post-processes:

1. `normalize_audio()` applies ffmpeg `loudnorm`, targeting −16 LUFS integrated,
   −1.5 dBTP true peak and 11 LU loudness range. A target setting is not a measured
   compliance result; `volumedetect` mean dB is a different metric.
2. `apply_fade()` applies configured fade-in/out (default 180 ms each).

Both helpers preserve input sample rate/channels and publish standard 16-bit PCM
headers readable on Python 3.11. Malformed PCM input, failed processing or output
errors raise `RenderError` without replacing prior output. Absent ffmpeg raises
`BackendUnavailableError`; no Python extra supplies that native executable.

The orchestration can retain the valid raw/unfaded voiceover when optional
post-processing fails and reports the skipped processing. That is not evidence
that normalization ran or that a subsequent encode succeeds. MP4 encoding still
requires ffmpeg/ffprobe.

## Configure and inspect the result

Create a config before using it:

```bash
democreate config audio.yaml
democreate render demo.json --config audio.yaml --tts system
```

Edit `audio.lead_silence_ms`, `gap_ms`, `trail_silence_ms`, `normalize`,
`fade_ms`, `voice` or `rate_wpm` as needed. Only the system backend uses the
speaking-rate override. CLI precedence matters: `render`'s default `--tts system`
overrides the config's backend, while a blank `--voice` preserves its voice.
See [configuration](config.md) for the complete contract, [CLI](cli.md#render)
for flags, [media identities](videos.md) for source-bound observations and
[testing](testing_philosophy.md) for what core checks do not establish.
