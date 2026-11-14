# ELF//SHELL — user-owned Google Workspace / MCP

**Current developer-preview architecture (November 2026).** The old instructions for connecting directly to the developer's private `cryogenized.workers.dev` deployment are superseded. Do not publish a connector that defaults to the developer's Cloudflare resources or shares developer OAuth credentials.

## Open Station

In the unsigned integrated ELF//SHELL build, open a new tab and select the visible **STATION / SETTINGS** control beneath the ELF//SHELL heading. The panel slides in from the left. Use the **Station**, **Ayarime**, **MCP**, and **Settings** tabs. There is no second extension and no need to manually enter a `moz-extension://` URI or visit a separate scrolling setup page.

The Ayarime tab exposes the existing AI enable switch. The Settings tab provides short routes to browser permissions, appearance, RSS, and saved workspaces.

## Recommended: Google's official Workspace MCP

The MCP tab defaults to the official Google Workspace MCP directory. Google currently offers separate remotely hosted MCP servers for Gmail, Drive, Docs, Sheets, Calendar, etc. Google Workspace MCP is **Developer Preview**, not universally available. Users need their own Google Cloud project, OAuth client, and preview eligibility.

Google's authoritative setup guide: https://developers.google.com/workspace/guides/configure-mcp-servers

Selecting a service displays Google's documented MCP URL; it does **not** connect automatically or ask for a personal Google token.

## Advanced: deploy your own Google Master

Open-source infrastructure template: https://github.com/cryogenized-spec/Google-master-worker-MCP

Deploy your own Cloudflare Worker, OAuth issuer and Google Workspace integration using your own Cloudflare and Google accounts. Then open Station → MCP → **Self-hosted Google Master** and enter:

- Your exact `https://YOUR-MCP-HOST/mcp` resource
- Your `https://YOUR-OAUTH-HOST` issuer origin

Press **Save my endpoints locally**. This only saves non-secret URLs in Firefox local extension storage; it makes no HTTP request and cannot authorize Google access. The old developer-owned OAuth and MCP transport modules are explicitly absent from the new opt-in engineering XPI and background MASTER routes remain denied.

**Not yet implemented:** Generic OAuth discovery/client registration, live authentication and `tools/list` against arbitrary user-owned servers. This is the next acceptance milestone. Do not treat saved settings or an official directory link as a connected account.

## Privacy and release gates

No shared Cloudflare traffic, no shared Google data vault, no developer-managed OAuth keys for public users. Any later live connector must use a user-controlled OAuth client, per-origin Firefox permission, user-initiated read-only access, session-only tokens and explicit tool authorization. Write actions require their own approval. The published Firefox extension and existing private Cloudflare Worker are unchanged by the current engineering build.

See [MCP-USER-OWNED.md](MCP-USER-OWNED.md) for the architecture and acceptance requirements.
