"""Backend abstraction for PDF transcription."""

import re
import tempfile
from pathlib import Path
from typing import Any, Callable, Protocol

from skoljka.transcription import transcribe_pdf
from skoljka.transcription.cache import APICache

ProgressCallback = Callable[[str, str], None]
MARKDOWN_IMAGE_RE = re.compile(
    r"!\[([^\]\n]*)\]\(([^)\s]+)(?:\s+\"([^\"]*)\")?\)(\{width=[^}]+\})?"
)
INCLUDEGRAPHICS_RE = re.compile(r"\\includegraphics(?:\[([^\]]*)\])?\{([^}]+)\}")


class SandboxBackend(Protocol):
    def transcribe(
        self,
        pdf_bytes: bytes,
        source_context: dict[str, Any] | None = None,
        progress: ProgressCallback | None = None,
    ) -> dict[str, Any]: ...


class InProcessBackend:
    """Runs transcription in the current process via a temp file."""

    def __init__(self, cache: APICache, ocr_model: str, chat_model: str) -> None:
        self.cache = cache
        self.ocr_model = ocr_model
        self.chat_model = chat_model

    def transcribe(
        self,
        pdf_bytes: bytes,
        source_context: dict[str, Any] | None = None,
        progress: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as f:
            f.write(pdf_bytes)
            f.flush()
            result = transcribe_pdf(
                f.name,
                ocr_model=self.ocr_model,
                chat_model=self.chat_model,
                cache=self.cache,
                source_context=source_context,
                progress=progress,
            )
            image_names = sorted(result.images)
            return {
                "year": result.year,
                "language": result.language,
                "images": result.images,
                "problems": [
                    {
                        **problem,
                        "source_md": normalize_image_references(
                            problem.get("source_md", ""), image_names,
                        ),
                    }
                    for problem in result.problems
                ],
            }


def make_default_backend() -> SandboxBackend:
    """Return the configured production backend."""
    from django.conf import settings

    cache_path = Path(settings.TRANSCRIPTION_PRIVATE_DIR) / "api_cache.sqlite"
    cache = APICache(cache_path, ttl_seconds=settings.TRANSCRIPTION_TTL_DAYS * 86400)
    return InProcessBackend(
        cache=cache,
        ocr_model=settings.TRANSCRIPTION_OCR_MODEL,
        chat_model=settings.TRANSCRIPTION_CHAT_MODEL,
    )


def normalize_image_references(source_md: str, image_names: list[str]) -> str:
    """Point known extracted images at ContentAttachment-style URLs.

    The OCR/LLM pipeline may produce either Markdown images, such as
    ``![figure](img-0.png)``, or LaTeX-ish ``\\includegraphics{img-0.png}``.
    The site renderer understands attachments through
    ``attachment:<name>``, so normalize only filenames that came from the
    PDF extraction stage.
    """
    name_by_basename = {Path(name).name: name for name in image_names}
    names = set(image_names)

    def known_name(raw: str) -> str | None:
        name = raw.removeprefix("attachment:").strip()
        if name in names:
            return name
        return name_by_basename.get(Path(name).name)

    def normalize_markdown(match: re.Match[str]) -> str:
        alt, src, title, width = match.groups()
        name = known_name(src)
        if not name:
            return match.group(0)
        title_part = f' "{title}"' if title else ""
        width_part = width or ""
        return f"![{alt}](attachment:{name}{title_part}){width_part}"

    def normalize_includegraphics(match: re.Match[str]) -> str:
        options, src = match.groups()
        name = known_name(src)
        if not name:
            return match.group(0)
        width = _includegraphics_width_percent(options or "")
        width_part = f"{{width={width}%}}" if width else ""
        return f"![figure](attachment:{name}){width_part}"

    source_md = MARKDOWN_IMAGE_RE.sub(normalize_markdown, source_md)
    return INCLUDEGRAPHICS_RE.sub(normalize_includegraphics, source_md)


def _includegraphics_width_percent(options: str) -> int | None:
    match = re.search(r"(?:^|,)\s*width\s*=\s*([^,\]]+)", options)
    if not match:
        return None
    raw = match.group(1).strip()
    if raw.endswith("%"):
        try:
            return round(float(raw[:-1]))
        except ValueError:
            return None
    linewidth = re.fullmatch(r"(\d+(?:\.\d+)?)\\linewidth", raw)
    if linewidth:
        return round(float(linewidth.group(1)) * 100)
    cm = re.fullmatch(r"(\d+(?:\.\d+)?)\s*cm", raw)
    if cm:
        return min(100, max(5, round(float(cm.group(1)) / 16 * 100)))
    return None
