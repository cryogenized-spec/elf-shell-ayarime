# Mozilla Add-ons automation for ELF//SHELL

## Distribution model

The existing Firefox extension was submitted as **unlisted** at AMO in version `0.5.4`, with the stable extension ID `elf-shell-ayarime@local.theme`. Updating it through the same unlisted channel keeps the same add-on identity. A public/listed release requires a separate channel decision.

Mozilla's current `web-ext` (v8+) supports the AMO v5 submission API for listed and unlisted versions. This workflow intentionally allows **unlisted** only.

## One-time private setup (human owner)

1. Sign in to the [Mozilla Add-ons Developer Hub](https://addons.mozilla.org/en-US/developers/).
2. Open [Manage API Keys](https://addons.mozilla.org/en-US/developers/addon/api/key/) and generate API credentials after any requested email confirmation. Do **not** paste the issuer or secret into ChatGPT, GitHub source code, issue comments, pull requests, or CI logs.
3. In GitHub repository Settings → Environments, create the environment **`mozilla-unlisted`**. Where supported, enable required reviewer approval to prevent an unreviewed submission.
4. Store the Mozilla credentials as **environment secrets**, with these exact names:
   - `AMO_JWT_ISSUER` = Mozilla JWT issuer / API key
   - `AMO_JWT_SECRET` = Mozilla JWT secret / API secret
5. Keep the credentials in GitHub Actions secret storage. The submission job uses the environment values as `WEB_EXT_API_KEY` and `WEB_EXT_API_SECRET` only at the signing step.

## For each update

1. Bump the extension's version in `manifest.json` and `package.json` to the same, **new** number; update the visual `V.XX.X` text in `newtab.html` and record release notes. Never reuse a version already submitted to AMO.
2. Merge the version change into an approved `release/` branch. Let the normal GitHub Actions tests run and resolve any failures.
3. Open [the AMO submission workflow](https://github.com/cryogenized-spec/elf-shell-ayarime/actions/workflows/amo-unlisted.yml) under Actions. Select the default-branch workflow, then **Run workflow** with:
   - `release_ref`: `release/v0.5.4-review` (or the active release branch)
   - `expected_version`: the exact committed version, initially `0.5.5`
   - `operation`: `verify-only` (safe default) to run all checks without contacting Mozilla.
4. For a successful candidate, launch the workflow with **`submit-unlisted`**. The verification job runs tests, real Firefox smoke checks, Mozilla lint and reproducible source/runtime packaging before the submission job begins.
5. If GitHub protected environments are configured, review/approve the `mozilla-unlisted` job. The job downloads the verified unsigned runtime and source archives and uses `web-ext@10.8.0 sign --channel unlisted --upload-source-code … --approval-timeout 0` to submit the update. No public/listed publication is possible from this workflow.
6. Inspect the status in the Mozilla Developer Hub. **Successful API upload does not mean Mozilla has finished review or signing.** A slow or rejected review is a separate event. Do not retry blindly after a timeout or conflict; check the version in AMO first.

## Automation boundaries

- **No automatic submission on push, merge, pull request or schedule.** A human explicitly chooses `submit-unlisted` in Actions.
- Workflow requires the original extension ID, unchanged Mozilla privacy declaration, consistent version metadata, and a release branch reference. New versions must exceed 0.5.4.
- No passwords, API keys or JWT values are stored in this repository. The GitHub environment may be configured to require an additional human approval before credentials become available.
- Current unlisted releases **do not update installed Firefox copies automatically** without a developer-hosted, HTTPS update manifest (`browser_specific_settings.gecko.update_url`) and a reliable source of signed XPIs. This is a separate future delivery feature; don't confuse upload automation with browser auto-update.
- The read-only native telemetry host is **not embedded or installed automatically** by the Firefox add-on. Users must independently install it and explicitly approve Firefox's nativeMessaging permission.

## Troubleshooting

If GitHub reports missing `AMO_JWT_ISSUER` or `AMO_JWT_SECRET`, create them in the `mozilla-unlisted` environment. If version validation fails, commit the next version to both `manifest.json` and `package.json`. If the AMO upload reports a duplicate version, inspect the Mozilla Developer Hub before attempting another run. The zipped source is already attached to the verified GitHub Actions run.

**Mozilla Developer Hub:** https://addons.mozilla.org/en-US/developers/

**Mozilla web-ext reference:** https://extensionworkshop.com/documentation/develop/web-ext-command-reference/

**Mozilla self-distribution:** https://extensionworkshop.com/documentation/publish/self-distribution/
