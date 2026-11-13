# Unified Ayarime — Firefox/AMO release sign-off

**Review date:** 13 November 2026. **Status: NOT AUTHORIZED FOR AMO SUBMISSION.**
This file describes the currently **unsigned, unmerged** one-extension prototype. It is not a replacement for the published ELF//SHELL extension's own `PRIVACY.md` and `RELEASE_CHECKLIST.md`.

## Verified in disposable Firefox

- One add-on with the original `elf-shell-ayarime@local.theme` identity, the original new-tab dashboard, and the integrated AI Hub/sidebar; no second Workspace AI installation.
- The production **core-only** manifest is left unchanged by the assembler; the unified preview retains `theme`, `search`, and `storage` as its only required API permissions. `tabs` and `tabGroups` are runtime-optional. Firefox's UI may silently grant certain optional APIs such as `tabGroups`, so explicit consent copy must distinguish them from visible prompts.
- The AI module defaults off. Explicitly enabling it does not grant Firefox tab or Google account access. The background rejects new AI commands and streaming while disabled.
- Real Firefox Deny/Allow for the *native tab-permission doorhanger*, plus pinned Hub creation and reuse; no unintended Google tab restore.
- Real Firefox **RSS subscription** permission prompt from a real form-submit click, then actual browser-chrome Deny/Allow/Revoke. Deny leaves no host grant or subscription; Allow grants only `https://github.blog/*`; Revoke removes it while retaining the local feed metadata; subsequent refresh does not make a new feed fetch (issue #40, PR #53).
- Same-ID development replacement of the original core-only v0.5.6 build with the unified XPI, legacy v3 field/data continuity, v5 JSON backup import, rollback to the core, and a subsequent re-upgrade. AI remains disabled by default.
- Both independent source test suites, exact packaged-file checks and `web-ext lint --warnings-as-errors` run in CI; no browser profile or actual Google account was used.

**Evidence:** [combined passing CI run 43461803259](https://github.com/cryogenized-spec/elf-shell-ayarime/actions/runs/43461803259).
The Firefox permission regression fix and this report are on a development branch. An issue is not resolved in the *release branch* until its fix is merged and rerun there.

## Release blockers still open

**1. Final signed-to-signed migration and owner approval.** The publicly signed **v0.5.5** baseline has now been downloaded from AMO, verified for the exact version and add-on ID, and used in a clean Firefox migration/backup/rollback test against the unsigned unified preview ([passing run 43463780533](https://github.com/cryogenized-spec/elf-shell-ayarime/actions/runs/43463780533)). This establishes compatibility from the real *starting version*, but not the normal signed **update** process: the target is still a *temporary unsigned development add-on*. The final signed candidate must have a higher version, preserve the published add-on ID and extension-origin data, and be installed using the supported Firefox update path in a **backed-up disposable profile**. Do not install an unsigned same-ID preview over a person's actual profile. The owner must explicitly approve AMO signing/upload and the release.

**2. Review and reconcile source branches.** The unified XPI is still assembled from stacked, unmerged core and companion branches (including PRs #39, #41, #47, #49, #50, #51, #52 and #53; Workspace AI PRs #41–#46). Audit licensing, bundled assets and permission deltas, integrate only approved commits, and rerun every gate on the **exact final signing candidate**, not only a feature branch. Keep the original AMO package script distinct until that decision.

**3. Unified privacy and data-sharing notice.** The original core privacy document describes a local dashboard and opt-in RSS. The companion introduces **user-authorized external AI-provider communications**, local API credentials and optional Google account access. A unified public privacy statement, AMO data disclosure and an opt-in dialog must explain what is sent to **which third-party provider**, that model-provider transmission is not developer telemetry, where local API credentials live, and how consent/revocation/deletion work. The development manifest declares optional `authenticationInfo`, `personalCommunications`, `websiteContent`, and `personallyIdentifyingInfo`; confirm this exactly describes what can leave the device when modules are enabled. Do not publish with only the old core-locality statement.

**4. Browser privileges and origin policy.** The core deliberately allows optional `https://*/*` hosts for arbitrary user-selected RSS feeds; this is a declaration **not a grant**. Real access must remain per-publisher and separately approved; imported OPML cannot grant hosts. The bundled companion names multiple Google and BYOK API hosts; review each optional origin and outbound request flow. Preserve the restrictive local-script CSP, and evaluate the broad `connect-src https:` needed for user-selected RSS against the AI-provider boundary. `identity` and `alarms` **cannot be made ordinary optional Firefox API permissions** and are deliberately **absent** in the preview; Google OAuth and automatic release polling are disabled rather than silently added as required privileges.

**5. Live BYOK and Google acceptance.** Run controlled inference with explicit provider keys and verify streaming, cancellation, token limits, costs and redacted errors. Integrate Google Master MCP only after its OAuth audience/scopes/Cloudflare bindings are stable. An MCP-resource bearer token is **not** a Google access token; Google account linking is independent consent. Verify a dedicated test account, per-operation approval, origin allowlist, response bounds and visible disclosure before any Google result is supplied to an AI provider.

**6. End-user accessibility, layout and restart acceptance.** Manually inspect the Rose Seal, colour contrast, readable thinking summaries, panel resizing, keyboard navigation, reduced-motion fallback and screen-reader labels in Firefox on Linux Mint. Confirm behaviour after a full restart and after real permission revocation, with graceful offline/error states. Tests of temporary extensions do not fully replace the manual signed-upgrade check.

## Go/no-go rule

**NO-GO** until the operator approves the complete release permission/privacy story, the reviewed final branch passes native Firefox regression, the real signed AMO update path and rollback plan are validated, and the owner approves the upload. The Google work may be released later as opt-in functionality, but disabled/inert code must not be represented as working Google MCP integration.

Official references:
- Mozilla [optional API and host permissions](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/manifest.json/optional_permissions)
- Mozilla [permissions.request and user activation](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/API/permissions/request)
- Firefox [extension updating](https://extensionworkshop.com/documentation/manage/updating-your-extension/)
- Firefox [signing and distribution](https://extensionworkshop.com/documentation/publish/signing-and-distribution-overview/)
