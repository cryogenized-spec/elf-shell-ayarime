"""Pure word-selection and replacement guards (safe to unit test headlessly)."""
import re
from dataclasses import dataclass

# Letters and accents only; internal apostrophes and hyphens are allowed.
WORD = re.compile(r"[^\W\d_]+(?:['’\-][^\W\d_]+)*", re.UNICODE)


@dataclass(frozen=True)
class WordRange:
    value: str
    start: int
    end: int


def word_at(text: str, offset: int) -> WordRange | None:
    """Return a word covering the clicked character, not nearby whitespace."""
    if offset < 0 or offset >= len(text):
        return None
    for match in WORD.finditer(text):
        if match.start() <= offset < match.end():
            word = match.group()
            if len(word) < 3 or len(word) > 42:
                return None
            # URLs, paths and emails must be edited manually.
            left = text[max(0, match.start()-12):match.start()]
            right = text[match.end():min(len(text), match.end()+12)]
            if (left.endswith(('@', '/', '.', ':')) or right.startswith(('@', '/', '.'))):
                return None
            return WordRange(word,match.start(),match.end())
    return None


def current_range_is_unchanged(now: str, before: str, selection: WordRange) -> bool:
    return (now == before and 0 <= selection.start < selection.end <= len(now)
            and now[selection.start:selection.end] == selection.value)
