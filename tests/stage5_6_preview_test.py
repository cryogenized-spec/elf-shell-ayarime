#!/usr/bin/env python3
"""Post-v0.5.6 Stage 5/6 preview contract — NO live Google or BYOK calls."""
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/"dist/unified-preview"


class StageFiveSixPreview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert STAGE.is_dir(), "Build unsigned unified preview first"
        cls.manifest=json.loads((STAGE/"manifest.json").read_text())
        cls.background=(STAGE/"workspace-ai-background.js").read_text()
        cls.master=(STAGE/"google/master-read-client.js").read_text()
        cls.source=(ROOT/"scripts/build_unified_preview.py").read_text()

    def test_one_extension_and_no_install_time_permission_escalation(self):
        self.assertEqual(self.manifest["version"],"0.5.6")
        self.assertEqual(set(self.manifest["permissions"]),{"theme","search","storage"})
        self.assertEqual(self.manifest["browser_specific_settings"]["gecko"]["id"],
                         "elf-shell-ayarime@local.theme")
        self.assertNotIn("externally_connectable",self.manifest)

    def test_nonstream_cancel_is_accepted_even_after_ai_is_switched_off(self):
        self.assertIn('case "AI_CANCEL_REQUEST":',self.background)
        self.assertIn('case "AI_SEND_PROMPT":',self.background)
        self.assertIn("cancelOneShot()",self.background)
        self.assertIn("activeOneShot",self.background)
        self.assertIn('"AI_CANCEL_REQUEST"',self.source)
        self.assertIn('storage.session.remove("elfshell.byok.apiKey.v1")',self.background)
        self.assertIn("UNIFIED_STREAMS",self.background)
        ui=(STAGE/"ui.js").read_text()
        self.assertIn('type:"AI_CANCEL_REQUEST"',ui)
        self.assertIn("Stop request",ui)

    def test_google_master_client_is_present_but_not_connected_to_ui(self):
        self.assertIn("google/master-read-client.js",self.manifest["background"]["scripts"])
        self.assertIn('const RESOURCE="https://google-master-mcp.cryogenized.workers.dev/mcp"',self.master)
        self.assertIn("USER_CONSENT_REQUIRED",self.master)
        self.assertIn("FIREFOX_HOST_PERMISSION_REQUIRED",self.master)
        self.assertIn("UNKNOWN_OPERATION",self.master)
        self.assertNotIn("GOOGLE_MASTER_READ",self.background)
        self.assertNotIn("GOOGLE_MASTER_CONNECT",self.background)
        self.assertIn("Google OAuth and update checks are disabled",self.background)
        self.assertIn('message.type.startsWith("MASTER_")',self.background)
        hub=(STAGE/"hub.html").read_text()
        self.assertIn('class="frame master-panel" hidden aria-hidden="true"',hub)
        self.assertNotIn('<script defer src="google/master-ui.js"></script>',hub)
        self.assertIn("body[data-view=\"hub\"] .master-panel[hidden]",
                      (STAGE/"unified/ui-polish.css").read_text())
        self.assertIn("google/master-oauth.js",self.manifest["background"]["scripts"])
        self.assertNotIn("identity",self.manifest["permissions"])
        self.assertNotIn('google/master-read-client.js', (STAGE/"hub.html").read_text())
        self.assertNotIn('google/master-read-client.js', (STAGE/"sidebar.html").read_text())

    def test_no_mutation_operation_names_in_client_allowlist(self):
        names=self.master.split("const READS=Object.freeze([",1)[1].split("]);",1)[0]
        for bad in ["tasks_create_task","gmail_send_message","drive_delete_file",
                    "write_prepare_action","script_update_sources"]:
            self.assertNotIn(bad,names)
        self.assertIn("gmail_list_messages",names)
        self.assertIn("tasks_list_tasklists",names)


if __name__=="__main__":
    unittest.main()
