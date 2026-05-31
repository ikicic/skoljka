"""Slice a PDF byte stream to selected pages."""

import io

import pymupdf


def slice_pdf(pdf_bytes: bytes, pages: list[int]) -> bytes:
    """Return a new PDF for the requested 0-based page indices."""
    src = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    try:
        indices = sorted({p for p in pages if 0 <= p < len(src)})
        if not indices:
            raise ValueError("no valid pages selected")
        dst = pymupdf.open()
        try:
            for idx in indices:
                dst.insert_pdf(src, from_page=idx, to_page=idx)
            buf = io.BytesIO()
            dst.save(buf)
            return buf.getvalue()
        finally:
            dst.close()
    finally:
        src.close()


def page_count(pdf_bytes: bytes) -> int:
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    try:
        return len(doc)
    finally:
        doc.close()
