"""PDF page rendering utilities."""

import base64
import logging
from typing import Any

import pymupdf

logger = logging.getLogger(__name__)


def pdf_pages_to_base64(pdf_path: str, dpi: int = 150) -> list[str]:
    """Render each PDF page to a base64-encoded PNG."""
    doc = pymupdf.open(pdf_path)
    result = []
    scale = dpi / 72
    matrix = pymupdf.Matrix(scale, scale)
    for page in doc:
        pix = page.get_pixmap(matrix=matrix)
        result.append(base64.b64encode(pix.tobytes("png")).decode("utf-8"))
    doc.close()
    return result


def extract_image_regions(
    pdf_path: str,
    raw_ocr_response: dict[str, Any],
    dpi: int = 300,
) -> dict[str, str]:
    """Render image regions from the PDF as lossless PNGs.

    Uses the bounding boxes from the OCR response to clip each detected
    image region from the PDF page at the given DPI.

    Returns a dict of image id → base64-encoded PNG.
    """
    doc = pymupdf.open(pdf_path)
    images: dict[str, str] = {}

    for page_data in raw_ocr_response.get("pages", []):
        page_idx = page_data["index"]
        page_images = page_data.get("images", [])
        if not page_images:
            continue

        dims = page_data.get("dimensions")
        if not dims:
            continue

        page = doc[page_idx]
        page_rect = page.rect

        # OCR coordinates are in the OCR image space (at dims["dpi"]).
        # Scale them to PDF points (72 dpi).
        ocr_dpi = dims.get("dpi", 200)
        ocr_to_points = 72.0 / ocr_dpi

        for img in page_images:
            x0, y0 = img.get("top_left_x"), img.get("top_left_y")
            x1, y1 = img.get("bottom_right_x"), img.get("bottom_right_y")
            if x0 is None or y0 is None or x1 is None or y1 is None:
                continue

            # Convert OCR pixel coords to PDF points
            clip = pymupdf.Rect(
                x0 * ocr_to_points,
                y0 * ocr_to_points,
                x1 * ocr_to_points,
                y1 * ocr_to_points,
            ) & page_rect  # intersect with page bounds

            scale = dpi / 72
            matrix = pymupdf.Matrix(scale, scale)
            pix = page.get_pixmap(matrix=matrix, clip=clip)

            img_id = img["id"]
            # Change extension to .png since we're rendering lossless
            if img_id.endswith((".jpeg", ".jpg")):
                img_id = img_id.rsplit(".", 1)[0] + ".png"

            images[img_id] = base64.b64encode(pix.tobytes("png")).decode("utf-8")
            logger.info("Extracted %s from page %d (%dx%d)",
                        img_id, page_idx, pix.width, pix.height)

    doc.close()
    return images
