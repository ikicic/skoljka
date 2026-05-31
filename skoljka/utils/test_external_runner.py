import base64
import importlib.util
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, Mock, patch

from django.test import override_settings

from skoljka.utils.external_runner import external_temporary_directory, run_external


class ExternalRunnerTest(TestCase):
    def test_missing_external_process_mode_is_configuration_error(self):
        with patch("skoljka.utils.external_runner.settings", SimpleNamespace()):
            with self.assertRaisesRegex(RuntimeError, "EXTERNAL_PROCESS_MODE must be set"):
                run_external(["node", "script.mjs"])

    @override_settings(EXTERNAL_PROCESS_MODE="direct")
    @patch("skoljka.utils.external_runner.subprocess.run")
    def test_direct_mode_delegates_to_subprocess(self, run: Mock):
        run.return_value = subprocess.CompletedProcess(["node"], 0, stdout="ok", stderr="")

        result = run_external(["node", "script.mjs"], text=True, capture_output=True, timeout=3)

        self.assertEqual(result.stdout, "ok")
        run.assert_called_once_with(
            ["node", "script.mjs"],
            input=None,
            cwd=None,
            text=True,
            capture_output=True,
            check=False,
            timeout=3,
        )

    @override_settings(EXTERNAL_PROCESS_MODE="docker")
    def test_invalid_external_process_mode_is_configuration_error(self):
        with self.assertRaisesRegex(RuntimeError, "EXTERNAL_PROCESS_MODE must be set"):
            run_external(["node", "script.mjs"])

    @override_settings(
        EXTERNAL_PROCESS_MODE="worker",
        EXTERNAL_WORKER_URL="http://worker.test/run",
        EXTERNAL_WORKER_TOKEN="secret",
        EXTERNAL_WORKER_HOST_ROOT=Path("/host/app"),
        EXTERNAL_WORKER_CONTAINER_ROOT=Path("/app"),
        EXTERNAL_WORKER_TMP_DIR=Path("/host/app/worker-files"),
    )
    @patch("skoljka.utils.external_runner.urllib.request.urlopen")
    def test_worker_mode_posts_mapped_command(self, urlopen: Mock):
        urlopen.return_value = _json_response({"returncode": 0, "stdout": "ok", "stderr": ""})

        result = run_external(
            ["xelatex", "/host/app/worker-files/export/problem.tex"],
            cwd="/host/app",
            text=True,
            capture_output=True,
            timeout=5,
        )

        self.assertEqual(result.stdout, "ok")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://worker.test/run")
        self.assertEqual(request.headers["Authorization"], "Bearer secret")
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["args"], ["xelatex", "/app/worker-files/export/problem.tex"])
        self.assertEqual(payload["cwd"], "/app")
        self.assertEqual(payload["timeout"], 5)

    @override_settings(
        EXTERNAL_PROCESS_MODE="worker",
        EXTERNAL_WORKER_URL="http://worker.test/run",
        EXTERNAL_WORKER_TOKEN="",
        EXTERNAL_WORKER_HOST_ROOT=Path("/host/app"),
        EXTERNAL_WORKER_CONTAINER_ROOT=Path("/app"),
        EXTERNAL_WORKER_TMP_DIR=Path("/host/app/worker-files"),
    )
    @patch("skoljka.utils.external_runner.urllib.request.urlopen")
    def test_worker_mode_supports_binary_output_and_check(self, urlopen: Mock):
        urlopen.return_value = _json_response({
            "returncode": 2,
            "stdout_b64": base64.b64encode(b"out").decode("ascii"),
            "stderr_b64": base64.b64encode(b"err").decode("ascii"),
        })

        with self.assertRaises(subprocess.CalledProcessError) as raised:
            run_external(["pdflatex", "x.tex"], check=True)

        self.assertEqual(raised.exception.returncode, 2)
        self.assertEqual(raised.exception.output, b"out")
        self.assertEqual(raised.exception.stderr, b"err")

    @override_settings(
        EXTERNAL_PROCESS_MODE="worker",
        EXTERNAL_WORKER_URL="http://worker.test/run",
        EXTERNAL_WORKER_HOST_ROOT=Path("/host/app"),
        EXTERNAL_WORKER_CONTAINER_ROOT=Path("/app"),
        EXTERNAL_WORKER_TMP_DIR=Path("/host/app/worker-files"),
    )
    def test_worker_mode_requires_explicit_token_setting(self):
        fake_settings = SimpleNamespace(
            EXTERNAL_PROCESS_MODE="worker",
            EXTERNAL_WORKER_URL="http://worker.test/run",
            EXTERNAL_WORKER_HOST_ROOT=Path("/host/app"),
            EXTERNAL_WORKER_CONTAINER_ROOT=Path("/app"),
            EXTERNAL_WORKER_TMP_DIR=Path("/host/app/worker-files"),
        )
        with patch("skoljka.utils.external_runner.settings", fake_settings):
            with self.assertRaises(AttributeError):
                run_external(["pdflatex", "x.tex"], check=True)

    @override_settings(EXTERNAL_PROCESS_MODE="worker", EXTERNAL_WORKER_TMP_DIR=Path("/tmp/skoljka-worker-test"))
    def test_worker_temporary_directory_uses_configured_shared_dir(self):
        with external_temporary_directory() as tmp:
            self.assertEqual(tmp.parent, Path("/tmp/skoljka-worker-test"))
            self.assertTrue(tmp.exists())

        self.assertFalse(tmp.exists())


class WorkerServerTest(TestCase):
    def test_worker_server_allows_only_known_commands(self):
        worker_server = _load_worker_server()

        self.assertEqual(worker_server._validated_args(["xelatex", "problem.tex"]), ["xelatex", "problem.tex"])

        with self.assertRaises(ValueError):
            worker_server._validated_args(["bash", "-lc", "echo nope"])
        with self.assertRaises(ValueError):
            worker_server._validated_args(["node", "script.mjs"])


def _json_response(payload: dict[str, object]) -> MagicMock:
    response = MagicMock()
    response.read.return_value = json.dumps(payload).encode("utf-8")
    response.__enter__.return_value = response
    response.__exit__.return_value = None
    return response


def _load_worker_server():
    server_path = Path(__file__).resolve().parents[2] / "docker" / "worker" / "server.py"
    spec = importlib.util.spec_from_file_location("skoljka_docker_worker_server", server_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
