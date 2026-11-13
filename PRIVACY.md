# Privacy statement — ELF//SHELL — Ayarime

ELF//SHELL is a locally run Firefox new-tab dashboard and optional browser
theme. It has no developer-operated server and does not collect or transmit
analytics, telemetry, crash reports, or browsing history to the developer.
Runtime artwork, fonts, scripts and icons are bundled locally.

**There is no custom website spellchecker in this release.** The extension
does not inject content scripts into other sites, read typed words in
webpage editors or send text to an AI/spelling service. Firefox's own
native spelling checker remains the user's choice.

Firefox extension-local storage holds dashboard notes, focus, configuration,
launcher URLs, memory-quote preferences, subscriptions, locally cached
public feed headlines, and optionally named browser tab sets and duplicate
recovery URLs. It is **not encrypted**. URLs sometimes contain private
tokens and query parameters. JSON and OPML exports contain user-defined
settings/URLs and should be handled as potentially sensitive documents.
Bookmark and browsing-history APIs are used only when the user explicitly
requests the corresponding feature.

## Browser permissions

- Required: theme, search, storage. Firefox chrome tint and user-initiated
  searches use Mozilla's supported browser APIs.
- Optional: tabs, tabGroups (unified only), sessions, bookmarks, history for explicitly requested
  workspace utilities; these may be denied or revoked.
- Optional HTTPS host access (https://*/* declaration): **only** for
  user-chosen RSS/Atom publications. This is not an installation-time blanket
  grant. Each publisher requires explicit Firefox permission during
  subscription, plus a distinct stored record of approved feed URLs.
  Importing an OPML/JSON backup never grants RSS approval. Previously saved
  feeds may require a one-time reapproval.

The extension never sends a user's notes, saved tabs, locally stored
settings or editor text to a developer-controlled server. Search terms,
user-opened links and restored tabs naturally contact websites selected by
the user. Opt-in RSS requests go **directly** to approved publishers;
those hosts see ordinary connection metadata, including IP addresses.
RSS requests omit credentials and referrers and reject redirects.
Cached feed metadata contains titles, dates and URLs, not article bodies.

## v0.5.6 optional Ayarime AI (unified release candidate)

The unified extension includes an **optional BYOK (bring your own API key)**
assistant. AI is **off by default**. Enabling it does not automatically send
anything, connect a Google account, authorize a model provider, or grant Firefox
tab access. Browser tab/workspace access and AI-provider access require separate
user actions and Firefox permissions.

When you explicitly allow an AI provider, Firefox requests that provider's
HTTPS API host and the following **optional data collection** categories:
`authenticationInfo` (API credential), `personalCommunications` (chat
prompts), `websiteContent` (content you voluntarily paste into a prompt),
and `personallyIdentifyingInfo` (details you choose to include). These
categories are optional in the Firefox manifest; the required declaration
remains `none`. You can decline or later revoke consent through Firefox
**Add-ons → Permissions and data**. Without provider consent and a session
API key, the add-on must not make model inference requests.

After those separate approvals, selecting **Ask Ayarime** sends your written
prompt, selected local persona instructions, and an API credential directly
to the **selected** OpenAI, Anthropic or Google Gemini API endpoint. The
provider processes the content under its own terms, retention policies and
billing. OpenAI requests set `store:false`, which does **not** eliminate
all service-side retention. Web search is separately opted in per request
for supported OpenAI models and may incur provider charges. No model is
contacted simply by opening a Firefox tab or reading stored conversation
history. Neither ChatGPT Plus nor another consumer chat subscription
automatically supplies an API key.

Your selected provider/model and AI on/off state are in Firefox local storage.
The entered API key lives **only** in Firefox `storage.session`, which is
not an encrypted credential vault. It is never added to an export or saved in
extension-local persistent storage. **Forget session key** removes it on
request. The unified AI toggle also clears the session API key before turning
AI off; background handling aborts ongoing streamed requests when AI is
disabled, and rejects requests made while disabled. Clear conversation is
a separate explicit action, not the same as forgetting an API key.

Up to ten recent prompt/reply exchanges may be retained in Firefox
**session-only storage** for display across the Hub and native sidebar.
This content is **not encrypted**. Previous exchanges are never added
to a new model request unless the user separately selects the
**Include recent conversation** option for that request; that checkbox
resets after sending. Clearing history removes this session transcript.
Explicitly typed personal information can reach the chosen provider, so
do not enter information you are unwilling to share with it.

**Google account and Google Master MCP connections are not enabled in
the v0.5.6 candidate.** Its Google-account, Morning Coffee and update-check
interface is hidden; their background requests are blocked. There are no
automatic Gmail, Calendar, Docs, Sheets, Drive, or Tasks reads, and no
account data is silently included in model requests. The inert future
Google Worker contract is not an active transport.

No prompts, provider credentials, conversation transcripts, Google records,
browsing history or telemetry are routed to an ELF//SHELL-operated backend.
The project has no developer analytics. Optional RSS requests and user-chosen
browser searches still operate separately, as described below.

## Native Linux cursor package

The optional Ayarime Linux cursor archive is **not a Firefox extension
dependency** and contains no networking or spelling component. Its installer
copies locally compiled Xcursor theme files into the user's
~/.local/share/icons directory without sudo or automatically changing
the active cursor. It can be removed independently. Artwork licensing
is documented in ARTWORK_LICENSE.md.

## Mozilla data-collection disclosure

For the core-only extension, the required declaration is `none`.
For the **unified v0.5.6 candidate**, the required declaration remains
`none`, with the four optional BYOK data categories disclosed above.
This does not mean optional model requests avoid third-party processing:
user-approved model inference transmits the prompt and API credential
directly to the selected provider. It does mean no developer-controlled
analytics endpoint exists. Ordinary chosen searches and RSS requests also
contact their explicitly selected external websites.

## Optional local hardware readings

Hardware readings are **not developer analytics**. After the user clicks **ENABLE TELEMETRY**, Firefox requests optional `nativeMessaging` permission. A separately installed, read-only Linux companion reads available CPU/GPU temperatures, fan speed, memory usage and system load using Linux system interfaces or local `nvidia-smi`. It returns readings to the Firefox add-on only over native messaging (local standard input/output). The companion opens no network port, does not upload or persist readings, and exits after each request. The browser shows N/A for unsupported sensors. The optional permission is revocable and the companion is independently uninstallable. No readings are transmitted to the developer or used for analytics.

The illustrated story archive is bundled locally; it makes no network requests. An additional footer link opens https://chatgpt.com/ in a separate browser tab **only when selected by the user**. ELF//SHELL is not affiliated with OpenAI.
