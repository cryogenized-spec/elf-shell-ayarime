"use strict";
(() => {
  if (document.body.dataset.view !== "sidebar") return;
  const shell = document.querySelector("main.side-shell");
  const header = shell?.querySelector(":scope > .sidebar-header");
  const chat = shell?.querySelector(":scope > .ai-console");
  if (!shell || !header || !chat) return;

  const sections = [
    {key:"chat", title:"Chat", hint:"Conversation and response controls"},
    {key:"model", title:"Model", hint:"Provider, model and session API key"},
    {key:"work", title:"Workspace", hint:"Profiles, tabs and saved links"},
    {key:"google", title:"Google", hint:"Account setup and Morning Coffee"},
    {key:"more", title:"More", hint:"Personality, updates and diagnostics"}
  ];
  const nav = document.createElement("nav");
  nav.className = "ayarime-sidebar-tabs";
  nav.setAttribute("role","tablist");
  nav.setAttribute("aria-label","Ayarime sidebar sections");
  const panes = new Map(), buttons = new Map();
  for (const section of sections) {
    const tab = document.createElement("button");
    tab.type = "button"; tab.setAttribute("role","tab");
    tab.id = "ayarime-sidebar-tab-" + section.key;
    tab.textContent = section.title;
    tab.title = section.hint;
    tab.dataset.section = section.key;
    tab.setAttribute("aria-controls","ayarime-sidebar-pane-" + section.key);
    const pane = document.createElement("div");
    pane.className = "ayarime-sidebar-pane";
    pane.id = "ayarime-sidebar-pane-" + section.key;
    pane.setAttribute("role","tabpanel");
    pane.setAttribute("aria-labelledby",tab.id);
    pane.hidden = true;
    nav.append(tab); panes.set(section.key,pane); buttons.set(section.key,tab);
  }
  header.after(nav);
  for (const pane of panes.values()) nav.after(...[]); // All panes are inserted below in fixed order.
  let last = nav;
  for (const section of sections) {
    const pane = panes.get(section.key);
    last.after(pane); last = pane;
  }
  const move = (section,element) => { if (element) panes.get(section).append(element); };
  const parentSection = selector => shell.querySelector(selector)?.closest("section.frame");
  move("work",parentSection("#profile-select"));
  move("work",parentSection("#launch"));
  move("work",parentSection("#resource-list"));
  move("google",parentSection(".companion-link"));
  move("google",shell.querySelector(":scope > .coffee-panel"));
  move("more",parentSection("#persona-current-mode"));
  move("more",shell.querySelector(":scope > .updater-panel"));
  move("more",shell.querySelector(':scope > [role="note"]'));
  move("more",shell.querySelector(":scope > footer"));

  const model = document.createElement("section");
  model.className = "frame ai-console ayarime-model-pane";
  model.setAttribute("aria-label","AI provider and model configuration");
  const eyebrow = document.createElement("p");
  eyebrow.className = "eyebrow"; eyebrow.textContent = "// AYARIME / MODEL SETUP";
  const title = document.createElement("h2");
  title.textContent = "Provider & API key";
  const note = document.createElement("p");
  note.className = "quiet";
  note.textContent = "Configure your chosen model here. API keys are session-only; this tab never connects Google automatically.";
  model.append(eyebrow,title,note);
  const disclosure = chat.querySelector(".unified-provider-settings");
  if (disclosure) {
    disclosure.open = true; // The Model tab replaces the old double-disclosure.
    model.append(disclosure);
  } else {
    for (const selector of ["#ai-settings-form",".ai-key-controls","#ai-offer-panel"])
      moveProvider(selector);
  }
  function moveProvider(selector) {
    const element = chat.querySelector(selector);
    if (element) model.append(element);
  }
  panes.get("model").append(model);
  const chatHeading = chat.querySelector(":scope > h2");
  if (chatHeading) chatHeading.textContent = "Conversation";
  const shortcut = document.createElement("button");
  shortcut.type = "button"; shortcut.className = "mini ayarime-model-shortcut";
  shortcut.textContent = "Configure model / API key";
  shortcut.addEventListener("click",() => select("model",true));
  chatHeading?.after(shortcut);
  move("chat",chat);

  function select(key, focus=false) {
    const selected = buttons.has(key) ? key : "chat";
    for (const [name,button] of buttons) {
      const active = name === selected;
      button.setAttribute("aria-selected",String(active));
      button.tabIndex = active ? 0 : -1;
      panes.get(name).hidden = !active;
    }
    if (focus) {
      const button = buttons.get(selected);
      button.focus();
      button.scrollIntoView({block:"nearest",inline:"nearest"});
    }
  }
  for (let i=0;i<sections.length;i++) {
    const key = sections[i].key, tab=buttons.get(key);
    tab.addEventListener("click",() => select(key,false));
    tab.addEventListener("keydown",event => {
      if (!["ArrowLeft","ArrowRight","Home","End"].includes(event.key)) return;
      event.preventDefault();
      const next = event.key === "Home" ? 0 :
        event.key === "End" ? sections.length-1 :
        (i + (event.key === "ArrowRight" ? 1 : -1) + sections.length) % sections.length;
      select(sections[next].key,true);
    });
  }
  select("chat");
})();
