"""Anthropic chat provider."""

import time
from typing import Any

from skoljka.transcription.api_keys import require_api_key
from skoljka.transcription.structured import parse_json_response, structured_json_prompt
from skoljka.transcription.types import ContentChunk

API_DELAY = 1


class AnthropicChat:
    def __init__(self) -> None:
        import anthropic
        self.client = anthropic.Anthropic(api_key=require_api_key("ANTHROPIC_API_KEY"))

    def chat(
        self,
        system: str,
        content: str | list[ContentChunk],
        model: str,
    ) -> str:
        time.sleep(API_DELAY)
        if isinstance(content, str):
            messages_content: Any = content
        else:
            blocks: list[dict[str, Any]] = []
            for chunk in content:
                if chunk["type"] == "text":
                    blocks.append({"type": "text", "text": chunk["text"]})
                elif chunk["type"] == "image_url":
                    data_url: str = chunk["image_url"]  # type: ignore[typeddict-item]
                    media_type, _, b64_data = data_url.partition(";base64,")
                    media_type = media_type.removeprefix("data:")
                    blocks.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64_data,
                        },
                    })
            messages_content = blocks
        response = self.client.messages.create(
            model=model,
            max_tokens=16384,
            system=system,
            messages=[{"role": "user", "content": messages_content}],
        )
        result = response.content[0].text
        assert isinstance(result, str)
        return result

    def structured_chat(
        self,
        system: str,
        content: str,
        model: str,
        schema: dict,
    ) -> dict:
        result = self.chat(structured_json_prompt(system, schema), content, model)
        return parse_json_response(result)
