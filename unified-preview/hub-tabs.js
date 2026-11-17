"use strict";
/* The unified Hub has one main view at a time. DOM nodes (and their existing
 * event handlers) are MOVED, never cloned, preserving existing form state. */
(() => {
  if (document.body?.dataset.view !== "hub") return;
  const shell = document.querySelector("main.shell");
  if (!shell) return;
  const names = [
    ["overview", "Workspace"],
    ["assistant", "Assistant"],
    ["coffee", "Morning Coffee"],
    ["connections", "Connections"],
    ["settings", "Preferences"],
  ];
  const nav = document.createElement("nav");
  nav.className = "unified-hub-tabs";
  nav.setAttribute("role", "tablist");
  nav.setAttribute("aria-label", "Workspace Hub sections");
  const panes = new Map();
  const buttons = new Map();
  for (const [key, label] of names) {
    const button = document.createElement("button");
    button.type = "button";
    button.id = "unified-hub-tab-" + key;
    button.setAttribute("role", "tab");
    button.setAttribute("aria-controls", "unified-hub-pane-" + key);
    button.textContent = label;
    button.dataset.hubTab = key;
    nav.append(button);
    buttons.set(key, button);
    const pane = document.createElement("section");
    pane.className = "unified-hub-pane";
    pane.id = "unified-hub-pane-" + key;
    pane.setAttribute("role", "tabpanel");
    pane.setAttribute("aria-labelledby", button.id);
    pane.hidden = true;
    panes.set(key, pane);
  }
  const masthead = shell.querySelector(":scope > .masthead");
  if (!masthead) return;
  masthead.after(nav);
  let anchor = nav;
  for (const [key] of names) {
    const pane = panes.get(key);
    anchor.after(pane);
    anchor = pane;
  }
  function move(key, selector) {
    const item = shell.querySelector(selector);
    if (item) panes.get(key).append(item);
  }
  // Existing script handlers reference IDs, so preserve each node identity.
  move("overview", ':scope > [role="note"]');
  move("overview", ":scope > .profile-manager");
  move("overview", ":scope > .columns");
  move("assistant", ":scope > #ai-console");
  move("coffee", ":scope > .coffee-panel");
  move("connections", ":scope > .google-section");
  move("connections", ":scope > .master-panel");
  move("settings", ":scope > .persona-section");
  move("settings", ":scope > .updater-panel");
  // Future sections remain accessible rather than falling into a long page.
  for (const element of [...shell.children]) {
    if (element.matches(".frame") && !element.closest(".unified-hub-pane"))
      panes.get("settings").append(element);
  }
  function show(name, keyboardFocus = false) {
    const key = panes.has(name) ? name : "overview";
    for (const [id, button] of buttons) {
      const active = key === id;
      button.setAttribute("aria-selected", String(active));
      button.tabIndex = active ? 0 : -1;
      panes.get(id).hidden = !active;
    }
    if (keyboardFocus) buttons.get(key).focus({preventScroll: true});
    shell.dataset.activeHubTab = key;
  }
  names.forEach(([key], i) => {
    const button = buttons.get(key);
    button.addEventListener("click", () => show(key, false));
    button.addEventListener("keydown", event => {
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      const next = event.key === "Home" ? 0 : event.key === "End" ? names.length - 1 :
        (i + (event.key === "ArrowRight" ? 1 : -1) + names.length) % names.length;
      show(names[next][0], true);
    });
  });
  const hashTab = () => {
    const tab = location.hash.slice(1);
    if (panes.has(tab)) show(tab);
  };
  const initial = location.hash.slice(1);
  show(panes.has(initial) ? initial : "overview");
  window.addEventListener("hashchange", hashTab);
})();
