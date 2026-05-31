#!/usr/bin/env python3
"""Batch-process math competition PDFs: download and transcribe to LaTeX.

Usage:
    python -m skoljka.tools.process download DATA/croatian/index.json
    python -m skoljka.tools.process transcribe DATA/croatian/index.json
    python -m skoljka.tools.process transcribe DATA/croatian/index.json --until=cleanup-prompt
    python -m skoljka.tools.process transcribe DATA/croatian/index.json --filter="školsko/2025/*"
"""

import argparse
import base64
import fnmatch
import html
import json
import logging
import re
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from subprocess import CalledProcessError
from typing import Any, Literal, Self, cast

logger = logging.getLogger(__name__)

from skoljka.transcription import (
    DEFAULT_CHAT_MODEL,
    DEFAULT_OCR_MODEL,
    DEFAULT_UNTIL,
    STAGES,
    Stage,
    TranscriptionResult,
    transcribe_pdf,
)
from skoljka.transcription.types import ContentChunk, ImageChunk
from skoljka.utils.external_runner import run_external
from skoljka.transcription.cache import APICache


@dataclass
class IndexEntry:
    url: str
    path: str
    competition_level: str
    school_type: str
    year: int | str
    titles: list[str]

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Self:
        return cls(
            url=d["url"],
            path=d["path"],
            competition_level=d["competition_level"],
            school_type=d["school_type"],
            year=d["year"],
            titles=d["titles"],
        )


@dataclass
class DownloadArgs:
    command: Literal["download"]
    index_path: Path
    force: bool
    filter: str | None
    limit: int | None
    verbose: bool


DEFAULT_OUTPUT_DIR = Path("PROCESSED")


@dataclass
class TranscribeArgs:
    command: Literal["transcribe"]
    index_path: Path
    force: bool
    filter: str | None
    limit: int | None
    verbose: bool
    output_dir: Path
    ocr_model: str
    model: str
    until: Stage


Args = DownloadArgs | TranscribeArgs


def load_index(path: Path) -> list[IndexEntry]:
    """Load the index JSON, parsing each entry into an IndexEntry."""
    with open(path) as f:
        raw = json.load(f)
    return [IndexEntry.from_dict(e) for e in raw]


def cmd_download(
    entries: list[IndexEntry],
    base_dir: Path,
    *,
    force: bool = False,
) -> None:
    """Download PDFs. Skip if file exists (unless --force)."""
    for entry in entries:
        dest = base_dir / entry.path
        if dest.exists() and not force:
            continue
        logger.info("Downloading %s from %s", entry.path, entry.url)
        dest.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(entry.url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req) as resp:
                dest.write_bytes(resp.read())
        except Exception as e:
            logger.error("Download failed for %s: %s", entry.path, e)


def output_dir_for_entry(output_dir: Path, entry: IndexEntry) -> Path:
    """Return the output directory for a single entry.

    Layout: output_dir/<level>/<year>/<stem>/
    e.g. PROCESSED/školsko/2025/zadOS_sk_2025/
    """
    pdf_rel = Path(entry.path)
    return output_dir / pdf_rel.parent / pdf_rel.stem


# Output filenames per stage.
OCR_FILE = "ocr_response.json"
OCR_PDF_FILE = "ocr_preview.pdf"
PROMPT_FILE = "prepared_prompt.json"
CLEANUP_FILE = "cleanup_result.json"
CLEANUP_PDF_FILE = "cleanup_preview.pdf"

STAGE_FILES: dict[Stage, str] = {
    "ocr": OCR_FILE,
    "ocr-pdf": OCR_PDF_FILE,
    "cleanup-prompt": PROMPT_FILE,
    "cleanup": CLEANUP_FILE,
    "cleanup-pdf": CLEANUP_PDF_FILE,
}


DOLLAR_MATH_LUA = Path(__file__).resolve().parent.parent / "transcription" / "dollar_math.lua"

LATEX_TEMPLATE = r"""\documentclass[a4paper,12pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{graphicx}
\usepackage{geometry}
\geometry{margin=2.5cm}

\begin{document}

%s

\end{document}
"""


def _render_markdown_pdf(markdown: str, output_path: Path) -> bool:
    """Render markdown+LaTeX to PDF via pandoc. Returns True on success.

    Saves the input as .md next to the output for debugging.
    """
    # Unescape HTML entities (OCR may output &gt; etc.)
    markdown = html.unescape(markdown)
    # Convert $$...$$ to raw LaTeX blocks — pandoc misparses $$ inside list items.
    markdown = re.sub(
        r'\$\$\s*\n(.*?)\n\s*\$\$',
        lambda m: '\n```{=latex}\n\\[\n' + m.group(1).strip() + '\n\\]\n```\n',
        markdown,
        flags=re.DOTALL,
    )
    # Replace Unicode chars that pdflatex can't handle.
    cleaned = ""
    for ch in markdown:
        try:
            ch.encode("latin-1")
            cleaned += ch
        except UnicodeEncodeError:
            if ord(ch) < 0x2000:  # extended latin — might work
                cleaned += ch
            else:
                cleaned += "?"

    md_path = output_path.with_suffix(".md")
    md_path.write_text(cleaned)
    logger.debug("Wrote pandoc input to %s", md_path)

    try:
        run_external(
            ["pandoc", "-f", "markdown", "--pdf-engine=pdflatex",
             f"--lua-filter={DOLLAR_MATH_LUA}",
             "-o", output_path.name],
            input=cleaned,
            cwd=output_path.parent,
            capture_output=True,
            text=True,
            check=True,
        )
        return True
    except CalledProcessError as e:
        logger.warning("pandoc PDF failed (see %s): %s", md_path, e.stderr[:200])
        return False


