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
        self.assertTrue(self.bundle["sidebar_action"]["open_at_install"])
        self.assertIn("action",self.bundle)
        self.assertNotIn("externally_connectable",self.bundle)

    def test_extra_runtime_grants_remain_optional(self):
        required=set(self.bundle["permissions"])
        optional=set(self.bundle["optional_permissions"])
        self.assertEqual(required,{"theme","search","storage"})
        self.assertTrue({"tabs","tabGroups","activeTab","scripting"}.issubset(optional))
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
        self.assertIn("This does not grant Google account access.",bridge)
        self.assertIn("Google account access remains separate.",bridge)
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

    def test_ai_available_by_default_without_touching_existing_settings(self):
        page=(STAGE/"newtab.html").read_text()
        module=(STAGE/"unified/module.js").read_text()
        bridge=(STAGE/"workspace/bridge.js").read_text()
        background=(STAGE/"workspace-ai-background.js").read_text()
        self.assertIn('id="ai-module-toggle"',page)
        self.assertIn('src="unified/module.js"',page)
        self.assertIn('id="ai-module-status"',page)
        self.assertIn('"elfshell.unified.aiEnabled.v1"',module)
        self.assertIn("enabled=data[KEY]!==false",module)
        self.assertIn("Ayarime is paused",module)
        self.assertIn("AyarimeUnifiedModule?.isEnabled()",bridge)
        self.assertIn("unifiedAiEnabled().then(allowed=>allowed ? handle(message)",background)
        self.assertIn("unifiedAiEnabled().then(allowed=>{",background)
        self.assertIn("AI_CONVERSATION_CLEAR",background)
        self.assertNotIn('elfshell.unified.aiEnabled.v1',(ROOT/"newtab.js").read_text())
        self.assertNotIn('ai-module-toggle',(ROOT/"newtab.html").read_text())
        self.assertNotIn('unified/module.js',(ROOT/"manifest.json").read_text())
        self.assertIn('const dataKey="elfshell-workspace-v3";',(ROOT/"newtab.js").read_text())

    def test_unified_interface_polish_is_scoped_and_accessible(self):
        css=(STAGE/"unified/ui-polish.css").read_text()
        for name in ("hub.html","sidebar.html"):
            html=(STAGE/name).read_text()
            self.assertIn('href="unified/ui-polish.css"',html)
            self.assertEqual(html.count('href="unified/ui-polish.css"'),1)
        self.assertIn('a,select,textarea,summary',css)
        self.assertIn(':focus-visible',css)
        self.assertIn('max-width: 420px',css)
        self.assertIn('conversation-bubble',css)
        self.assertNotIn("unified/ui-polish.css",(ROOT/"newtab.html").read_text())
        self.assertNotIn("unified/ui-polish.css",(ROOT/"manifest.json").read_text())
        sidebar=(STAGE/"sidebar.html").read_text()
        self.assertNotIn('unified-provider-settings',sidebar)
        self.assertIn('id="ai-model-picker"',sidebar)
        self.assertIn('id="ai-settings-form"',sidebar)
        self.assertIn('id="ai-key"',sidebar)
        self.assertEqual(sidebar.count('id="ai-provider"'),1)
        self.assertNotIn('unified-provider-settings',(STAGE/"hub.html").read_text())

    def test_sidebar_first_and_hub_tabs_are_source_backed(self):
        hub=(STAGE/"hub.html").read_text()
        sidebar=(STAGE/"sidebar.html").read_text()
        newtab=(STAGE/"newtab.html").read_text()
        background=(STAGE/"workspace-ai-background.js").read_text()
        self.assertIn('src="unified/hub-tabs.js"',hub)
        self.assertIn('href="unified/hub-tabs.css"',hub)
        self.assertIn('src="unified/page-context.js"',sidebar)
        self.assertIn('src="unified/sidebar-handoff.js"',sidebar)
        self.assertIn('id="ayarime-sidebar-launcher"',newtab)
        self.assertIn('id="ayarime-workspace-launcher"',newtab)
        self.assertNotIn('id="station-drawer"',newtab)
        self.assertNotIn('station-drawer.js',newtab)
        self.assertIn('id="ai-model-picker"',sidebar)
        self.assertIn('id="ai-model-picker"',hub)
        self.assertIn('src="unified/workspace-settings.js"',hub)
        self.assertIn('src="unified/coffee-readiness.js"',hub)
        self.assertIn('browser.sidebarAction.open()',background)
        self.assertIn('state[UNIFIED_AI_KEY]!==false',background)
        for asset in ("hub-tabs.js","hub-tabs.css","page-context.js",
                      "sidebar-handoff.js","workspace-settings.js",
                      "workspace-settings.css","coffee-readiness.js",
                      "station-launcher.js","station-launcher.css"):
            self.assertTrue((STAGE/"unified"/asset).is_file())
        self.assertFalse((STAGE/"unified/station-drawer.js").exists())

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
