"""Divinity II: Developer's Cut's own files: its archives, the binary XML in them, named,
and the Osiris story and savegames. Read, and written where a mod needs it.

    python -m dv2lib unpack <out> [<game folder>]

Standard library only, so it runs anywhere Python 3.11 does, Blender's included.
The focused reader shared by the tools, Blender, and Unity workflows.
"""

__version__ = "0.2.0"


class Dv2Error(Exception):
    """A file this library cannot use. The message says which and why."""
