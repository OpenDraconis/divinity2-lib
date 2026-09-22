"""The one way bytes from the game become text and go back.

Larian's files are UTF-8 where they are anything, but a handful of strings
are not valid UTF-8 at all. `surrogateescape` carries those bytes through a
str untouched, so a document read, edited and written back keeps every byte
the tool did not mean to change. Nothing here translates newlines.
"""
from __future__ import annotations

ENCODING = "utf-8"
ERRORS = "surrogateescape"

#: The story is the exception: the Osiris compiler reads and writes one byte per
#: character. latin-1 and cp1252 differ over 0x80-0x9F, which is where Larian's smart
#: quotes would sit, so the choice is worth having in one place to change.
STORY_ENCODING = "latin-1"


def decode(raw: bytes) -> str:
    return raw.decode(ENCODING, errors=ERRORS)


def encode(text: str) -> bytes:
    return text.encode(ENCODING, errors=ERRORS)


def decode_story(raw: bytes) -> str:
    return raw.decode(STORY_ENCODING)


def encode_story(text: str) -> bytes:
    return text.encode(STORY_ENCODING, errors="replace")
