// Minimal stdio client for the Crucible MCP server (npm @codepawlhq/crucible, MIT).
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

export const dir = path.dirname(fileURLToPath(import.meta.url));

export async function connect({ backend = process.env.CRUCIBLE_BACKEND || "gpu", memory = 1024 } = {}) {
  for (const sub of ["assets", "jobs"]) fs.mkdirSync(`${dir}/.work/${sub}`, { recursive: true });
  const client = new Client({ name: "gallery-crucible", version: "1" });
  await client.connect(new StdioClientTransport({
    command: process.execPath,
    args: [
      dir + "/node_modules/@codepawlhq/crucible/bin/crucible-mcp.mjs",
      "--browser", process.env.CRUCIBLE_BROWSER || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
      "--backend", backend, "--memory", String(memory),
      "--assets", `${dir}/.work/assets`, "--jobs", `${dir}/.work/jobs`,
      "--ffmpeg", process.env.CRUCIBLE_FFMPEG || "/opt/homebrew/bin/ffmpeg",
    ],
    stderr: "inherit",
  }));
  async function call(name, args = {}, timeout = 180000) {
    const result = await client.callTool({ name, arguments: args }, undefined, { timeout });
    if (result.isError) throw Error(name + ": " + JSON.stringify(result.content).slice(0, 3000));
    return result;
  }
  async function data(name, args, timeout) {
    const result = await call(name, args, timeout);
    if (result.structuredContent) return result.structuredContent;
    const text = result.content.find(block => block.type === "text");
    try { return JSON.parse(text.text); } catch { return text?.text; }
  }
  return { client, call, data, close: () => client.close() };
}
