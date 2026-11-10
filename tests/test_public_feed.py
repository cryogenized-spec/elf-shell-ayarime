#!/usr/bin/env python3
"""Offline regression tests for ELF//SHELL's public RSS channel."""
from __future__ import annotations
import copy
import json
import re
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


    def test_illustrated_serviteur_release_page_and_rss_permalink(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            meta = build(out=out)
            source = json.loads(SOURCE.read_text(encoding="utf-8"))
            dispatch = next(post for post in source["items"] if post["id"] == "clickup-serviteur-public-beta")
            page = out / dispatch["page"]
            self.assertEqual(meta["count"], 3)
            self.assertTrue(page.is_file())
            content = page.read_text(encoding="utf-8")
            self.assertIn("THE SERVITEUR ENGINE", content)
            self.assertIn('alt="ClickUp"', content)
            self.assertIn('alt="Model Context Protocol (MCP)"', content)
            self.assertIn("No sponsorship or endorsement is implied", content)
            self.assertIn("Mango Technologies", content)
            for mark in ("clickup-logo-gradient-on-dark.svg", "mcp-logo-dark.svg"):
                self.assertIn("brands/" + mark, content)
                path = out / "dispatches" / "brands" / mark
                self.assertTrue(path.is_file(), mark)
                self.assertGreater(path.stat().st_size, 1000)
                mark_xml = ET.parse(path).getroot()
                self.assertTrue(mark_xml.tag.endswith("svg"), mark)
                self.assertFalse(any(node.tag.endswith("script") for node in mark_xml.iter()))
            emblem = out / "dispatches" / "assets" / "serviteur_logo_mcp_corrected.png"
            self.assertTrue(emblem.is_file(), "The approved Serviteur emblem must be deployed")
            emblem_bytes = emblem.read_bytes()
            self.assertEqual(len(emblem_bytes), 8496)
            self.assertLess(len(emblem_bytes), 10 * 1024)
            self.assertEqual(emblem_bytes[:8], bytes.fromhex("89504e470d0a1a0a"))
            self.assertEqual(emblem_bytes[16:24], bytes.fromhex("000000a0000000a0"))
            self.assertIn('class="release-stamp release-stamp-logo"', content)
            self.assertIn('src="assets/serviteur_logo_mcp_corrected.png"', content)
            self.assertIn('download="serviteur_logo_mcp_corrected.png"', content)
            self.assertNotIn("ᓚᘏᗢ", content, "The placeholder must be removed")

            self.assertNotIn("<script", content, "No analytics or remote scripts")

            self.assertIn("v0.3.0-beta.1", content)

            self.assertIn('rel="alternate"', content)
            self.assertNotIn("v0.4.0", content, "do not invent further ClickUp releases")
            self.assertIn("clickup-serviteur-slivers-01-04.webp", content)
            self.assertIn("clickup-serviteur-slivers-05-08.webp", content)
            self.assertTrue((out / "dispatches" / "serviteur.css").is_file())
            for image in ("clickup-serviteur-slivers-01-04.webp",
                          "clickup-serviteur-slivers-05-08.webp"):
                raw = (out / "media" / image).read_bytes()
                self.assertGreater(len(raw), 100_000)
                self.assertEqual(raw[:4], b"RIFF")
                self.assertEqual(raw[8:12], b"WEBP")
            channel = ET.parse(out / "feed.xml").getroot().find("channel")
            item = next(node for node in channel.findall("item") if
                        node.find("guid").text == "urn:elfshell:transmission:clickup-serviteur-public-beta")
            self.assertEqual(item.find("link").text, meta["url"].removesuffix("feed.xml") + dispatch["page"])
            index_html = (out / "index.html").read_text(encoding="utf-8")
            self.assertIn('href="dispatches/clickup-serviteur-v0.3.0-beta.1.html"', index_html)
            self.assertIn("READ THE ILLUSTRATED DOSSIER", index_html)

    def test_serviteur_source_tool_schema_appendix(self):
        """The illustrated release stays historic while the separate 80-tool guide is explicit."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            build(out=out)
            article = (out / "dispatches/clickup-serviteur-v0.3.0-beta.1.html").read_text(
                encoding="utf-8"
            )
            css = (out / "dispatches/serviteur.css").read_text(encoding="utf-8")
            rows = re.findall(r'<div class="registry-row" id="tool-([^\"]+)"', article)
            self.assertEqual(len(rows), 80, "66 REST-backed + 14 gateway/scoped tools")
            self.assertEqual(len(rows), len(set(rows)), "Each tool must appear once")
            self.assertEqual(article.count('class="registry-parameters"'), 80)
            self.assertEqual(article.count('class="registry-tool-name"'), 80)
            self.assertEqual(article.count('class="registry-tool-detail"'), 80)
            for tool in (
                "clickup_get_my_attention_items",
                "clickup_get_chat_channel_messages",
                "clickup_get_document_pages",
                "clickup_create_task_checklist",
                "clickup_get_task_templates",
                "clickup_set_workspace_access",
                "service_info",
            ):
                self.assertIn(tool, rows)
            for version in ("v2", "v3", "custom", "hybrid"):
                self.assertIn('registry-badge-' + version, article)
            self.assertIn('id="registry-title"', article)
            self.assertIn('href="#tools"', article)
            self.assertIn('rel="alternate"', article)
            self.assertIn('f1dd7aa3759d584f6acf6f0eb4b96dbfc61a2a48', article)
            self.assertIn("not</em> the frozen tool inventory", article)
            self.assertNotIn("<script", article)
            self.assertNotIn("@import", css)
            self.assertNotIn("url(http", css)
            self.assertIn(".registry-row{display:grid", css)
            self.assertIn("@media(max-width:620px)", css)
            feed = ET.parse(out / "feed.xml").getroot().find("channel")
            item = next(
                x for x in feed.findall("item")
                if x.find("guid").text == "urn:elfshell:transmission:clickup-serviteur-public-beta"
            )
            self.assertIn("80 current named MCP tools", item.find("description").text)
            self.assertEqual(item.find("pubDate").text, "Sun, 08 Nov 2026 07:02:00 GMT")

    def test_serviteur_glama_comparison_is_sourced_and_non_disruptive(self):
        """The article distinguishes current engineering choices from its historical beta."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            build(out=out)
            article = (
                out / "dispatches/clickup-serviteur-v0.3.0-beta.1.html"
            ).read_text(encoding="utf-8")
            css = (out / "dispatches/serviteur.css").read_text(encoding="utf-8")
            self.assertIn('id="why-serviteur"', article)
            self.assertIn('href="#why-serviteur"', article)
            self.assertIn('id="comparison-title"', article)
            self.assertEqual(article.count('class="positioning-principle"'), 6)
            self.assertIn('id="registry-title"', article)
            self.assertEqual(article.count('class="registry-tool-name"'), 80)
            self.assertIn("f1dd7aa3759d584f6acf6f0eb4b96dbfc61a2a48", article)
            for url in (
                "https://glama.ai/mcp/servers/mikah13/mcp-clickup",
                "https://glama.ai/mcp/servers/alexfdez1010/clickup-mcp",
                "https://glama.ai/mcp/servers/helbertparanhos/clickup-mcp-pro",
                "https://glama.ai/mcp/servers/saigontechnology/reclickup-mcp/tools/clickup_doc_write",
                "https://developer.clickup.com/docs/mcp-tools",
            ):
                self.assertIn('href="' + url + '"', article)
            self.assertIn("Where the others lead.", article)
            self.assertIn("not</em> claim complete ClickUp API coverage", article)
            self.assertIn("not</em> a verified ranking", article)
            self.assertNotIn("<script", article, "Do not add scripts or external tracking")
            self.assertNotIn("@import", css)
            self.assertNotIn("url(http", css)
            self.assertIn("prefers-reduced-motion", css)
            self.assertIn(".positioning-principles{display:grid", css)
            self.assertIn("@media(max-width:650px)", css)
            feed = ET.parse(out / "feed.xml").getroot().find("channel")
            item = next(
                node for node in feed.findall("item")
                if node.find("guid").text == "urn:elfshell:transmission:clickup-serviteur-public-beta"
            )
            self.assertEqual(
                item.find("pubDate").text, "Sun, 08 Nov 2026 07:02:00 GMT"
            )
            self.assertIn("Glama", item.find("description").text)
            self.assertIn("evidence-linked comparison", item.find("description").text)
            self.assertTrue(
                item.find("link").text.endswith(
                    "/dispatches/clickup-serviteur-v0.3.0-beta.1.html"
                )
            )

    def test_rejects_untrusted_dispatch_page_paths(self):
        document = json.loads(SOURCE.read_text(encoding="utf-8"))
        for unsafe in ("../private.html", "https://example.org/test.html", "dispatches/../../secrets.html", "/dispatches/x.html", "dispatches/file.js"):
            test = copy.deepcopy(document)
            test["items"][-1]["page"] = unsafe
            with self.subTest(page=unsafe):
                with self.assertRaisesRegex(ValueError, "unsafe article page path"):
                    validated(test)


if __name__ == "__main__":
    unittest.main()
