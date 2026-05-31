# syntax=docker/dockerfile:1.7

FROM python:3.13-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

ARG APP_UID=1000
ARG APP_GID=1000

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        lmodern \
        pandoc \
        poppler-utils \
        texlive-fonts-recommended \
        texlive-latex-base \
        texlive-latex-extra \
        texlive-latex-recommended \
        texlive-xetex \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /worker

COPY --chmod=0444 worker/server.py ./server.py

RUN groupadd --gid "${APP_GID}" worker \
    && useradd --uid "${APP_UID}" --gid "${APP_GID}" --create-home --shell /usr/sbin/nologin worker

USER worker

CMD ["python", "/worker/server.py"]
