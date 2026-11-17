import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';

const root = process.cwd();
const index = execFileSync('git', ['ls-files', '--stage', '-z'], { encoding: 'utf8', maxBuffer: 32 * 1024 * 1024 });
const tracked = new Map(index.split('\0').filter(Boolean).map(row => {
  const [mode, hash, , file] = row.match(/^(\d+) ([a-f0-9]+) (\d)\t(.*)$/s).slice(1);
  if (mode === '120000') throw new Error('Deployment inputs must be ordinary files: ' + file);
  return [file, hash];
}));
const selected = new Set([...tracked.keys()].filter(file =>
  /^(src|scripts|public|data)\//.test(file) ||
  ['index.html', 'package.json', 'package-lock.json', 'vite.config.js', 'models/catalog.json'].includes(file)));
function include(file) {
  if (!tracked.has(file)) throw new Error('Deployment references an untracked or missing file: ' + file);
  selected.add(file);
}
const catalog = JSON.parse(fs.readFileSync('models/catalog.json', 'utf8'));
for (const collection of catalog.collections) for (const asset of collection.assets) {
  for (const field of ['file', 'thumbnail', 'metadata']) if (asset[field]) include(asset[field]);
}
// Include literal model imports, URL constructors and Vite glob patterns, including
// model-owned JS dependencies. The production build checks that this closure is complete.
const pending = [...selected].filter(file => /\.(?:[cm]?js|css|html)$/.test(file));
const scanned = new Set();
while (pending.length) {
  const file = pending.pop();
  if (scanned.has(file)) continue;
  scanned.add(file);
  const source = fs.existsSync(path.join(root, file))
    ? fs.readFileSync(path.join(root, file), 'utf8')
    : execFileSync('git', ['show', ':' + file], { encoding: 'utf8' });
  for (const match of source.matchAll(/["'`]([^"'`\r\n]+)["'`]/g)) {
    const literal = match[1].split('?')[0];
    if (literal.includes('${') || !/^(?:\.?\.?\/|\/models\/)/.test(literal)) continue;
    const resolved = literal.startsWith('/') ? literal.slice(1) : path.posix.normalize(path.posix.join(path.posix.dirname(file), literal));
    if (!resolved.startsWith('models/')) continue;
    const matches = /[*?{[]/.test(resolved)
      ? [...tracked.keys()].filter(candidate => path.matchesGlob(candidate, resolved))
      : tracked.has(resolved) ? [resolved] : [];
    for (const candidate of matches) {
      include(candidate);
      if (/\.[cm]?js$/.test(candidate)) pending.push(candidate);
    }
  }
}
const files = [...selected].sort();
const digest = crypto.createHash('sha256').update(files.map(file => file + '\0' + tracked.get(file)).join('\n')).digest('hex');
const patterns = ['/*', '!/models/', '!/docs/', '!/output/', '!/tests/', '!/.agents/', '!/.tripo/',
  ...files.filter(file => file.startsWith('models/')).map(file => '/' + file)];
fs.writeFileSync('/tmp/gallery-deployment-patterns', patterns.join('\n') + '\n');
if (process.env.GITHUB_OUTPUT) fs.appendFileSync(process.env.GITHUB_OUTPUT, 'cache_key=pages-v1-' + digest + '\n');
console.log('Selected ' + files.length + ' deployment inputs, including ' + files.filter(file => file.startsWith('models/')).length + ' model files. Cache key ' + digest);
