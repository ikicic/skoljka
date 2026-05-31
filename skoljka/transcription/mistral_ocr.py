"""Mistral OCR for PDF text extraction."""

import base64
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from skoljka.transcription.api_keys import require_api_key
from skoljka.transcription.cache import APICache, file_sha256

logger = logging.getLogger(__name__)

API_DELAY = 1
CACHE_VERSION = 2  # bump when changing what we store

DEFAULT_OCR_MODEL = "mistral-ocr-latest"


@dataclass
class OcrPage:
    """OCR result for a single page."""
    index: int
    markdown: str
    images: dict[str, str] = field(default_factory=dict)  # image id → base64


@dataclass
class OcrResult:
    """Full OCR result."""
    pages: list[OcrPage]
    model: str
    raw_response: dict[str, Any]  # full serialized API response


def ocr_pdf(pdf_path: str, model: str, cache: APICache) -> OcrResult:
    """Run Mistral OCR on a PDF and return full result (cached)."""
    fhash = file_sha256(pdf_path)
    cache_key = f"ocr:v{CACHE_VERSION}:{model}:{fhash}"
    cached = cache.get(cache_key)
    if cached is not None:
        logger.debug("OCR cache hit for %s", pdf_path)
        return _parse_cached(json.loads(cached))

    from mistralai.client import Mistral

    client = Mistral(api_key=require_api_key("MISTRAL_API_KEY"))
    with open(pdf_path, "rb") as f:
        pdf_b64 = base64.b64encode(f.read()).decode("utf-8")

    logger.info("Sending OCR request to %s for %s", model, pdf_path)
    time.sleep(API_DELAY)
    response = client.ocr.process(
        model=model,
        document={
            "type": "document_url",
            "document_url": f"data:application/pdf;base64,{pdf_b64}",
        },
        include_image_base64=True,
    )

    raw = response.model_dump()
    cache.put(cache_key, json.dumps(raw))
    result = _parse_cached(raw)
    logger.info("OCR response: %d pages, %d images",
                len(result.pages), sum(len(p.images) for p in result.pages))
    return result


def _parse_cached(raw: dict[str, Any]) -> OcrResult:
    """Parse a cached raw OCR response dict into an OcrResult."""
    pages = []
    for p in raw["pages"]:
        images = {}
        for img in p.get("images", []):
            b64 = img.get("image_base64", "")
            if b64:
                # Strip data URL prefix if present (e.g. "data:image/jpeg;base64,")
                if "," in b64:
                    b64 = b64.split(",", 1)[1]
                images[img["id"]] = b64
        pages.append(OcrPage(
            index=p["index"],
            markdown=p["markdown"],
            images=images,
        ))
    return OcrResult(pages=pages, model=raw.get("model", ""), raw_response=raw)
