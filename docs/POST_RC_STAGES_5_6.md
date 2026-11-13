# Post-v0.5.6 — Ayarime Stages 5 and 6 engineering preview

This is a **separate experimental development preview**, not a signed release, update or replacement for the already verified v0.5.6 unified RC. The existing `release/v0.5.6-development` branch and its PR #60 release evidence remain the reference until separately approved.

## 5 · Personas and BYOK model requests

The Ayarime/Professional/Custom personas stay local style instructions and cannot authorize tools. The integrated companion now sets a 30-second timeout and 256 KiB response-size cap for one-shot OpenAI/Anthropic/Gemini calls, and retains direct provider HTTPS, session-only keys, bounded prompts and no automatic Google forwarding. Anthropic/Gemini have a visible Stop request button, real AbortController cancellation and only one in-flight one-shot prompt per Firefox extension. The user can stop a request without queuing cancellation behind it; clearing the session key aborts it.

The existing OpenAI streaming trace and cancellation remain separate. Existing conversation history continues to require per-prompt explicit context consent. These controls do not replace real low-budget, locally owned API-key and provider-billing acceptance.

## 6 · Google Master Worker read-only client

The companion now bundles `google/master-read-client.js`: a transport-only module with the **exact operator-owned protected MCP resource origin** and 24 hardcoded M21 read operations. It does not expose the M23 write/prepare catalogue. Each read requires a user-approval callback, exact Firefox optional host permission and an independently acquired short-lived **MCP OAuth** bearer. It never receives the Google D1 vault refresh/access token and neither stores, logs nor refreshes any credentials. Capability metadata cannot grant new operations not hardcoded in the client.

**Deliberately not connected:** The Google Master module is loaded in the background but has no callable Firefox runtime message, sign-in UI, automatic fetch, provider tool capability or scheduled polling. The original Google OAuth/account and auto-update routes remain blocked by the unified-preview adapter. Google account data is never sent to an AI model by this change.

To actually enable Google Master in a later release, build a Firefox-specific OAuth authorization-code/PKCE session flow, register the exact installed `moz-extension://...` browser origin in Cloudflare's CORS allowlist, verify login/expiry/logout/consent, require separately linked Google vault data, and limit Google scopes appropriately. **Do not copy a ChatGPT MCP bearer into the browser or embed a Google client secret.** Broad Gmail/Drive access has restricted-scope Google verification obligations.

## QA and release boundaries

`tests/stage5_6_preview_test.py` verifies the unified build still has the original `elf-shell-ayarime@local.theme` ID, no expanded required install-time permissions, the new explicit cancellation route, and an inert Google Master client with zero write methods. The companion tests cover cancellation, privacy redaction, 24 allowed reads and negative approvals. The native Firefox suites and Mozilla lint also run on the pinned companion source.

This branch has no Mozilla upload, deployment, Cloudflare update, real Google content retrieval, paid BYOK call, account migration or stable `main` merge. Keep the v0.5.6 release candidate separate unless a future approved release explicitly incorporates these post-RC changes.
