import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const here = fileURLToPath(new URL(".", import.meta.url));
const run = spawnSync("./run.sh", ["wardrobe_batch.py", "--", ...process.argv.slice(2)], {
  cwd: here,
  stdio: "inherit",
});
if (run.error) throw run.error;
process.exitCode = run.status ?? 1;
