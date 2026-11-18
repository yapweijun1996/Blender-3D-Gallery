import { getLanguage, messages, t } from "../i18n/index.js";

// Version-1 checkpoints store English status text. Resolve old and new saves
// at the presentation boundary without changing the checkpoint schema.
const keys = new Map(Object.entries(messages.en)
  .filter(([key]) => key.startsWith("game.state.") || key.startsWith("game.saveError."))
  .map(([key, value]) => [value, key]));

export const englishGameMessage = key => t(key, {}, "en");
export const gameMessageKey = value => keys.get(value);
export function translateGameMessage(value) {
  if (!value) return "";
  const key = gameMessageKey(value);
  return key ? t(key) : getLanguage() === "en" ? value : t("game.state.error");
}
