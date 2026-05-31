import base64
import json
import os
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


ALLOWED_COMMANDS = {"xelatex", "pdflatex", "pdftocairo", "pandoc"}
MAX_REQUEST_BYTES = 10 * 1024 * 1024


class WorkerHandler(BaseHTTPRequestHandler):
    server_version = "SkoljkaWorker/1.0"

    def do_POST(self) -> None:
        if self.path != "/run":
            self._send_json(404, {"error": "not found"})
            return
        token = os.environ.get("EXTERNAL_WORKER_TOKEN", "")
        if token and self.headers.get("Authorization") != f"Bearer {token}":
            self._send_json(401, {"error": "unauthorized"})
            return

        text = False
        try:
            request = self._read_request()
            args = _validated_args(request.get("args"))
            text = bool(request.get("text", False))
            timeout = request.get("timeout")
            cwd = request.get("cwd")
            run_input = request.get("input") if text else _decode_input(request)
            result = subprocess.run(
                args,
                cwd=cwd,
                input=run_input,
                text=text,
                capture_output=True,
                check=False,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            result = subprocess.CompletedProcess(
                exc.cmd,
                124,
                stdout=exc.stdout or ("" if text else b""),
                stderr=exc.stderr or (f"Command timed out after {exc.timeout} seconds" if text else b""),
            )
        except Exception as exc:
            self._send_json(400, {"error": str(exc)})
            return

        payload: dict[str, Any] = {"returncode": result.returncode}
        if text:
            payload["stdout"] = result.stdout or ""
            payload["stderr"] = result.stderr or ""
        else:
            stdout = result.stdout if isinstance(result.stdout, bytes) else b""
            stderr = result.stderr if isinstance(result.stderr, bytes) else b""
            payload["stdout_b64"] = base64.b64encode(stdout).decode("ascii")
            payload["stderr_b64"] = base64.b64encode(stderr).decode("ascii")
        self._send_json(200, payload)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _read_request(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_REQUEST_BYTES:
            raise ValueError("request body is too large")
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def _validated_args(raw_args: object) -> list[str]:
    if not isinstance(raw_args, list) or not raw_args or not all(isinstance(arg, str) for arg in raw_args):
        raise ValueError("args must be a non-empty list of strings")
    command = Path(raw_args[0]).name
    if command not in ALLOWED_COMMANDS:
        raise ValueError(f"command is not allowed: {command}")
    return raw_args


def _decode_input(request: dict[str, Any]) -> bytes | None:
    raw = request.get("input_b64")
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise ValueError("input_b64 must be a string")
    return base64.b64decode(raw)


def main() -> None:
    host = os.environ.get("EXTERNAL_WORKER_HOST", "0.0.0.0")
    port = int(os.environ.get("EXTERNAL_WORKER_PORT", "8765"))
    ThreadingHTTPServer((host, port), WorkerHandler).serve_forever()


if __name__ == "__main__":
    main()
