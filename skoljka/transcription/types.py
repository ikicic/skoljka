"""Shared types for the transcription pipeline."""

from typing import NotRequired, TypedDict


class Problem(TypedDict):
    problem_label: str
    source_md: str
    set: str
    source_key: NotRequired[str]


class TextChunk(TypedDict):
    type: str  # "text"
    text: str


class ImageChunk(TypedDict):
    type: str  # "image_url"
    image_url: str


ContentChunk = TextChunk | ImageChunk


class PreparedPrompt(TypedDict):
    system: str
    content: list[ContentChunk]
