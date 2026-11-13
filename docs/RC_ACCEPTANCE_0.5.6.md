# Ayarime v0.5.6 — release candidate acceptance and owner sign-off

**Current state:** unsigned, reproducible candidate for a disposable desktop Firefox profile. This is **not** an AMO-submitted, signed, published or production-approved version. Public signed v0.5.5 remains untouched.

## Evidence required before owner sign-off

- Inspect the latest **Ayarime v0.5.6 unified RC — verify only** GitHub Actions run on the exact proposed commit. It must pass both source test suites, Mozilla `web-ext lint --warnings-as-errors`, deterministic package/source ZIP reproduction, standalone Google disconnection, real Firefox privacy, browser prompts, Hub/sidebar responsive and keyboard checks, and signed v0.5.5-to-**unsigned** RC migration/rollback.
- Inspect `dist/unified-rc-evidence.json`, SHA-256 values and the runtime/source archives in the workflow artifact. The runtime ZIP and XPI must have the same digest. The source package must include **both** the core and the exact pinned Workspace AI tree. No secrets are to be included in artifacts or workflow logs.
- Check the candidate manifest: unchanged `elf-shell-ayarime@local.theme` Firefox ID, version `0.5.6`, only `theme`, `search`, `storage` required; optional browser permissions, per-host access, and optional `authenticationInfo`, `personalCommunications`, `websiteContent`, `personallyIdentifyingInfo` data consent. Do not misdescribe optional model-provider traffic as zero data leaving the browser.
- Inspect `PRIVACY.md` and `amo/listing-metadata-v0.5.6-draft.json`. The legacy `amo/listing-metadata.json` is for the earlier 0.5.5 listing and must not be used to describe the unified candidate.

## Disposable Firefox profile — owner/manual acceptance

**Never use an active work profile, real notes or actual customer data.** The testing build is unsigned and temporary; Firefox removes temporary add-ons on restart. Keep your signed v0.5.5 profile separate.

1. Load the extracted **unsigned RC XPI** via `about:debugging#/runtime/this-firefox`, or load its `manifest.json` as a temporary extension. Confirm the original new-tab, RSS, search, notes and workspace settings still work; desktop resolution, 390px and 320px compact views must have no unwanted horizontal scroll.
2. Confirm new installation has Ayarime AI **OFF**. Clicking Ask Ayarime while disabled must not launch inference or grant Firefox tab access. Enable AI explicitly; deny tabs access, then approve separately. It must reuse one pinned Hub. Verify the sidebar opens using its own user gesture.
3. With the provider controls, try **Deny** for a provider API host and optional data collection. A model call and key entry should be blocked. Then approve one selected provider, enter a **low-privilege, budget-limited** API key locally (never commit or paste it into a public issue/CI). Call the model metadata check. With budget approval, send one harmless prompt, inspect its response, provenance, and cost in the provider's dashboard. This is the **live BYOK** gate; CI intentionally does not possess real API keys.
4. Confirm no automatic provider request on opening new tabs, Hub or sidebar; confirm `store:false` semantics do not imply zero retention. Test a bounded prompt, streaming cancellation and any reported errors without exposing response bodies or keys.
5. Confirm the local session history is visible across Hub/sidebar. Unless the user explicitly opts in for **that request**, previous exchanges are never included as model context. After a request, the history checkbox resets. Test `Clear conversation` independently.
6. Choose **Forget session key** and confirm it is not restored after closing and reopening the Hub. Enter a new *test* key, turn Ayarime AI **OFF**, confirm the key is purged and any in-progress stream is aborted. Re-enable AI; the old key must not reappear.
7. Revoke provider host and optional data permissions in `about:addons` → **Permissions and data**. Previously stored configuration must not authorize further inference without fresh consent. Confirm Google account/OAuth, Morning Coffee and update-check controls are disabled, and no Google Master MCP requests are made.
8. In a disposable profile, compare the already-tested v0.5.5 public signed baseline with the unsigned RC and rollback. **A real signed-v0.5.6 upgrade test is still impossible until Mozilla signs v0.5.6**. Do not call the current test a signed-to-signed upgrade.
9. Capture authentic Firefox screenshots for Mozilla. Confirm the accessible privacy URL, optional categories, artwork licensing, and current release notes.

## Publication control

No automatic AMO submission job exists for unified v0.5.6. The legacy `amo-listed.yml` deliberately **refuses** v0.5.6+, so it cannot accidentally ship the core-only build under the unified version number. After the above evidence is reviewed and the owner explicitly approves publication, prepare a separate, checked listed-update workflow for the **existing** AMO add-on. Mozilla review/signing and a real signed 0.5.5 → signed 0.5.6 upgrade come **after** that approval, not before.

The pinned Google Master MCP contract remains inactive. Enabling Google is a later, separately reviewed opt-in release milestone.
