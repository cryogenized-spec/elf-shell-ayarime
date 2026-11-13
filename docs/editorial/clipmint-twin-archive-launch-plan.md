# Transmission 004 — The Twin Archive
## Joint launch story, storyboard and release design brief — DRAFT, 13 November 2026

**Editorial working title:** *The Twin Archive — A Story of Two Workshops*  
**Public-facing release headline (provisional):** *ClipMint arrives on Linux Mint and Windows x64*  
**Publication location:** ELF//SHELL — Ayarime Transmission Log (existing RSS 2.0 site, issue/dispatch 004)  
**Public status:** NOT PUBLISHED. This is the design-and-story plan for a **simultaneous public release**, not a claim that both editions have already been launched.

### Premise and tone

In a rain-soaked human enclave of Ayarime's retro-futurist Lower City, small records are lost every day: copied scraps, photographs, workshop measurements, and fragments caught between machines. Ayarime discovers a rose-gold archive device that can retain them. Two neighbouring workshops, each with different tools and conventions, develop **two independent versions** of the same idea. Their creations pass through separate inspections; neither workshop announces victory before the other is ready. On release day, two doors open together.

This is an **allegory**, not a technical claim about automatic synchronisation, shared storage, cross-OS binary portability, or an AI inside ClipMint.

The prose should feel like a 1990s OVA scene, not software advertising: atmospheric, curious, tactile, economical. The product facts appear in a separate, plainly written release dossier. No fabricated release metrics, security claims or customer quotes.

### Eight illustrated narrative plates

Each plate has an independent narrative beat. The existing static page can illustrate them with original CSS-only art while full illustrated panels await approval. Do **not** reuse Linux-edition Crimson Maid or Kohaku art until redistribution rights are resolved.

| Plate | Working title | Visual / composition | Narrative beat and proposed one-line caption |
| --- | --- | --- | --- |
| 01 | Rain on the Lower City | Wide evening establishing shot; wet cobblestones, tram cables, street stalls, rust-coloured neon, blurred human silhouettes | “The city forgot the little things first.” |
| 02 | A Slip of Rose Gold | Ayarime's hand retrieves a luminous red folio near a workshop counter, dust and tiny paper slips suspended in light | “Something was keeping the fragments.” |
| 03 | The Crimson Archive | Close-up of rose-and-gold mechanical petals opening around ordered strips of data; no real product UI compositing | “A place for what would otherwise be lost.” |
| 04 | The Fork in the Passage | Two opposite workshop doors seen from a corridor, left green/copper, right midnight-blue/gold; shared crimson line splits cleanly | “One idea. Two different machines.” |
| 05 | The Mint Workshop | Warm green Linux Mint desk, X11 screen silhouettes, ledger pages, native package stamp; no proprietary logo needed | “The first archive knows its own home.” |
| 06 | The Windows Workshop | Cooler indigo workstation, geometric four-pane window, portable archive casing, technical inspection lights | “The second is built anew, on its own terms.” |
| 07 | Separate Inspections | Two independent tables, checklists and seals. The Windows table still needs real-desktop acceptance; Linux needs its own release gates, including image redistribution rights | “Neither seal is awarded in advance.” |
| 08 | Two Doors at Dawn | Wide final frame: doors opening simultaneously onto the same rainy passage; a separate illuminated archive rests within each room | “When both are ready, the doors open together.” |

**Character/art direction:** Ayarime can be glimpsed as the observing she-sage but avoid claiming any pictured person/character asset is cleared for release. Original commission or newly generated images require separate review of provenance and content. No deceptive fake screenshots or fake Windows trust badges.

### Composition and visual system

