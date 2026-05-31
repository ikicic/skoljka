import json
import re
import struct
from pathlib import Path
from subprocess import CompletedProcess

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from skoljka.apps.accounts.challenges import configured_challenges
from skoljka.utils.external_runner import external_temporary_directory, run_external


MANIFEST_FILENAME = "manifest.json"
RENDER_DPI = 360
TEX_PT_PER_INCH = 72.27
MAX_DEPTH_PX = 10000
DEPTH_RE = re.compile(r"SKOLJKA_DEPTH_PT=(-?\d+(?:\.\d+)?)")


class Command(BaseCommand):
    help = "Render registration math challenges as PNG files."

    def add_arguments(self, parser):
        parser.add_argument("--output-dir", default=None, help="Directory for rendered PNG files.")

    def handle(self, *args, **options):
        output_dir = Path(options["output_dir"] or settings.REGISTRATION_MATH_CHALLENGE_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)

        manifest = {}
        count = 0
        for challenge in configured_challenges().values():
            manifest[challenge.id] = self._render_challenge(challenge.id, challenge.tex, output_dir)
            count += 1

        manifest["label-email"] = self._render_challenge("label-email", r"\text{Email}", output_dir)
        (output_dir / MANIFEST_FILENAME).write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        self.stdout.write(self.style.SUCCESS(f"Rendered {count} registration challenge(s) and labels to {output_dir}."))

    def _render_challenge(self, challenge_id: str, tex: str, output_dir: Path) -> dict[str, int]:
        with external_temporary_directory() as tmp_path:
            tex_path = tmp_path / "challenge.tex"
            pdf_path = tmp_path / "challenge.pdf"
            png_path = tmp_path / "challenge.png"
            tex_path.write_text(_latex_document(tex), encoding="utf-8")

            result = run_external(
                [
                    "pdflatex",
                    "-interaction=nonstopmode",
                    "-halt-on-error",
                    "-output-directory",
                    str(tmp_path),
                    str(tex_path),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            if result.returncode != 0:
                raise CommandError(_format_error("pdflatex", challenge_id, result))
            if not pdf_path.exists():
                raise CommandError(f"pdflatex did not produce a PDF for {challenge_id}.")
            depth = _parse_depth_px(challenge_id, result)

            result = run_external(
                ["pdftocairo", "-png", "-singlefile", "-transp", "-r", str(RENDER_DPI), str(pdf_path), str(tmp_path / "challenge")],
                text=True,
                capture_output=True,
                check=False,
            )
            if result.returncode != 0:
                raise CommandError(_format_error("pdftocairo", challenge_id, result))
            if not png_path.exists():
                raise CommandError(f"pdftocairo did not produce a PNG for {challenge_id}.")

            width, height = _png_size(png_path)
            png_path.replace(output_dir / f"{challenge_id}.png")
            return {"width": width, "height": height, "depth": depth}


def _latex_document(tex: str) -> str:
    return "\n".join([
        r"\documentclass[border=0pt]{standalone}",
        r"\usepackage{amsmath}",
        r"\newsavebox{\skoljkaregbox}",
        r"\makeatletter",
        r"\begin{document}",
        rf"\sbox{{\skoljkaregbox}}{{$\displaystyle {tex} = $}}%",
        r"\typeout{SKOLJKA_DEPTH_PT=\strip@pt\dp\skoljkaregbox}",
        r"\usebox{\skoljkaregbox}",
        r"\end{document}",
        "",
    ])


def _format_error(command: str, challenge_id: str, result: CompletedProcess[str]) -> str:
    output = (result.stderr or result.stdout or "").strip()
    return f"{command} failed for {challenge_id}:\n{output}"


def _parse_depth_px(challenge_id: str, result: CompletedProcess[str]) -> int:
    output = result.stdout or ""
    match = DEPTH_RE.search(output)
    if not match:
        raise CommandError(f"pdflatex did not report a depth for {challenge_id}.")
    depth = round(float(match.group(1)) * RENDER_DPI / TEX_PT_PER_INCH)
    if depth < 0 or depth > MAX_DEPTH_PX:
        raise CommandError(f"pdflatex reported an invalid depth for {challenge_id}: {depth}.")
    return depth


def _png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as f:
        header = f.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise CommandError(f"Rendered file is not a valid PNG: {path}")
    return struct.unpack(">II", header[16:24])
