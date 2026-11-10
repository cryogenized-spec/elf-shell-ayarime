# Ayarime + Workspace AI — Firefox companion integration

## Intent

Keep one coherent Ayarime experience while preserving two independently installed modules:

- **ELF//SHELL — Ayarime** is the public, privacy-first new-tab workstation, artwork, Memory Trace, local notes, RSS, launcher, search palette and theme.
- **ELF//SHELL — Workspace AI** is an optional, currently unsigned developer companion with a Firefox-native sidebar, pinned Super Tab, BYOK inference and separately consented Google services.

The core extension must remain fully useful when Workspace AI is absent. Do not convert the core into a permission-heavy Google/AI extension or claim features that have not passed live acceptance.

## First integration — 0.5.6 development

- Station menu entry **✧ AYARIME · WORKSPACE AI**.
- Command palette entry for `> workspace` and exact spoken/written command **“Ayarime, please bring up my workspace.”**
- Explicit click triggers the existing v1 external messaging bridge via `browser.runtime.sendMessage("workspace-ai@elf-shell.local", payload)`.
- Probe via `HELLO` (protocol kind/version and capability check), then send only `OPEN_WORKSPACE`.
- Companion reuses a pinned Super Tab and existing Google tabs and keeps its own sidebar and all account/AI operations; the core receives only numeric opened/reused counts.
- Missing or incompatible companion produces a visible, nonfatal error without turning the command into a web search.
- No automatic startup requests, new core permissions, provider credentials, OAuth requests, source data, model prompts, or Google tool access.

### Firefox sidebar gesture boundary

Firefox requires a direct user gesture to call `sidebarAction.open()`. A cross-extension async bridge request is **not** a reliable substitute. Therefore, the Station command focuses/opens the companion's pinned Hub; the companion toolbar control opens its own native sidebar directly. The core must not claim it opened the companion sidebar.

## Seamless UX design plan

1. **One vocabulary**: Ayarime Station, Workspace, Tools, Models, Connections, Memory Trace. Share visual tokens (indigo/lavender/magenta, typography, borders) via reviewed source assets or coordinated design tokens—not remote CSS, iframe overlays or a duplicated chat engine.
2. **One identity**: Ayarime's default conversational personality lives in the companion; Professional and Custom modes are already configurable there. The core's offline Memory Trace remains independent from provider inference.
3. **One workspace handoff**: reuse a pinned hub and real Google tabs, dedupe by stable file ID, preserve profile names and keep documents in their own Firefox tabs.
4. **One explicit AI gateway**: companion alone owns BYOK provider credentials in session storage and Google consent. No silent copying of tabs, page contents, Gmail, files, prompts or notes between extensions.
5. **Shared Google platform later**: after Google-master-worker-MCP's OAuth and authenticated client transport are validated, add an optional companion adapter to the shared service for Ayarime/ChatGPT/CiRYVA interoperability; keep tab management local. Do not silently replace the working direct REST adapters.
6. **Native sidebar**: companion stays visible next to Firefox pages; the core dashboard is not forced to embed a web page or second chatbot.

## Future increments (separately reviewed)

- Integration diagnostics: visible Installed / Missing / Incompatible status, only on user interaction or an explicitly chosen check.
- Persona/visual consistency: versioned shared design tokens and no fictional model capabilities in the UI.
- Assistant entry: user-gesture-safe deep link or explicit handoff to a focused chat input in Hub (without bypassing sidebar gesture rules).
- Selective context: each Google record or browser page must be explicitly selected for model use; show the exact payload/source before a provider request. No automatic broad account ingestion.
- User-approved write actions (e.g. new task, email draft/send) only after OAuth scopes, policy, tool execution and human confirmation have been reviewed.
- Signed companion / AMO listing and user onboarding; core 0.5.5/0.5.6 stable releases must not be replaced without separate release acceptance.

## Verification

Run `npm test` and AMO package/lint on the core integration branch, and the companion's `npm test` plus dual-extension native Firefox test. Manually confirm: no companion / compatible companion / incompatible protocol; repeated launch creates no duplicate hub; toolbar independently opens sidebar; neither AI nor Google network activity starts on a new tab without user action.

## Next slice — Ask Ayarime (developer preview)

The Station now has two separate options: **AYARIME · WORKSPACE AI** (restore/reuse Google tabs), and **ASK AYARIME · AI CONSOLE** (focus the companion's existing BYOK prompt). Ctrl+K matches `> ask` and the explicit text `Ask Ayarime`; neither sends user query text to the companion. The core sends an allowlisted, versioned `HELLO` followed by `OPEN_ASSISTANT` only when the upgraded companion advertises that capability. Older versions receive clear update guidance. The companion's Hub handles its own constant `#assistant` focus route. No sidebar-opening claims and no automatic model/provider requests.

### Coordinated companion
Companion implementation: `cryogenized-spec/elf-shell-workspace-ai`, branch `feature/assistant-console-handoff-014`. This Station PR is intentionally based on `feature/workspace-ai-integration-056`; it does not replace the original v0.5.5 or authorize publication. Verify the staged branches together in actual Firefox before merging any of them.
