"""Markdown + LaTeX compilation pipeline.

The renderer lives in TypeScript under ts/shared so browser previews and
server-side cached HTML use the same parser/compiler.
"""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

_NODE_RENDERER = Path(__file__).resolve().parents[2] / "scripts" / "render-markdown.mjs"
_NODE_LATEX_RENDERER = Path(__file__).resolve().parents[2] / "scripts" / "render-latex.mjs"


@dataclass(frozen=True)
class LatexRenderResult:
    body: str
    errors: list[dict[str, str]]
    packages: list[str]


def compile_markdown(
    source_md: str,
    *,
    attachment_urls: dict[str, str] | None = None,
) -> tuple[str, str]:
    """Compile Markdown + LaTeX source to cached HTML and search text."""
    # TODO: If imports become render-heavy, replace per-save Node startup with
    # a batched renderer or a small long-running local rendering service.
    payload = json.dumps(
        {"source": source_md, "attachmentUrls": attachment_urls or {}},
        ensure_ascii=False,
    )
    result = subprocess.run(
        ["node", str(_NODE_RENDERER)],
        input=payload,
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )
    if result.returncode:
        raise RuntimeError(f"Markdown renderer failed: {result.stderr.strip()}")
    data = json.loads(result.stdout)
    return data["html"], data["text"]


def render_latex(
    source_md: str,
    *,
    attachment_paths: dict[str, str] | None = None,
) -> LatexRenderResult:
    """Render Markdown + LaTeX source to a normalized LaTeX body."""
    payload = json.dumps(
        {"source": source_md, "attachmentPaths": attachment_paths or {}},
        ensure_ascii=False,
    )
    result = subprocess.run(
        ["node", str(_NODE_LATEX_RENDERER)],
        input=payload,
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )
    if result.returncode:
        raise RuntimeError(f"LaTeX renderer failed: {result.stderr.strip()}")
    data = json.loads(result.stdout)
    return LatexRenderResult(
        body=data["body"],
        errors=data["errors"],
        packages=data["packages"],
    )
