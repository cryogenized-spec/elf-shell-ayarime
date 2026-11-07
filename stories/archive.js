"use strict";
/* Ayarime illustrated side stories. Entirely local; no storage, telemetry or network access. */
(() => {
  const $ = id => document.getElementById(id);
  const root = "assets/";
  const stories = Object.freeze({
    letters: {
      volume: "001", name: "Letters from the Lower City",
      deck: "The ruined post office. Seven silent encounters with a world that still remembers.",
      blocks: [
        {image:"letters-from-the-lower-city-01-04.png",frames:"01–04",
          location:"BERALIA-01 / LOWER CITY / POSTAL DISTRICT",
          title:"Letters left behind",
          body:"Ayarime enters the abandoned postal district. Rusted mailboxes, a sleeping city and a stray cat punctuate four quiet observations.",
          quote:"“Beralia-01 — the blighted vale, land of the survivors.”"},
        {image:"letters-from-the-lower-city-05-07.png",frames:"05–07",
          location:"BERALIA-01 / LETTERS / NO SIGNAL",
          title:"Unsent messages",
          body:"Law and order, ignorance and aversion mingle in an archive of correspondence. The upstream feeds the downstream long after destruction.",
          quote:"“Though destroyed, the upstream fed the downstream regardless.”"}
      ]
    },
    beans: {
      volume:"002",name:"Crushed Rainforest Beans",
      deck:"A cup of coffee. Twelve glimpses of a universe that does not forget.",
      blocks: [
        {image:"crushed-rainforest-beans-01-04.png",frames:"01–04",
          location:"BERALIA-01 / COFFEE STALL / FIRST BREW",
          title:"Coffee and euphoria",
          body:"Grinding, churning, tasting and imbibing. The first shimmering bubbles carry searches beyond the physical world.",
          quote:"“grep, grep, grep… I, the pipedream. grep |”"},
        {image:"crushed-rainforest-beans-05-08.png",frames:"05–08",
          location:"BERALIA-01 / CONCATENATED IMPRESSIONS",
          title:"The memories concatenate",
          body:"The cat meows. An unseen command completes. Fear, craving, attachment and the passing of violence cross the night in strange fragments.",
          quote:"“By that very noose of fear, the sword changes hands, not its thirst.”"},
        {image:"crushed-rainforest-beans-09-12.png",frames:"09–12",
          location:"YAMA’S COURT / THE QUIET RETURN",
          title:"The judgment and return",
          body:"An entire drama of suffering and judgment arrives as residual impressions. Beyond the phantasmagoria, Ayarime remains at her coffee stall, contemplating the silent night.",
          quote:"“Retribution cuts deeply, and inevitably. There is no escape.”"}
      ]
    }
  });
  let story = "beans";
  let index = 2;
  const dialog = $("art-dialog");
  const sequenceList = $("sequence-list");
  const allowedKeys = new Set(Object.keys(stories));

  function readFragment(){
    const match = /^#(letters|beans)\/([0-9]+)$/.exec(location.hash);
    if(!match || !allowedKeys.has(match[1])) return null;
    const n = Number(match[2]);
    if(!Number.isSafeInteger(n) || n < 0 || n >= stories[match[1]].blocks.length) return null;
    return {story:match[1],index:n};
  }
  function render(){
    const collection = stories[story];
    const scene = collection.blocks[index];
    const imagePath = root + scene.image;
    const alt = collection.name + " — original illustrated frames " + scene.frames;
    $("hero-volume").textContent = collection.volume;
    $("hero-title").textContent = collection.name;
    $("hero-deck").textContent = collection.deck;
    $("main-art").src = imagePath;
    $("main-art").alt = alt;
    $("expanded-art").src = imagePath;
    $("expanded-art").alt = alt + ", expanded";
    $("art-dialog-label").textContent = collection.name.toUpperCase() + " / FRAMES " + scene.frames;
    $("record-code").textContent = "MEMORY RECORD / " + collection.volume + " / FRAMES " + scene.frames;
    $("inspector-location").textContent = scene.location;
    $("inspector-title").textContent = scene.title;
    $("inspector-body").textContent = scene.body;
    $("inspector-quote").textContent = scene.quote;
    $("archive-id").textContent = "AYR-" + collection.volume + "-" + String.fromCharCode(65 + index);
    $("archive-announcement").textContent = collection.name + ", frames " + scene.frames + ": " + scene.title;
    for(const control of document.querySelectorAll("button[data-story]")){
      const selected = control.dataset.story === story;
      control.classList.toggle("active",selected);
      control.setAttribute("aria-pressed",String(selected));
    }
    sequenceList.replaceChildren();
    collection.blocks.forEach((block,i) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "sequence-card" + (i===index?" active":"");
      button.dataset.set = String(i);
      button.setAttribute("aria-label",collection.name + ", frames " + block.frames + ": " + block.title);
      button.setAttribute("aria-pressed",String(i===index));
      const preview = document.createElement("img");
      preview.src = root + block.image;
      preview.alt = "";
      preview.width = 1672;
      preview.height = 941;
      preview.loading = "lazy";
      preview.decoding = "async";
      const label = document.createElement("span");
      label.textContent = String(i+1).padStart(2,"0") + " / FRAMES " + block.frames;
      button.append(preview,label);
      button.addEventListener("click",() => select(story,i));
      sequenceList.append(button);
    });
  }
  function select(nextStory,nextIndex){
    if(!allowedKeys.has(nextStory) || nextIndex < 0 || nextIndex >= stories[nextStory].blocks.length) return;
    story = nextStory;
    index = nextIndex;
    render();
    const fragment = "#" + story + "/" + index;
    if(location.hash !== fragment) history.replaceState(null,"",fragment);
  }
  for(const control of document.querySelectorAll("button[data-story]")){
    control.addEventListener("click",() => select(control.dataset.story,0));
  }
  $("previous-set").addEventListener("click",() => select(story,(index - 1 + stories[story].blocks.length) % stories[story].blocks.length));
  $("next-set").addEventListener("click",() => select(story,(index + 1) % stories[story].blocks.length));
  $("expand-art").addEventListener("click",() => {if(!dialog.open) dialog.showModal();});
  $("close-art").addEventListener("click",() => dialog.close());
  dialog.addEventListener("click",event => {if(event.target === dialog) dialog.close();});
  document.addEventListener("keydown",event => {
    if(dialog.open || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
    if(event.target.closest("input,textarea,select,[contenteditable=true]")) return;
    if(event.key === "ArrowLeft" || event.key === "ArrowRight"){
      event.preventDefault();
      const direction = event.key === "ArrowLeft" ? -1 : 1;
      select(story,(index+direction+stories[story].blocks.length)%stories[story].blocks.length);
    }
  });
  window.addEventListener("hashchange",() => {
    const fromUrl = readFragment();
    if(fromUrl) select(fromUrl.story,fromUrl.index);
  });
  const deepLink = readFragment();
  if(deepLink){story=deepLink.story;index=deepLink.index;}
  render();
})();
