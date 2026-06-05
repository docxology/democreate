"""Poppler command-line wrapper for reading and rasterizing PDFs.

DemoCreate ingests research papers without any pip PDF dependency: it shells out
to the poppler utilities (``pdfinfo``, ``pdftotext``, ``pdftoppm``) that ship on
most scientific workstations. Every function that touches a binary first checks
that the binary is on ``PATH`` and raises
:class:`~democreate.errors.BackendUnavailableError` (``backend="poppler"``,
``extra="pdf"``) if it is missing, so callers get an actionable message instead
of an opaque ``FileNotFoundError``.

All subprocess calls are deterministic, read-only, and operate on real files.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .._logging import get_logger
from ..errors import BackendUnavailableError, DemoCreateError

__all__ = [
    "poppler_available",
    "pdf_info",
    "pdf_page_count",
    "extract_text",
    "render_page",
    "render_pages",
]

_log = get_logger(__name__)

# poppler binaries this module depends on.
_PDFINFO = "pdfinfo"
_PDFTOTEXT = "pdftotext"
_PDFTOPPM = "pdftoppm"


def poppler_available() -> bool:
    """Report whether the required poppler binaries are installed.

    Returns:
        ``True`` only if ``pdfinfo``, ``pdftoppm`` and ``pdftotext`` are all on
        ``PATH``; ``False`` otherwise.
    """
    return all(
        shutil.which(binary) is not None
        for binary in (_PDFINFO, _PDFTOPPM, _PDFTOTEXT)
    )


def _require(binary: str) -> str:
    """Return the absolute path to ``binary`` or raise.

    Args:
        binary: Name of the poppler executable to locate.

    Returns:
        The resolved path to the executable.

    Raises:
        BackendUnavailableError: If the executable is not on ``PATH``.
    """
    found = shutil.which(binary)
    if found is None:
        raise BackendUnavailableError("poppler", extra="pdf")
    return found


def pdf_info(pdf: Path) -> dict[str, str]:
    """Return ``pdfinfo`` metadata as a dict of lowercased keys.

    Args:
        pdf: Path to the PDF file.

    Returns:
        Mapping of lowercased metadata keys (e.g. ``"title"``, ``"author"``,
        ``"pages"``) to their string values.

    Raises:
        BackendUnavailableError: If ``pdfinfo`` is not installed.
        DemoCreateError: If the file is missing or ``pdfinfo`` fails.
    """
    binary = _require(_PDFINFO)
    pdf = Path(pdf)
    if not pdf.is_file():
        raise DemoCreateError(f"pdf not found: {pdf}")
    try:
        completed = subprocess.run(  # pragma: no cover
            [binary, str(pdf)],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:  # pragma: no cover
        raise DemoCreateError(
            f"pdfinfo failed for {pdf}: {exc.stderr.strip() or exc}"
        ) from exc
    return _parse_info(completed.stdout)


def _parse_info(text: str) -> dict[str, str]:
    """Parse ``Key: value`` lines from ``pdfinfo`` output.

    Args:
        text: Raw stdout from ``pdfinfo``.

    Returns:
        Mapping of lowercased keys to stripped values.
    """
    info: dict[str, str] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        if key:
            info[key] = value.strip()
    return info


def pdf_page_count(pdf: Path) -> int:
    """Return the number of pages in ``pdf``.

    Args:
        pdf: Path to the PDF file.

    Returns:
        The page count parsed from ``pdfinfo``.

    Raises:
        BackendUnavailableError: If ``pdfinfo`` is not installed.
        DemoCreateError: If the page count is missing or unparseable.
    """
    info = pdf_info(pdf)
    raw = info.get("pages", "")
    try:
        return int(raw)
    except ValueError as exc:
        raise DemoCreateError(
            f"could not parse page count from pdfinfo: {raw!r}"
        ) from exc


def extract_text(
    pdf: Path,
    *,
    first: int | None = None,
    last: int | None = None,
) -> str:
    """Extract text from a (range of) PDF page(s) via ``pdftotext``.

    Args:
        pdf: Path to the PDF file.
        first: 1-based first page to include (``-f``); ``None`` for the start.
        last: 1-based last page to include (``-l``); ``None`` for the end.

    Returns:
        The extracted UTF-8 text (``pdftotext ... -`` stdout).

    Raises:
        BackendUnavailableError: If ``pdftotext`` is not installed.
        DemoCreateError: If the file is missing or ``pdftotext`` fails.
    """
    binary = _require(_PDFTOTEXT)
    pdf = Path(pdf)
    if not pdf.is_file():
        raise DemoCreateError(f"pdf not found: {pdf}")
    cmd = [binary]
    if first is not None:
        cmd += ["-f", str(first)]
    if last is not None:
        cmd += ["-l", str(last)]
    cmd += [str(pdf), "-"]
    try:
        completed = subprocess.run(  # pragma: no cover
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:  # pragma: no cover
        raise DemoCreateError(
            f"pdftotext failed for {pdf}: {exc.stderr.strip() or exc}"
        ) from exc
    return completed.stdout


def render_page(pdf: Path, page: int, out_path: Path, *, dpi: int = 150) -> Path:
    """Rasterize a single PDF page to a PNG via ``pdftoppm``.

    Args:
        pdf: Path to the PDF file.
        page: 1-based page number to render.
        out_path: Destination PNG path (extension added if absent).
        dpi: Render resolution in dots per inch.

    Returns:
        The path to the written PNG.

    Raises:
        BackendUnavailableError: If ``pdftoppm`` is not installed.
        DemoCreateError: If the file is missing or ``pdftoppm`` fails.
    """
    binary = _require(_PDFTOPPM)
    pdf = Path(pdf)
    if not pdf.is_file():
        raise DemoCreateError(f"pdf not found: {pdf}")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # pdftoppm -singlefile appends ".png"; strip a supplied extension for the stem.
    stem = out_path.with_suffix("")
    png_path = stem.with_suffix(".png")
    cmd = [
        binary,
        "-png",
        "-r",
        str(dpi),
        "-f",
        str(page),
        "-l",
        str(page),
        "-singlefile",
        str(pdf),
        str(stem),
    ]
    try:
        subprocess.run(  # pragma: no cover
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:  # pragma: no cover
        raise DemoCreateError(
            f"pdftoppm failed for {pdf} page {page}: "
            f"{exc.stderr.strip() or exc}"
        ) from exc
    if not png_path.is_file():  # pragma: no cover
        raise DemoCreateError(f"pdftoppm produced no output at {png_path}")
    return png_path


def render_pages(
    pdf: Path,
    out_dir: Path,
    *,
    pages: list[int] | None = None,
    dpi: int = 150,
    prefix: str = "page",
) -> list[Path]:
    """Rasterize several PDF pages to ``out_dir/<prefix>_<NNN>.png``.

    Args:
        pdf: Path to the PDF file.
        out_dir: Directory to write the PNGs into (created if absent).
        pages: 1-based page numbers to render; ``None`` renders every page.
        dpi: Render resolution in dots per inch.
        prefix: Filename prefix for each rendered page.

    Returns:
        Sorted list of written PNG paths.

    Raises:
        BackendUnavailableError: If ``pdftoppm``/``pdfinfo`` are not installed.
        DemoCreateError: If the file is missing or a render fails.
    """
    # _require here so the missing-backend path is exercised before page math.
    _require(_PDFTOPPM)
    pdf = Path(pdf)
    if not pdf.is_file():
        raise DemoCreateError(f"pdf not found: {pdf}")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if pages is None:
        pages = list(range(1, pdf_page_count(pdf) + 1))
    written: list[Path] = []
    for page in pages:
        out_path = out_dir / f"{prefix}_{page:03d}.png"
        written.append(render_page(pdf, page, out_path, dpi=dpi))
    return sorted(written)
