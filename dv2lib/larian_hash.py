from __future__ import annotations

import functools

MASK = 0xFFFFFFFF


@functools.lru_cache(maxsize=65536)
def name_hash(text: str | bytes) -> int:
    data = text.encode("latin-1") if isinstance(text, str) else text
    h = 0
    for c in data:
        h = (h * 33 + c) & MASK
    return h
