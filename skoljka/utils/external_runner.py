import base64
import json
import subprocess
import urllib.error
import urllib.request
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Literal, overload

from django.conf import settings


Arg = str | Path


@overload
def run_external(
    args: Sequence[Arg],
    *,
    input: str | None = None,
    cwd: str | Path | None = None,
    text: Literal[True],
    capture_output: bool = False,
    check: bool = False,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]: ...


@overload
def run_external(
    args: Sequence[Arg],
    *,
    input: str | bytes | None = None,
    cwd: str | Path | None = None,
    text: Literal[False] = False,
    capture_output: bool = False,
    check: bool = False,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[bytes]: ...


def run_external(
    args: Sequence[Arg],
    *,
    input: str | bytes | None = None,
    cwd: str | Path | None = None,
    text: bool = False,
    capture_output: bool = False,
    check: bool = False,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]:
    if _external_process_mode() == "worker":
        return _run_worker(
            args,
            input=input,
            cwd=cwd,
            text=text,
            check=check,
            timeout=timeout,
        )
    return subprocess.run(
        list(args),
        input=input,
        cwd=cwd,
        text=text,
        capture_output=capture_output,
        check=check,
        timeout=timeout,
    )


@contextmanager
def external_temporary_directory() -> Generator[Path, None, None]:
    if _external_process_mode() == "worker":
        base_dir = Path(settings.EXTERNAL_WORKER_TMP_DIR)
        base_dir.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=base_dir) as tmp:
            yield Path(tmp)
    else:
        with TemporaryDirectory() as tmp:
            yield Path(tmp)


def _run_worker(
    args: Sequence[Arg],
    *,
    input: str | bytes | None,
    cwd: str | Path | None,
    text: bool,
    check: bool,
    timeout: float | None,
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]:
    if not args:
        raise ValueError("External command arguments cannot be empty.")

    mapped_args = [_map_path_argument(arg) for arg in args]
    payload: dict[str, Any] = {
        "args": mapped_args,
        "cwd": _map_path_argument(cwd) if cwd is not None else None,
        "text": text,
        "timeout": timeout,
    }
    if input is not None:
        if text:
            if not isinstance(input, str):
                raise TypeError("text=True requires string input.")
            payload["input"] = input
        else:
            raw_input = input if isinstance(input, bytes) else input.encode()
            payload["input_b64"] = base64.b64encode(raw_input).decode("ascii")

    headers = {"Content-Type": "application/json"}
    token = settings.EXTERNAL_WORKER_TOKEN
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        str(settings.EXTERNAL_WORKER_URL),
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=(timeout or 30) + 5) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"External worker request failed: {exc}") from exc

    if text:
        stdout = str(data.get("stdout", ""))
        stderr = str(data.get("stderr", ""))
        result_text = subprocess.CompletedProcess(list(args), int(data["returncode"]), stdout=stdout, stderr=stderr)
        if check and result_text.returncode:
            raise subprocess.CalledProcessError(result_text.returncode, list(args), output=stdout, stderr=stderr)
        return result_text

    stdout_bytes = base64.b64decode(data.get("stdout_b64", ""))
    stderr_bytes = base64.b64decode(data.get("stderr_b64", ""))
    result_bytes = subprocess.CompletedProcess(
        list(args),
        int(data["returncode"]),
        stdout=stdout_bytes,
        stderr=stderr_bytes,
    )
    if check and result_bytes.returncode:
        raise subprocess.CalledProcessError(
            result_bytes.returncode,
            list(args),
            output=stdout_bytes,
            stderr=stderr_bytes,
        )
    return result_bytes


def _map_path_argument(arg: Arg | None) -> str:
    if arg is None:
        return ""
    raw = str(arg)
    if not raw.startswith("/"):
        return raw

    host_root = Path(settings.EXTERNAL_WORKER_HOST_ROOT).resolve()
    container_root = Path(settings.EXTERNAL_WORKER_CONTAINER_ROOT)
    path = Path(raw).resolve()
    try:
        relative = path.relative_to(host_root)
    except ValueError:
        return raw
    return str(container_root / relative)


def _external_process_mode() -> Literal["direct", "worker"]:
    try:
        mode = settings.EXTERNAL_PROCESS_MODE
    except AttributeError as exc:
        raise RuntimeError("EXTERNAL_PROCESS_MODE must be set to 'direct' or 'worker'.") from exc
    if mode not in {"direct", "worker"}:
        raise RuntimeError("EXTERNAL_PROCESS_MODE must be set to 'direct' or 'worker'.")
    return mode
