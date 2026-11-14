#!/usr/bin/env python3
"""Opt-in, UNSIGNED Google Master engineering assembly (no live credentials)."""
import json
from pathlib import Path
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "dist/unified-google-master-preview"
PACKAGE = ROOT / "dist/ELF-SHELL-Ayarime-Google-Master-UNSIGNED.xpi"
DEFAULT = ROOT / "dist/unified-preview"


class GoogleMasterEngineering(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert STAGE.is_dir() and PACKAGE.is_file(), (
            "Build with --enable-google-master using the exact pinned companion"
        )
        cls.manifest = json.loads((STAGE / "manifest.json").read_text())
        cls.core = json.loads((ROOT / "manifest.json").read_text())

    def test_integration_is_isolated_from_core_and_default_preview(self):
        self.assertEqual(self.core["permissions"], ["theme", "search", "storage"])
        self.assertEqual(self.manifest["permissions"],
                         ["theme", "search", "storage", "identity"])
        self.assertNotIn("identity", self.manifest["optional_permissions"])
        self.assertEqual(self.manifest["browser_specific_settings"]["gecko"]["id"],
                         "elf-shell-ayarime@local.theme")
        self.assertEqual(self.manifest["content_security_policy"],
                         self.core["content_security_policy"])
        self.assertNotIn("externally_connectable", self.manifest)
        self.assertTrue((DEFAULT / "manifest.json").is_file())
        self.assertNotIn("identity", json.loads(
            (DEFAULT / "manifest.json").read_text())["permissions"])

    def test_explicit_worker_permissions_and_manual_firefox_login(self):
        origins = self.manifest["optional_host_permissions"]
        for host in ["google-master-auth", "google-master-mcp"]:
            self.assertIn(
                f"https://{host}.cryogenized.workers.dev/*", origins
            )
        self.assertIn("personalCommunications", self.manifest
                      ["browser_specific_settings"]["gecko"]
                      ["data_collection_permissions"]["optional"])
        self.assertIn("google/master-oauth.js",
                      self.manifest["background"]["scripts"])
        self.assertIn("unified/google-master-tunnel.js",
                      self.manifest["background"]["scripts"])
        self.assertLess(self.manifest["background"]["scripts"].index(
            "unified/google-master-tunnel.js"),
            self.manifest["background"]["scripts"].index(
                "workspace-ai-background.js"))

    def test_manual_hub_controls_and_background_router(self):
        hub = (STAGE / "hub.html").read_text()
        background = (STAGE / "workspace-ai-background.js").read_text()
        self.assertIn('<script defer src="google/master-ui.js"></script>', hub)
        self.assertIn('<script defer src="unified/google-master-tunnel-ui.js"></script>', hub)
        self.assertIn('id="master-mcp-ping"', hub)
        self.assertIn('id="master-mcp-ping-result"', hub)
        self.assertIn("Leave it UNCHECKED", hub)
        self.assertIn('class="frame master-panel" aria-label=', hub)
        self.assertNotIn('class="frame master-panel" hidden', hub)
        self.assertIn('case "MASTER_CONNECT":', background)
        self.assertIn('case "MASTER_DISCONNECT":', background)
        self.assertIn('case "MASTER_MCP_PING":', background)
        self.assertIn('AyarimeGoogleMasterTunnel.probe', background)
        # Standalone Google Desktop OAuth and update checks remain blocked.
        self.assertIn('message.type.startsWith("GOOGLE_")', background)
        self.assertIn('Google OAuth and update checks', (
            DEFAULT / "workspace-ai-background.js").read_text())
        self.assertIn('case "MASTER_MCP_PING":',
                      background)
        self.assertNotIn('message.type.startsWith("MASTER_") ||',
                         background)

    def test_no_local_proxy_or_user_secrets_are_bundled(self):
        transport = (STAGE / "unified/google-master-tunnel.js").read_text()
        assert 'const RESOURCE="https://google-master-mcp.cryogenized.workers.dev/mcp"' in transport
        self.assertIn('method:"tools/list"', transport)
        self.assertNotIn('method:"tools/call"', transport)
        self.assertIn('credentials:"omit"', transport)
        self.assertIn('redirect:"error"', transport)
        self.assertNotIn("localhost", transport)
        self.assertNotIn("127.0.0.1", transport)
        self.assertNotIn("Cloudflare tunnel token", transport)

    def test_xpi_is_exactly_staged_package(self):
        with ZipFile(PACKAGE) as archive:
            self.assertIsNone(archive.testzip())
            names = archive.namelist()
            self.assertEqual(len(names), len(set(names)))
            self.assertEqual(set(names), {
                p.relative_to(STAGE).as_posix()
                for p in STAGE.rglob("*") if p.is_file()
            })
            for name in names:
                self.assertEqual(archive.read(name), (STAGE / name).read_bytes())


if __name__ == "__main__":
    unittest.main()
