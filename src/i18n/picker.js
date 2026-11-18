import { getLanguage, languages, localize, onLanguageChange, setLanguage } from "./index.js";
import "./picker.css";

export function setupLanguagePicker() {
  const dialog = document.querySelector("#language-picker");
  const group = dialog.querySelector(".language-options");
  const menu = document.querySelector("#mobile-menu");
  const triggers = [...document.querySelectorAll("[data-open-language]")];
  let opener;

  for (const [id, { label }] of Object.entries(languages)) {
    const option = document.createElement("label");
    const radio = document.createElement("input");
    radio.type = "radio";
    radio.name = "gallery-language";
    radio.value = id;
    const name = document.createElement("span");
    name.lang = id;
    name.textContent = label;
    option.append(radio, name);
    group.append(option);
  }

  function refresh() {
    const id = getLanguage();
    const { label, short } = languages[id];
    for (const radio of group.querySelectorAll("input")) radio.checked = radio.value === id;
    for (const trigger of triggers) {
      if (menu.contains(trigger)) localize(trigger, "language.menuLabel", { code: short });
      else trigger.textContent = short;
      localize(trigger, "language.current", { language: label }, "aria-label");
      localize(trigger, "language.current", { language: label }, "title");
    }
  }
  onLanguageChange(refresh);
  refresh();
  group.addEventListener("change", event => setLanguage(event.target.value));

  for (const trigger of triggers) {
    trigger.hidden = false;
    trigger.addEventListener("click", () => {
      opener = trigger;
      dialog.showModal();
      trigger.setAttribute("aria-expanded", "true");
      group.querySelector(":checked").focus();
    });
  }
  dialog.querySelector("button").addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", event => {
    if (event.target !== dialog) return;
    const bounds = dialog.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right ||
        event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();
  });
  dialog.addEventListener("close", () => {
    opener.setAttribute("aria-expanded", "false");
    (menu.contains(opener) && !menu.open ? triggers[0] : opener).focus();
  });
  menu.addEventListener("close", () => {
    if (dialog.open && menu.contains(opener)) dialog.close();
  });
}
