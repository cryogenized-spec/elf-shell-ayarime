# ELF//SHELL / Mozilla PUBLIC listing — deployment runbook

**Owner decision:** switch from self-distributed (unlisted) to a publicly listed Firefox Add-ons extension immediately, authorised on 7 November 2026.

## How the channel conversion works

The existing unlisted version 0.5.4 cannot itself be reclassified. Instead, upload **a NEW version** of the **existing** add-on ID `elf-shell-ayarime@local.theme`, selecting `On this site (listed)`. Do **not** choose Submit New Add-on: Mozilla will reject a duplicate GUID. The first public release candidate is version `0.5.5`, provided that version has not already been uploaded to Mozilla.

Mozilla staff confirmed this workflow in August 2026: https://discourse.mozilla.org/t/help-me-change-my-addon-from-private-to-public/149165
The current `web-ext` signing reference documents `--channel listed`, `--amo-metadata` and `--upload-source-code`: https://extensionworkshop.com/documentation/develop/web-ext-command-reference/

## Current code

- Public release workflow: `.github/workflows/amo-listed.yml`, in default branch `main`; the older `amo-unlisted.yml` workflow was retired.
- Public listing metadata and reviewer notes: `amo/listing-metadata.json`.
- Proposed customer-facing description: `amo/LISTING_COPY.md`.
- Canonical release source: `release/v0.5.4-review`, manifest and package version 0.5.5; stable extension GUID unchanged.
- All code and artwork are packaged from clean Git-tracked files and validated with `npm test`, strict `web-ext lint`, source-rebuild checks and Firefox smoke tests.

## One-time GitHub configuration

In [repo Settings → Environments](https://github.com/cryogenized-spec/elf-shell-ayarime/settings/environments), create `mozilla-listed` with required review if supported. Add the private secrets `AMO_JWT_ISSUER` and `AMO_JWT_SECRET` from the [Mozilla Developer Hub API keys page](https://addons.mozilla.org/en-US/developers/addon/api/key/). **Never put secret values into a chat, PR, GitHub file or logs.** They may already be stored in the old `mozilla-unlisted` environment; copy them using GitHub's secret-input UI into the new listed environment. They are not readable from repository source.

## To submit

1. Check the existing add-on in the [Developer Hub](https://addons.mozilla.org/en-US/developers/addons). Confirm v0.5.5 has NOT already been submitted. If it has, use a strictly higher version in source first.
2. Review the listing copy, privacy statement, attribution, real screenshots and Mozilla Add-on policies.
3. Open [Mozilla AMO — verify and submit PUBLIC listing](https://github.com/cryogenized-spec/elf-shell-ayarime/actions/workflows/amo-listed.yml) under Actions, select **Run workflow**, `release_ref = release/v0.5.4-review`, `expected_version = 0.5.5`, `operation = verify-only`.
4. Once verification passes, run again choosing `submit-listed`. Only this explicit action exposes secrets to the `mozilla-listed` job and attempts submission via `web-ext@10.8.0 sign --channel listed --amo-metadata dist/amo-listing-metadata.json --upload-source-code <source ZIP> --approval-timeout 0`.
5. **First listed conversion caveat:** if AMO refuses the API transition or indicates missing add-on-level metadata, open the **existing add-on** → **Upload New Version** → **On this site**, then complete listing details and upload that same 0.5.5 verified runtime ZIP and source ZIP from the Actions artifacts. Do not create a new add-on or blindly retry an accepted upload. Mozilla reviews the listed version before public availability.
6. In Developer Hub, verify whether the listed version is pending, accepted, signed and publicly accessible. No GitHub CI result proves Mozilla approval by itself.

## Updates after public listing

For subsequent listed versions, bump `manifest.json` + `package.json` and update release notes, run tests and submit with `submit-listed` when desired. Approved AMO-listed add-ons normally receive Firefox-managed updates. We no longer need an independent unlisted-XPI update host for the public channel. RSS announcements remain separate and cannot publish a Mozilla release.

## Privacy and third-party dependencies

Browser notes/workspaces are stored locally and not encrypted. RSS network access is explicitly opt-in. The Linux hardware sensor bridge requires a separately installed native-messaging host and explicit Firefox permission. The extension does not collect or upload hardware metrics. No service-provider affiliation is implied by optional website links. Full disclosures are in `PRIVACY.md` and `ARTWORK_LICENSE.md`.

## Publication status

**Public channel requested and source prepared; DO NOT claim the listing is live until the Mozilla Developer Hub confirms acceptance.** No API issuer or secret is stored in GitHub files. The owner authorised publication, not bypassing Mozilla review.
