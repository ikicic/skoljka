"""Helpers for prompt-based structured chat responses."""

import json
from typing import Any


def structured_json_prompt(system: str, schema: dict[str, Any]) -> str:
    return (
        system
        + "\n\nReturn only valid JSON matching this JSON schema. "
        + "Do not wrap the response in Markdown fences or add explanatory text.\n"
        + json.dumps(schema, separators=(",", ":"), sort_keys=True)
    )


def parse_json_response(response: str) -> dict[str, Any]:
    text = response.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("Structured chat response must be a JSON object")
    return parsed
