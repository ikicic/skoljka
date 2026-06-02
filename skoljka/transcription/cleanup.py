"""LLM-based cleanup of OCR output."""

import hashlib
import json
import logging

from skoljka.transcription.cache import APICache
from skoljka.transcription.chat import ChatProvider
from skoljka.transcription.types import ContentChunk

logger = logging.getLogger(__name__)

CLEANUP_SYSTEM_PROMPT = """\
You are a LaTeX formatting assistant for math competition problems.
You will receive raw OCR output from a math competition PDF, together \
with the original page images.

Your task:
- Output ONLY the math problems as clean LaTeX.
- Remove all headers, footers, page numbers, contest titles, dates, \
organizer names, solutions and any other non-problem text.
- A single PDF may contain multiple problem sets (e.g. different grades \
or categories). Preserve this structure. Use \\section*{Problem N} for \
each problem, keeping the original numbering from each set. When \
numbering restarts (e.g. 1–5 for grade 5, then 1–5 for grade 6), \
output a separator to mark the new set. Use this format:

\\subsection*{Set: <set title>}

\\section*{Problem 1}
...problem text...

\\section*{Problem 2}
...problem text...

\\subsection*{Set: <next set title>}

\\section*{Problem 1}
...problem text...

- Use the app's Markdown+LaTeX math delimiters: $...$ for inline math \
and $$...$$ for display math.
- Do not use \\[...\\], \\(...\\), or bare display environments such as \
\\begin{align*}...\\end{align*}. For aligned display math, put an \
aligned environment inside $$...$$, e.g. \
$$\\begin{aligned}...\\end{aligned}$$.
- Preserve the original mathematical content exactly. Do not solve or \
simplify anything.
- The OCR text may be missing italic and bold formatting. Use the page \
images to restore \\textit{} and \\textbf{} where appropriate.
- Keep all image references from the OCR markdown. Convert them to \
\\includegraphics[width=Xcm]{filename}, e.g. ![img-0.png](img-0.png) \
becomes \\includegraphics[width=4cm]{img-0.png}. Estimate the display \
width in cm based on how large the figure appears on the page. These \
images contain figures referenced by the problems.
- Do not include \\documentclass, \\begin{document}, or any preamble. \
Output only the body content.
- Do not wrap the output in markdown code fences or any other markup.
- Make sure you don't mix up absolute values and floor/ceil functions.
- Escape the percent sign as \\% in text mode (e.g. 80\\%).
- In geometry problems, prefer \\measuredangle over \\angle when referring to \
the measurement of an angle, and use \\angle when referring to the geometric \
angle as a shape.
"""


def cleanup_with_llm(
    chat_provider: ChatProvider,
    system: str,
    content: list[ContentChunk],
    model: str,
    cache: APICache,
) -> str:
    """Send a pre-built prompt to the LLM for cleanup."""
    h = hashlib.sha256()
    h.update(system.encode())
    h.update(model.encode())
    h.update(json.dumps(content, sort_keys=True).encode())
    cache_key = f"cleanup:{h.hexdigest()}"
    cached = cache.get(cache_key)
    if cached is not None:
        logger.debug("Cleanup cache hit")
        return cached

    n_images = sum(1 for c in content if c.get("type") == "image_url")
    logger.info("Sending cleanup request to %s (%d images)", model, n_images)
    result = chat_provider.chat(system, content, model)
    logger.info("Cleanup response: %d chars", len(result))

    cache.put(cache_key, result)
    return result


def cleanup_system_prompt_with_source_context(source_context: dict | None) -> str:
    if not source_context:
        return CLEANUP_SYSTEM_PROMPT
    return CLEANUP_SYSTEM_PROMPT + f"""\

Source assignment:
- The import UI selected a parent/default source and may provide child sources.
- Use headers, footers, contest titles, grade labels, and page context to assign
  each problem to exactly one allowed source key.
- If the source is unclear, use default_source_key.
- Before each group of problems from the same source, output:
  \\subsection*{{Source: <source_key>}}
- At the top of the output, infer year and language from problem statements:
  % year: 2024
  % language: hr
- If year is unclear, write % year:
- If language is unclear, write % language:
- Allowed source context:
{json.dumps(source_context, ensure_ascii=False, indent=2)}
"""
