"use strict";
/* Explicit-consent, local-only Firefox native messaging. Never mock live sensor readings. */
(() => {
  const $ = id => document.getElementById(id);
  const ids = ["cpu-temp", "gpu-temp", "ram-usage", "fan-speed", "system-load"];
  let timer = null;
  let busy = false;
  let enabled = false;
  let generation = 0;
  const numeric = value => typeof value === "number" && Number.isFinite(value) ? value : null;
  const temp = value => numeric(value) === null ? "N/A" : value.toFixed(1) + "°C";
  function clearValues() { ids.forEach(id => $(id).textContent = "N/A"); }
  function state(label, detail) {
    $("telemetry-status").textContent = label;
    $("telemetry-hint").textContent = detail || "";
  }
  async function allowed() {
    try { return !!(typeof browser !== "undefined" && browser.permissions &&
      await browser.permissions.contains({permissions:["nativeMessaging"]})); }
    catch { return false; }
  }
  function showData(data) {
    if(!data || data.ok !== true) throw Error(data?.error || "Invalid sensor response");
    $("cpu-temp").textContent = temp(data.cpu_c);
    $("gpu-temp").textContent = temp(data.gpu_c);
    const used=numeric(data.ram_used_gib), total=numeric(data.ram_total_gib);
    $("ram-usage").textContent = used === null || total === null || total <= 0 ?
      "N/A" : used.toFixed(1) + " / " + total.toFixed(1) + " GiB";
    const fans = Array.isArray(data.fan_rpm) ? data.fan_rpm.filter(n => numeric(n)!==null && n>0) : [];
    $("fan-speed").textContent = fans.length ? fans.slice(0,2).join(" / ") + " RPM" : "N/A";
    $("system-load").textContent = numeric(data.load_1m) === null ? "N/A" : data.load_1m.toFixed(2);
    state("LIVE", "LOCAL HARDWARE · REFRESH 15s");
  }
  async function poll() {
    if(busy || document.hidden) return;
    busy = true;
    const current = generation;
    try {
      const response=await browser.runtime.sendMessage({type:"elfshell:telemetry:read:v1"});
      if(current === generation) showData(response);
    } catch (error) {
      if(current !== generation) return;
      clearValues();
      const detail = String(error?.message || "Native host unavailable").slice(0,180);
      state("HOST MISSING", "Run python3 telemetry/install.py · " + detail);
    } finally { busy=false; }
  }
  async function refresh() {
    generation++;
    enabled=await allowed();
    if(timer) { clearInterval(timer); timer=null; }
    if(!enabled) { clearValues();state("OFF","OPT-IN · LINUX MINT");$("telemetry-toggle").textContent="ENABLE TELEMETRY"; return; }
    $("telemetry-toggle").textContent="DISABLE TELEMETRY";
    state("CONNECTING","LOCAL READ-ONLY SENSOR BRIDGE");
    await poll();
    timer=setInterval(poll,15000);
  }
  $("telemetry-toggle").addEventListener("click", async () => {
    if(typeof browser === "undefined" || !browser.permissions) {
      state("PREVIEW", "Available only inside the Firefox extension");
      return;
    }
    try {
      // Request optional Firefox permission directly from the click gesture.
      // Awaiting a permission probe here can lose the user activation token.
      if(enabled) {
        await browser.permissions.remove({permissions:["nativeMessaging"]});
        await refresh();
      } else {
        const granted = await browser.permissions.request({permissions:["nativeMessaging"]});
        if(!granted) {state("DECLINED","Firefox permission was not granted");return;}
        await refresh();
      }
    } catch(error) {state("ERROR",String(error?.message||error).slice(0,160));}
  });
  document.addEventListener("visibilitychange",()=>{if(!document.hidden && timer)poll();});
  if(typeof browser!=="undefined" && browser.permissions?.onRemoved)
    browser.permissions.onRemoved.addListener(change=>{if(change.permissions?.includes("nativeMessaging"))refresh();});
  if(typeof browser!=="undefined" && browser.permissions?.onAdded)
    browser.permissions.onAdded.addListener(change=>{if(change.permissions?.includes("nativeMessaging"))refresh();});
  if(typeof browser==="undefined" || !browser.runtime) state("PREVIEW","Install as Firefox extension for live data");
  else refresh();
})();
