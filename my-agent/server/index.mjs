import dotenv from "dotenv";
import { readFile } from "node:fs/promises";

// Load .env, then expand ${VAR} references using system environment variables
const parsed = dotenv.config({ path: ".env" }).parsed ?? {};
for (const [key, value] of Object.entries(parsed)) {
  const expanded = value.replace(/\$\{(\w+)\}/g, (_, name) => process.env[name] ?? "");
  process.env[key] = expanded;
}
import path from "node:path";
import { fileURLToPath } from "node:url";

import { createApp } from "./app.mjs";
import { assertPublicationReady } from "./policy.mjs";
import { createModelAnswerer } from "./provider.mjs";

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

async function readJson(fileName) {
  return JSON.parse(await readFile(path.join(projectRoot, "data", fileName), "utf8"));
}

const [candidate, style, presentation] = await Promise.all([
  readJson("candidate.json"),
  readJson("agent-style.json"),
  readJson("presentation.json"),
]);

assertPublicationReady(candidate);
const answerQuestion = createModelAnswerer({ candidate, style });
const port = Math.max(1, Number(process.env.PORT) || 8787);
const trustProxy = process.env.TRUST_PROXY === "1" ? 1 : false;
const app = createApp({
  candidate,
  style,
  presentation,
  answerQuestion,
  staticDir: path.join(projectRoot, "dist"),
  trustProxy,
});

app.listen(port, "0.0.0.0", () => {
  console.log(`Interview Agent listening on http://0.0.0.0:${port}`);
});
