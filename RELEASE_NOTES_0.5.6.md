# ELF//SHELL — Ayarime v0.5.6 (development; release-candidate preparation)

**Status:** The v0.5.6 branch is development-only. The integrated AI build is an **unsigned, separate engineering preview**, not the current AMO package. Do not upload or describe it as a publicly released v0.5.6 add-on. The signed, published v0.5.5 baseline is unchanged.

## Integrated Firefox improvements

- **Six-state cursor gallery previews:** Pointer, I-beam, busy, crosshair, resize, and link samples show their own hover examples even when the dashboard is set to *System Default*. Hovering does not save a choice. Custom cursors remain confined to the extension dashboard.
- **First-party Transmissions RSS:** The `+ SUBSCRIBE TO TRANSMISSIONS` button asks Firefox for the specific HTTPS host permission directly in a user gesture. Accepting subscribes and fetches the official feed; denying does neither. No first-run subscription, blanket host grant, or silent network fetch is added. Existing drafts and subscriptions are preserved.
- These were forward-ported to the integrated branch in **PR #56 and #57**, replacing earlier, unmerged PRs #37 and #38.

## Ayarime unified interface — unsigned preview only

- One extension ID and new-tab dashboard, with an integrated Workspace Hub and native Firefox sidebar.
- Ayarime AI remains **off by default**. Enabling it does not grant tab access, provider permission, a model API key, or Google account access.
- A locally bundled **Rose Seal** appears during active AI work; reduced-motion settings stop its animation.
- The Hub and sidebar provide explicit model/API-key controls, local Firefox-session conversation history, and per-request opt-in for including recent exchanges. Settings in the compact sidebar are tucked behind a disclosure; they are not a second account or separate storage system.
- Google Master MCP integration stays inert while OAuth/allowlists are reviewed. The preview's Google OAuth and automatic update requests are disabled.
- Assembly uses an exact pinned companion commit, with a separate unsigned XPI and reproducible source manifest. The core-only AMO packaging path is not silently replaced.

## Validation and remaining gates

Core Firefox validation and native temporary-extension smoke checks passed on development commit `64dd66deade7` (13 November 2026). The integrated Hub/sidebar accessibility, viewport, Rose Seal, conversation-state and reduced-motion acceptance suite is being reviewed in PR #59; record its final GitHub Actions result before describing it as passed.

Before publishing v0.5.6, review the final manifest and privacy disclosures, complete controlled BYOK acceptance without sharing secrets, verify real Firefox session/permission behaviours, validate signed v0.5.5-to-release-candidate upgrade and rollback, inspect screenshots in a disposable user profile, and obtain explicit owner approval for AMO upload and signing.

The Firefox ID must remain `elf-shell-ayarime@local.theme`; no Google connectivity is required for the initial optional-AI release.
