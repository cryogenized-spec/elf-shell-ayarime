"use strict";
(() => {
  if (document.body.dataset.view !== "sidebar") return;
  const shell = document.querySelector("main.side-shell");
  const header = shell?.querySelector(":scope > .sidebar-header");
  const chat = shell?.querySelector(":scope > .ai-console");
  if (!shell || !header || !chat) return;

  const sections = [
    {key:"chat", title:"Chat", hint:"Conversation"},
    {key:"settings", title:"Settings", hint:"Integrations and preferences"}
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
  let last = nav;
  for (const section of sections) {
    const pane = panes.get(section.key);
    last.after(pane); last = pane;
  }
  const move = (section,element) => { if (element) panes.get(section).append(element); };
  const parentSection = selector => shell.querySelector(selector)?.closest("section.frame");
  // One sidebar: compact groups share the Settings tab, and no duplicate
  // launch button or deep link can open another Workspace from inside it.
  const settings=panes.get("settings");
  function group(title,elements) {
    const detail=document.createElement("details");
    detail.className="ayarime-sidebar-settings-group";
    const summary=document.createElement("summary");
    summary.textContent=title;
    detail.append(summary);
    for(const element of elements)if(element)detail.append(element);
    settings.append(detail);
    return detail;
  }
  const workspace=group("Workspace",[
    parentSection("#profile-select"),
    parentSection("#launch"),
    parentSection("#resource-list")
  ]);
  const oldLaunch=document.getElementById("launch");
  if(oldLaunch)oldLaunch.hidden=true;
  const google=group("Google & Morning Coffee",[
    parentSection(".companion-link"),
    shell.querySelector(":scope > .coffee-panel")
  ]);
  google.querySelector(".companion-link")?.setAttribute("hidden","");
  const coffeeLaunch=google.querySelector("#coffee-run");
  if(coffeeLaunch)coffeeLaunch.hidden=true;
  const coffeeDesc=google.querySelectorAll(".quiet");
  for(const item of coffeeDesc)if(!item.id)item.hidden=true;
  group("More",[
    parentSection("#persona-current-mode"),
    shell.querySelector(":scope > .updater-panel"),
    shell.querySelector(':scope > [role="note"]'),
    shell.querySelector(":scope > footer")
  ]);
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
