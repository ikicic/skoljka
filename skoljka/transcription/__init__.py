"""OCR + LLM pipeline for converting math competition PDFs to LaTeX."""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

logger = logging.getLogger(__name__)

from skoljka.transcription.cache import APICache
from skoljka.transcription.chat import make_chat_provider, parse_model_flag
from skoljka.transcription.cleanup import cleanup_system_prompt_with_source_context, cleanup_with_llm
from skoljka.transcription.mistral_ocr import DEFAULT_OCR_MODEL, ocr_pdf
from skoljka.transcription.pdf import extract_image_regions, pdf_pages_to_base64
from skoljka.transcription.types import (
    ContentChunk,
    ImageChunk,
    PreparedPrompt,
    Problem,
    TextChunk,
)

DEFAULT_CHAT_MODEL = "anthropic/claude-sonnet-4-20250514"

Stage = Literal["ocr", "ocr-pdf", "cleanup-prompt", "cleanup", "cleanup-pdf"]
STAGES: list[Stage] = ["ocr", "ocr-pdf", "cleanup-prompt", "cleanup", "cleanup-pdf"]
DEFAULT_UNTIL: Stage = "cleanup-pdf"

PROBLEM_SECTION_RE = re.compile(
    r"\\section\*\{(?:Problem|Zadatak)\s+([A-Za-z0-9][A-Za-z0-9-]*)\}",
    re.IGNORECASE,
)

SET_SECTION_RE = re.compile(
    r"\\subsection\*\{(Set|Source):\s*(.*?)\}",
    re.IGNORECASE,
)

METADATA_RE = re.compile(r"^%\s*(year|language):\s*(.*?)\s*$", re.IGNORECASE | re.MULTILINE)
ProgressCallback = Callable[[str, str], None]


def split_problems(latex_body: str) -> list[Problem]:
    """Split a LaTeX body into individual problems.

    Recognizes \\subsection*{Set: <title>} as set separators and
    \\section*{Problem N} as problem headers.
    """
    events: list[tuple[int, str, re.Match[str]]] = []
    for m in SET_SECTION_RE.finditer(latex_body):
        events.append((m.start(), "set", m))
    for m in PROBLEM_SECTION_RE.finditer(latex_body):
        events.append((m.start(), "problem", m))
    events.sort(key=lambda e: e[0])

    if not any(t == "problem" for _, t, _ in events):
        return [Problem(problem_label="1", source_md=latex_body.strip(), set="")]

    problems: list[Problem] = []
    current_set = ""
    current_source_key = ""
    for i, (_, typ, m) in enumerate(events):
        if typ == "set":
            label = m.group(1).lower()
            value = m.group(2).strip()
            if label == "source":
                current_source_key = value
                current_set = value
            else:
                current_set = value
            continue
        start = m.end()
        end = events[i + 1][0] if i + 1 < len(events) else len(latex_body)
        source_md = latex_body[start:end].strip()
        problem = Problem(
            problem_label=m.group(1).upper(),
            source_md=source_md,
            set=current_set,
        )
        if current_source_key:
            problem["source_key"] = current_source_key
        problems.append(problem)
    return problems


def _extract_metadata(latex_body: str) -> tuple[str, int | None, str | None]:
    year = None
    language = None
    for key, value in METADATA_RE.findall(latex_body):
        value = value.strip()
        if key.lower() == "year" and value:
            try:
                year = int(value)
            except ValueError:
                pass
        elif key.lower() == "language" and value:
            language = value.lower()[:16]
    cleaned = METADATA_RE.sub("", latex_body).strip()
    return cleaned, year, language


@dataclass
class StageResult:
    """Result of a single processing stage (OCR or LLM cleanup)."""
    model: str
    text: str
    problems: list[Problem]


@dataclass
class TranscriptionResult:
    """Full transcription result with all intermediate stages."""
    stages: list[StageResult] = field(default_factory=list)
    images: dict[str, str] = field(default_factory=dict)  # id → base64
    ocr_raw_response: dict[str, Any] = field(default_factory=dict)
    prepared_prompt: PreparedPrompt | None = None
    year: int | None = None
    language: str | None = None

    @property
    def problems(self) -> list[Problem]:
        """Problems from the last stage."""
        return self.stages[-1].problems if self.stages else []


