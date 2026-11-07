#!/usr/bin/env python3
"""Offline regression tests for ELF//SHELL's public RSS channel."""
from __future__ import annotations
import copy
import json
from html.parser import HTMLParser
from pathlib import Path
import tempfile
import unittest
from xml.etree import ElementTree as ET
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_public_feed import build, validated, ATOM, SOURCE


class PublicationParser(HTMLParser):
    """Collect the structural archive landmarks without a browser dependency."""
    def __init__(self):
        super().__init__()
        self.articles = []
        self.anchors = []
        self.skip = False

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "article":
            self.articles.append(attributes.get("id"))
        if tag == "a" and attributes.get("href", "").startswith("#"):
            self.anchors.append(attributes["href"][1:])
            self.skip |= attributes["href"] == "#dispatches"


class FeedTests(unittest.TestCase):
    def test_build_valid_rss_and_accessible_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            meta = build(out=out)
            source = json.loads(SOURCE.read_text(encoding="utf-8"))
            self.assertEqual(meta["count"], len(source["items"]))
            tree = ET.parse(out / "feed.xml")
            root = tree.getroot()
            self.assertEqual(root.tag, "rss")
            self.assertEqual(root.attrib["version"], "2.0")
            channel = root.find("channel")
            self.assertIsNotNone(channel)
            self.assertEqual(channel.find("language").text, "en-ZA")
            atom = channel.find(f"{{{ATOM}}}link")
            self.assertEqual(atom.get("rel"), "self")
            self.assertEqual(atom.get("href"), meta["url"])
            items = channel.findall("item")
            self.assertEqual(len(items), len(source["items"]))
            self.assertEqual(items[0].find("guid").attrib["isPermaLink"], "false")
            self.assertEqual(
                {item.find("guid").text for item in items},
                {"urn:elfshell:transmission:" + post["id"] for post in source["items"]},
            )
            self.assertTrue(any(item.find("link").text.endswith("#transmission-log-initialized") for item in items))
            html = (out / "index.html").read_text(encoding="utf-8")
            self.assertIn('rel="alternate"', html)
            self.assertIn('id="transmission-log-initialized"', html)
            doc = PublicationParser()
            doc.feed(html)
            ids = {post["id"] for post in source["items"]}
            self.assertEqual(set(doc.articles), ids)
            self.assertEqual(len(doc.articles), len(ids))
            self.assertTrue(ids <= set(doc.anchors), "Each dispatch needs a matching index/permalink")
            self.assertTrue(doc.skip, "The skip link must reach the main archive section")
            self.assertIn("class=\"archive-rail\"", html)
            self.assertIn("class=\"illustration\"", html)
            self.assertIn("ELF//SHELL", html)
            self.assertNotIn("is not affiliated with", html)
            css = (out / "style.css").read_text(encoding="utf-8")
            self.assertIn("@media (max-width: 490px)", css)
            self.assertIn("prefers-reduced-motion", css)
            self.assertNotIn("@import", css)
            self.assertNotIn("url(http", css)

            self.assertNotIn("<script", html)
            self.assertTrue((out / ".nojekyll").exists())
            self.assertTrue((out / "style.css").exists())
            # A second build of the same editorial input must not alter the feed.
            before = (out / "feed.xml").read_bytes()
            build(out=out)
            self.assertEqual(before, (out / "feed.xml").read_bytes())

    def test_duplicate_ids_rejected(self):
        doc = json.loads(SOURCE.read_text(encoding="utf-8"))
        doc["items"].append(copy.deepcopy(doc["items"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            validated(doc)

    def test_non_canonical_host_and_malformed_timestamps_rejected(self):
        doc = json.loads(SOURCE.read_text(encoding="utf-8"))
        doc["base_url"] = "http://localhost/"
        with self.assertRaisesRegex(ValueError, "canonical"):
            validated(doc)
        doc = json.loads(SOURCE.read_text(encoding="utf-8"))
        doc["items"][0]["published"] = "2026-11-07T13:00:00"
        with self.assertRaisesRegex(ValueError, "timezone"):
            validated(doc)

    def test_markup_is_escaped_in_generated_feed_and_page(self):
        doc = json.loads(SOURCE.read_text(encoding="utf-8"))
        doc["items"][0]["title"] = '<img src=x onerror="alert(1)">'
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "posts.json"
            src.write_text(json.dumps(doc), encoding="utf-8")
            build(src, Path(tmp) / "output")
            page = (Path(tmp) / "output" / "index.html").read_text()
            self.assertNotIn("<img src=x", page)
            self.assertIn("&lt;img", page)
            channel = ET.parse(Path(tmp) / "output" / "feed.xml").getroot().find("channel")
            item = next(item for item in channel.findall("item") if
                        item.find("guid").text == "urn:elfshell:transmission:" + doc["items"][0]["id"])
            self.assertEqual(item.find("title").text, doc["items"][0]["title"])


if __name__ == "__main__":
    unittest.main()
