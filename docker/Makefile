COMPOSE ?= $(shell docker compose version >/dev/null 2>&1 && printf 'docker compose -f compose.worker.yml' || printf 'docker-compose -f compose.worker.yml')
IMAGE ?= skoljka-worker:latest
APP_UID ?= $(shell id -u)
APP_GID ?= $(shell id -g)

.PHONY: help build up down restart shell logs ps check-tools check-user

help:
	@printf '%s\n' \
		'Targets:' \
		'  make build                         Build the worker/tools image' \
		'  make up                            Build and start the worker service' \
		'  make shell                         Open a shell in the running worker' \
		'  make check-tools                   Print versions of external tools' \
		'  make down                          Stop the worker service'

check-user:
	@test "$(APP_UID)" != "0" || { echo "Do not build the worker as root. Run this as the app user, or pass APP_UID/APP_GID explicitly."; exit 1; }

build: check-user
	DOCKER_BUILDKIT=1 docker build --build-arg APP_UID=$(APP_UID) --build-arg APP_GID=$(APP_GID) -f worker.Dockerfile -t $(IMAGE) .

up: build
	mkdir -p ../worker-files
	SKOLJKA_WORKER_IMAGE=$(IMAGE) APP_UID=$(APP_UID) APP_GID=$(APP_GID) $(COMPOSE) up -d --no-build worker

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart worker

shell:
	$(COMPOSE) exec worker sh

logs:
	$(COMPOSE) logs -f worker

ps:
	$(COMPOSE) ps

check-tools:
	$(COMPOSE) exec worker sh -lc 'xelatex --version | head -n1 && pdflatex --version | head -n1 && pdftocairo -v 2>&1 | head -n1 && pandoc --version | head -n1'
