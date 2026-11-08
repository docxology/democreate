# Schema 1.1: authored scenes, narration chunks and timed actions

The schema is the declarative spine, using Python value types and serialization,
defined in `src/democreate/schema.py`, and round-trips losslessly through
`dict` / JSON / YAML. `SCHEMA_VERSION` is currently `"1.1"` (1.0 is intentionally rejected); the enum *string
values* are the on-disk representation and must not be renamed without a
schema-version bump.

Hierarchy: **`Demo` → `Scene` → `Chunk` → `Action`**. Two enums (`ActionType`,
`SceneKind`) and one transcription type (`WordTimestamp`) complete the model.
Related media value types (`AudioClip`, `FrameState`) live in `media.py`.

## `Demo`

The top-level authored walkthrough. Reproduction additionally needs assets,
render configuration and a fixed environment; edit and rebuild rather than record.

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `title` | `str` | required | Must be non-empty (validation). |
| `scenes` | `list[Scene]` | `[]` | Ordered chapters. |
| `width` | `int` | `1920` | Output frame width (px), must be positive. |
| `height` | `int` | `1080` | Output frame height (px), must be positive. |
| `fps` | `int` | `30` | Output frame rate, must be positive. |
| `voice` | `str` | `"default"` | Default narration voice id. |
| `metadata` | `dict` | `{}` | Free-form (author, source repo, license, …). |
| `schema_version` | `str` | `"1.1"` | On-disk schema version. |

Key methods: `validate() -> list[str]` (empty == valid; checks non-empty title,
positive geometry/fps, unique scene/chunk ids, valid action types), `is_valid()`,
`iter_chunks()`, `iter_actions()`, `estimated_duration_ms(wpm=150)`,
`to_dict()` / `from_dict()`, `to_json()` / `from_json()`, `to_yaml()` /
`from_yaml()`. `__eq__` compares the serialized dicts.

## `Scene`

A logical chapter with a single capture strategy.

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `id` | `str` | required | Unique within the demo. |
| `title` | `str` | `""` | Used for navigation/chapters. |
| `kind` | `SceneKind` | `CODEBASE` | Capture/render strategy. |
| `chunks` | `list[Chunk]` | `[]` | Ordered narration+action units. |
| `context` | `dict` | `{}` | Scene context (file tree snapshot, base URL, …). |

`estimated_duration_ms(wpm=150)` sums chunk estimates.

## `Chunk`

A narration unit and the actions it triggers.

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `id` | `str` | required | Unique within the demo. |
| `text` | `str` | `""` | Narration spoken for this chunk. |
| `actions` | `list[Action]` | `[]` | Actions anchored to words in `text`. |
| `voice` | `str \| None` | `None` | Per-chunk voice override. |
| `audio_path` | `str \| None` | `None` | Filled by the TTS backend. |
| `start_ms` | `int \| None` | `None` | Absolute audio start, filled by sync. |
| `duration_ms` | `int \| None` | `None` | Measured clip duration after sync; playback estimates only when absent. |

Methods: `word_count()`, `estimated_duration_ms(wpm=150)` (a wordless chunk still
reserves a 300 ms beat), and `playback_duration_ms(wpm=150)` (measurement first).

## `Action`

One typed event mutating the virtual environment (the CodeVideo model).

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `type` | `ActionType` | required | Coerced from its string value on construction. |
| `params` | `dict` | `{}` | Action-specific payload, free-form so new actions need no downstream schema change. |
| `trigger_word` | `str \| None` | `None` | A word in the parent chunk's `text` the sync engine anchors this action to. |
| `timestamp_ms` | `int \| None` | `None` | Absolute fire time (ms from demo start); `None` until sync fills it. |
| `duration_ms` | `int \| None` | `None` | How long the action plays out (typing, a zoom). |
| `timestamp_source` | `str` | `"authored"` | `"authored"` preserves explicit absolute times; `"sync"` refreshes derived times after narration edits. |

