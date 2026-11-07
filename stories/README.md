# Illustrated Memory Archive — Ayarime Side Stories

> **GitHub source integration approved 7 November 2026; Mozilla publication still requires separate approval.**
> See [Human approval record](DO_NOT_MERGE_UNTIL_HUMAN_APPROVAL.md).

## Stories

### 01. Letters from the Lower City — seven slivers

A contemplative night through Beralia-01's ruined postal district, ending
with a small joke about the misplaced GitHub `sudo` code. Intended as two
connected 16:9 compositions: four narrow portrait slivers, then three.

- 01 — Her right hand traces the rusted postal compartments.
- 02 — Beralia-01 from a guarded overlook: *the blighted vale, land of the survivors*.
- 03 — The cat appears: *Meow.*
- 04 — They continue through a shaft of light; reflection on the tragedy of the commons.
- 05 — Distant silhouette: *Law and Order, Crime and Punishment, Ignorance and Aversion*.
- 06 — She retrieves surviving correspondence: *Though destroyed, the upstream fed the downstream regardless.*
- 07 — She searches the letters: *ah.. Where is the sudo?*

### 02. Crushed Rainforest Beans — twelve slivers

Three sequential 16:9 compositions, each containing **four tall vertical slivers**:

- **01–04: the coffee and phantasmagoria.** Brewing; tasting; euphoric eyes close;
  iridescent bubbles ascend and disperse as `grep, grep, grep` gives way to
  `I, the Pipedream` and the unfinished pipe `grep |`.
- **05–08: the cat concatenates, and memories emerge.** Cat's `Meow` signifies
  `cat` (concatenation), after `grep |`. Images of fear, a woman approached,
  her dissociated aftermath, and a frightened man cornered by snarling dogs.
  The figures might be **residual local memories**, not contemporaneous events.
  Ayarime is a detached observer of broader causal formations, not a partisan
  arbiter or executioner.
- **09–12: the judgment and return.** The young man is led before Yama by two
  Yakshas; Yama judges him in solemn Japanese; a great fire appears; the scene
  returns to Ayarime quietly drinking coffee beside the sleeping cat.

The caption **“Grasping. Craving. Attachment. I am this.”** denotes both
self-identification through grasping and conditioned karmic formations.
It is not a claim that the woman deserved harm or that Ayarime participated
in the events. Consequences may be revealed out of chronological order.

## Artwork and presentation contract

- Preserve the approved art **unchanged**, including hair and headgear
  continuity, burgundy cloak, pointed ears, cat and 1990s hand-drawn OVA look.
- Four slender portrait panels across each 16:9 master for *Crushed Rainforest Beans*.
  *Letters from the Lower City* uses one 4-panel and one 3-panel master.
- Thin technical frames, small `NN / AYR` upper-corner identifiers.
- **Always use the approved bottom caption block:** dark semi-opaque rectangle,
  delicate thin outline, modest off-white monospaced/serif text, **Japanese above
  English**, no speech-bubble pointer or unrelated decorative subtitles.
- Neither cover imagery nor the runtime may interrupt the existing six shortcut
  launch actions. The archive is a separate opt-in exploratory view.
- Intended asset loading is entirely offline. No network telemetry, no external
  services, and no new permissions.

## Asset staging

All five original PNG masters were imported byte-for-byte and committed to
the feature branch on 6 November 2026, commit `c2d501b`. Before committing,
the user verified all five files against the SHA-256 values in
`asset-manifest.json`; GitHub subsequently confirmed all five paths
in pull request #22.

The original source art must not be regenerated, recropped, or replaced with
remote image URLs. Before approving integration, review captions in both
languages and inspect image scaling, offline loading, and packaging in Firefox.

## Implemented reader (PR #22)

The archive is now a standalone offline Firefox extension page at
`stories/archive.html`, with bundled `archive.css` and `archive.js`.
The native 1672×941 PNGs are used directly from `stories/assets/`;
no external image provider or runtime permission is involved.

It follows the approved desktop composition: story index on the left,
large original four- or three-sliver spread in the centre, adjacent record
inspector, selectable sequence thumbnails and an expandable image modal.
Responsive breakpoints collapse the inspector and stack the panels on
narrower displays, preserving image aspect ratio and original captions.

Reach it from Memory Trace, the `✧ STATION` menu, or Ctrl+K by searching
for “illustrated”. All links open the reader in a separate extension tab,
so the original six quick links remain unchanged.

Keyboard: **Left / Right** changes spreads; **Escape** closes the native
expanded-art dialog. The optional `#letters/0` or `#beans/2` fragment
identifies a selected spread and can be shared inside the same Firefox profile.

The build's strict whitelist includes the three reader files and
**only the five reviewed original PNG masters**. The stories themselves require
no new permissions. The separate opt-in local telemetry feature adds only the
optional `nativeMessaging` permission; existing shortcut URLs are unchanged.

### Acceptance checks

- Node suite: `npm test` (includes `tests/illustrated_archive.cjs`).
- Package integrity: `python3 scripts/package.py` followed by
  `python3 scripts/package.py --verify-only` (local validation only;
  do not submit the ZIP to Mozilla).
- Live Firefox: load the draft branch temporarily, select both story
  volumes, test each spread, inspect full-size bilingual artwork, close
  with Esc, use Ctrl+K and confirm all six existing shortcut links.
- Check mobile/tablet reflow, font fallback, keyboard focus, zoom and
  remote/network requests in Firefox Developer Tools.
- The five original PNGs were checked against their SHA-256 manifest
  before the user committed them to the branch.

## Status

**Source merge authorised by the human owner on 7 November 2026.**
The original images remain unchanged. Publication or signing through Mozilla
requires separate approval and real Firefox release verification.
