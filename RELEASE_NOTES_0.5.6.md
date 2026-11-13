# ELF//SHELL — Ayarime v0.5.6 — unified unsigned release candidate

**Status: prepared for owner review, NOT published or signed.** The existing signed AMO v0.5.5 is unchanged. GitHub Actions prepares reproducible *unsigned* Firefox runtime, XPI and reviewer-source archives; no AMO upload, signature, Google Master MCP activation or external account automation is performed.

## Firefox improvements and integrated interface

- The six-state pointer / I-beam / busy / crosshair / resize / link cursor gallery previews each cursor even with System Default selected. Previewing never saves a selection or modifies system cursors (forward-ported in PR #56).
- **+ SUBSCRIBE TO TRANSMISSIONS** asks Firefox for per-host RSS access in an explicit click and subscribes only after approval; refusal never authorizes a fetch. Drafts are preserved, with no first-run network opt-in (forward-ported in PR #57).
- Unified Workspace Hub and native Firefox sidebar open inside the existing add-on ID. Station AI remains default **OFF**; tab access, provider data collection and API credentials are separate explicit permissions.
- Sidebar provider settings are collapsed for a chat-first layout. Browser keyboard focus, 1366px / 390px / 320px responsive geometry, local session transcript/clear, reduced-motion Rose Seal and core upgrade migration passed native Firefox tests in PR #59.
- An API key lives only in Firefox session storage; turning AI off clears that session credential before saving OFF, and a background guard aborts active streams. Provider/model preferences do not constitute permission to call a provider.
- Conversation transcript is session-only and not encrypted. Prior exchanges are included in model context only when explicitly requested for one prompt. Provider inference may incur charges; chosen prompts, persona and opt-in context go directly to the selected third-party provider.
- **No Google Master MCP, Google account OAuth, Morning Coffee or automatic update checks** in this candidate. Those routes are blocked and UI is hidden until a separate reviewed release.

## Release-candidate artifact and security gate

Build the unsigned candidate with `python3 scripts/package_unified_rc.py --companion workspace-ai` using pinned Workspace AI commit `3a586bcce19a6e66bf924521d54fefc732faffb3` and the reviewed core commit. The verify-only GitHub workflow validates both test suites, Mozilla lint, reproducible source and runtime archives, native Firefox opt-in/revocation/UI tests, signed-v0.5.5 baseline to **unsigned-v0.5.6** migration/rollback, and privacy disclosures.

Mozilla's optional BYOK data collection categories are `authenticationInfo`, `personalCommunications`, `websiteContent` and `personallyIdentifyingInfo`. Required data collection remains `none`; required extension permissions remain `theme`, `search`, `storage`, and the Gecko ID stays `elf-shell-ayarime@local.theme`.

See `PRIVACY.md`, `docs/RC_ACCEPTANCE_0.5.6.md` and `amo/listing-metadata-v0.5.6-draft.json`. Before an approved public listed update, the owner must inspect the Firefox candidate and authorize controlled **live BYOK** tests using their own local API key. CI does not hold a real provider key, so it cannot certify live inference, provider billing or production stability. A real **signed v0.5.5 → signed v0.5.6** upgrade test can only follow Mozilla signing, which has **not** been requested.

The previous AMO workflow refuses 0.5.6+ to prevent accidental submission of the old core-only package. A separately reviewed listed submission path will require explicit owner approval.
