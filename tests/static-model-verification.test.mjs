import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { hasGreenParent, parseRawDiff, scopeStaticAppend } from "../scripts/static-model-verification.mjs";

const base = "1".repeat(40);
const next = "2".repeat(40);
const zero = "0".repeat(40);
const id = "mock-static-model";
const folder = "models/" + id + "/";
const glb = folder + "exports/" + id + ".glb";
const preview = folder + "previews/studio.webp";
const metadata = folder + "metadata.json";
const source = folder + id + ".blend";
const mod = path => `:100644 100644 ${base} ${next} M\0${path}\0`;
const add = (path, mode = "100644") => `:000000 ${mode} ${zero} ${next} A\0${path}\0`;
const validDiff = mod("models/catalog.json") + [glb, preview, metadata, source, folder + "verify.mjs"].map(p => add(p)).join("");
const fixture = () => {
  const old = { revision: 1, collections: [
    { id: "earlier-set", name: "Earlier set", assets: [{ id: "earlier", name: "Earlier" }] },
    { id: "second-set", name: "Second set", assets: [{ id: "second", name: "Second" }] },
  ] };
  const candidate = structuredClone(old);
  candidate.collections.push({ id, name: "Mock static model", assets: [
    { id, name: "Demo", category: "Transport", file: glb, thumbnail: preview, metadata, downloadable: false },
  ] });
  return { old, candidate };
};
const route = (raw, old, candidate) => scopeStaticAppend(parseRawDiff(raw), old, candidate);

test("admits one ordinary new static package plus one append; optional authoring files are inert", () => {
  const { old, candidate } = fixture();
  assert.equal(route(validDiff, old, candidate).id, id);
  assert.equal(route(validDiff.replace(add(folder + "verify.mjs"), ""), old, candidate).id, id);
});

test("shared, security, workflow, executable, symlink, submodule and noncanonical path changes are never fast", () => {
  const { old, candidate } = fixture();
  for (const path of [".github/workflows/deploy.yml", "package-lock.json", "src/viewer.js", "scripts/catalog.mjs",
    "tests/catalog.test.mjs", "models/other/exports/other.glb", folder + "plugin.js", folder + "models/extra.glb",
    folder + "previews/../studio.webp", folder + "README.md\n", "models/" + id + "-other/generate.py"])
    assert.equal(route(validDiff + add(path), old, candidate), null, path);
  for (const mode of ["100755", "120000", "160000"])
    assert.equal(route(validDiff.replace(add(glb), add(glb, mode)), old, candidate), null, mode);
  assert.equal(route(validDiff.replace(add(glb), mod(glb)), old, candidate), null);
  assert.equal(route(validDiff.replace(add(source), ""), old, candidate), null);
  assert.throws(() => parseRawDiff(validDiff + `:100644 000000 ${base} ${zero} D\0delete\0`), /Git status/);
  assert.throws(() => parseRawDiff(validDiff.slice(0, -1)), /unrecognized/);
});

test("any preexisting mutation, reorder, multi-model or loose new alias/family/path fails closed", () => {
  const changes = [
    c => c.collections[0].assets[0].name = "Altered",
    c => [c.collections[0], c.collections[1]] = [c.collections[1], c.collections[0]],
    c => c.revision++,
    c => c.collections.at(-1).assets.push({ id: "another" }),
    c => c.collections.push({ id: "extra", assets: [{ id: "extra" }] }),
    c => c.collections.at(-1).assets[0].family = "solar-system",
    c => c.collections.at(-1).assets[0].slug = "override",
    c => c.collections.at(-1).assets[0].file = "models/other/exports/other.glb",
    c => c.collections.at(-1).assets[0].downloadable = true,
  ];
  for (const change of changes) {
    const { old, candidate } = fixture();
    change(candidate);
    assert.equal(route(validDiff, old, candidate), null);
  }
  const { old, candidate } = fixture();
  old.collections[0].assets[0].slug = id;
  candidate.collections[0].assets[0].slug = id;
  assert.equal(route(validDiff, old, candidate), null);
});

test("anonymous hosted proof must identify an exact successful same-repo main push; no Authorization header", async () => {
  const repoId = 12, repository = "example/gallery";
  const run = { head_sha: base, head_branch: "main", event: "push", status: "completed", conclusion: "success",
    path: ".github/workflows/deploy.yml", repository: { id: repoId }, head_repository: { id: repoId } };
  const query = { repository, repoId, base };
  const result = async (run, ok = true) => hasGreenParent({ ...query, fetchImpl: async (url, options) => {
    assert.equal(url.origin, "https://api.github.com");
    assert.equal(url.pathname, "/repos/example/gallery/actions/workflows/deploy.yml/runs");
    assert.equal(url.searchParams.get("head_sha"), base);
    assert.equal(url.searchParams.get("branch"), "main");
    assert.equal(Object.hasOwn(options.headers, "Authorization"), false);
    assert.equal(options.redirect, "error");
    return { ok, json: async () => ({ workflow_runs: [run] }) };
  } });
  assert.equal(await result(run), true);
  assert.equal(await result(run, false), false);
  for (const patch of [{ head_sha: next }, { head_branch: "other" }, { event: "workflow_dispatch" },
    { path: ".github/workflows/other.yml" }, { conclusion: "cancelled" }, { conclusion: "failure" },
    { status: "queued" }, { repository: { id: 41 } }, { head_repository: { id: 41 } }])
    assert.equal(await result({ ...run, ...patch }), false);
});

test("manual dispatch is classified full without using Git credentials or accessing the network", () => {
  const scratch = mkdtempSync(join(tmpdir(), "gallery-verification-test-"));
  const output = join(scratch, "output");
  try {
    const result = spawnSync(process.execPath, ["scripts/static-model-verification.mjs", "classify"], {
      encoding: "utf8", env: { ...process.env, GITHUB_EVENT_NAME: "workflow_dispatch", GITHUB_OUTPUT: output },
    });
    assert.equal(result.status, 0, result.stderr);
    assert.equal(readFileSync(output, "utf8"), "mode=full\n");
  } finally {
    rmSync(scratch, { recursive: true, force: true });
  }
});
