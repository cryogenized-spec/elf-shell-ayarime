# Google Master Worker → Ayarime: read-only merger seam

**Status:** engineering preparation only. This does not authorize an account, deploy a Worker, obtain an OAuth token, execute Google APIs, or send document content to a model.

## Documented upstream contract

The Google Master Worker MCP repository's M10 client-API document describes a distinct, authenticated read-only JSON interface:

- `GET /v1/capabilities` yields `{"operations":[{"name":"...","description":"...","risk":"read"}]}`.
- `POST /v1/operations/{name}` takes a JSON object with at most **32 KiB** of UTF-8 request data, and returns `{"result": ...}`.
- Only a client-facing **MCP resource** bearer token authorized for `mcp:read` may be used. Google OAuth access/refresh tokens are never sent as that bearer token.
- Server authorization and CORS allowlisting are mandatory; a client extension ID is not enough. Google Workspace account linking is a second, independent consent boundary.
- The M10 baseline lists precisely seven read operations: `tasks_list_tasklists`, `tasks_list_tasks`, `tasks_get_task`, `script_get_project`, `script_get_content`, `script_list_versions`, and `script_list_deployments`.

The user is actively expanding the Worker's Google OAuth scopes and operations. Those future capabilities should be reviewed and approved **individually**, not silently enabled by a wildcard or inferred from descriptions.

## What this branch adds

The file `unified-preview/google-worker-contract.js` is an **inert**, reusable boundary. It validates a catalog of server-advertised capabilities against the current seven-operation read allowlist, rejects write-labelled/unknown entries, validates a prospective JSON argument object against the 32 KiB limit, and produces a human-reviewable plan containing the operation, product, request path, argument key names, expected scope and a clear `executionEnabled:false`.

This file is packaged in the *unsigned unified development preview* for inspection, but **is not imported into background scripts, included in page scripts, connected to the model, or given a network transport**. It cannot read account data, call the Worker, obtain or store OAuth credentials, discover new scopes, invoke mutations, or broaden the Firefox manifest. The existing no-Google-account execution guards remain intact.

## Future implementation gates

1. Verify the deployed Worker's actual versioned capabilities, server origin and resource audience once Google OAuth scopes and Cloudflare bindings stabilize.
2. Decide the Firefox `identity` permission strategy. Mozilla does not support treating it as an ordinary optional permission in this manifest, so user consent and AMO disclosures need explicit review.
3. Implement a secure, separately authenticated OAuth PKCE login and short-lived MCP-resource token handling in an **extension background service**, without putting refresh or Google tokens in UI pages.
4. Allowlist the exact installed `moz-extension://` origin on the Worker; no wildcard or copied browser installation UUID.
5. Add a visible per-operation **data-sharing preview** and require separate, user-initiated approval before any Google output becomes model input. Read-only operation access and permission to disclose content to an LLM are different.
6. Add bounded transport, abort, redacted errors, expected response schemas, and safe revocation/logout.
7. Run live acceptance against a dedicated test account. Only then wire this interface into the actual Ayarime conversation engine.

Until those gates pass, the Worker adapter is a compiled, testable contract **without a live connection**. Google Master OAuth work can continue independently of the ELF//SHELL merge.
