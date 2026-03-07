"""Minimal locale-aware string helper.

Returns the Japanese string when the user's locale is set to Japanese
(LC_ALL, LC_MESSAGES, or LANG starts with "ja"), otherwise returns English.
"""

import os


def is_japanese() -> bool:
    """Return True if the effective locale is Japanese.

    Follows Unix locale priority: LC_ALL overrides LC_MESSAGES and LANG.
    If LC_ALL is set to a non-Japanese value, Japanese locale variables are ignored.
    """
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        val = os.environ.get(var, "")
        if val:
            return val.startswith("ja")
    return False


def h(en: str, ja: str) -> str:
    """Return the Japanese string if locale is Japanese, otherwise English."""
    return ja if is_japanese() else en
