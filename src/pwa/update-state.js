/**
 * Decide what an update prompt should do when the waiting worker it offered is gone.
 * `waiting` is the registration's current waiting worker, `pageVersion` the version this
 * document was built with and `latestVersion` the version published in build-info.json.
 * Returns "waiting" (offer it), "current" (nothing newer exists: hide the prompt),
 * "stale" (a newer build is already active: offer a reload) or "unknown" (could not tell).
 */
export function classifyUpdate({ waiting, pageVersion, latestVersion }) {
  if (waiting) return "waiting";
  if (typeof latestVersion !== "string" || typeof pageVersion !== "string") return "unknown";
  return latestVersion === pageVersion ? "current" : "stale";
}

/**
 * The version to name on an update action. A waiting build that carries the page's own
 * version would read as "Update to v<current>", so it gets the plain label (null) instead.
 */
export function updateLabelVersion(updateVersion, pageVersion) {
  return updateVersion && updateVersion !== pageVersion ? updateVersion : null;
}
