"use strict";
// An extension and a static theme cannot occupy the same manifest.
// The Firefox theme API applies the palette dynamically.
const AYARIME_THEME = {
  images: { theme_frame: "assets/theme-frame.jpg" },
  colors: {
    frame: "#131723", tab_background_text: "#E9E5E5", toolbar: "#1B1A28",
    toolbar_text: "#EEE9E8", tab_selected: "#4C293C", tab_text: "#F7E8F2",
    tab_line: "#CA839F", toolbar_field: "#171924", toolbar_field_text: "#F0EBE8",
    toolbar_field_border: "#9E6982", toolbar_field_focus: "#1F2031",
    toolbar_field_text_focus: "#FFFFFF", toolbar_field_border_focus: "#D598B1",
    popup: "#191B27", popup_text: "#EDE8EA", popup_border: "#764862",
    button_background_hover: "#433248", button_background_active: "#683C55",
    sidebar: "#171923", sidebar_text: "#EEE9E8", sidebar_border: "#4A3A4D",
    ntp_background: "#111824", ntp_text: "#EDE7E8",
  }
};
async function applyTheme() {
  try { await browser.theme.update(AYARIME_THEME); }
  catch (error) { console.error("ELF//SHELL: could not apply theme", error); }
}
applyTheme();
browser.runtime.onInstalled.addListener(applyTheme);
browser.runtime.onStartup.addListener(applyTheme);
