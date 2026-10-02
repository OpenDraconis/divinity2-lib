from __future__ import annotations

ENCODING = "utf-8"
ERRORS = "surrogateescape"

STORY_ENCODING = "latin-1"


def decode(raw: bytes) -> str:
    return raw.decode(ENCODING, errors=ERRORS)


def encode(text: str) -> bytes:
    return text.encode(ENCODING, errors=ERRORS)


def decode_story(raw: bytes) -> str:
    return raw.decode(STORY_ENCODING)


def encode_story(text: str) -> bytes:
    return text.encode(STORY_ENCODING, errors="replace")
