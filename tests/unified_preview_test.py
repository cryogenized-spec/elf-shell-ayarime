#!/usr/bin/env python3
"""Contract checks for the unsigned, intentionally separate unified XPI."""
import json
from pathlib import Path
import unittest
from zipfile import ZipFile
ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/"dist/unified-preview"
ZIP=ROOT/"dist/ELF-SHELL-Ayarime-unified-UNSIGNED.xpi"

class UnifiedPreviewContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert STAGE.is_dir() and ZIP.is_file(), "Run build_unified_preview.py first"
        cls.core=json.loads((ROOT/"manifest.json").read_text())
        cls.bundle=json.loads((STAGE/"manifest.json").read_text())

    def test_core_manifest_is_not_modified_and_id_survives(self):
        self.assertEqual(self.core["browser_specific_settings"]["gecko"]["id"],
                         self.bundle["browser_specific_settings"]["gecko"]["id"])
        self.assertEqual(self.core["permissions"],self.bundle["permissions"])
        self.assertEqual(self.core["chrome_url_overrides"],self.bundle["chrome_url_overrides"])
        self.assertEqual(self.core["content_security_policy"],
                         self.bundle["content_security_policy"])
        self.assertNotIn("sidebar_action",self.core)
        self.assertIn("sidebar_action",self.bundle)
        self.assertIn("action",self.bundle)
        self.assertNotIn("externally_connectable",self.bundle)

    def test_extra_runtime_grants_remain_optional(self):
        required=set(self.bundle["permissions"])
        optional=set(self.bundle["optional_permissions"])
        self.assertEqual(required,{"theme","search","storage"})
        self.assertTrue({"tabs","tabGroups"}.issubset(optional))
        self.assertFalse({"tabs","tabGroups","identity","alarms"} & required)
        self.assertNotIn("identity",optional)
        self.assertNotIn("alarms",optional)
        self.assertEqual(self.bundle["browser_specific_settings"]["gecko"]
                         ["data_collection_permissions"]["required"],["none"])
        self.assertIn("personalCommunications",
                      self.bundle["browser_specific_settings"]["gecko"]
                      ["data_collection_permissions"]["optional"])

    def test_background_routers_are_isolated_and_unified(self):
        scripts=self.bundle["background"]["scripts"]
        self.assertEqual(scripts[0],"background.js")
        self.assertEqual(scripts[-1],"workspace-ai-background.js")
        self.assertEqual(len(scripts),len(set(scripts)))
        for name in scripts:
            self.assertTrue((STAGE/name).is_file(),name)
        companion=(STAGE/"workspace-ai-background.js").read_text()
        self.assertTrue(companion.startswith('(function(){\n"use strict";'))
        self.assertIn("const WORKSPACE_MESSAGE_TYPES = new Set",companion)
        self.assertIn('if (sender?.id !== browser.runtime.id',companion)
        self.assertIn('"UNIFIED_HELLO"',companion)
        self.assertIn('browser.runtime.getURL("newtab.html")',companion)
        self.assertNotIn("browser.runtime.sendMessage(\"workspace-ai@elf-shell.local\"",
                         (STAGE/"workspace/bridge.js").read_text())
        self.assertNotIn('type:"AI_SEND_PROMPT"',(STAGE/"workspace/bridge.js").read_text())

    def test_original_google_and_model_permissions_are_not_automatically_granted(self):
        bridge=(STAGE/"workspace/bridge.js").read_text()
        self.assertIn('openAssistant:()=>launch("OPEN_ASSISTANT",["tabs"])',bridge)
        self.assertIn('openWorkspace:()=>launch("OPEN_WORKSPACE",["tabs","tabGroups"])',bridge)
        self.assertIn("browser.permissions.request({permissions})",bridge)
        self.assertIn('type:"OPEN_WORKSPACE"',(STAGE/"ui.js").read_text())
        self.assertIn('permissions:["tabs","tabGroups"]',(STAGE/"ui.js").read_text())
        self.assertIn("Google OAuth and update checks are disabled",
                      (STAGE/"workspace-ai-background.js").read_text())
        self.assertIn("UNSIGNED UNIFIED PREVIEW",
                      (STAGE/"hub.html").read_text())
        companion=(STAGE/"workspace-ai-background.js").read_text()
        self.assertIn('permissions:["tabs"]',companion)
        self.assertIn('permissions:["tabs","tabGroups"]',companion)
        self.assertIn("tab access must be granted",companion)
        self.assertIn("tab-group access must be approved first",companion)
        self.assertNotIn("https://google",bridge)
        self.assertNotIn("api.openai.com",bridge)

    def test_unified_station_labels_do_not_claim_a_second_companion(self):
        html=(STAGE/"newtab.html").read_text()
        js=(STAGE/"newtab.js").read_text()
        self.assertIn("integrated Ayarime AI console",html)
        self.assertIn("integrated Ayarime Workspace Hub",html)
        self.assertIn("INTEGRATED AYARIME WORKSPACE",js)
        self.assertIn("FOCUS AYARIME AI CONSOLE",js)
        self.assertNotIn("OPTIONAL WORKSPACE AI COMPANION",js)
        self.assertNotIn("optional companion",html)
        self.assertIn("OPTIONAL WORKSPACE AI COMPANION",(ROOT/"newtab.js").read_text())

    def test_complete_assets_are_bundled_and_exact(self):
        self.assertTrue((STAGE/"icons/ayarime-rose-outline.svg").is_file())
        for name in ["hub.html","sidebar.html","newtab.html","ui.css",
                     "ui-trace.js","ai/openai-stream.js","google/session.js"]:
            self.assertTrue((STAGE/name).is_file(),name)
        with ZipFile(ZIP) as z:
            paths=z.namelist()
            self.assertEqual(len(paths),len(set(paths)))
            self.assertEqual(set(paths),{
                p.relative_to(STAGE).as_posix() for p in STAGE.rglob("*") if p.is_file()
            })
            self.assertIsNone(z.testzip())
            for path in paths:
                self.assertEqual(z.read(path),(STAGE/path).read_bytes(),path)

if __name__=="__main__":
    unittest.main()
