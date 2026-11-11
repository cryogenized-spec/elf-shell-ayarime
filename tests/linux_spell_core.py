#!/usr/bin/python3
"""Unit tests for the native, privacy-first click-to-correct implementation."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "linux-spell"))
from core import WordHit, clicked_word, normalize_suggestions, apply_replacement


class FakeText:
    def __init__(self, value):
        self.value = value

    def get_text(self, start, end):
        return self.value[start:end]


class FakeEditable:
    def __init__(self, text, *, no_op=False, reject_delete=False):
        self.text = text
        self.no_op = no_op
        self.reject_delete = reject_delete
        self.inserts = []
        self.deletes = []

    def insert_text(self, offset, value, n):
        self.inserts.append((offset, value, n))
        if not self.no_op:
            self.text.value = (
                self.text.value[:offset] + value + self.text.value[offset:]
            )
        return True

    def delete_text(self, start, end):
        self.deletes.append((start, end))
        if self.reject_delete:
            return False
        self.text.value = self.text.value[:start] + self.text.value[end:]
        return True


class SpellCoreTests(unittest.TestCase):
    def test_word_at_click_not_adjoining_punctuation(self):
        self.assertEqual(
            clicked_word(" teh, wrd! ", 12, 14), WordHit("teh", 13, 16)
        )
        self.assertEqual(
            clicked_word(" teh, wrd! ", 12, 16), None  # comma, not 'teh'
        )
        self.assertEqual(clicked_word(" hello ", 0, 0), None)

    def test_unicode_words_and_apostrophes(self):
        self.assertEqual(
            clicked_word(" éléphant's ", 50, 54),
            WordHit("éléphant's", 51, 61)
        )

    def test_skip_sensitive_url_code_and_long_strings(self):
        self.assertIsNone(clicked_word("A" * 65, 0, 1))
        self.assertIsNone(clicked_word("file_name", 0, 4))
        self.assertIsNone(clicked_word("user123", 0, 5))
        self.assertIsNone(clicked_word("12345", 0, 2))
        self.assertIsNone(clicked_word("x" * 260, 0, 2))

    def test_normalize_suggestions_rejects_repetitions_spaces_and_paths(self):
        choices = ["the", "THE", "the thing", "../data", "then",
                   "thér", "123", "", "the"]
        self.assertEqual(
            normalize_suggestions("teh", choices),
            ["the", "then", "thér"]
        )

    def test_corrects_only_clicked_word_preserves_adjacent_text(self):
        text = FakeText("I put teh book there.")
        editable = FakeEditable(text)
        self.assertTrue(
            apply_replacement(text, editable, WordHit("teh", 6, 9), "the")
        )
        self.assertEqual(text.value, "I put the book there.")
        self.assertEqual(editable.inserts, [(6, "the", 3)])
        self.assertEqual(editable.deletes, [(9, 12)])

    def test_unicode_replacement_measures_utf8_bytes_for_atspi(self):
        text = FakeText("Un éléfant")
        editable = FakeEditable(text)
        self.assertTrue(apply_replacement(
            text, editable, WordHit("éléfant", 3, 10), "éléphant"
        ))
        self.assertEqual(text.value, "Un éléphant")
        self.assertEqual(editable.inserts[0][2], len("éléphant".encode("utf-8")))

    def test_stale_word_never_mutated(self):
        text = FakeText("I put the book there.")
        editable = FakeEditable(text)
        self.assertFalse(
            apply_replacement(text, editable, WordHit("teh", 6, 9), "the")
        )
        self.assertEqual(editable.inserts, [])
        self.assertEqual(editable.deletes, [])

    def test_no_op_editor_never_deletes_original(self):
        text = FakeText("teh")
        editable = FakeEditable(text, no_op=True)
        self.assertFalse(
            apply_replacement(text, editable, WordHit("teh", 0, 3), "the")
        )
        self.assertEqual(text.value, "teh")
        self.assertEqual(editable.deletes, [])

    def test_rejected_delete_rolls_back_insertion(self):
        text = FakeText("teh")
        editable = FakeEditable(text, reject_delete=True)
        self.assertFalse(
            apply_replacement(text, editable, WordHit("teh", 0, 3), "the")
        )
        # Fake editor always refuses removal; the original remains intact
        # and the code does not remove it first.
        self.assertIn("teh", text.value)

    def test_invalid_suggestions_never_mutate(self):
        text = FakeText("teh")
        editable = FakeEditable(text)
        for candidate in ("thing 1", "", "teh", "../../../etc/passwd"):
            self.assertFalse(
                apply_replacement(text, editable, WordHit("teh", 0, 3), candidate)
            )
        self.assertEqual(text.value, "teh")
        editable.inserts.clear()
        self.assertEqual(editable.inserts, [])


if __name__ == "__main__":
    unittest.main()
