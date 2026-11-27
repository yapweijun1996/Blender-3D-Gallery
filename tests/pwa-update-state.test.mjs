import assert from "node:assert/strict";
import test from "node:test";
import { classifyUpdate, updateLabelVersion } from "../src/pwa/update-state.js";

test("a vanished waiting worker heals the update prompt", () => {
  assert.equal(classifyUpdate({ waiting: {}, pageVersion: "0.2.0", latestVersion: "0.2.1" }), "waiting");
  assert.equal(classifyUpdate({ waiting: null, pageVersion: "0.2.0", latestVersion: "0.2.0" }), "current");
  assert.equal(classifyUpdate({ waiting: null, pageVersion: "0.2.0", latestVersion: "0.2.1" }), "stale");
  assert.equal(classifyUpdate({ waiting: null, pageVersion: "0.2.0", latestVersion: null }), "unknown");
  assert.equal(classifyUpdate({ waiting: null, pageVersion: undefined, latestVersion: "0.2.0" }), "unknown");
});

test("an update action names only a version that differs from the page", () => {
  assert.equal(updateLabelVersion("0.3.1", "0.3.0"), "0.3.1");
  assert.equal(updateLabelVersion("0.3.0", "0.3.0"), null);
  assert.equal(updateLabelVersion(null, "0.3.0"), null);
});
