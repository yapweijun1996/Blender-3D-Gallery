// Minimal stdio client for the Crucible MCP server (npm @codepawlhq/crucible 0.21.0).
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

export const dir = path.dirname(fileURLToPath(import.meta.url));

export async function connect({ backend = process.env.CRUCIBLE_BACKEND || 'gpu', memory = 1024 } = {}) {
  for (const sub of ['assets', 'jobs']) fs.mkdirSync(`${dir}/${sub}`, { recursive: true });
  const client = new Client({ name: 'rag-explainer', version: '1' });
  await client.connect(new StdioClientTransport({
    command: process.execPath,
    args: [
      dir + '/node_modules/@codepawlhq/crucible/bin/crucible-mcp.mjs',
      '--browser', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
      '--backend', backend,
      '--memory', String(memory),
      '--assets', dir + '/assets',
      '--jobs', dir + '/jobs',
      '--ffmpeg', '/opt/homebrew/bin/ffmpeg',
    ],
    stderr: 'inherit',
  }));
  async function call(name, args = {}, timeout = 180000) {
    const v = await client.callTool({ name, arguments: args }, undefined, { timeout });
    if (v.isError) throw Error(name + ': ' + JSON.stringify(v.content).slice(0, 3000));
    return v;
  }
  // Returns structured data, falling back to the first text block.
  async function data(name, args, timeout) {
    const v = await call(name, args, timeout);
    if (v.structuredContent) return v.structuredContent;
    const t = v.content.find((c) => c.type === 'text');
    try { return JSON.parse(t.text); } catch { return t?.text; }
  }
  // Saves every image block of a tool result to file(s) and returns the text part.
  async function image(name, args, file, timeout) {
    const v = await call(name, args, timeout);
    const imgs = v.content.filter((c) => c.type === 'image');
    imgs.forEach((img, i) => fs.writeFileSync(imgs.length > 1 ? file.replace(/\.png$/, `-${i}.png`) : file, Buffer.from(img.data, 'base64')));
    return { images: imgs.length, text: v.content.filter((c) => c.type === 'text').map((c) => c.text).join('\n'), structured: v.structuredContent };
  }
  return { client, call, data, image, close: () => client.close() };
}
