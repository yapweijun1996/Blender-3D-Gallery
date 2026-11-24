import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { appendFileSync, copyFileSync, lstatSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { pathToFileURL } from "node:url";
import { isDeepStrictEqual } from "node:util";

const sha = /^[a-f0-9]{40}$/;
const slug = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const modes = new Set(["100644"]);
const groupKeys = new Set(["id", "name", "description", "assets"]);
const assetKeys = new Set(["id", "name", "description", "category", "tags", "file", "thumbnail", "metadata", "downloadable", "license"]);
const allKeysIn = (object, allowed) => object && !Array.isArray(object) &&
  typeof object === "object" && Object.keys(object).every(key => allowed.has(key));

export function parseRawDiff(raw) {
  const fields = raw.split("\0");
  if (fields.pop() !== "" || fields.length % 2) throw new Error("unrecognized Git diff");
  return Array.from({ length: fields.length / 2 }, (_, i) => {
    const match = /^:(\d{6}) (\d{6}) ([a-f0-9]{40}) ([a-f0-9]{40}) ([AM])$/.exec(fields[i * 2]);
    if (!match) throw new Error("unexpected Git status");
    return { oldMode: match[1], mode: match[2], status: match[5], path: fields[i * 2 + 1] };
  });
}

export function scopeStaticAppend(changes, before, after) {
  if (!Array.isArray(before?.collections) || !Array.isArray(after?.collections) ||
      after.collections.length !== before.collections.length + 1) return null;
  const { collections: [...existing], ...details } = after;
  const { collections: previous, ...priorDetails } = before;
  const collection = existing.pop();
  if (!isDeepStrictEqual(existing, previous) || !isDeepStrictEqual(details, priorDetails) ||
      !allKeysIn(collection, groupKeys) || !Array.isArray(collection.assets) ||
      collection.assets.length !== 1 || !allKeysIn(collection.assets[0], assetKeys)) return null;
  const asset = collection.assets[0];
  const id = asset.id;
  if (typeof id !== "string" || !slug.test(id) || collection.id !== id || asset.downloadable !== false ||
      previous.some(c => c.id === id || c.slug === id || c.assets.some(a => a.id === id || a.slug === id))) return null;
  const folder = `models/${id}/`;
  if (asset.file !== folder + `exports/${id}.glb` || asset.thumbnail !== folder + "previews/studio.webp" ||
      asset.metadata !== folder + "metadata.json") return null;
  const required = [asset.file, asset.thumbnail, asset.metadata, folder + id + ".blend"];
  const allowed = new Set([...required, ...["README.md", "generate.py", "verify.mjs", "verify_blender.py"].map(name => folder + name)]);
  const paths = new Set(changes.map(change => change.path));
  if (paths.size !== changes.length || !paths.has("models/catalog.json") || required.some(p => !paths.has(p)) ||
      changes.some(({ path, oldMode, mode, status }) =>
        !modes.has(mode) || (path === "models/catalog.json"
          ? oldMode !== "100644" || status !== "M"
          : !allowed.has(path) || oldMode !== "000000" || status !== "A"))) return null;
  return { id, folder, collection, asset, source: required[3], additions: changes.filter(c => c.status === "A").map(c => c.path) };
}

export async function hasGreenParent({ repository, repoId, base, fetchImpl = fetch }) {
  if (!/^[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+$/.test(repository) || !Number.isSafeInteger(repoId) || !sha.test(base)) return false;
  const url = new URL(`https://api.github.com/repos/${repository}/actions/workflows/deploy.yml/runs`);
  url.search = new URLSearchParams({ branch: "main", event: "push", status: "success", head_sha: base, per_page: "10" });
  const response = await fetchImpl(url, {
    headers: { Accept: "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28" },
    signal: AbortSignal.timeout(5000), redirect: "error",
  });
  if (!response.ok) return false;
  const body = await response.json();
  return Array.isArray(body.workflow_runs) && body.workflow_runs.some(run =>
    run?.head_sha === base && run.head_branch === "main" && run.event === "push" &&
    run.status === "completed" && run.conclusion === "success" && run.path === ".github/workflows/deploy.yml" &&
    run.repository?.id === repoId && run.head_repository?.id === repoId);
}

const git = (...args) => execFileSync("git", args, { encoding: "utf8", maxBuffer: 4 * 1024 * 1024, stdio: ["ignore", "pipe", "pipe"] });
const jsonAt = commit => JSON.parse(git("show", commit + ":models/catalog.json"));
function readGLB(file) {
  const data = readFileSync(file);
  if (data.length < 20 || data.toString("ascii", 0, 4) !== "glTF" || data.readUInt32LE(4) !== 2 ||
      data.readUInt32LE(8) !== data.length || data.toString("ascii", 16, 20) !== "JSON" ||
      data.readUInt32LE(12) > data.length - 20) throw new Error("invalid GLB header");
  const gltf = JSON.parse(data.subarray(20, 20 + data.readUInt32LE(12)).toString("utf8"));
  return { data, gltf };
}

function exactScope(base, head) {
  if (!sha.test(base) || !sha.test(head) || git("rev-parse", "HEAD").trim() !== head ||
      git("rev-list", "--parents", "-n", "1", head).trim() !== head + " " + base) return null;
  const changes = parseRawDiff(git("diff-tree", "--raw", "--no-commit-id", "--no-renames", "--no-abbrev", "-r", "-z", base, head, "--"));
  const candidate = scopeStaticAppend(changes, jsonAt(base), jsonAt(head));
  if (!candidate || git("ls-tree", "-r", "--name-only", base, "--", candidate.folder).trim()) return null;
  return candidate;
}

function cleanStatic({ gltf }) {
  return (gltf.animations === undefined || (Array.isArray(gltf.animations) && gltf.animations.length === 0)) &&
    (gltf.skins === undefined || (Array.isArray(gltf.skins) && gltf.skins.length === 0));
}

async function classify() {
  const env = process.env;
  let mode = "full";
  try {
    if (env.GITHUB_EVENT_NAME !== "push" || env.GITHUB_REF !== "refs/heads/main") throw new Error("not a main push");
    const event = JSON.parse(readFileSync(env.GITHUB_EVENT_PATH, "utf8"));
    if (event.forced !== false || event.created !== false || event.deleted !== false ||
        event.ref !== env.GITHUB_REF || event.after !== env.GITHUB_SHA ||
        event.repository?.full_name !== env.GITHUB_REPOSITORY) throw new Error("unverified push event");
    const candidate = exactScope(event.before, event.after);
    if (!candidate) throw new Error("not a single static-shaped model append");
    if (!await hasGreenParent({ repository: env.GITHUB_REPOSITORY, repoId: event.repository.id, base: event.before }))
      throw new Error("successful exact predecessor not proven");
    // Patterns are generated from a validated slug; only its folder is hydrated during verification.
    execFileSync("git", ["sparse-checkout", "add", "--stdin"], {
      input: "/" + candidate.folder + "\n", stdio: ["pipe", "pipe", "pipe"],
    });
    if (!cleanStatic(readGLB(candidate.asset.file))) throw new Error("animated or skinned model");
    // Reuse the actual selector. A new authored verifier/Blender source stays inert, never a runtime dependency.
    execFileSync(process.execPath, ["scripts/deployment-inputs.mjs"], {
      env: { ...env, GITHUB_OUTPUT: "" }, stdio: ["ignore", "pipe", "pipe"],
    });
    const patterns = readFileSync("/tmp/gallery-deployment-patterns", "utf8").split("\n");
    const selected = patterns.filter(line => line.startsWith("/" + candidate.folder));
    const expected = [candidate.asset.file, candidate.asset.thumbnail, candidate.asset.metadata].map(path => "/" + path);
    if (!isDeepStrictEqual([...selected].sort(), expected.sort())) throw new Error("new model reached another deployment dependency");
    mode = "fast";
    appendFileSync(env.GITHUB_OUTPUT, `model=${candidate.id}\nbase=${event.before}\n`);
  } catch (error) {
    console.log(`Full verification: ${String(error.message).split("\n")[0]}`);
  }
  appendFileSync(env.GITHUB_OUTPUT, `mode=${mode}\n`);
  console.log(`Verification lane: ${mode}`);
}

function checkWebp(data) {
  if (data.length < 20 || data.toString("ascii", 0, 4) !== "RIFF" ||
      data.readUInt32LE(4) !== data.length - 8 || data.toString("ascii", 8, 12) !== "WEBP")
    throw new Error("invalid studio WebP container");
  let at = 12, image = 0;
  while (at + 8 <= data.length) {
    const name = data.toString("ascii", at, at + 4), size = data.readUInt32LE(at + 4);
    if (name === "ANIM" || name === "ANMF") throw new Error("animated thumbnail");
    if (name === "VP8 " || name === "VP8L") image++;
    if (size === 0 || size > data.length - at - 8) throw new Error("invalid studio WebP chunk");
    at += 8 + size + (size % 2);
  }
  if (at !== data.length || image !== 1) throw new Error("missing or ambiguous studio WebP image");
}

export async function verifyNewModel(candidate, fullCatalog) {
  const [{ loadCatalog, validateCatalog }, { default: validator }] = await Promise.all([
    import("./catalog.mjs"), import("gltf-validator"),
  ]);
  validateCatalog(fullCatalog);
  for (const path of candidate.additions)
    if (!lstatSync(path).isFile()) throw new Error("not an ordinary model file");
  const { asset, source, collection } = candidate;
  const glb = readGLB(asset.file);
  if (!cleanStatic(glb)) throw new Error("not a static GLB");
  const metadata = JSON.parse(readFileSync(asset.metadata, "utf8"));
  const preview = readFileSync(asset.thumbnail);
  checkWebp(preview);
  if (metadata.source !== source.slice(candidate.folder.length) ||
      metadata.export !== asset.file.slice(candidate.folder.length) ||
      metadata.preview !== asset.thumbnail.slice(candidate.folder.length)) throw new Error("metadata paths disagree with package");
  for (const [data, expected] of [[glb.data, metadata.metrics?.glb_sha256],
    [preview, metadata.metrics?.preview_sha256], [readFileSync(source), metadata.metrics?.source_sha256]]) {
    if (createHash("sha256").update(data).digest("hex") !== expected) throw new Error("declared model SHA-256 mismatch");
  }
  if (metadata.metrics.glb_bytes !== glb.data.length || metadata.metrics.preview_bytes !== preview.length ||
      metadata.metrics.animations !== 0) throw new Error("metadata byte counts or animations disagree");
  // The trusted full loader validates resource containment, metadata and core external URI rules on the new files.
  const root = mkdtempSync(join(tmpdir(), "gallery-static-model-"));
  try {
    for (const file of [asset.file, asset.thumbnail, asset.metadata]) {
      const destination = join(root, file);
      mkdirSync(dirname(destination), { recursive: true });
      copyFileSync(file, destination);
    }
    writeFileSync(join(root, "models/catalog.json"), JSON.stringify({ collections: [collection] }));
    const checked = loadCatalog(root).collections[0].assets[0];
    if (checked.animations !== 0) throw new Error("animated model is not eligible for fast verification");
    const report = await validator.validateBytes(new Uint8Array(glb.data), { uri: asset.file, maxIssues: 100 });
    if (report.issues.numErrors || report.issues.numWarnings) throw new Error(JSON.stringify(report.issues));
    console.log(`Static model verified: ${candidate.id}, ${checked.triangles} triangles, ${checked.bytes} bytes`);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  if (process.argv[2] === "classify") {
    await classify();
  } else if (process.argv[2] === "verify") {
    const [base, id] = process.argv.slice(3);
    const head = process.env.GITHUB_SHA;
    const candidate = exactScope(base, head);
    if (!candidate || candidate.id !== id) throw new Error("fast verification scope changed");
    await verifyNewModel(candidate, jsonAt(head));
  } else {
    throw new Error("expected classify or verify");
  }
}
