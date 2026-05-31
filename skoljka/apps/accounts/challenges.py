import json
import random
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.core.signals import setting_changed
from django.dispatch import receiver
from django.http import HttpRequest


_SESSION_KEY = "registration_math_challenge_id"
_IMAGE_MANIFEST = "manifest.json"
_DEFAULT_IMAGE_METRICS = {"width": 160, "height": 48, "depth": 0}
_REGISTRATION_IMAGE_DISPLAY_SCALE = 0.4
_REGISTRATION_IMAGE_BASELINE_CORRECTION_PX = 1


@dataclass(frozen=True)
class MathChallenge:
    id: str
    tex: str
    answer: str


@lru_cache(maxsize=1)
def configured_challenges() -> dict[str, MathChallenge]:
    challenges = {}
    for raw in getattr(settings, "REGISTRATION_MATH_CHALLENGES", []):
        if not isinstance(raw, dict):
            raise ValueError("Each registration challenge must be a dictionary.")
        missing = {"id", "tex", "answer"} - set(raw)
        if missing:
            raise ValueError(f"Registration challenge is missing: {', '.join(sorted(missing))}.")
        challenge_id = str(raw["id"])
        if not re.fullmatch(r"[-A-Za-z0-9_]+", challenge_id):
            raise ValueError(f"Invalid registration challenge id: {challenge_id!r}")
        if challenge_id in challenges:
            raise ValueError(f"Duplicate registration challenge id: {challenge_id!r}")
        tex = str(raw["tex"]).strip()
        if not tex:
            raise ValueError(f"Registration challenge {challenge_id!r} must define non-empty tex.")
        answer = str(raw["answer"])
        if not _normalize_answer(answer):
            raise ValueError(f"Registration challenge {challenge_id!r} must define a non-empty answer.")
        challenges[challenge_id] = MathChallenge(id=challenge_id, tex=tex, answer=answer)
    if not challenges:
        raise ValueError("REGISTRATION_MATH_CHALLENGES must define at least one challenge.")
    return challenges


@receiver(setting_changed)
def _clear_challenge_cache(setting, **kwargs):
    if setting in {"REGISTRATION_MATH_CHALLENGES", "REGISTRATION_MATH_CHALLENGE_DIR"}:
        configured_challenges.cache_clear()
        _image_manifest.cache_clear()


def current_challenge(request: HttpRequest) -> MathChallenge:
    challenge_id = request.session.get(_SESSION_KEY)
    challenge = configured_challenges().get(challenge_id) if challenge_id else None
    if challenge is None:
        challenge = rotate_challenge(request)
    return challenge


def rotate_challenge(request: HttpRequest) -> MathChallenge:
    challenge = random.choice(list(configured_challenges().values()))
    request.session[_SESSION_KEY] = challenge.id
    request.session.modified = True
    return challenge


def clear_challenge(request: HttpRequest) -> None:
    request.session.pop(_SESSION_KEY, None)
    request.session.modified = True


def challenge_image_path(challenge_id: str) -> Path:
    return Path(settings.REGISTRATION_MATH_CHALLENGE_DIR) / f"{challenge_id}.png"


def registration_label_image_path(label_id: str) -> Path:
    return Path(settings.REGISTRATION_MATH_CHALLENGE_DIR) / f"label-{label_id}.png"


def registration_image_metrics(image_id: str) -> dict[str, str | int]:
    try:
        raw = _image_manifest().get(image_id)
        width = int(raw["width"])
        height = int(raw["height"])
        depth = int(raw.get("depth", 0))
    except (KeyError, TypeError, ValueError):
        width = _DEFAULT_IMAGE_METRICS["width"]
        height = _DEFAULT_IMAGE_METRICS["height"]
        depth = _DEFAULT_IMAGE_METRICS["depth"]
    if width <= 0 or height <= 0 or depth < 0:
        width = _DEFAULT_IMAGE_METRICS["width"]
        height = _DEFAULT_IMAGE_METRICS["height"]
        depth = _DEFAULT_IMAGE_METRICS["depth"]

    display_width = max(1, round(width * _REGISTRATION_IMAGE_DISPLAY_SCALE))
    display_height = max(1, round(height * _REGISTRATION_IMAGE_DISPLAY_SCALE))
    display_depth = max(0, round(depth * _REGISTRATION_IMAGE_DISPLAY_SCALE) + _REGISTRATION_IMAGE_BASELINE_CORRECTION_PX)
    return {
        "width": display_width,
        "height": display_height,
        "style": f"vertical-align: -{display_depth}px;",
    }


@lru_cache(maxsize=1)
def _image_manifest() -> dict:
    path = Path(settings.REGISTRATION_MATH_CHALLENGE_DIR) / _IMAGE_MANIFEST
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def session_challenge_matches(request: HttpRequest, challenge_id: str) -> bool:
    return request.session.get(_SESSION_KEY) == challenge_id and challenge_id in configured_challenges()


def _normalize_answer(value: str) -> str:
    return re.sub(r"\s+", "", value).strip()


def answer_is_correct(challenge: MathChallenge, value: str) -> bool:
    return _normalize_answer(value) == _normalize_answer(challenge.answer)
