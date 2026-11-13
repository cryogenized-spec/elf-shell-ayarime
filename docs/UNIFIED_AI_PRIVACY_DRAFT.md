# Unified Ayarime — privacy and Firefox permission disclosure DRAFT

**FOR REVIEW, NOT PUBLICATION.** This document examines the current staged unified developer build, not the publicly signed v0.5.5 extension. The public core's `PRIVACY.md` remains unchanged until the new release's operation and permissions are approved.

## Current local-only features

ELF//SHELL's dashboard, note/focus editor, saved tabs, memory quotations, appearance preferences, and recovery lists remain stored in local Firefox extension storage. They are **not encrypted**. Saved addresses may contain private query strings and authentication tokens; exported JSON backup files need the same protection as other personal documents.

The existing core retains only `theme`, `search` and `storage` as required Firefox API permissions. RSS subscriptions still use a separate runtime browser permission for each publisher's HTTPS origin, plus a locally recorded approved feed URL. RSS requests go directly to the publisher with cookies and referrer omitted, not to a developer-controlled collection endpoint. History/bookmark and tab features remain runtime-optional.

## Optional AI module — what may be transmitted

The staged unified build starts with AI **off**. A user must enable it in the Station; that alone does **not** grant model-provider or Google account permissions. Real AI requests require separately granted provider host/data-sharing permissions and a user-entered BYOK credential.

Depending on the selected provider, requests may go directly to **OpenAI** (`api.openai.com`), **Anthropic** (`api.anthropic.com`) or **Google Gemini** (`generativelanguage.googleapis.com`). Requests include the user-entered prompt, the configured model, system/persona instructions, and the necessary provider authentication key as an HTTP header. **Only when the user enables bounded conversation context** may the request also include recent past conversation turns from the same model/provider; the default is not to silently forward the previous transcript. The OpenAI Responses implementation requests `store:false`, but each third-party model provider's own retention and privacy policies still govern what it receives.

The account holder, not the ELF//SHELL developer, is responsible for any provider account/API billing. The extension must not advertise provider 'complimentary' tokens as a guaranteed entitlement.

BYOK API credentials are held in Firefox's `browser.storage.session`, not saved in the normal exported ELF//SHELL settings file. The session-only transcript is likewise stored using `browser.storage.session`, with bounded history. Selected provider/model settings and some non-sensitive usage estimates can persist locally. Users must be able to clear the session credential and transcript independently. Turning AI off is not equivalent to deleting records already received by a third-party model service.

The OpenAI streaming UI may show genuine provider-exposed reasoning **summaries** and activity events. It must not represent these as raw private chain-of-thought, and it must never send arbitrary local tab/Google data simply because the model requests it.

## Google Master MCP — explicitly not connected

The unified preview **does not connect to Google Master MCP**. Its packaged read-operation contract is inert. Browser Google OAuth/account operations and automatic update checks are disabled. Merely enabling AI or restoring browser workspace tabs does not authorize Gmail, Drive, Docs, Sheets, Calendar or Tasks API access.

Future integration requires distinct, explicit user authorization for the MCP resource and the Google account's scopes, a reviewable read/write operation allowlist, secure credentials and revocation. Even an authorized **read-only** Google result must not be sent to an external model without a separate user-facing disclosure and approval.

## Mozilla add-on data declarations to review

The compiled preview currently declares **no required data collection** and lists these categories as optional in `browser_specific_settings.gecko.data_collection_permissions.optional`:

- `authenticationInfo` — a provider API key and/or authorized credentials accompany requests to their intended endpoints when the user activates the feature.
- `personalCommunications` — the user may type communication content into the AI assistant.
- `websiteContent` — a user may paste webpage text or explicitly authorize permitted content for provider processing.
- `personallyIdentifyingInfo` — text entered into prompts may contain identifying information.

These categories must be checked against the actual final network and UI capabilities before AMO submission. This is **data transmitted to user-selected third parties**, not an assertion of developer-run analytics. The public signed v0.5.5 core declares `required:["none"]` and lacks these AI features. Reusing its existing core-only privacy statement unchanged for the unified release would omit material information.

## Reviewer checklist

The final public privacy text and AMO listing must be accurate and approved by the owner. They should identify the provider destinations, what is shared, when/how the user opts in, location/duration of local key and conversation storage, deletion and revocation controls, and what external providers may retain. Validate privacy promises against a trace of **real, opt-in** provider and Google network requests in a disposable profile. Never put credentials or conversation text into CI logs or screenshots.

For now, no public privacy policy, Mozilla listing, installed extension or provider/account authorization has been changed.
