import { t } from "../i18n/index.js";

export const pwaCopy = {
  get update() { return t("pwa.update"); },
  updateTo: version => t("pwa.updateTo", { version }),
  version: version => t("pwa.version", { version }),
  appVersion: version => t("pwa.appVersion", { version }),
};

export const workerErrorKeys = [
  "pwa.packFailed", "pwa.legacyTab", "pwa.updateExpired",
  "pwa.tabNotReady", "pwa.activationFailed",
];

export function workerErrorKey(message, fallback) {
  // Older workers send English detail over the existing update protocol.
  return workerErrorKeys.find(key => t(key, {}, "en") === message) ?? fallback;
}

export function copyError(copyKey) {
  return Object.assign(new Error(t(copyKey, {}, "en")), { copyKey });
}