def _render_latex_pdf(latex_body: str, output_path: Path) -> bool:
    """Render LaTeX body to PDF via pdflatex. Returns True on success.

    Saves the .tex source next to the output for debugging.
    """
    tex_path = output_path.with_suffix(".tex")
    tex_path.write_text(LATEX_TEMPLATE % latex_body)
    logger.debug("Wrote pdflatex input to %s", tex_path)

    try:
        run_external(
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error",
             tex_path.name],
            cwd=tex_path.parent,
            capture_output=True,
            text=True,
            check=True,
        )
        # Clean up aux files (keep .tex for debugging)
        for ext in (".aux", ".log"):
            p = output_path.with_suffix(ext)
            if p.exists():
                p.unlink()
        return True
    except CalledProcessError as e:
        output = e.stdout or e.stderr or ""
        # Find the error line
        error_lines = [l for l in output.splitlines() if l.startswith("!")]
        logger.warning("pdflatex failed (see %s): %s",
                       tex_path, "; ".join(error_lines) or output[:200])
        return False


def _strip_image_base64(raw: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of the OCR response with image_base64 replaced."""
    raw = json.loads(json.dumps(raw))
    for page in raw.get("pages", []):
        for img in page.get("images", []):
            if "image_base64" in img:
                img["image_base64"] = "<stripped>"
    return raw


def _save_ocr(entry_dir: Path, result: TranscriptionResult) -> None:
    """Save OCR stage outputs: ocr_response.json + images."""
    entry_dir.mkdir(parents=True, exist_ok=True)

    ocr_stripped = _strip_image_base64(result.ocr_raw_response)
    (entry_dir / OCR_FILE).write_text(
        json.dumps(ocr_stripped, indent=2, ensure_ascii=False))

    saved = 0
    for img_id, img_b64 in result.images.items():
        (entry_dir / img_id).write_bytes(base64.b64decode(img_b64))
        saved += 1
    if saved:
        logger.info("Saved %d images to %s", saved, entry_dir)


def _save_ocr_pdf(entry_dir: Path, result: TranscriptionResult) -> None:
    """Render OCR markdown to PDF preview."""
    ocr_text = result.stages[0].text
    if _render_markdown_pdf(ocr_text, entry_dir / OCR_PDF_FILE):
        logger.info("Rendered OCR preview PDF")


def _save_prompt(entry_dir: Path, result: TranscriptionResult) -> None:
    """Save the prepared LLM prompt (with base64 truncated for readability)."""
    if result.prepared_prompt is None:
        return
    entry_dir.mkdir(parents=True, exist_ok=True)
    prompt_dump = dict(result.prepared_prompt)
    content = cast(list[ContentChunk], prompt_dump["content"])
    prompt_dump["content"] = [_strip_prompt_chunk(c) for c in content]
    (entry_dir / PROMPT_FILE).write_text(
        json.dumps(prompt_dump, indent=2, ensure_ascii=False))
    logger.info("Saved prepared prompt to %s", entry_dir / PROMPT_FILE)


def _strip_prompt_chunk(chunk: ContentChunk) -> ContentChunk:
    if chunk.get("type") != "image_url":
        return chunk
    image_chunk = cast(ImageChunk, chunk)
    return {**image_chunk, "image_url": image_chunk["image_url"][:40] + "...<base64>"}


def _save_cleanup(entry_dir: Path, result: TranscriptionResult) -> None:
    """Save cleanup stage output."""
    stage = result.stages[-1]
    output = {"model": stage.model, "text": stage.text, "problems": stage.problems}
    entry_dir.mkdir(parents=True, exist_ok=True)
    (entry_dir / CLEANUP_FILE).write_text(
        json.dumps(output, indent=2, ensure_ascii=False))


def _save_cleanup_pdf(entry_dir: Path, result: TranscriptionResult) -> None:
    """Render cleanup LaTeX to PDF preview."""
    stage = result.stages[-1]
    if _render_latex_pdf(stage.text, entry_dir / CLEANUP_PDF_FILE):
        logger.info("Rendered cleanup preview PDF")


def cmd_transcribe(
    entries: list[IndexEntry],
    data_dir: Path,
    output_dir: Path,
    *,
    force: bool = False,
    ocr_model: str = DEFAULT_OCR_MODEL,
    chat_model: str = DEFAULT_CHAT_MODEL,
    until: Stage = DEFAULT_UNTIL,
    cache: APICache,
) -> None:
    """Transcribe PDFs to structured JSON. Each stage checks its own output file."""
    target_idx = STAGES.index(until)

    for entry in entries:
        pdf_path = data_dir / entry.path
        entry_dir = output_dir_for_entry(output_dir, entry)

        if not pdf_path.exists():
            logger.warning("SKIP (no PDF): %s", entry.path)
            continue

        # Find the earliest stage that needs to run.
        earliest_needed: Stage | None = None
        for stage in STAGES[:target_idx + 1]:
            if force or not (entry_dir / STAGE_FILES[stage]).exists():
                earliest_needed = stage
                break

        if earliest_needed is None:
            logger.debug("SKIP (all stages done): %s", entry.path)
            continue

        # We always run the pipeline from the start (OCR is cached),
        # but only up to the requested stage.
        logger.info("Processing %s (%s → %s)", entry.path, earliest_needed, until)
        try:
            result = transcribe_pdf(
                str(pdf_path),
                ocr_model=ocr_model,
                chat_model=chat_model,
                until=until,
                cache=cache,
            )
        except Exception as e:
            logger.error("Transcription failed for %s: %s", entry.path, e)
            continue

        # Save outputs for each stage that was requested.
        if target_idx >= STAGES.index("ocr"):
            _save_ocr(entry_dir, result)
        if target_idx >= STAGES.index("ocr-pdf"):
            _save_ocr_pdf(entry_dir, result)
        if target_idx >= STAGES.index("cleanup-prompt"):
            _save_prompt(entry_dir, result)
        if target_idx >= STAGES.index("cleanup") and len(result.stages) >= 2:
            _save_cleanup(entry_dir, result)
        if target_idx >= STAGES.index("cleanup-pdf") and len(result.stages) >= 2:
            _save_cleanup_pdf(entry_dir, result)

        logger.info("Done: %s (until=%s)", entry.path, until)


def filter_entries(entries: list[IndexEntry], pattern: str) -> list[IndexEntry]:
    """Filter entries by glob pattern matched against the path."""
    return [e for e in entries if fnmatch.fnmatch(e.path, pattern)]


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    add = parser.add_argument
    add("index_path", type=Path, help="Path to the index JSON file.")
    add("--force", action="store_true",
        help="Re-run even if output already exists.")
    add("--filter", default=None,
        help="Glob pattern to select entries by path (e.g. 'školsko/2025/*').")
    add("--limit", type=int, default=None,
        help="Maximum number of entries to process.")
    add("-v", "--verbose", action="store_true",
        help="Enable debug logging.")


def parse_args(argv: list[str] | None = None) -> Args:
    parser = argparse.ArgumentParser(
        description="Batch-process math competition PDFs.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    dl = sub.add_parser("download", help="Download PDFs.",
                        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    _add_common_args(dl)

    tr = sub.add_parser("transcribe", help="Transcribe PDFs to LaTeX.",
                        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    _add_common_args(tr)
    add = tr.add_argument
    add("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
        help="Output directory for transcription results.")
    add("--ocr-model", default=DEFAULT_OCR_MODEL, help="Mistral OCR model.")
    add("--model", default=DEFAULT_CHAT_MODEL, help="Chat model as provider/model.")
    add("--until", choices=STAGES, default=DEFAULT_UNTIL,
        help="Stop after this stage.")

    ns = parser.parse_args(argv)

    match ns.command:
        case "download":
            return DownloadArgs(
                command=ns.command,
                index_path=ns.index_path,
                force=ns.force,
                filter=ns.filter,
                limit=ns.limit,
                verbose=ns.verbose,
            )
        case "transcribe":
            return TranscribeArgs(
                command=ns.command,
                index_path=ns.index_path,
                force=ns.force,
                filter=ns.filter,
                limit=ns.limit,
                verbose=ns.verbose,
                output_dir=ns.output_dir,
                ocr_model=ns.ocr_model,
                model=ns.model,
                until=ns.until,
            )
        case _:
            parser.error(f"Unknown command: {ns.command}")


def main() -> None:
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    if not args.index_path.exists():
        logger.error("Index file not found: %s", args.index_path)
        sys.exit(1)

    base_dir = args.index_path.parent
    entries = load_index(args.index_path)
    logger.info("Loaded %d entries from %s", len(entries), args.index_path)

    if args.filter:
        entries = filter_entries(entries, args.filter)
        logger.info("Filtered to %d entries", len(entries))

    if args.limit is not None:
        entries = entries[:args.limit]
        logger.info("Limited to %d entries", len(entries))

    match args:
        case DownloadArgs():
            cmd_download(entries, base_dir, force=args.force)
        case TranscribeArgs():
            cache = APICache(base_dir / "api_cache.db", ttl_seconds=7 * 24 * 60 * 60)
            cmd_transcribe(
                entries, base_dir, args.output_dir,
                force=args.force,
                ocr_model=args.ocr_model,
                chat_model=args.model,
                until=args.until,
                cache=cache,
            )

    logger.info("Done.")


if __name__ == "__main__":
    main()