def _strip_image_base64(raw: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of the OCR response with image_base64 replaced."""
    raw = json.loads(json.dumps(raw))
    for page in raw.get("pages", []):
        for img in page.get("images", []):
            if "image_base64" in img:
                img["image_base64"] = "<stripped>"
    return raw


def _build_cleanup_prompt(
    ocr_raw_response: dict[str, Any],
    page_images_b64: list[str],
    extracted_images: dict[str, str],
    source_context: dict | None = None,
) -> PreparedPrompt:
    """Build the full prompt for the LLM cleanup stage."""
    content: list[ContentChunk] = []
    ocr_stripped = _strip_image_base64(ocr_raw_response)

    for page_data, img_b64 in zip(ocr_stripped.get("pages", []), page_images_b64):
        idx = page_data["index"]
        content.append(ImageChunk(
            type="image_url",
            image_url=f"data:image/png;base64,{img_b64}",
        ))
        content.append(TextChunk(
            type="text",
            text=f"Page {idx + 1} OCR:\n" + json.dumps(page_data, indent=2, ensure_ascii=False),
        ))

    for img_id, img_b64 in extracted_images.items():
        content.append(TextChunk(type="text", text=f"[Extracted figure: {img_id}]"))
        content.append(ImageChunk(
            type="image_url",
            image_url=f"data:image/png;base64,{img_b64}",
        ))

    return PreparedPrompt(
        system=cleanup_system_prompt_with_source_context(source_context),
        content=content,
    )


def _report_progress(progress: ProgressCallback | None, key: str, status: str) -> None:
    if progress:
        progress(key, status)


def transcribe_pdf(
    pdf_path: str,
    *,
    ocr_model: str = DEFAULT_OCR_MODEL,
    chat_model: str = DEFAULT_CHAT_MODEL,
    until: Stage = DEFAULT_UNTIL,
    cache: APICache,
    source_context: dict | None = None,
    progress: ProgressCallback | None = None,
) -> TranscriptionResult:
    """Full pipeline: OCR → cleanup-prompt → cleanup.

    Stages:
      ocr: OCR + image extraction
      cleanup-prompt: build the LLM prompt (but don't send)
      cleanup: send to LLM and get cleaned LaTeX

    Returns a TranscriptionResult with all completed stages.
    """
    result = TranscriptionResult()
    logger.info("Transcribing %s (until=%s)", pdf_path, until)

    # Stage: ocr
    _report_progress(progress, "ocr", "running")
    ocr_result = ocr_pdf(pdf_path, ocr_model, cache)
    ocr_text = "\n\n".join(p.markdown for p in ocr_result.pages)

    result.images = extract_image_regions(pdf_path, ocr_result.raw_response)
    result.ocr_raw_response = ocr_result.raw_response

    for page in ocr_result.pages:
        for old_id in page.images:
            new_id = old_id.rsplit(".", 1)[0] + ".png" if old_id.endswith((".jpeg", ".jpg")) else old_id
            if old_id != new_id:
                ocr_text = ocr_text.replace(old_id, new_id)

    ocr_problems = split_problems(ocr_text)
    result.stages.append(StageResult(
        model=ocr_model,
        text=ocr_text,
        problems=ocr_problems,
    ))
    logger.info("OCR done: %d pages, %d images, %d problems detected",
                len(ocr_result.pages), len(result.images), len(ocr_problems))
    _report_progress(progress, "ocr", "done")

    if until in ("ocr", "ocr-pdf"):
        return result

    # Stage: cleanup-prompt
    _report_progress(progress, "llm", "running")
    page_images_b64 = pdf_pages_to_base64(pdf_path)
    prompt = _build_cleanup_prompt(
        ocr_result.raw_response, page_images_b64, result.images, source_context,
    )
    result.prepared_prompt = prompt

    if until == "cleanup-prompt":
        return result

    # Stage: cleanup
    provider_name, model_name = parse_model_flag(chat_model)
    chat_provider = make_chat_provider(provider_name)

    cleaned = cleanup_with_llm(
        chat_provider, prompt["system"], prompt["content"],
        model=model_name, cache=cache,
    )
    cleaned_body, year, language = _extract_metadata(cleaned)
    result.year = year
    result.language = language
    cleaned_problems = split_problems(cleaned_body)
    result.stages.append(StageResult(
        model=chat_model,
        text=cleaned_body,
        problems=cleaned_problems,
    ))
    logger.info("LLM cleanup done: %d problems", len(cleaned_problems))
    _report_progress(progress, "llm", "done")

    return result