`to_dict()` omits unset optional fields.
`timestamp_source` is persisted, including before a time is assigned. Triggered
actions are always re-anchored; an untriggered WAIT advances the fallback
sequence cursor. Captured discrete inputs use zero duration.

## `ActionType`

A string enum of every primitive change a demo can express, grouped by surface:

| Group | Members (value) |
|-------|-----------------|
| editor | `OPEN_FILE` (`open_file`), `CREATE_FILE` (`create_file`), `TYPE_CODE` (`type_code`), `HIGHLIGHT_LINES` (`highlight_lines`), `CLOSE_FILE` (`close_file`) |
| terminal | `RUN_COMMAND` (`run_command`), `PRINT_OUTPUT` (`print_output`) |
| browser | `NAVIGATE` (`navigate`), `CLICK` (`click`), `SCROLL` (`scroll`), `FILL` (`fill`) |
| mouse / camera | `MOVE_MOUSE` (`move_mouse`), `ZOOM` (`zoom`), `PAN` (`pan`) |
| narration / timing | `SPEAK` (`speak`), `WAIT` (`wait`) |

## `SceneKind`

The capture/render strategy a scene implies: `CODEBASE` (`codebase`), `WEBSITE`
(`website`), `TERMINAL` (`terminal`), `SLIDE` (`slide`).

## `WordTimestamp`

A word with millisecond bounds: `word: str`, `start_ms: int`, `end_ms: int`.
The default transcriber estimates these bounds from supplied text and measured
WAV duration; the type itself does not establish acoustic recognition.

## Related media types

- **`AudioClip`** — a rendered narration file and its measured properties:
  `path: Path`, `duration_ms: int`, `sample_rate: int = 22050`, `text: str`,
  `chunk_id: str | None`.
- **`FrameState`** — a renderable snapshot of the virtual environment at one
  instant: `scene_kind`, `title`, `caption`, `file_path`, `code_lines`,
  `highlight_lines`, `cursor_typed`, `terminal_lines`, `url`, `cursor_xy`,
  `scale`, `background_image` (base contain fit; camera motion and overlays may
  hide pixels), `section` (top-chrome chapter label), `subtitle` (slide headline),
  `bullets: list[str]` (a packed bullet-list slide surface), and
  `stats: list[tuple[str, str]]` (big-number stat-card slide surface). Producers
  fill only the fields relevant to the scene kind; `bullets`/`stats`/`subtitle`/
  `section`/`background_image` are populated from a scene's `context` dict by the
  compositor (see [config.md](config.md#slide-surfaces-bullet-lists-and-stat-cards)).

## JSON example

A valid starter with the same scenes/actions as `democreate init`; serialization
also emits each action's default `timestamp_source: "authored"`.

```json
{
  "schema_version": "1.1",
  "title": "Starter Demo",
  "width": 1920,
  "height": 1080,
  "fps": 30,
  "voice": "default",
  "metadata": {},
  "scenes": [
    {
      "id": "intro",
      "title": "Welcome",
      "kind": "codebase",
      "context": {},
      "chunks": [
        {
          "id": "c1",
          "text": "Welcome to this project. Let us open the main module.",
          "actions": [
            {
              "type": "open_file",
              "params": { "path": "main.py" },
              "trigger_word": "open"
            },
            {
              "type": "type_code",
              "params": { "code": "print('hello, world')" },
              "trigger_word": "main"
            }
          ]
        }
      ]
    },
    {
      "id": "run",
      "title": "Run It",
      "kind": "terminal",
      "context": {},
      "chunks": [
        {
          "id": "c2",
          "text": "Now we run the program from the terminal.",
          "actions": [
            {
              "type": "run_command",
              "params": { "command": "python main.py", "output": "hello, world" },
              "trigger_word": "run"
            }
          ]
        }
      ]
    }
  ]
}
```

Round-trip guarantee: `Demo.from_dict(demo.to_dict()) == demo`, and likewise for
JSON and YAML.
