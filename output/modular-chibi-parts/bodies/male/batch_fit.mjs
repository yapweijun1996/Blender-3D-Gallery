import { createWriteStream } from "node:fs";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const here = fileURLToPath(new URL(".", import.meta.url));
const names = ["hair-bob", "hair-spiky", "hair-sidepart", "sneakers", "tshirt", "jeans", "dress"];
const [iterations = "6", ...selected] = process.argv.slice(2);
const queue = selected.length ? selected : names;
if (!queue.every(name => names.includes(name))) throw Error("Unknown module");
const failed = [];
async function worker() {
  while (queue.length) {
    const name = queue.shift();
    const log = createWriteStream(new URL(`qa/fit-${name}.log`, import.meta.url));
    const child = spawn("./run.sh", ["run_module.py", "--", name, iterations],
      { cwd: here, env: { ...process.env, MALE_THREADS: "2" }, stdio: ["ignore", "pipe", "pipe"] });
    child.stdout.pipe(log, { end: false });
    child.stderr.pipe(log, { end: false });
    const [code, signal] = await new Promise((resolve, reject) => {
      child.once("error", reject);
      child.once("close", (code, signal) => resolve([code, signal]));
    });
    log.end();
    console.log(name, code ?? signal);
    if (code !== 0) failed.push(name);
  }
}
await Promise.all(Array.from({ length: Math.min(2, queue.length) }, worker));
if (failed.length) {
  console.error("Failed:", failed);
  process.exitCode = 1;
}
