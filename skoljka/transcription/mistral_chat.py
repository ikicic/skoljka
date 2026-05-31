"""Mistral chat provider."""

import time
from typing import cast

from skoljka.transcription.api_keys import require_api_key
from skoljka.transcription.structured import parse_json_response, structured_json_prompt
from skoljka.transcription.types import ContentChunk

API_DELAY = 1


class MistralChat:
    def __init__(self) -> None:
        from mistralai.client import Mistral
        self.client = Mistral(api_key=require_api_key("MISTRAL_API_KEY"))

    def chat(
        self,
        system: str,
        content: str | list[ContentChunk],
        model: str,
    ) -> str:
        time.sleep(API_DELAY)
        response = self.client.chat.complete(
            model=model,
            messages=cast(list, [  # type: ignore[arg-type]
                {"role": "system", "content": system},
                {"role": "user", "content": content},
            ]),
        )
        result = response.choices[0].message.content
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
