import { readdirSync, readFileSync } from "node:fs";
import { relative, resolve } from "node:path";

const directory = new URL("../src/", import.meta.url);
const root = resolve(import.meta.dirname, "..");
const colorLiteral = /#(?:[0-9a-f]{8}|[0-9a-f]{6}|[0-9a-f]{4}|[0-9a-f]{3})(?![\w-])|\b(?:rgba?|hsla?|hwb|(?:ok)?lab|(?:ok)?lch|color)\s*\(/gi;
const ignored = /\/\*[\s\S]*?\*\/|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\burl\([^)]*\)/gi;
const declaration = /(?:^|[;{}])\s*[-_a-z][\w-]*\s*:\s*([^;{}]+)(?=[;}]|$)/gi;

const files = readdirSync(directory, { recursive: true, withFileTypes: true })
  .filter((file) => file.isFile() && file.name.endsWith(".css"))
  .map((file) => resolve(file.parentPath, file.name))
  .sort();

let violations = 0;
for (const file of files) {
  const css = readFileSync(file, "utf8");
  // Ignore comments, strings and URLs without losing source offsets.
  const declarations = css.replace(ignored, (match) => match.replace(/[^\r\n]/g, " "));
  for (const match of declarations.matchAll(declaration)) {
    const value = match[1];
    const start = match.index + match[0].length - value.length;
    for (const literal of value.matchAll(colorLiteral)) {
      const line = css.slice(0, start + literal.index).split("\n").length;
      console.error(`${relative(root, file)}:${line}: use a semantic color role in place of ${literal[0]}`);
      violations += 1;
    }
  }
}

if (violations) process.exitCode = 1;
else console.log(`Color token ratchet passed: ${files.length} stylesheets, 0 color literals.`);
