# ELF//SHELL MCP architecture — user-owned by default

## Design decision (2026-11-14)

**One Firefox extension, one source repository, no shared tenant.** The Station drawer is visible on every ELF//SHELL new-tab page. Its **Station / Ayarime / MCP / Settings** tabs replace the obscure Station navigation and the need to locate a separate, scrolling configuration hub for routine setup. The existing Workspace Hub is retained as an engineering compatibility surface, but it is not the primary settings flow.

The **recommended** connection is the official Google Workspace remote MCP family (currently in Google Workspace Developer Preview). Google provides separate HTTPS endpoints for Gmail, Drive, Docs, Sheets, Calendar, and other services. Every end user must configure their own Google Cloud project and OAuth application, and meet Google preview eligibility. See https://developers.google.com/workspace/guides/configure-mcp-servers

The **advanced alternative** is deploying the open-source Google Master Worker in the user's own Cloudflare account. Reference infrastructure: https://github.com/cryogenized-spec/Google-master-worker-MCP . The user supplies their own MCP `https://.../mcp` URL and OAuth issuer. The extension must never silently use the developer's `cryogenized.workers.dev` Workers, Google accounts, OAuth clients, token vaults, or API quota.

## Current engineering implementation

- The visible Station button opens a left-side sliding drawer; Escape, outside click, Close and keyboard-accessible tab navigation work without opening another page.
- The Ayarime enable control mirrors the original persisted AI preference, preserving API-key clearance on disable and existing saved settings.
- The MCP tab defaults to Google's official service directory, with read-only endpoint suggestions and a direct official guide link. No remote MCP requests occur merely by visiting the tab.
- Advanced users may validate and store *their own* HTTPS MCP resource/issuer URLs in the extension's local Firefox storage. These are settings, **not authorization credentials**.
- The opt-in Google Master engineering build excludes the prior personal Cloudflare transport and OAuth JS modules and removes both personal Worker host permissions. The old background `MASTER_*` commands remain denied.
- A generic user-supplied OAuth client and Streamable HTTP connection is **not yet implemented or verified**. Local endpoint saving does not connect, register, authorize, list tools or read Workspace data. Do not label this as a completed functional BYOK connector.
- Published AMO packages and protected Google Master Workers are unchanged.

## Safe follow-up gates

1. Provide a **user-owned OAuth 2.0 client** setup experience: PKCE, exact issuer validation, scoped `mcp:read`, no developer/shared token, bounded responses, and session-only secrets. Official Google OAuth may require a product-specific client setup and Developer Preview access.
2. Connect only to the selected, explicitly approved HTTPS origin using an exact Firefox host grant; reject loopback, private destinations, embedded credentials, insecure schemes, unexpected redirects, and forbidden owner endpoints.
3. Require an explicit user gesture for OAuth, discovery and all tool calls. Keep read and write scopes separate, with tool-specific approvals.
4. Test a disposable Firefox profile against a **separately owned** test Google Cloud project and Worker tenant. Prove no calls to the developer's Cloudflare infrastructure, no automatic account reads, and that disconnect clears session secrets.
5. Release only after code, privacy, Mozilla permissions, OAuth/CORS and user-consent review. The historical private engineering connection is not a public default.

This architecture makes the source and deployment templates freely available without running any other user's traffic through the project's developer-owned service.
