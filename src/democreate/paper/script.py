"""Build a narrated :class:`~democreate.schema.Demo` from a research paper.

``build_paper_demo`` turns a :class:`~democreate.paper.extract.PaperSummary` —
optionally enriched with rendered PDF page images and a summary of the associated
codebase — into a complete demo: a title card, the abstract (paced into chunks),
the paper's figures and selected pages as full-frame backgrounds, an
architecture overview of the code, and a closing card.

The narration is deterministic and template-driven (no LLM required), so the same
paper always yields the same demo; pass ``narration_overrides`` to customise.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..schema import Action, ActionType, Chunk, Demo, Scene, SceneKind
from .extract import PaperSummary

__all__ = ["build_paper_demo", "chunk_sentences"]


def chunk_sentences(text: str, *, max_words: int = 26) -> list[str]:
    """Split prose into narration-sized chunks at sentence boundaries.

    Args:
        text: The prose to chunk (e.g. an abstract).
        max_words: Soft cap on words per chunk; sentences are grouped up to it.

    Returns:
        A list of chunk strings (never empty if ``text`` has content).
    """
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    chunks: list[str] = []
    cur: list[str] = []
    count = 0
    for sentence in sentences:
        words = sentence.split()
        if cur and count + len(words) > max_words:
            chunks.append(" ".join(cur))
            cur, count = [], 0
        cur.extend(words)
        count += len(words)
    if cur:
        chunks.append(" ".join(cur))
    return chunks


def _slide(id_: str, section: str, narration: str, *, title="", subtitle="",
           background=None, kind=SceneKind.SLIDE) -> Scene:
    """Construct a single-chunk scene with optional background/section/subtitle."""
    scene = Scene(id=id_, title=title or section, kind=kind)
    scene.context["section"] = section
    if subtitle:
        scene.context["subtitle"] = subtitle
    if background is not None:
        scene.context["background_image"] = str(background)
    scene.chunks.append(
        Chunk(id=f"{id_}-c", text=narration,
              actions=[Action(ActionType.OPEN_FILE, {"path": title or section})])
    )
    return scene


def _group_modules(code_summaries: list) -> list[tuple[str, list[str]]]:
    """Group module summaries into ``(top_level_dir, [module names])`` columns."""
    groups: dict[str, list[str]] = {}
    for summ in code_summaries:
        name = getattr(summ, "name", None) or (
            summ.get("name") if isinstance(summ, dict) else "module")
        path = getattr(summ, "path", None) or (
            summ.get("path", "") if isinstance(summ, dict) else "")
        parts = Path(str(path)).parts
        top = parts[-2] if len(parts) >= 2 else "src"
        groups.setdefault(top, []).append(str(name))
    columns = []
    for top in sorted(groups):
        columns.append((top, sorted(groups[top])[:5]))
    return columns[:5]


def build_paper_demo(
    summary: PaperSummary,
    *,
    code_summaries: list | None = None,
    page_images: list[Path] | None = None,
    architecture_image: Path | None = None,
    figure_captions: list | None = None,
    sections: list | None = None,
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
    voice: str = "Samantha",
    max_figures: int = 6,
) -> Demo:
    """Assemble a narrated demo from a paper summary and optional code/pages.

    Args:
        summary: The extracted paper summary.
        code_summaries: Optional list of ``ModuleSummary`` (or dicts) for the
            associated codebase, used for the architecture overview.
        page_images: Optional rendered PDF page images (e.g. the title page) used
            as full-frame backgrounds.
        architecture_image: Optional pre-rendered architecture diagram image.
        width / height / fps: Output geometry.
        voice: Default narration voice.
        max_figures: Cap on how many figures to feature.

    Returns:
        A validated :class:`~democreate.schema.Demo`.
    """
    scenes: list[Scene] = []
    authors = summary.authors or "the authors"
    n_pages = summary.page_count

    # 1. Title
    scenes.append(
        _slide(
            "title", "Paper",
            f"{summary.title}. A {n_pages}-page paper by {authors}.",
            title=summary.title if len(summary.title) <= 48 else summary.title[:46] + "…",
            subtitle=authors,
        )
    )

    # 2. Title page image (if rendered)
    pages = list(page_images or [])
    if pages:
        scenes.append(
            _slide(
                "frontpage", "Title Page",
                "Here is the paper's front matter — title, authors, and venue.",
                title="Title Page", background=pages[0],
            )
        )

    # 3. Abstract — paced across chunks
    abstract_chunks = chunk_sentences(summary.abstract, max_words=26)
    if abstract_chunks:
        abstract_scene = Scene(id="abstract", title="Abstract", kind=SceneKind.SLIDE)
        abstract_scene.context["section"] = "Abstract"
        # Subtitle = the paper's own title (not a duplicate "Abstract" label).
        _sub = summary.title.strip()
        abstract_scene.context["subtitle"] = (
            _sub if len(_sub) <= 64 else _sub[:61].rstrip() + "…")
        for i, text in enumerate(abstract_chunks[:6]):
            prefix = "Here is the core idea, in the authors' own words. " if i == 0 else ""
            abstract_scene.chunks.append(
                Chunk(id=f"abstract-{i}", text=prefix + text,
                      actions=[Action(ActionType.OPEN_FILE, {"path": "Abstract"})])
            )
        scenes.append(abstract_scene)

    # 3b. Section structure — a guided map of the paper
    section_titles = [getattr(s, "title", str(s)) for s in (sections or [])]
    section_titles = [t for t in section_titles if t.lower() != "abstract"]
    if section_titles:
        named = ", ".join(section_titles[:6])
        scenes.append(
            _slide(
                "sections", "Structure",
                f"The paper is organised into {len(section_titles)} parts: {named}.",
                title="How the Paper Is Organised",
                subtitle=" · ".join(section_titles[:5]),
            )
        )

    # 4. Figures — frame each one (a varied lead-in + the real caption), so the
    #    tour reads as a guided walk through the evidence rather than a list of
    #    captions read aloud. (For a fully hand-authored, interpretive tour of a
    #    specific paper, see examples/make_paper_showcase.py.)
    caption_by_num = {
        getattr(fc, "number", 0): getattr(fc, "caption", "") for fc in (figure_captions or [])
    }
    leads = [
        "Take figure {i}.", "Figure {i} makes its point visually.",
        "Here is figure {i}.", "Consider figure {i}.",
        "Look at figure {i}.", "Then figure {i}.",
    ]
    for i, fig in enumerate(summary.figures[:max_figures], start=1):
        real = caption_by_num.get(i, "")
        lead = leads[(i - 1) % len(leads)].format(i=i)
        if real:
            narration = f"{lead} {real}"
        else:
            narration = (
                f"{lead} One of the paper's {len(summary.figures)} figures, "
                "generated from the project's reproducible analysis."
            )
        scenes.append(
            _slide(
                f"figure-{i}", f"Figure {i}", narration,
                title=f"Figure {i}", background=fig,
            )
        )

    # 5. Additional pages
    for i, page in enumerate(pages[1:4], start=2):
        scenes.append(
            _slide(
                f"page-{i}", "From the Paper",
                "A page from the manuscript, rendered directly from the PDF.",
                title="From the Paper", background=page,
            )
        )

    # 6. Codebase architecture
    if architecture_image is not None:
        scenes.append(
            _slide(
                "architecture", "Codebase",
                f"The paper is backed by code. Here is the architecture of its "
                f"{len(code_summaries or [])}-module implementation.",
                title="Codebase Architecture", background=architecture_image,
            )
        )
    elif code_summaries:
        n = len(code_summaries)
        scenes.append(
            _slide(
                "architecture", "Codebase",
                f"The paper is backed by a {n}-module codebase implementing and "
                "checking its claims.",
                title="Codebase", subtitle=f"{n} modules",
            )
        )

    # 7. Closing
    doi = summary.to_dict().get("doi", "")
    scenes.append(
        _slide(
            "outro", "Reproducible",
            "Reproducible by construction: the figures, the code, and this very "
            "overview are all generated from the same sources.",
            title=summary.title if len(summary.title) <= 48 else "Thank You",
            subtitle=str(doi) if doi else authors,
        )
    )

    demo = Demo(
        title=summary.title,
        scenes=scenes,
        width=width,
        height=height,
        fps=fps,
        voice=voice,
        metadata={"kind": "paper", "pdf": summary.pdf_path, "pages": n_pages},
    )
    return demo
