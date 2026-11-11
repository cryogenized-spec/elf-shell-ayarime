"""Small, testable spell-correction core for the Linux Mint AT-SPI helper.

No globals, keyboard hooks, clipboard access, network operations or imports
from GTK. A click reads only the word-sized accessibility text range, and a
correction never deletes original text before insertion is verified.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

# No digits, underscores, URLs, paths, emails, or arbitrary long words.
WORD = re.compile(r"[^\W\d_]+(?:[’'][^\W\d_]+)*", re.UNICODE)
MAX_WORD = 64


@dataclass(frozen=True)
class WordHit:
    word: str
    start: int
    end: int


def clicked_word(range_text: str, range_start: int, offset: int) -> WordHit | None:
    """Find a word *containing* the clicked character, not the word beside it."""
    if not isinstance(range_text, str) or len(range_text) > 256:
        return None
    if not isinstance(range_start, int) or not isinstance(offset, int):
        return None
    if range_start < 0 or not range_start <= offset < range_start + len(range_text):
        return None
    for match in WORD.finditer(range_text):
        if match.start() <= offset - range_start < match.end():
            word = match.group()
            if 2 <= len(word) <= MAX_WORD and word.isprintable():
                return WordHit(word, range_start + match.start(), range_start + match.end())
    return None


def valid_suggestion(value: str) -> bool:
    return (
        isinstance(value, str)
        and 1 <= len(value) <= MAX_WORD
        and bool(WORD.fullmatch(value))
        and value.isprintable()
    )


def normalize_suggestions(word: str, suggestions: list[str], limit: int = 7) -> list[str]:
    """Keep only safe, distinct, word-like local dictionary suggestions."""
    if not 2 <= len(word) <= MAX_WORD:
        return []
    result: list[str] = []
    seen = {word.casefold()}
    for value in suggestions[:35]:
        if not valid_suggestion(value):
            continue
        lowered = value.casefold()
        if lowered in seen:
            continue
        seen.add(lowered)
        result.append(value)
        if len(result) >= limit:
            break
    return result


def _read(text_iface, start: int, end: int) -> str:
    """Read only the bounded word-sized range, never a complete editor buffer."""
    return text_iface.get_text(start, end)


def apply_replacement(text_iface, editable_iface, hit: WordHit, suggestion: str) -> bool:
    """Conservative two-step AT-SPI edit with pre/post checks and rollback.

    Insert the correction *before* trying to delete the original. This prevents
    accidental loss of the original if an application rejects accessibility
    writes (some Firefox builds can claim success but ignore the mutation).
    Applications may expose these as separate undo steps; this is not an atomic
    native editor operation. Do not claim undo equivalence to Firefox.
    """
    if not valid_suggestion(suggestion) or suggestion.casefold() == hit.word.casefold():
        return False
    if hit.start < 0 or hit.end - hit.start != len(hit.word):
        return False
    try:
        if _read(text_iface, hit.start, hit.end) != hit.word:
            return False  # Text changed while the suggestion menu was visible.
        if editable_iface.insert_text(
            hit.start, suggestion, len(suggestion.encode("utf-8"))
        ) is not True:
            return False
        length = len(suggestion)
        # Fail closed when accessibility method reports success but is a no-op.
        if _read(text_iface, hit.start, hit.start + length) != suggestion:
            return False
        old_start = hit.start + length
        old_end = old_start + len(hit.word)
        if _read(text_iface, old_start, old_end) != hit.word:
            # Unexpected live document mutation: leave original untouched and
            # attempt to undo just our verified insertion.
            editable_iface.delete_text(hit.start, hit.start + length)
            return False
        if editable_iface.delete_text(old_start, old_end) is not True:
            editable_iface.delete_text(hit.start, hit.start + length)
            return False
        return _read(text_iface, hit.start, hit.start + length) == suggestion
    except (RuntimeError, ValueError, TypeError, OSError):
        return False
