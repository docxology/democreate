"""Pure-text extraction of a paper's abstract, figure captions, and sections.

The naive paper summarizer narrates figures generically and grabs the title
block instead of the real abstract, because long papers front-load a table of
contents (TOC) whose dotted-leader lines defeat simple ``/abstract/i`` heuristics.

This module fixes that with deliberate text parsing. The core functions —
:func:`extract_figure_captions`, :func:`extract_sections`, and
:func:`extract_abstract` — operate on *already-extracted* text, so they are pure
and fully testable without poppler. The single convenience wrapper
:func:`summarize_structure` is the only function that touches the (guarded)
poppler-backed :func:`democreate.paper.pdf.extract_text`.

The TOC is the adversary throughout: every extractor explicitly recognizes and
rejects TOC artifacts (dotted leaders ``....``, trailing page numbers) so a
table-of-contents line is never mistaken for a heading, caption, or abstract.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .._logging import get_logger
from . import pdf as _pdf

__all__ = [
    "FigureCaption",
    "PaperSection",
    "extract_figure_captions",
    "extract_sections",
    "extract_abstract",
    "summarize_structure",
]

_log = get_logger(__name__)

_WS_RE = re.compile(r"\s+")

# A caption: "Figure 3: ...", "Figure 3. ...", "Fig. 3 ...". The body may span
# multiple wrapped lines (math captions often continue onto a second line), so
# the tail is captured across newlines (DOTALL) up to a blank line, the next
# figure/table marker, or end of text; `_bound_caption` then trims it to its
# first sentence. Capturing only the first line truncated multi-line captions
# mid-formula.
_FIGURE_RE = re.compile(
    r"(?ims)^\s*fig(?:ure|\.|)\s*(\d+)\s*[:.]?\s+"
    r"(.+?)(?=\n\s*\n|\n\s*(?:fig(?:ure|\.)|table)\s*\d|\Z)",
)

# A run of dotted leaders, optionally followed by a page number: the TOC tell.
_DOTTED_LEADER_RE = re.compile(r"\.\s*\.\s*\.")
# A trailing page number (TOC entries end in one): "... Setup 17".
_TRAILING_PAGENUM_RE = re.compile(r"\s\d{1,4}\s*$")
# Sentence boundary used to bound a caption to its first sentence.
_SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s")

# Numbered heading: "1 Introduction", "2.1 Setup", "3. Results".
_NUMBERED_HEADING_RE = re.compile(
    r"^(\d+(?:\.\d+)*)\.?\s+(.+)$",
)

# Well-known unnumbered section names (matched case-insensitively, exactly).
_NAMED_SECTIONS = (
    "abstract",
    "introduction",
    "background",
    "methods",
    "methodology",
    "results",
    "discussion",
    "conclusion",
    "conclusions",
    "references",
    "acknowledgments",
    "acknowledgements",
)

# "Part I — Introduction" / "Part II - Theory": capture the title after the dash.
_PART_HEADING_RE = re.compile(
    r"^part\s+[ivxlcdm\d]+\s*[—–-]\s*(.+)$",
    re.IGNORECASE,
)

_ABSTRACT_LINE_RE = re.compile(r"^\s*abstract\s*$", re.IGNORECASE)
# Markers that terminate the abstract body.
_ABSTRACT_END_RE = re.compile(
    r"^\s*(?:\d+\.?\s+)?(?:introduction|keywords?|background)\b",
    re.IGNORECASE,
)

# Heading heuristics.
_MAX_HEADING_CHARS = 70
# An abstract / fallback paragraph must have real substance.
_MIN_ABSTRACT_CHARS = 200


# Math operators that NFKC does not fold, mapped to glyphs a UI sans can render.
_MATH_OPERATOR_FOLD = {
    "⋆": "*",  # ⋆ star operator
    "∗": "*",  # ∗ asterisk operator
    "−": "-",  # − minus sign
    "·": "·",  # middle dot (keep, but normalize variants below)
    "…": "...",  # … ellipsis
}


def _fold_text(text: str) -> str:
    """Fold characters a UI sans font cannot draw into renderable equivalents.

    PDF captions use astral-plane *Mathematical Alphanumeric Symbols* (e.g.
    U+1D706 mathematical-italic lambda) and operators (U+22C6 star) that the UI
    font lacks — they render as tofu boxes on screen. NFKC normalization folds the
    math-alphanumerics down to their plain Latin/Greek (BMP) forms, and a small
    table handles the operators NFKC leaves alone.
    """
    text = unicodedata.normalize("NFKC", text)
    if any(ch in _MATH_OPERATOR_FOLD for ch in text):
        text = "".join(_MATH_OPERATOR_FOLD.get(ch, ch) for ch in text)
    return text


def _clean(text: str) -> str:
    """Collapse runs of whitespace into single spaces, fold math glyphs, strip.

    Args:
        text: Raw text to normalize.

    Returns:
        Whitespace-normalized, glyph-folded text.
    """
    return _fold_text(_WS_RE.sub(" ", text).strip())


def _looks_like_toc_line(line: str) -> bool:
    """Report whether a single line looks like a table-of-contents entry.

    Args:
        line: A raw text line.

    Returns:
        ``True`` if the line has dotted leaders or ends in a bare page number.
    """
    if _DOTTED_LEADER_RE.search(line):
        return True
    return bool(_TRAILING_PAGENUM_RE.search(line))


@dataclass
class FigureCaption:
    """A figure number paired with its caption sentence.

    Attributes:
        number: The 1-based figure number.
        caption: The cleaned caption text (first sentence, length-bounded).
    """

    number: int
    caption: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-friendly dict.

        Returns:
            Mapping with keys ``number`` and ``caption``.
        """
        return {"number": self.number, "caption": self.caption}


