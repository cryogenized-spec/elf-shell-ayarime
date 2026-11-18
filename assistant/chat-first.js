"use strict";
/* Chat-first layout, shared by the Hub and native Firefox sidebar.
 * Reparent existing DOM nodes so original event handlers, form state and
 * permission boundaries stay intact. No duplicate forms or shadow state. */
(() => {
  const root=document.querySelector(".ai-console");
  if(!root||!["hub","sidebar"].includes(document.body.dataset.view))return;
  const find=selector=>root.querySelector(selector);
  const node=(tag,className,text)=>{
    const element=document.createElement(tag);
    if(className)element.className=className;
    if(text!==undefined)element.textContent=text;
    return element;
  };
  const transcript=find(".conversation-panel");
  const conversation=find("#ai-conversation-list");
  const output=find("#ai-output");
  const prompt=find("#ai-prompt");
  const send=find("#ai-send");
  const cancel=find("#ai-cancel");
  const status=find("#ai-status");
  const settings=find("#ai-settings-form");
  const keyControls=find(".ai-key-controls");
  const verify=find("#ai-check-model");
  const verifyResult=find("#ai-check-result");
  const streamOptions=find("#ai-stream-options");
  const context=find(".ai-context-panel");
  const trace=find("#ai-trace");
  if(!transcript||!conversation||!output||!prompt||!send||!cancel||!status||
     !settings||!keyControls||!verify||!verifyResult||!streamOptions||!context||!trace)return;

  // The session transcript and answer stream are the primary surface.
  const stage=node("section","chat-first-stage");
  stage.setAttribute("aria-label","Ayarime conversation");
  const composer=node("div","chat-first-composer");
  const promptLabel=find('label[for="ai-prompt"]');
  if(promptLabel){promptLabel.classList.add("sr-only");composer.append(promptLabel);}
  composer.append(prompt);
  const actions=node("div","chat-first-send-actions");
  send.textContent="Send";
  cancel.textContent="Stop";
  actions.append(send,cancel);
  composer.append(actions);
  const feedback=node("div","chat-first-feedback");
  feedback.append(status);
  composer.append(feedback);
  // Provider output is visible in the conversation while a request streams.
  conversation.after(output);
  const privacy=find(".conversation-privacy");
  if(privacy)privacy.remove();
  stage.append(transcript,composer);

  const controls=node("div","chat-first-controls");
  controls.setAttribute("aria-label","Conversation controls");
  function disclosure(label,className,contents){
    const details=node("details","chat-first-disclosure "+className);
    const summary=node("summary","",label);
    const body=node("div","chat-first-disclosure-body");
    for(const element of contents)if(element)body.append(element);
    details.append(summary,body);
    controls.append(details);
    return {details,summary,body};
  }
  const provider=disclosure("Model & connection","chat-first-provider",
    [settings,keyControls,verify,verifyResult]);
  const modelLabel=node("span","chat-first-current-model","");
  provider.summary.append(modelLabel);
  const picker=find("#ai-model-picker");
  const idField=find("#ai-model");
  const providerField=find("#ai-provider");
  const updateModelLabel=()=>{
    if(!providerField||!idField)return;
    const display=providerField.selectedOptions?.[0]?.textContent||"Model";
    modelLabel.textContent=display+" · "+(idField.value||"Choose a model");
  };
  providerField?.addEventListener("change",updateModelLabel);
  picker?.addEventListener("change",updateModelLabel);
  idField?.addEventListener("input",updateModelLabel);
  // Existing async refresh sets the saved provider/model and status together.
  const stateStatus=find("#ai-status");
  if(stateStatus)new MutationObserver(updateModelLabel)
    .observe(stateStatus,{childList:true,characterData:true,subtree:true});
  updateModelLabel();

  disclosure("Response settings","chat-first-options",[streamOptions,context]);
  const activity=disclosure("Response activity","chat-first-activity",[trace]);
  // Keep the optional inspection surface out of the way until an actual
  // stream begins; a user can expand it to inspect real provider events.
  const syncActivity=()=>{activity.details.hidden=trace.hidden;};
  new MutationObserver(syncActivity).observe(trace,{attributes:true,attributeFilter:["hidden"]});
  syncActivity();

  const sidebarActions=find(".ai-sidebar-actions");
  if(sidebarActions){
    // A lightweight shortcut next to the heading, never a full-width banner.
    const heading=find(".section-head");
    if(heading)heading.append(sidebarActions);
    else controls.append(sidebarActions);
  }
  const extraLabel=find(".prompt-shortcut");
  extraLabel?.remove();
  const eyebrow=find(':scope > .eyebrow');
  if(eyebrow)eyebrow.remove();
  const heading=find(":scope > h2");
  if(heading)heading.textContent="Ayarime";

  // Everything optional follows the conversation; no layout-changing copies.
  root.append(stage,controls);
})();
