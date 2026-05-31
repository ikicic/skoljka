"""Chat provider protocol and factory."""

from typing import Protocol

from skoljka.transcription.types import ContentChunk


class ChatProvider(Protocol):
    def chat(
        self,
        system: str,
        content: str | list[ContentChunk],
        model: str,
    ) -> str: ...

    def structured_chat(
        self,
        system: str,
        content: str,
        model: str,
        schema: dict,
    ) -> dict: ...


def parse_model_flag(model_str: str) -> tuple[str, str]:
    """Parse 'provider/model' into (provider, model). Default provider: mistral."""
    if "/" in model_str:
        provider, model = model_str.split("/", 1)
        return provider, model
    return "mistral", model_str


def make_chat_provider(provider: str) -> ChatProvider:
    if provider == "mistral":
        from skoljka.transcription.mistral_chat import MistralChat
        return MistralChat()
    elif provider == "anthropic":
        from skoljka.transcription.anthropic_chat import AnthropicChat
        return AnthropicChat()
    else:
        raise ValueError(f"Unknown provider: {provider}")
