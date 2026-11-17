# ELF//SHELL + Ayarime — canonical monorepo

**Source of truth:** `cryogenized-spec/elf-shell-ayarime`. The Ayarime companion has been integrated as ordinary tracked source under `assistant/`, rather than copied at build time from a second GitHub repository.

## Repository layout

| Path | Purpose |
|---|---|
| `newtab.html`, `newtab.js`, `background.js`, `styles.css` | ELF//SHELL core workstation |
| `assistant/ai/`, `assistant/google/`, `assistant/shared/` | Ayarime AI engine, Google Master MCP integration, authorization and workspace logic |
| `assistant/hub.html`, `assistant/sidebar.html`, `assistant/ui.js` | Ayarime's integrated sidebar and Hub sources |
| `assistant/tests/` | Modular assistant regression tests |
| `assistant/mcp/` | Legacy auxiliary MCP source, retained separately from the central Google Master Worker service |
| `scripts/build_unified_preview.py` | **Local-only** source assembly into one development XPI |
| `scripts/package_unified_rc.py` | Deterministic, reviewable unified unsigned release-candidate XPI and source archive |
| `.github/workflows/unified-rc.yml` | Canonical unsigned release-candidate verification pipeline, including reproducibility, Mozilla lint, Firefox migration/rollback |
| `.github/workflows/unified-preview.yml` | Development validation and unsigned engineering preview |
| `.github/workflows/signed-baseline-acceptance.yml` | Additional regression against historical signed Mozilla v0.5.5 |
| `assistant/SOURCE_LOCK.json` | Historical migration snapshot mapping original Git blob hashes and exact imported commit; **not** a future development version freeze |

All three workflows execute entirely from the **same** repository checkout. CI can still download a *historical signed Mozilla add-on* for upgrade comparison, but it never checks out or builds from the old companion repository. The Google Master Cloudflare Worker is an **external service**, not a second copy of the Ayarime extension source.

## Build and tests (from the repository root)

```sh
npm test
(cd assistant && npm test)
python3 scripts/build_unified_preview.py
python3 scripts/package_unified_rc.py
```

These commands require no second `git clone`, `--companion` flag, remote source checkout, copied OAuth token, or independent Ayarime repository. The full integrated runtime remains one Firefox extension with the established ID `elf-shell-ayarime@local.theme`. The original public AMO build and its required permissions are unchanged; an unsigned candidate is not a published add-on.

## Maintenance and issue tracking

- File new ELF//SHELL, Ayarime, Google Master Firefox-client, interface, packaging and regression issues in **this repository's Issues**. Use subsystem names in titles (e.g. `Ayarime:`), and references to original historical issues where needed.
- Update `assistant/` **in place**. Do not copy commits from the original companion repository or force all changes to reproduce the import-time snapshot. `SOURCE_LOCK.json` documents provenance, not code-locking.
- Add/modify tests under `assistant/tests/` for AI/Google changes and under `tests/` for single-extension integration. The unified preview CI runs both suites.
- Do not create a second independent release pipeline. `unified-rc.yml` is the one release-candidate packaging gate; the other jobs provide validation only. Publishing to AMO requires a separately approved, appropriately versioned release and signing.
- Keep the original `cryogenized-spec/elf-shell-workspace-ai` Git history and existing links readable. Once source/import, issue migration, and CI parity are verified, mark it **archived/read-only** in GitHub Settings (requires repository administration permission). Do not delete it.

## Security and Google Master MCP

Ayarime's Google Master client and OAuth code are in `assistant/google/`. The ordinary v0.5.6 unified preview and RC intentionally block Google authorization and automatic data access; the optional engineering-only preview exists for scoped testing. A verified ChatGPT-to-MCP connection does **not** authenticate Firefox or authorize automatic Google reads. Never reuse ChatGPT MCP bearer tokens in a Firefox build; use the separate Firefox PKCE client with exact Worker host/origin permissions.

## Migration provenance

Imported `95` source files from `cryogenized-spec/elf-shell-workspace-ai` at `885157e3d7bfeba3d1a344068448c1f4782d3be0` and recorded exact SHA-1 Git blob hashes in `assistant/SOURCE_LOCK.json`. Excluded only four duplicated GitHub Actions workflows; the new canonical repository owns CI. The initial copy preserved the file bytes exactly, and source packaging now includes each source file just once.

**Completion boundary:** This code consolidation is a source/build restructuring. It is not by itself authorization to publish a signed extension, silently increase Firefox install-time permissions, connect a Google account, write to Google Workspace, or change the protected Cloudflare Worker.
