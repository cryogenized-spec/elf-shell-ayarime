import sys
import unittest
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(BASE/'spellcheck'),str(BASE/'cursors')]
from words import word_at, current_range_is_unchanged, WordRange
from build import draw_icon, PALETTES, ALIASES, SIZES

class TestWords(unittest.TestCase):
    def test_exact_click(self):
        self.assertEqual(word_at('A mistkae here',3),WordRange('mistkae',2,9))
        self.assertIsNone(word_at('A mistkae here',9))
        self.assertIsNone(word_at('A mistkae here',-1))
    def test_no_path_email(self):
        self.assertIsNone(word_at('foo@example.com',4))
        self.assertIsNone(word_at('foo/bar',4))
    def test_stale_field(self):
        x='mistkae'
        self.assertTrue(current_range_is_unchanged(x,x,WordRange(x,0,7)))
        self.assertFalse(current_range_is_unchanged('changed',x,WordRange(x,0,7)))
    def test_unicode(self):
        self.assertEqual(word_at('café',2).value,'café')

class TestCursorDraw(unittest.TestCase):
    def test_every_role_every_size(self):
        for color in PALETTES.values():
            for kind in ALIASES:
                for size in SIZES:
                    image,x,y=draw_icon(kind,size,color['bright'],color['shade'])
                    self.assertEqual(image.size,(size,size))
                    self.assertTrue(0<=x<size and 0<=y<size)
                    self.assertIsNotNone(image.getbbox())

if __name__=='__main__':
    unittest.main()
