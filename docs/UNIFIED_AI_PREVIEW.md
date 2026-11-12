# One-extension Ayarime prototype — unsigned merger preparation

**Status:** engineering-only unified preview. This is NOT an AMO release, not installed into the user's Firefox, and does not merge either source repository.

## Architecture and source ownership

The public **ELF//SHELL — Ayarime** project retains its existing Firefox add-on identity, new-tab interface, themes, icons, local memory and RSS permissions. The independent **Workspace AI** repository remains the development source of AI, Google REST, profiles, Hub, sidebar, tool activity, reasoning UI and the Rose Seal loader.

The new Python assembler copies two **explicit source whitelists**, pins the companion at commit `3c678bda35a64fe185135eb1b937e2d5eb26d810` and produces:

- `dist/unified-preview/`: unpacked, testable Firefox extension source
- `dist/ELF-SHELL-Ayarime-unified-UNSIGNED.xpi`: a separate deterministic, unsigned archive

The normal `scripts/package.py` and `manifest.json` files are **never modified**. The original AMO export remains a separate, core-only product. The unified preview is not signed and is suitable only for a temporary, isolated Firefox profile.

## Manifest and security model

The merged preview retains the original add-on ID `elf-shell-ayarime@local.theme`, core `theme/search/storage` required permissions and new-tab override. Workspace AI's `tabs/tabGroups` privileges are **optional**. Mozilla does not permit `identity` and `alarms` as optional permissions, so neither is added; Google OAuth/account operations and automatic release checks remain **disabled in this unsigned preview**, rather than silently escalating core permissions. The companion's optional data collection classes and specific host origins remain optional. A separate native sidebar and toolbar action are declared in the preview manifest.

For the **Ask Ayarime** and **Restore Workspace** Station commands, the compiled-only bridge initiates a Firefox permission request directly from the user gesture, before the command is routed. Ask Ayarime requests optional `tabs` only; Restore Workspace requests `tabs` and `tabGroups`. Declining the prompt does nothing to existing tabs. The companion's Hub/Sidebar Launch control has a corresponding one-time grant path. No model key, Google data or prompt is carried by the core bridge.

**Google authorization is not an automatic consequence of enabling Ayarime AI.** The Worker MCP endpoint and Google OAuth scope verification are separate. The existing Google REST modules remain in the packaged source, but the preview background refuses Google account operations. A separate authorization design is required because Firefox's `identity` permission is non-optional; no live Google account should be used with this preview.

The packaged companion background is wrapped in a private JavaScript function scope to avoid collisions with the core background's top-level variables. Its runtime message listener accepts only the **exact companion message types** discovered from the reviewed source handler. Core message families are left to the core handler. The dashboard uses a **new, allowlisted same-extension bridge** that accepts HELLO, OPEN_WORKSPACE or OPEN_ASSISTANT only, and validates the actual internal new-tab sender URL. No external extension connection is exposed.

## Build locally (only after reviewing the branch)

Have both repositories checked out in separate sibling directories and position Workspace AI at exactly the pinned commit. From the Ayarime core checkout:

```bash
python3 scripts/build_unified_preview.py --companion ../elf-shell-workspace-ai
python3 -m unittest discover -s tests -p unified_preview_test.py -v
npx --yes web-ext@10.8.0 lint --source-dir dist/unified-preview --warnings-as-errors
```

Do **not** install this as a permanent extension in a profile already running the public, signed version; Firefox uses the same add-on ID. Native CI installs it only as a temporary add-on in an isolated profile.

## Required acceptance before merger

1. Independent source tests, exact-inventory packaging tests and Firefox Mozilla lint.
2. A **real one-extension Firefox smoke test**: original theme/Station, original ID, valid internal HELLO, no unauthorized AI commands, correct core message routing, AI Hub and sidebar documents accessible, no separate companion installed, and optional workspace permissions ungranted on first load.
3. In an explicitly approved manual profile, click-through grant/deny testing for `tabs` and `tabGroups`, sidebar opening and repeated hub/tab reuse. Ensure no accidental network calls. Reject unsafe permissions transitions.
4. Validate preserved settings/backup/migrations and existing RSS host-consent test [issue #40](https://github.com/cryogenized-spec/elf-shell-ayarime/issues/40).
5. Live BYOK provider acceptance, real Google OAuth `identity` permission and scoped Google Worker MCP connection after its endpoints and scope contract stabilize. Test account isolation and explicit AI data-sharing previews.
6. Review Mozilla AMO disclosures and source licensing, produce a signed candidate, and only then consider merging or releasing.

**Important:** A successful build is not equivalent to finished Google scope integration, secure account onboarding or signed distribution. Keep the branches unmerged until review and explicit approval.
