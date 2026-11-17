"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const hub = fs.readFileSync(path.join(root, "assistant/ui.css"), "utf8");
const station = fs.readFileSync(path.join(root, "styles.css"), "utf8");
const base = fs.readFileSync(path.join(root, "assistant/sidebar-tabs.css"), "utf8");
const source = fs.readFileSync(path.join(root, "assistant/hub.html"), "utf8");
const builder = fs.readFileSync(path.join(root, "scripts/build_unified_preview.py"), "utf8");

// Keep the performance policy tied to real extension pages, not demo HTML or
// a fabricated new scrolling widget. Firefox performs native wheel scrolling.
assert.match(hub, /body:is\(\[data-view="hub"\],\[data-view="sidebar"\]\) \.frame\s*\{[\s\S]*?backdrop-filter:none;/);
assert.match(hub, /body\[data-view="hub"\] \.backdrop\s*\{display:none\}/);
assert.match(hub, /@supports\s*\(content-visibility:auto\)/);
assert.match(hub, /body\[data-view="hub"\] \.shell > \.frame/);
assert.match(hub, /body\[data-view="hub"\] \.shell > #ai-console/);
assert.match(hub, /contain-intrinsic-size:auto 1000px/);
assert.match(hub, /body\[data-view="sidebar"\] \.ayarime-sidebar-pane\s*\{\s*overscroll-behavior:contain;/);

// Paint reduction must not remove the underlying artwork, theme, modal and
// existing native scrolling/focus behaviour.
assert.match(hub, /\.conversation-list\{[^}]*overflow:auto/);
assert.match(base, /\.ayarime-sidebar-pane\{[^}]*overflow-y:auto/);
assert.match(base, /\.ayarime-sidebar-pane\[hidden\]\{display:none!important\}/);
assert.match(station, /\.backdrop\{[^}]*ayarime-background\.webp/);
assert.match(station, /\.settings-dialog\{max-height:90vh;overflow:auto/);
assert.match(station, /@media \(max-height:740px\), \(max-width:760px\)/);
assert.match(station, /\.frame,\.search,\.shortcut,\.station-menu summary,\.settings-dialog::backdrop\s*\{[\s\S]*?backdrop-filter:none/);
assert.match(source, /<section id="ai-console"/);
assert.match(builder, /"ui\.css"/);

// Avoid a regression that intercepts the browser's scroll wheel in script.
for (const file of ["newtab.js", "unified-preview/station-launcher.js",
                    "assistant/ui.js", "assistant/sidebar-tabs.js"]) {
  const code = fs.readFileSync(path.join(root, file), "utf8");
  assert.doesNotMatch(code, /addEventListener\s*\(\s*["']wheel["']/, file);
}

console.log("Unified scroll compositor policy PASS: no frosted scrolling panels, offscreen Hub culling, native wheel preserved.");