- **Format:** 8 plates organised as two sequences of 4, matching the established ELF//SHELL sliver tradition. Proposed artwork master: a 16:9 sheet per set of four panels (four equal-width vertical slivers) with preserved boundaries. A separate single hero panorama may later be commissioned, but the site should function and read beautifully without raster illustrations.
- **Palette:** deep ink #101720; warm paper #efe4d1; crimson #a9425b; dark rose #512c3e; old gold #d6b183. *Linux Mint track:* muted jade/verdigris #91c6ad. *Windows track:* midnight slate blue #94a9d3. Never use vendor-brand colour as a claim of endorsement.
- **Editorial type:** expressive book-serif headings + restrained system monospace labels and small technical metadata. No network fonts.
- **Hero:** hinged dual-window arch, two independent chambers connected **only by a drawn red thread of common purpose**, never by a data cable. The metaphor must not imply clipboard sync.
- **Page rhythm:** dramatic opening → eight compact scenes (tactile CSS artwork now; genuine story slivers only after approval) → paired platform cards → release verification and known limitations → unified launch links.
- **Accessibility:** meaningful text outside visual art; each illustrated asset will need specific alt text. Strong contrast, real heading hierarchy, focus-visible links, responsive single column below 780px, reduced-motion support, no JS or trackers.
- **Public URLs:** single canonical Transmission 004 permalink and stable RSS GUID. Never swap the GUID after publication. The draft may change its permalink before publication because nothing is live yet.

### Product truth / copy restrictions

**Linux Mint edition:** independently maintained at https://github.com/cryogenized-spec/clipmint-linux. Public *preview* packages exist, but the final public-beta gate is still open. A release must verify the exact final .deb, installer/uninstaller behaviour, physical Mint Cinnamon/X11 acceptance, and illustration redistribution rights or replacement. The existing upstream rights issue: https://github.com/cryogenized-spec/clipmint-linux/issues/95. Current release acceptance task: https://github.com/cryogenized-spec/clipmint-linux/issues/96.

**Windows x64 edition:** independently maintained at https://github.com/cryogenized-spec/clipmint-windows. Developer-alpha CI run https://github.com/cryogenized-spec/clipmint-windows/actions/runs/43473029848 passed 32 tests and created a complete offline ZIP with Python, Qt and FFmpeg. It has an **untrusted self-signed Authenticode development signature** and **GitHub-signed provenance**. There is no permanent release entry yet; a GitHub Actions artifact expires. Physical Windows 11 field acceptance remains open at https://github.com/cryogenized-spec/clipmint-windows/issues/1.

**Shared:** two **separate** repositories, separate settings and local clip histories; no promise of direct data sync, parity, cross-platform installer, automatic migration, cloud backup or Microsoft-trusted publisher status. ClipMint Windows local history is currently **plaintext** by default. Avoid attributing Linux-only functionality to Windows.

### Coordinated release policy

1. Freeze each edition's scope and land its separate release gates; name the exact final Linux and Windows commits/tags.
2. Obtain or replace any illustration assets lacking clearly documented redistribution rights. The editorial CSS artwork requires no such bundled user-image permissions.
3. Verify Linux .deb and Windows portable ZIP (and their accompanying checksums/provenance) *on their exact release commits*, including physical desktop testing.
4. Prepare one permanent GitHub Release or equivalent non-expiring download destination **for each** edition; never put an expiring Actions artifact in a launch-day permanent download button.
5. Assemble one release dossier for the paired launch: 2 version names, 2 release links, 2 exact checksums, source links, support matrix, known limitations, license/asset notices and field-acceptance results.
6. Agree on a single launch date/time in **SAST (UTC+02:00)**; freeze and test both assets before that time. Mark either release as pending if one is blocked; **do not promote only one edition as the joint launch**.
7. Update the draft RSS `published` timestamp only when actual publishing is authorised. Verify static-site CI, merge the editorial PR, then confirm the GitHub Pages deployment and public RSS entry.
8. No overclaim of 'beta', 'signed/trusted publisher', 'secure vault' or 'feature parity' beyond independent verifiable evidence.

### Publication state and checkpoints

- [x] Independent Linux and Windows repositories identified.
- [x] Windows x64 development-signed alpha / GitHub provenance build verified.
- [x] Linux public preview release availability verified.
- [x] Coordinated launch narrative and visual treatment drafted.
- [ ] Windows physical acceptance on real workstation.
- [ ] Linux physical final-build acceptance.
- [ ] Linux imagery rights resolved or images replaced.
- [ ] Exact final version numbers/tags/checksums/links verified for BOTH editions.
- [ ] User approves story, illustrations and public release copy.
- [ ] User authorises publishing Transmission 004 and both public download links together.

### Content ownership

This is a planning document, not a public announcement. Its story slivers are proposed illustrated scenes; the initial page uses pure CSS/HTML motifs rather than representing them as final artwork. Keep it attached to the existing RSS editorial draft PR for iterative review.
