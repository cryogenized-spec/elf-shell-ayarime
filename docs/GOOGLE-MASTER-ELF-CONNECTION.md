# ELF//SHELL unified Ayarime → Google Master MCP
**Engineering preparation: optional unsigned build only. Not an AMO release.**

## No local tunnel or Git directory needed to operate

Our existing protected Cloudflare deployment **is** the remote endpoint. The
Firefox WebExtension runs on the laptop (or a compatible Firefox client); its
background script calls the secure Cloudflare API over HTTPS. It does not
launch `cloudflared`, bind a local port, require the source repository on the
device, or forward access tokens to an AI provider.

Pinned remote addresses:
- MCP Streamable HTTP resource: `https://google-master-mcp.cryogenized.workers.dev/mcp`
- Resource's typed HTTPS façade: `https://google-master-mcp.cryogenized.workers.dev/v1/capabilities` and `/v1/operations/{name}`
- OAuth issuer: `https://google-master-auth.cryogenized.workers.dev`
- Issuer discovery: `/.well-known/oauth-authorization-server`
- OAuth public client DCR: `/oauth/register`
- OAuth code/PKCE login: `/authorize`
- OAuth token exchange/revoke: `/oauth/token`, `/oauth/revoke`
- Google Workspace linking/secret vault stays in the independently protected
  `google-master-workspace-setup` Worker, not in the extension.

## Exact opt-in development build

The normal v0.5.6 unified preview and its signed/published release boundaries
remain unchanged: Google OAuth is intentionally disabled there.

For a **separate, unsigned engineering XPI** with the existing companion
Stage 6.1 OAuth and the remote MCP discovery control, run:

```bash
git clone https://github.com/cryogenized-spec/elf-shell-workspace-ai.git workspace-ai
git -C workspace-ai checkout 885157e3d7bfeba3d1a344068448c1f4782d3be0
python3 scripts/build_unified_preview.py --companion workspace-ai --enable-google-master
```

Output: `dist/ELF-SHELL-Ayarime-Google-Master-UNSIGNED.xpi`
with contents in `dist/unified-google-master-preview/`. The normal
`dist/unified-preview/` is kept separately.

The opt-in engineering manifest adds the **required** Firefox `identity`
permission because `browser.identity.launchWebAuthFlow` cannot be used
without it. It retains core extension ID and existing CSP, and asks for the
**exact two Worker hosts** and optional Firefox data-sharing permissions only
on the owner's *Allow private Worker host* click. No blanket install-time
Google host grant or Google API OAuth secret is added. User preference,
notes and public AMO artifacts are not modified.

## User-initiated connection flow

1. Install the opt-in unsigned build in an isolated Firefox development profile;
   never replace the publicly signed version for this experiment.
2. Open the integrated Workspace Hub → Google Master panel.
3. Click **Allow private Worker host** to ask Firefox for both exact hosts and
   relevant optional data access. Denial has no network/account effects.
4. Click **Connect read-only OAuth**. The existing companion client fetches
   pinned OAuth discovery, dynamically registers a *public* client, creates a
   state and PKCE S256 challenge, runs interactive Firefox identity login, then
   stores the short-lived MCP resource token in `browser.storage.session`.
   No copied ChatGPT token and no Google refresh token enters ELF.
5. Google Master M26's consent screen may also offer optional `mcp:write`.
   **Leave it unchecked in this engineering preview**: the Stage 6.1 Firefox
   client intentionally rejects unexpected write scope.
6. Use **Verify available read operations** to exercise the existing bounded
   `/v1/capabilities` adapter, which filters to 24 known read-only operations.
7. Use **Check protected remote MCP endpoint** to issue precisely one
   `tools/list` request over the real `/mcp` HTTPS transport. It reads only
   tool names/security metadata and reports read/write counts; no tools are
   called and no Google account content is fetched.
8. Click **Disconnect and forget session** to clear local OAuth state and
   request best-effort remote token revocation.

## Boundaries and acceptance still outstanding

The current engineering build is **read-only** and **manual**. This change
does not yet let Ayarime's AI model issue Google Tasks, Gmail or other
tool actions. Future tool execution requires reviewed per-tool allowlists,
explicit user intent, bounded tool parameters, and separate authenticated
write scope handling; the current AI/background model cannot bypass them.

Real native Firefox OAuth/DCR, token-exchange CORS, the exact Firefox
installation origin, and protected Cloudflare Worker host behavior still
need acceptance in a disposable profile. If a browser-origin allowlist is
necessary for the HTTP façade, add ONLY that profile's exact
`moz-extension://<uuid>` via a reviewed Worker configuration change; never
use `*` or a permissive proxy. No deployment or provider mutation is
performed by the engineering build.

Google Master is already exposed over HTTPS. **Do not create a new public
Cloudflare tunnel**, run a local unauthenticated bridge, or embed the Google
vault's access/refresh tokens in the Firefox extension.

## Validation

CI builds both default-off and opt-in engineering packages, checks the
original release invariants, runs synthetic OAuth and remote transport
regressions, confirms source/ZIP parity and applies Firefox extension lint.
The opt-in XPI is distributed only as a private developer artifact until a
real Firefox smoke check and further user approval.