@dataclass
class PaperSection:
    """A section heading: its number (possibly empty) and title.

    Attributes:
        number: The section number (e.g. ``"2.1"``); empty for named sections.
        title: The cleaned section title.
    """

    number: str
    title: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-friendly dict.

        Returns:
            Mapping with keys ``number`` and ``title``.
        """
        return {"number": self.number, "title": self.title}


def _bound_caption(raw: str, *, max_caption_chars: int) -> str:
    """Trim a raw caption tail to its first sentence and a char budget.

    Args:
        raw: The text following the ``Figure N`` marker (whitespace-collapsed).
        max_caption_chars: Hard cap on the returned caption length.

    Returns:
        The bounded caption text.
    """
    cleaned = _clean(raw)
    # Bound to the first sentence end, if one occurs within the budget window.
    match = _SENTENCE_END_RE.search(cleaned)
    if match is not None and match.start() <= max_caption_chars:
        cleaned = cleaned[: match.start() + 1].strip()
    if len(cleaned) > max_caption_chars:
        cleaned = cleaned[:max_caption_chars].rstrip()
    return cleaned


def extract_figure_captions(
    text: str,
    *,
    max_caption_chars: int = 320,
) -> list[FigureCaption]:
    """Extract figure captions from paper text.

    Matches caption lines like ``"Figure 3: ..."``, ``"Figure 3. ..."``, and
    ``"Fig. 3 ..."``. The caption sentence is captured up to the next sentence
    end or ``max_caption_chars``, whitespace is collapsed, and entries are
    deduplicated by figure number (keeping the first, or a strictly longer later
    caption for the same number). Results are sorted by figure number.

    Args:
        text: Extracted paper text.
        max_caption_chars: Maximum length of any single caption.

    Returns:
        Figure captions sorted ascending by number.
    """
    best: dict[int, str] = {}
    for match in _FIGURE_RE.finditer(text):
        number = int(match.group(1))
        tail = match.group(2)
        # Skip cross-reference / TOC fragments: a tail that is just a page
        # number, or that carries dotted leaders, is not a real caption.
        if tail.strip().isdigit() or _looks_like_toc_line(tail):
            continue
        caption = _bound_caption(tail, max_caption_chars=max_caption_chars)
        if not caption:
            continue
        existing = best.get(number)
        # Keep the first caption seen, unless a later one is strictly longer.
        if existing is None or len(caption) > len(existing):
            best[number] = caption
    return [
        FigureCaption(number=number, caption=best[number])
        for number in sorted(best)
    ]


def _named_section(line: str) -> PaperSection | None:
    """Return a :class:`PaperSection` if ``line`` is a known named heading.

    Args:
        line: A stripped text line.

    Returns:
        A section with empty number, or ``None`` if not a named heading.
    """
    lowered = line.strip().lower()
    if lowered in _NAMED_SECTIONS:
        # Normalize the display title to title case of the matched word.
        return PaperSection(number="", title=line.strip().title())
    return None


def _part_section(line: str) -> PaperSection | None:
    """Return a :class:`PaperSection` if ``line`` is a ``Part N — Title`` heading.

    Args:
        line: A stripped text line.

    Returns:
        A section whose number is empty and title is the post-dash text, or
        ``None`` if the line is not a part heading.
    """
    match = _PART_HEADING_RE.match(line.strip())
    if match is None:
        return None
    title = match.group(1).strip()
    if not title or not title[0].isalpha():
        return None
    return PaperSection(number="", title=title)


def _numbered_section(line: str) -> PaperSection | None:
    """Return a :class:`PaperSection` if ``line`` is a numbered heading.

    Args:
        line: A stripped text line.

    Returns:
        A numbered section, or ``None`` if the line is not a heading.
    """
    match = _NUMBERED_HEADING_RE.match(line.strip())
    if match is None:
        return None
    number = match.group(1)
    title = match.group(2).strip()
    # A heading title starts with a letter and is title-cased / capitalized.
    if not title or not title[0].isalpha() or not title[0].isupper():
        return None
    return PaperSection(number=number, title=title)


def extract_sections(text: str) -> list[PaperSection]:
    """Extract section headings from paper text.

    Recognizes numbered headings (``"1 Introduction"``, ``"2.1 Setup"``,
    ``"3. Results"``) and well-known unnumbered headings (Abstract,
    Introduction, Background, Methods, Methodology, Results, Discussion,
    Conclusion, References, Acknowledgments). Table-of-contents lines — those
    with dotted leaders or trailing page numbers — are skipped. Results are
    deduplicated by title, preserving first-seen order.

    Args:
        text: Extracted paper text.

    Returns:
        Sections in first-seen order, deduplicated by title.
    """
    sections: list[PaperSection] = []
    seen: set[str] = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or len(line) > _MAX_HEADING_CHARS:
            continue
        if _looks_like_toc_line(line):
            continue
        section = (
            _named_section(line)
            or _part_section(line)
            or _numbered_section(line)
        )
        if section is None:
            continue
        key = section.title.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        sections.append(section)
    return sections


def _looks_like_toc_block(text: str) -> bool:
    """Report whether a block of text reads as a table of contents.

    Args:
        text: A candidate abstract slice.

    Returns:
        ``True`` if the block contains multiple dotted-leader / page-number
        patterns characteristic of a TOC.
    """
    leaders = len(_DOTTED_LEADER_RE.findall(text))
    if leaders >= 2:
        return True
    pagenums = sum(
        1
        for line in text.splitlines()
        if _TRAILING_PAGENUM_RE.search(line.rstrip())
    )
    return pagenums >= 3


def _abstract_after_marker(lines: list[str], *, max_chars: int) -> str:
    """Collect abstract prose following a standalone ``Abstract`` line.

    Iterates over *every* standalone ``Abstract`` marker (a long paper has at
    least two: one in the table of contents and the real one), and returns the
    first following block that is substantial and not itself a TOC. This is what
    lets the real abstract win over the front-matter TOC entry.

    Args:
        lines: All text lines.
        max_chars: Hard cap on the returned length.

    Returns:
        The best candidate slice (uncleaned), or empty string if no standalone
        marker yields a usable block.
    """
    marker_idxs = [
        idx for idx, line in enumerate(lines) if _ABSTRACT_LINE_RE.match(line)
    ]
    last_candidate = ""
    for start in marker_idxs:
        collected: list[str] = []
        for line in lines[start + 1 :]:
            if _ABSTRACT_END_RE.match(line):
                break
            collected.append(line)
            if sum(len(part) for part in collected) > max_chars * 2:
                break
        candidate = "\n".join(collected)
        cleaned = _clean(candidate)
        last_candidate = candidate
        if len(cleaned) >= _MIN_ABSTRACT_CHARS and not _looks_like_toc_block(
            candidate
        ):
            return candidate
    return last_candidate


def _fallback_abstract(text: str, *, max_chars: int) -> str:
    """Find the first substantial prose paragraph after the first third.

    Args:
        text: Full extracted text.
        max_chars: Hard cap on the returned length.

    Returns:
        Cleaned fallback abstract text, possibly empty.
    """
    offset = len(text) // 3
    tail = text[offset:]
    title_first_line = text.splitlines()[0].strip().lower() if text.strip() else ""
    for para in re.split(r"\n\s*\n", tail):
        cleaned = _clean(para)
        if len(cleaned) < _MIN_ABSTRACT_CHARS:
            continue
        if _looks_like_toc_block(para):
            continue
        # Reject a paragraph that is just the repeated title.
        if title_first_line and cleaned.lower().startswith(title_first_line):
            continue
        return cleaned[:max_chars].strip()
    return ""


def extract_abstract(text: str, *, max_chars: int = 1200) -> str:
    """Extract the real abstract from paper text, rejecting the TOC.

    Locates a standalone short line matching ``/^abstract$/i`` and takes the
    following prose up to the next heading (Introduction / ``"1 "`` / Keywords)
    or ``max_chars``. If that slice looks like a TOC (multiple dotted leaders or
    trailing page numbers, or is mostly the repeated title), it is rejected and
    the function falls back to the first substantial prose paragraph (>= 200
    chars, not the title) found after the first third of the text.

    Args:
        text: Extracted paper text.
        max_chars: Hard cap on the returned abstract length.

    Returns:
        The cleaned abstract text, possibly empty if nothing qualifies.
    """
    lines = text.splitlines()
    candidate_raw = _abstract_after_marker(lines, max_chars=max_chars)
    candidate = _clean(candidate_raw)
    if (
        len(candidate) >= _MIN_ABSTRACT_CHARS
        and not _looks_like_toc_block(candidate_raw)
    ):
        return candidate[:max_chars].strip()
    fallback = _fallback_abstract(text, max_chars=max_chars)
    if fallback:
        return fallback
    # Last resort: return whatever non-TOC candidate we have, bounded.
    return candidate[:max_chars].strip()


def summarize_structure(pdf: Path, *, max_text_pages: int = 14) -> dict[str, Any]:
    """Extract abstract, figure captions, and sections from a PDF.

    This is the only guarded entry point: it shells out to poppler via
    :func:`democreate.paper.pdf.extract_text` (which raises
    :class:`~democreate.errors.BackendUnavailableError` if poppler is absent)
    and then applies the pure extractors above.

    Args:
        pdf: Path to the source PDF.
        max_text_pages: Number of leading pages to scan for the abstract and
            sections (the front matter); figure captions are scanned across the
            whole document.

    Returns:
        Mapping with keys ``abstract`` (str), ``figure_captions``
        (list of :class:`FigureCaption`), and ``sections``
        (list of :class:`PaperSection`).

    Raises:
        BackendUnavailableError: If poppler is not installed.
        DemoCreateError: If the PDF is missing or unreadable.
    """
    pdf = Path(pdf)
    front = _pdf.extract_text(pdf, last=max_text_pages)
    whole = _pdf.extract_text(pdf)
    abstract = extract_abstract(front)
    if not abstract:
        abstract = extract_abstract(whole)
    sections = extract_sections(front)
    figure_captions = extract_figure_captions(whole)
    _log.info(
        "structure: abstract=%d chars, %d figures, %d sections",
        len(abstract),
        len(figure_captions),
        len(sections),
    )
    return {
        "abstract": abstract,
        "figure_captions": figure_captions,
        "sections": sections,
    }
