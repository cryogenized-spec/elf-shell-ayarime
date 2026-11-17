#!/usr/bin/env python3
"""Single-source ELF//SHELL + Ayarime acceptance: no second checkout."""
import ast
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
ASSISTANT = ROOT / "assistant"
WORKFLOWS = [".github/workflows/unified-preview.yml",
             ".github/workflows/unified-rc.yml",
             ".github/workflows/signed-baseline-acceptance.yml"]

class MonorepoContract(unittest.TestCase):
    def test_original_import_provenance_survives_source_consolidation(self):
        self.assertTrue((ASSISTANT/"SOURCE_LOCK.json").is_file())
        source=json.loads((ASSISTANT/"SOURCE_LOCK.json").read_text())
        self.assertEqual(source["source_repository"],
                         "cryogenized-spec/elf-shell-workspace-ai")
        self.assertEqual(source["source_commit"],
                         "885157e3d7bfeba3d1a344068448c1f4782d3be0")
        self.assertEqual(source["import_path"],"assistant")
        self.assertEqual(len(source["files"]),95)
        self.assertIn("ai/providers.js",source["files"])
        self.assertIn("google/master-oauth.js",source["files"])
        self.assertIn("mcp/src/server.js",source["files"])
        # The provenance snapshot is intentionally NOT a code freeze.
        self.assertTrue(all((ASSISTANT/name).is_file() for name in source["files"]))

    def test_packager_explicitly_whitelists_companion_runtime(self):
        node=ast.parse((ASSISTANT/"scripts/package.py").read_text())
        matches=[ast.literal_eval(n.value) for n in node.body
                 if isinstance(n,ast.Assign)
                 and any(isinstance(t,ast.Name) and t.id=="FILES" for t in n.targets)]
        self.assertEqual(len(matches),1)
        runtime=matches[0]
        self.assertIn("background.js",runtime)
        self.assertIn("google/master-read-client.js",runtime)
        self.assertIn("google/master-oauth.js",runtime)
        self.assertEqual(len(runtime),len(set(runtime)))
        for name in runtime:
            path=(ASSISTANT/name).resolve()
            self.assertTrue(path.is_relative_to(ASSISTANT.resolve()),name)
            self.assertTrue(path.is_file(),name)

    def test_single_repo_build_never_uses_external_companion_checkout(self):
        source=(ROOT/"scripts/build_unified_preview.py").read_text()
        rc=(ROOT/"scripts/package_unified_rc.py").read_text()
        self.assertIn('build(ROOT / "assistant"',source)
        self.assertIn('release(ROOT / "assistant")',rc)
        self.assertNotIn('parser.add_argument("--companion"',source)
        self.assertNotIn('p.add_argument("--companion"',rc)
        self.assertIn("SOURCE_LOCK.json",source)
        self.assertIn("core/assistant/ai/providers.js",rc)
        self.assertNotIn('git", "-C", str(companion)',rc)

    def test_one_ci_checkout_runs_both_source_suites(self):
        for path in WORKFLOWS:
            text=(ROOT/path).read_text()
            self.assertNotIn('repository: cryogenized-spec/elf-shell-workspace-ai',text,path)
            self.assertNotIn('--companion workspace-ai',text,path)
        preview=(ROOT/WORKFLOWS[0]).read_text()
        rc=(ROOT/WORKFLOWS[1]).read_text()
        self.assertIn('(cd assistant && npm test)',preview)
        self.assertIn('(cd assistant && npm test)',rc)
        self.assertIn("assistant/**",rc)
        self.assertIn("scripts/package_unified_rc.py",rc)

    def test_release_identity_still_pinned_to_core(self):
        manifest=json.loads((ROOT/"manifest.json").read_text())
        self.assertEqual(manifest["browser_specific_settings"]["gecko"]["id"],
                         "elf-shell-ayarime@local.theme")
        self.assertEqual(set(manifest["permissions"]),{"theme","search","storage"})

if __name__=="__main__":
    unittest.main()
