"""Kokoro neural-TTS support: model paths, downloads, and synthesis helpers.

Split out of :mod:`democreate.narration.tts` (agent refactoring lane); the
public surface remains importable from :mod:`democreate.narration.tts`.
"""

from __future__ import annotations

import os
from pathlib import Path

from .._logging import get_logger

logger = get_logger(__name__)

# Kokoro neural TTS defaults. The model + voices files are large (~340 MB) and
# are NOT bundled or pip-installed; they are resolved from env vars or a cache
# dir (see :func:`_kokoro_model_paths`). 24 kHz is Kokoro's native output rate.
_KOKORO_DEFAULT_VOICE = "af_heart"  # warm US-English female; see Kokoro voice list
_KOKORO_MODEL_NAMES = ("kokoro-v1.0.onnx", "kokoro-v0.19.onnx", "kokoro.onnx")
_KOKORO_VOICES_NAMES = ("voices-v1.0.bin", "voices.bin", "voices-v1.0.json")


_KOKORO_RELEASE = (
    "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
)
_KOKORO_MODEL_URL = f"{_KOKORO_RELEASE}/kokoro-v1.0.onnx"
_KOKORO_VOICES_URL = f"{_KOKORO_RELEASE}/voices-v1.0.bin"

def fetch_kokoro_model(  # pragma: no cover - network + large (~340 MB) download
    dest: Path | None = None,
) -> tuple[Path, Path]:
    """Download the Kokoro model + voices into the cache dir if absent.

    This is an explicit, opt-in network operation (never run on the default path).
    Existing files are not re-downloaded.

    Args:
        dest: Target directory; defaults to :func:`_kokoro_cache_dir`.

    Returns:
        ``(model_path, voices_path)``.
    """
    import urllib.request

    dest = Path(dest) if dest is not None else _kokoro_cache_dir()
    dest.mkdir(parents=True, exist_ok=True)
    model = dest / "kokoro-v1.0.onnx"
    voices = dest / "voices-v1.0.bin"
    if not voices.exists():
        logger.info("downloading Kokoro voices → %s", voices)
        urllib.request.urlretrieve(_KOKORO_VOICES_URL, voices)
    if not model.exists():
        logger.info("downloading Kokoro model (~310 MB) → %s", model)
        urllib.request.urlretrieve(_KOKORO_MODEL_URL, model)
    return model, voices


def _kokoro_synth_segment(engine, text, *, voice, speed, lang):  # pragma: no cover - model
    """Synthesize one segment, recovering from Kokoro's ~510-phoneme overflow.

    Char-based splitting cannot bound *phonemes* (numbers, arrows, and symbols
    expand into many), so a short-looking segment can still exceed the limit. On
    any failure we split the segment in half on word boundaries and recurse, then
    concatenate — guaranteeing success for arbitrary, phoneme-dense narration.
    """
    import numpy as np

    try:
        return engine.create(text, voice=voice, speed=speed, lang=lang)
    except Exception:
        words = text.split()
        if len(words) <= 1:
            raise
        mid = len(words) // 2
        left, rate = _kokoro_synth_segment(
            engine, " ".join(words[:mid]), voice=voice, speed=speed, lang=lang
        )
        right, _ = _kokoro_synth_segment(
            engine, " ".join(words[mid:]), voice=voice, speed=speed, lang=lang
        )
        return np.concatenate([left, right]), rate


def _split_for_tts(text: str, *, max_chars: int = 250) -> list[str]:
    """Split ``text`` into segments under ``max_chars``, at sentence/word bounds.

    Kokoro's ONNX model has a per-call token limit (~510 phoneme tokens); a long
    narration chunk overflows it (``index 510 out of bounds``). Splitting at
    sentence boundaries — falling back to word boundaries for a single overlong
    sentence — keeps each synthesis call safely within the limit. Pure and
    deterministic, so it is unit-tested without the model installed.
    """
    clean = " ".join(text.split())
    if len(clean) <= max_chars:
        return [clean] if clean else []

    # Sentence-ish split that keeps the terminator attached.
    import re

    sentences = re.findall(r"[^.!?]+[.!?]?", clean)
    segments: list[str] = []
    cur = ""
    for sentence in (s.strip() for s in sentences if s.strip()):
        if len(sentence) > max_chars:  # a single overlong sentence → split on words
            if cur:
                segments.append(cur)
                cur = ""
            word_cur = ""
            for word in sentence.split():
                if word_cur and len(word_cur) + 1 + len(word) > max_chars:
                    segments.append(word_cur)
                    word_cur = word
                else:
                    word_cur = f"{word_cur} {word}".strip()
            if word_cur:
                cur = word_cur
        elif cur and len(cur) + 1 + len(sentence) > max_chars:
            segments.append(cur)
            cur = sentence
        else:
            cur = f"{cur} {sentence}".strip()
    if cur:
        segments.append(cur)
    return segments


def _kokoro_cache_dir() -> Path:
    """Return the directory Kokoro model files are looked for in.

    Honors ``DEMOCREATE_KOKORO_DIR``; defaults to ``~/.cache/democreate/kokoro``.
    """
    override = os.environ.get("DEMOCREATE_KOKORO_DIR")
    if override:
        return Path(override)
    return Path.home() / ".cache" / "democreate" / "kokoro"


def _kokoro_model_paths() -> tuple[Path, Path] | None:
    """Resolve ``(model_path, voices_path)`` for Kokoro, or ``None`` if absent.

    Resolution order: the explicit ``KOKORO_MODEL_PATH`` + ``KOKORO_VOICES_PATH``
    env vars, then the first known filename present in :func:`_kokoro_cache_dir`.
    Returns ``None`` (rather than raising) so callers can decide how to report it.
    """
    env_model = os.environ.get("KOKORO_MODEL_PATH")
    env_voices = os.environ.get("KOKORO_VOICES_PATH")
    if env_model and env_voices:
        model, voices = Path(env_model), Path(env_voices)
        return (model, voices) if model.exists() and voices.exists() else None

    cache = _kokoro_cache_dir()
    found_model = next(
        (cache / n for n in _KOKORO_MODEL_NAMES if (cache / n).exists()), None
    )
    found_voices = next(
        (cache / n for n in _KOKORO_VOICES_NAMES if (cache / n).exists()), None
    )
    if found_model is not None and found_voices is not None:
        return found_model, found_voices
    return None
