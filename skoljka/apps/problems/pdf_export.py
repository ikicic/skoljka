import shutil
from io import BytesIO
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from django.utils.translation import get_language, gettext as _

from skoljka.apps.problems.models import Problem
from skoljka.apps.problems.titles import problem_display_title, problem_title_context
from skoljka.utils.external_runner import external_temporary_directory, run_external
from skoljka.utils.markdown import render_latex


MAX_PDF_EXPORT_PROBLEMS = 100
PDF_HEADING_NONE = "none"
PDF_HEADING_NUMBER = "number"
PDF_HEADING_LABEL = "label"
PDF_HEADING_TITLE = "title"
PDF_HEADING_NUMBER_TITLE = "number-title"
PDF_HEADING_MODES = {
    PDF_HEADING_NONE,
    PDF_HEADING_NUMBER,
    PDF_HEADING_LABEL,
    PDF_HEADING_TITLE,
    PDF_HEADING_NUMBER_TITLE,
}
PDF_HEADING_DEFAULT = PDF_HEADING_LABEL


class PdfExportError(Exception):
    pass


@dataclass(frozen=True)
class ProblemPdfExport:
    filename: str
    data: bytes


@dataclass(frozen=True)
class ProblemLatexExport:
    filename: str
    data: bytes


def export_problems_pdf(
    problems: list[Problem],
    *,
    title: str,
    filename: str,
    compact_generated_titles_for: tuple[int, int] | None = None,
    heading_mode: str = PDF_HEADING_DEFAULT,
) -> ProblemPdfExport:
    if len(problems) > MAX_PDF_EXPORT_PROBLEMS:
        raise PdfExportError(_("Too many problems to export at once."))
    with external_temporary_directory() as build_dir:
        tex_path = _build_latex_export(
            problems,
            build_dir,
            title=title,
            compact_generated_titles_for=compact_generated_titles_for,
            heading_mode=heading_mode,
        )
        pdf_path = build_dir / "problems.pdf"

        result = run_external(
            ["xelatex", "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
            cwd=build_dir,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        if result.returncode != 0 or not pdf_path.exists():
            log = (result.stderr or result.stdout or "").strip()
            raise PdfExportError(log[:1000] or _("PDF export failed."))
        return ProblemPdfExport(filename=filename, data=pdf_path.read_bytes())


def export_problems_latex_zip(
    problems: list[Problem],
    *,
    title: str,
    filename: str,
    compact_generated_titles_for: tuple[int, int] | None = None,
    heading_mode: str = PDF_HEADING_DEFAULT,
) -> ProblemLatexExport:
    if len(problems) > MAX_PDF_EXPORT_PROBLEMS:
        raise PdfExportError(_("Too many problems to export at once."))
    with external_temporary_directory() as build_dir:
        _build_latex_export(
            problems,
            build_dir,
            title=title,
            compact_generated_titles_for=compact_generated_titles_for,
            heading_mode=heading_mode,
        )
        data = BytesIO()
        with ZipFile(data, "w", ZIP_DEFLATED) as zf:
            for path in sorted(p for p in build_dir.rglob("*") if p.is_file()):
                zf.write(path, path.relative_to(build_dir).as_posix())
        return ProblemLatexExport(filename=filename, data=data.getvalue())


def _build_latex_export(
    problems: list[Problem],
    build_dir: Path,
    *,
    title: str,
    compact_generated_titles_for: tuple[int, int] | None,
    heading_mode: str,
) -> Path:
    heading_mode = normalize_pdf_heading_mode(heading_mode)
    packages: set[str] = set()
    body = _problem_sections(problems, build_dir, packages, compact_generated_titles_for, heading_mode)
    tex = _latex_document(title, body, packages)
    tex_path = build_dir / "problems.tex"
    tex_path.write_text(tex, encoding="utf-8")
    return tex_path


def _problem_sections(
    problems: list[Problem],
    build_dir: Path,
    packages: set[str],
    compact_generated_titles_for: tuple[int, int] | None = None,
    heading_mode: str = PDF_HEADING_DEFAULT,
) -> str:
    if not problems:
        return _latex_problem_placeholder(_("No problems found."))
    parts = []
    language = get_language()
    title_context = problem_title_context(problems, compact_generated_titles_for)
    for index, problem in enumerate(problems, start=1):
        content = next(iter(problem.content.all()), None)
        statement = ""
        if content:
            source = content.source_for(language)
            attachment_paths = _copy_attachments(content, build_dir, problem_index=index)
            rendered = render_latex(source, attachment_paths=attachment_paths)
            statement = rendered.body
            packages.update(rendered.packages)
        if not statement:
            statement = _latex_problem_placeholder(_("No problem statement available."))
        parts.append(_problem_latex_section(index, problem, title_context, heading_mode, statement))
    return "\n".join(parts)


def normalize_pdf_heading_mode(raw: str | None) -> str:
    return raw if raw in PDF_HEADING_MODES else PDF_HEADING_DEFAULT


def problem_export_heading(index: int, problem: Problem, title_context=None, heading_mode: str = PDF_HEADING_DEFAULT) -> str:
    heading_mode = normalize_pdf_heading_mode(heading_mode)
    if heading_mode == PDF_HEADING_NONE:
        return ""
    title = problem_display_title(problem, title_context)
    if heading_mode == PDF_HEADING_NUMBER:
        return f"{index}."
    if heading_mode == PDF_HEADING_LABEL:
        return _problem_label_heading(index, problem)
    if heading_mode == PDF_HEADING_TITLE:
        return title
    return f"{index}. {title}"


def _problem_latex_heading(index: int, problem: Problem, title_context, heading_mode: str) -> str:
    heading_mode = normalize_pdf_heading_mode(heading_mode)
    if heading_mode == PDF_HEADING_NONE:
        return ""
    title = problem_display_title(problem, title_context)
    if heading_mode == PDF_HEADING_NUMBER:
        return render_latex(f"{index}\\.").body
    if heading_mode == PDF_HEADING_LABEL:
        return render_latex(_problem_label_heading(index, problem).replace(".", r"\.")).body
    if heading_mode == PDF_HEADING_TITLE:
        return render_latex(title).body
    return render_latex(f"{index}\\. {title}").body


def _problem_latex_section(index: int, problem: Problem, title_context, heading_mode: str, statement: str) -> str:
    heading_mode = normalize_pdf_heading_mode(heading_mode)
    if heading_mode in {PDF_HEADING_NUMBER, PDF_HEADING_LABEL}:
        heading = _problem_latex_heading(index, problem, title_context, heading_mode)
        return f"\\problemblock\n\\noindent {heading}\\quad {statement}\n"
    heading = _problem_latex_heading(index, problem, title_context, heading_mode)
    heading_tex = f"\\problemheading{{{heading}}}\n\n" if heading else "\\problemblock\n"
    return f"{heading_tex}{statement}\n"


def _problem_label_heading(index: int, problem: Problem) -> str:
    label = (problem.problem_label or "").strip() or str(index)
    return label if label.endswith(".") else f"{label}."


def _copy_attachments(content, build_dir: Path, *, problem_index: int) -> dict[str, str]:
    attachment_dir = build_dir / "attachments" / f"p{problem_index}"
    attachment_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for attachment in content.attachments.all():
        if not attachment.file:
            continue
        target = attachment_dir / attachment.name
        target.parent.mkdir(parents=True, exist_ok=True)
        with attachment.file.open("rb") as src, target.open("wb") as dst:
            shutil.copyfileobj(src, dst)
        paths[attachment.name] = f"attachments/p{problem_index}/{attachment.name}"
    return paths


def _latex_problem_placeholder(text: str) -> str:
    return render_latex(text).body


def _latex_document(title: str, body: str, packages: set[str]) -> str:
    rendered_title = render_latex(title).body
    extra = []
    if "xcolor" in packages:
        extra.append("\\usepackage{xcolor}")
    if "graphicx" in packages:
        extra.append("\\usepackage{graphicx}")
    if "ulem" in packages:
        extra.append("\\usepackage[normalem]{ulem}")
    if "hyperref" in packages:
        extra.append("\\usepackage{hyperref}")
    preamble = "\n".join(extra)
    return rf"""\documentclass[a4paper,12pt]{{article}}
\usepackage{{fontspec}}
\usepackage[a4paper,margin=2.5cm]{{geometry}}
\usepackage{{amsmath,amssymb}}
{preamble}
\newcommand{{\problemblock}}{{\par\bigskip}}
\newcommand{{\problemheading}}[1]{{\problemblock\noindent{{\large\normalfont #1}}\par\smallskip}}

\title{{{rendered_title}}}
\date{{}}

\begin{{document}}
\maketitle

{body}

\end{{document}}
"""
