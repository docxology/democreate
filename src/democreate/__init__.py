"""DemoCreate — declarative, deterministic audio-visual demo generation.

DemoCreate turns a single declarative :class:`~democreate.schema.Demo` artifact
into an audio-visual walkthrough of a codebase, website, or terminal session. The
package is built on three load-bearing ideas:

1. **Declarative spine.** All content is a :class:`~democreate.schema.Demo` —
   an ordered stream of typed actions plus narration chunks. Rendering is a pure
   function of it, so you edit the artifact and re-render rather than re-record.
2. **Backends behind interfaces.** Every heavy capability (TTS, transcription,
   screen capture, browser drive, animation, video assembly) sits behind an
   abstract base class with a pure-Python *deterministic default*. The package
   produces a real demo with only its light core dependencies installed, and
   upgrades to high fidelity when optional extras are present.
3. **TTS → STT sync.** Narration audio is generated, then transcribed back to
   word-level timestamps; on-screen actions anchor to spoken words via their
   ``trigger_word``. Real audio is the single source of timing truth.

The most common entry point is the :class:`~democreate.pipeline.Pipeline`, or the
``democreate`` command-line interface.
"""

from __future__ import annotations

from ._logging import get_logger, log_stage
from .errors import (
    BackendUnavailableError,
    CaptureError,
    DemoCreateError,
    RenderError,
    SchemaValidationError,
    SyncError,
)
from .pipeline import Pipeline, PipelineResult, build_demo
from .project_paths import Workspace, default_output_root
from .schema import (
    SCHEMA_VERSION,
    Action,
    ActionType,
    Chunk,
    Demo,
    Scene,
    SceneKind,
    WordTimestamp,
)

__version__ = "0.6.2"

__all__ = [
    "__version__",
    # schema
    "Demo",
    "Scene",
    "Chunk",
    "Action",
    "ActionType",
    "SceneKind",
    "WordTimestamp",
    "SCHEMA_VERSION",
    # pipeline
    "Pipeline",
    "PipelineResult",
    "build_demo",
    # paths
    "Workspace",
    "default_output_root",
    # errors
    "DemoCreateError",
    "SchemaValidationError",
    "BackendUnavailableError",
    "RenderError",
    "SyncError",
    "CaptureError",
    # logging
    "get_logger",
    "log_stage",
]
