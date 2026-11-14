#!/usr/bin/env python3
"""User-owned MCP engineering build: no shared Cloudflare service by default."""
import json
from pathlib import Path
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "dist/unified-google-master-preview"
PACKAGE = ROOT / "dist/ELF-SHELL-Ayarime-Google-Master-UNSIGNED.xpi"
DEFAULT = ROOT / "dist/unified-preview"
PRIVATE = "cryogenized.workers.dev"
OLD = ("google/master-oauth.js", "google/master-read-client.js",
       "google/master-ui.js", "unified/google-master-tunnel.js",
       "unified/google-master-tunnel-ui.js")

class PrivateMcpOptIn(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert STAGE.is_dir() and PACKAGE.is_file(), "Build --enable-google-master first"
        cls.manifest = json.loads((STAGE / "manifest.json").read_text())
        cls.core = json.loads((ROOT / "manifest.json").read_text())

    def test_one_extension_identity_and_privacy_gate(self):
        self.assertEqual(self.manifest["browser_specific_settings"]["gecko"]["id"],
                         "elf-shell-ayarime@local.theme")
        self.assertEqual(self.manifest["permissions"],
                         ["theme", "search", "storage", "identity"])
        self.assertEqual(self.manifest["content_security_policy"],
                         self.core["content_security_policy"])
        self.assertTrue((DEFAULT / "manifest.json").exists())
        self.assertNotIn("identity", json.loads((DEFAULT / "manifest.json")
                                                .read_text())["permissions"])

    def test_no_owner_cloudflare_or_legacy_master_network_in_xpi(self):
        scripts = self.manifest["background"]["scripts"]
        for path in OLD:
            self.assertNotIn(path, scripts)
            self.assertFalse((STAGE / path).exists(), path)
        self.assertNotIn(PRIVATE, json.dumps(self.manifest))
        compiled = (STAGE / "workspace-ai-background.js").read_text()
        self.assertIn('message.type.startsWith("MASTER_")', compiled)
        self.assertNotIn('case "MASTER_MCP_PING":', compiled)
        with ZipFile(PACKAGE) as z:
            self.assertFalse(any(path in z.namelist() for path in OLD))
            self.assertFalse(any(
                b"https://google-master-mcp.cryogenized.workers.dev" in
                z.read(path) for path in z.namelist()
                if path.endswith((".js", ".json", ".html"))
            ))

    def test_station_is_always_visible_and_tabbed(self):
        station = (STAGE / "newtab.html").read_text()
        for needle in (
            'id="station-drawer-open"', 'id="station-drawer"',
            'role="tablist"', 'id="sd-tab-station"',
            'id="sd-tab-ayarime"', 'id="sd-tab-mcp"',
            'id="sd-tab-settings"', 'id="sd-ai-toggle"',
            'id="sd-provider"', 'id="sd-mcp-resource"',
            'id="sd-mcp-issuer"', 'id="google-master-toggle"'
        ):
            self.assertIn(needle, station)
        self.assertIn('src="unified/station-drawer.js"', station)
        self.assertIn('href="unified/station-drawer.css"', station)
        self.assertNotIn('href="hub.html#google-master"', station)

    def test_official_default_and_byo_no_auto_network(self):
        drawer=(STAGE / "unified/station-drawer.js").read_text()
        station=(STAGE / "newtab.html").read_text()
        hub=(STAGE / "hub.html").read_text()
        self.assertIn('option value="official"', station)
        self.assertIn("https://gmailmcp.googleapis.com/mcp/v1", drawer)
        self.assertIn("https://calendarmcp.googleapis.com/mcp/v1", drawer)
        self.assertIn("elfshell.mcp.userProfile.v1", drawer)
        self.assertIn("browser.storage.local.set", drawer)
        self.assertNotIn("fetch(", drawer)
        self.assertNotIn("launchWebAuthFlow", drawer)
        self.assertNotIn("google/master-ui.js", hub)
        self.assertIn('class="frame master-panel" hidden', hub)

    def test_archive_matches_exact_staged_files(self):
        with ZipFile(PACKAGE) as z:
            self.assertIsNone(z.testzip())
            listed=z.namelist()
            self.assertEqual(len(listed),len(set(listed)))
            self.assertEqual(set(listed), {
                p.relative_to(STAGE).as_posix() for p in STAGE.rglob("*") if p.is_file()
            })
            for path in listed:
                self.assertEqual(z.read(path),(STAGE/path).read_bytes())

if __name__ == "__main__":
    unittest.main()
