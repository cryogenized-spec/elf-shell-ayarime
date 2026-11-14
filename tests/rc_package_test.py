#!/usr/bin/env python3
"""Release-candidate manifest, privacy and deterministic Mozilla package gate."""
from pathlib import Path
from zipfile import ZipFile
import hashlib
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]
DIST=ROOT/"dist"
STAGE=DIST/"unified-rc"
ZIP=DIST/"ELF-SHELL-Ayarime-v0.5.6-unified-RC-UNSIGNED.zip"
XPI=DIST/"ELF-SHELL-Ayarime-v0.5.6-unified-RC-UNSIGNED.xpi"
SOURCE=DIST/"ELF-SHELL-Ayarime-v0.5.6-unified-RC-source.zip"
REPORT=DIST/"unified-rc-evidence.json"


class UnifiedRC(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for p in [STAGE,ZIP,XPI,SOURCE,REPORT]:
            assert p.exists(), "Run scripts/package_unified_rc.py first: "+str(p)
        cls.m=json.loads((STAGE/"manifest.json").read_text(encoding="utf-8"))
        cls.core=json.loads((ROOT/"manifest.json").read_text(encoding="utf-8"))
        cls.evidence=json.loads(REPORT.read_text(encoding="utf-8"))

    def test_addon_identity_and_no_required_permission_expansion(self):
        m=self.m
        self.assertEqual(m["name"],"ELF//SHELL — Ayarime")
        self.assertEqual(m["version"],"0.5.6")
        self.assertEqual(m["browser_specific_settings"]["gecko"]["id"],
                         "elf-shell-ayarime@local.theme")
        self.assertEqual(m["permissions"],self.core["permissions"])
        self.assertEqual(set(m["permissions"]),{"theme","search","storage"})
        self.assertNotIn("externally_connectable",m)
        self.assertEqual(m["content_security_policy"],
                         self.core["content_security_policy"])
        self.assertEqual(m["chrome_url_overrides"],self.core["chrome_url_overrides"])
        self.assertIn("sidebar_action",m)
        self.assertIn("workspace-ai-background.js",m["background"]["scripts"])

    def test_byok_optional_data_transmission_is_disclosed(self):
        types=self.m["browser_specific_settings"]["gecko"]["data_collection_permissions"]
        self.assertEqual(types["required"],["none"])
        self.assertEqual(set(types["optional"]),{
            "authenticationInfo","personalCommunications","websiteContent",
            "personallyIdentifyingInfo"})
        privacy=(ROOT/"PRIVACY.md").read_text(encoding="utf-8")
        for name in types["optional"]:
            self.assertIn(name,privacy)
        for disclosure in ["off by default","storage.session",
                           "not an encrypted","not enabled",
                           "directly", "selected provider"]:
            self.assertIn(disclosure.lower(),privacy.lower())

    def test_ai_switch_purges_key_and_google_remains_inert(self):
        module=(STAGE/"unified/module.js").read_text()
        background=(STAGE/"workspace-ai-background.js").read_text()
        self.assertIn('type:"AI_CLEAR_SESSION_KEY"',module)
        self.assertIn("UNIFIED_STREAMS",background)
        self.assertIn("controller.abort()",background)
        self.assertIn('storage.session.remove("elfshell.byok.apiKey.v1")',background)
        self.assertIn("Google OAuth and update checks are disabled",background)
        self.assertNotIn("externally_connectable",
                         (STAGE/"manifest.json").read_text())
        self.assertIn('id="ai-module-toggle"',(STAGE/"newtab.html").read_text())

    def test_google_and_update_controls_not_visible(self):
        css=(STAGE/"unified/rc.css").read_text()
        self.assertIn(".google-section",css)
        self.assertIn(".coffee-panel",css)
        self.assertIn(".updater-panel",css)
        for name in ["hub.html","sidebar.html"]:
            html=(STAGE/name).read_text()
            self.assertIn('href="unified/rc.css"',html)
            self.assertNotIn("UNSIGNED UNIFIED PREVIEW",html)
        self.assertIn("rc-unavailable",(STAGE/"sidebar.html").read_text())

    def test_runtime_and_reviewer_source_are_byte_verified(self):
        runtime={p.relative_to(STAGE).as_posix():p.read_bytes()
                 for p in STAGE.rglob("*") if p.is_file()}
        with ZipFile(ZIP) as package:
            self.assertEqual(set(package.namelist()),set(runtime))
            self.assertEqual(len(package.namelist()),len(runtime))
            self.assertIsNone(package.testzip())
            for name,body in runtime.items():
                self.assertEqual(package.read(name),body,name)
        self.assertEqual(ZIP.read_bytes(),XPI.read_bytes())
        self.assertEqual(hashlib.sha256(ZIP.read_bytes()).hexdigest(),
                         self.evidence["runtime_sha256"])
        with ZipFile(SOURCE) as source:
            self.assertIsNone(source.testzip())
            names=set(source.namelist())
            self.assertIn("core/scripts/package_unified_rc.py",names)
            self.assertIn("core/scripts/build_unified_preview.py",names)
            self.assertIn("core/assistant/ai/providers.js",names)
            self.assertIn("core/assistant/ai/openai-stream.js",names)
            self.assertIn("core/assistant/google/master-oauth.js",names)
            self.assertIn("core/assistant/SOURCE_LOCK.json",names)
            self.assertFalse(any(n.startswith("workspace-ai/") for n in names))
            self.assertIn("RC-BUILD-INSTRUCTIONS.txt",names)
            guide=source.read("RC-BUILD-INSTRUCTIONS.txt").decode()
            self.assertIn(self.evidence["companion_commit"],guide)
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                         self.evidence["source_sha256"])

    def test_no_signed_or_submitted_status_is_claimed(self):
        self.assertEqual(self.evidence["status"],"UNSIGNED_RC_ONLY")
        self.assertFalse(self.evidence["signed_v056"])
        self.assertFalse(self.evidence["mozilla_submitted"])
        self.assertFalse(self.evidence["google_worker_connected"])
        self.assertEqual(self.evidence["live_byok"],"NOT_TESTED_NO_USER_KEY")


if __name__=="__main__":
    unittest.main()
