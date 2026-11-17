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

    def test_direct_credential_shortcuts_and_no_automatic_auth(self):
        connections=(STAGE / "unified/workspace-settings.js").read_text()
        for url in ("https://console.cloud.google.com/projectcreate",
                    "https://console.cloud.google.com/apis/library",
                    "https://console.cloud.google.com/auth/clients",
                    "https://dash.cloudflare.com/",
                    "https://github.com/cryogenized-spec/Google-master-worker-MCP"):
            self.assertIn(url, connections)
        self.assertIn("unified-google-client-id", connections)
        self.assertIn("unified-google-save-client", connections)
        self.assertIn("public Google OAuth client ID", connections)
        self.assertIn("elfshell.mcp.publicGoogleClient.v1",connections)
        self.assertIn("elfshell.mcp.userProfile.v1",connections)
        sidebar=(STAGE / "sidebar.html").read_text()
        self.assertIn('src="sidebar-tabs.js"', sidebar)
        self.assertIn('href="sidebar-tabs.css"', sidebar)
        self.assertIn('src="unified/workspace-settings.js"',sidebar)

    def test_only_one_sidebar_with_tabbed_workspace(self):
        station=(STAGE / "newtab.html").read_text()
        hub=(STAGE / "hub.html").read_text()
        self.assertIn('id="ayarime-sidebar-launcher"',station)
        self.assertIn('id="ayarime-workspace-launcher"',station)
        self.assertNotIn('id="station-drawer"',station)
        self.assertNotIn('station-drawer.js',station)
        self.assertIn('src="unified/workspace-settings.js"',hub)
        self.assertIn('src="unified/hub-tabs.js"',hub)
        self.assertNotIn('href="hub.html#google-master"',station)

    def test_official_default_and_byo_no_auto_network(self):
        connections=(STAGE / "unified/workspace-settings.js").read_text()
        hub=(STAGE / "hub.html").read_text()
        self.assertIn("https://gmailmcp.googleapis.com/mcp/v1",connections)
        self.assertIn("https://calendarmcp.googleapis.com/mcp/v1",connections)
        self.assertIn("elfshell.mcp.registry.v1",connections)
        self.assertIn("browser.storage.local.set",connections)
        self.assertNotIn("fetch(",connections)
        self.assertNotIn("launchWebAuthFlow",connections)
        self.assertNotIn("google/master-ui.js",hub)
        self.assertIn('class="frame master-panel" hidden',hub)

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
