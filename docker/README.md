# Školjka Worker/Tools Container

This container keeps the large and riskier toolchain out of the host OS:

- XeLaTeX for user-facing problem PDF export
- pdfLaTeX and Poppler `pdftocairo` for registration challenge images
- Pandoc for the optional offline transcription preview tool

It runs a small local HTTP worker for allowlisted external commands. The image
contains only the worker server and the external binaries.

## Prerequisites

- Docker with Compose v2
- BuildKit enabled

The Makefile auto-detects either the Compose v2 plugin (`docker compose`) or
the older standalone binary (`docker-compose`). You can override it if needed:

```sh
make up COMPOSE="docker-compose -f compose.worker.yml"
```

## Build

From this directory:

```sh
make build
```

```sh
DOCKER_BUILDKIT=1 docker build -f worker.Dockerfile -t skoljka-worker:latest .
```

## Launch

```sh
EXTERNAL_WORKER_TOKEN="<same long random shared secret>" make up
make ps
make check-tools
```

`make up` builds the image first, then starts the worker on
`127.0.0.1:8765`. It also creates `../worker-files`, which is the shared
temporary directory used for TeX/PDF inputs and outputs.

To make Django use it, set these in `skoljka/config/local.py`:

```py
EXTERNAL_PROCESS_MODE = "worker"
EXTERNAL_WORKER_URL = "http://127.0.0.1:8765/run"
EXTERNAL_WORKER_TOKEN = "<long random shared secret>"
```

For production, set a non-empty `EXTERNAL_WORKER_TOKEN` both in the app config
and in the environment used by `docker compose`.

The token is a shared secret. Django sends it as an HTTP Bearer token, and the
worker compares it with its `EXTERNAL_WORKER_TOKEN` environment variable. Start
the worker with the same value:

```sh
EXTERNAL_WORKER_TOKEN="<same long random shared secret>" make up
```

Mounted host paths:

- `../worker-files` -> `/app/worker-files`
