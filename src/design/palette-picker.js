import { DEFAULT_PALETTE, PALETTE_STORAGE_KEY, paletteThemes } from "./tokens.js";
import { applyPalette, readSavedPalette } from "./palette.js";
import "./palette-picker.css";

const paletteCopy = {
  trigger: "Palette",
  title: "Choose a palette",
  close: "Close palette picker",
  names: {
    "editorial-moss": "Editorial Moss",
    "midnight-ink": "Midnight Ink",
    "obsidian-gold": "Obsidian Gold",
    "nordic-frost": "Nordic Frost",
    "porcelain-sage": "Porcelain Sage",
    "ember-copper": "Ember Copper",
    "deep-ocean": "Deep Ocean",
    "plum-velvet": "Plum Velvet",
    "graphite-mono": "Graphite Mono",
    "sand-dune": "Sand Dune",
  },
};

export function setupPalettePicker() {
  const dialog = document.querySelector("#palette-picker");
  const group = dialog.querySelector('[role="radiogroup"]');
  const title = dialog.querySelector("#palette-title");
  const close = dialog.querySelector(".icon-button");
  const menu = document.querySelector("#mobile-menu");
  const menuTrigger = document.querySelector("#menu-trigger");
  const desktopTrigger = document.querySelector(".header [data-open-palette]");
  const radios = new Map();
  let opener;

  title.textContent = paletteCopy.title;
  close.setAttribute("aria-label", paletteCopy.close);
  for (const id of Object.keys(paletteThemes)) {
    const card = document.createElement("label");
    card.className = "palette-card";
    card.innerHTML = '<input type="radio" name="gallery-palette"><span class="palette-preview" aria-hidden="true"></span><span class="palette-name"></span><span class="palette-check" aria-hidden="true">✓</span>';
    const radio = card.querySelector("input");
    radio.value = id;
    card.querySelector(".palette-preview").dataset.palette = id;
    card.querySelector(".palette-name").textContent = paletteCopy.names[id];
    radios.set(id, radio);
    group.append(card);
  }

  function select(id) {
    const active = applyPalette(id, paletteThemes, DEFAULT_PALETTE);
    radios.get(active).checked = true;
  }

  select(document.documentElement.dataset.palette);
  group.addEventListener("change", (event) => {
    const id = event.target.value;
    select(id);
    try {
      window.localStorage.setItem(PALETTE_STORAGE_KEY, id);
    } catch {
      // Keep the live selection if storage is unavailable.
    }
  });
  window.addEventListener("storage", (event) => {
    if (event.key !== PALETTE_STORAGE_KEY && event.key !== null) return;
    try {
      if (event.storageArea !== window.localStorage) return;
    } catch {
      return;
    }
    select(readSavedPalette(PALETTE_STORAGE_KEY));
  });

  for (const trigger of document.querySelectorAll("[data-open-palette]")) {
    trigger.textContent = paletteCopy.trigger;
    trigger.hidden = false;
    trigger.addEventListener("click", () => {
      opener = trigger;
      dialog.showModal();
      trigger.setAttribute("aria-expanded", "true");
      group.querySelector(":checked").focus();
    });
  }

  close.addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (event) => {
    if (event.target !== dialog) return;
    const { left, right, top, bottom } = dialog.getBoundingClientRect();
    if (event.clientX < left || event.clientX > right || event.clientY < top || event.clientY > bottom) {
      dialog.close();
    }
  });
  dialog.addEventListener("close", () => {
    opener.setAttribute("aria-expanded", "false");
    if (opener.getClientRects().length && (!menu.contains(opener) || menu.open)) {
      opener.focus();
    } else {
      (desktopTrigger.getClientRects().length ? desktopTrigger : menuTrigger).focus();
    }
  });
  menu.addEventListener("close", () => {
    if (dialog.open && menu.contains(opener)) dialog.close();
  });
}
