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


def apply_replacement(text_iface, editable_iface, hit: WordHit, suggestion: str,
                      diagnostic=None) -> bool:
    """Verify each AT-SPI edit without trusting a toolkit-specific return type.

    The optional diagnostic reports *only stage names*, never document text.
    Insertion precedes deletion to preserve the misspelling if a remote editor
    declines an edit. It is not an atomic native editor undo operation.
    """
    def stage(value: str) -> None:
        if diagnostic is not None:
            diagnostic("edit: " + value)

    if not valid_suggestion(suggestion) or suggestion.casefold() == hit.word.casefold():
        stage("invalid candidate")
        return False
    if hit.start < 0 or hit.end - hit.start != len(hit.word):
        stage("invalid offsets")
        return False
    stage("before original read")
    try:
        if _read(text_iface, hit.start, hit.end) != hit.word:
            stage("stale text")
            return False
        stage("before insert")
        inserted = editable_iface.insert_text(
            hit.start, suggestion, len(suggestion.encode("utf-8"))
        )
        stage("insert result type=" + type(inserted).__name__)
        length = len(suggestion)
        stage("before inserted readback")
        # Some AT-SPI bindings return int/None rather than a Python bool.
        # Actual readback is the only reliable evidence of an applied edit.
        if _read(text_iface, hit.start, hit.start + length) != suggestion:
            stage("insert readback mismatch")
            return False
        old_start = hit.start + length
        old_end = old_start + len(hit.word)
        stage("before shifted-original readback")
        if _read(text_iface, old_start, old_end) != hit.word:
            stage("original shifted text mismatch")
            editable_iface.delete_text(hit.start, hit.start + length)
            return False
        stage("before delete")
        deleted = editable_iface.delete_text(old_start, old_end)
        stage("delete result type=" + type(deleted).__name__)
        # The source word must have gone; a no-op delete MUST NOT be reported
        # as successful. Roll back our insertion only when the original is
        # still at the shifted offset, otherwise avoid overwriting changes.
        if _read(text_iface, hit.start, hit.start + length) != suggestion:
            stage("final replacement mismatch")
            return False
        if _read(text_iface, hit.start + length, old_end) == hit.word:
            stage("delete readback mismatch")
            editable_iface.delete_text(hit.start, hit.start + length)
            return False
        stage("success")
        return True
    except (RuntimeError, ValueError, TypeError, OSError) as exc:
        stage("exception=" + type(exc).__name__)
        return False
