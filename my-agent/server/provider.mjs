import { buildSystemPrompt, normalizeModelAnswer } from "./policy.mjs";

const DEFAULT_TIMEOUT_MS = 45_000;
const MAX_ACTIVE_REQUESTS = 4;
let activeRequests = 0;

function providerConfig(env) {
  const baseUrl = (env.MODEL_BASE_URL ?? "").trim().replace(/\/+$/, "");
  const apiKey = (env.MODEL_API_KEY ?? "").trim();
  const model = (env.MODEL_NAME ?? "").trim();
  const timeoutMs = Math.max(5_000, Number(env.MODEL_TIMEOUT_MS) || DEFAULT_TIMEOUT_MS);

  if (!baseUrl || !apiKey || !model) {
    throw new Error("MODEL_BASE_URL, MODEL_API_KEY and MODEL_NAME are required");
  }
  const parsed = new URL(baseUrl);
  const localHost = new Set(["127.0.0.1", "localhost", "::1"]).has(parsed.hostname);
  if (parsed.protocol !== "https:" && !localHost) {
    throw new Error("MODEL_BASE_URL must use HTTPS outside localhost");
  }
  return { baseUrl, apiKey, model, timeoutMs };
}

function outputTokenLimit(depth) {
  if (depth === "concise") return 500;
  if (depth === "detailed") return 1_200;
  return 800;
}

export function createModelAnswerer({ candidate, style, env = process.env, fetchImpl = fetch }) {
  const systemPrompt = buildSystemPrompt(candidate, style);

  return async function answerQuestion({ message, history }) {
    if (activeRequests >= MAX_ACTIVE_REQUESTS) {
      throw new Error("model concurrency limit reached");
    }
    const config = providerConfig(env);
    activeRequests += 1;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), config.timeoutMs);

    try {
      const response = await fetchImpl(`${config.baseUrl}/chat/completions`, {
        method: "POST",
        headers: {
          authorization: `Bearer ${config.apiKey}`,
          "content-type": "application/json",
        },
        body: JSON.stringify({
          model: config.model,
          messages: [
            { role: "system", content: systemPrompt },
            ...history,
            { role: "user", content: message },
          ],
          temperature: 0.2,
          max_tokens: outputTokenLimit(style.answer_depth),
        }),
        signal: controller.signal,
      });
      if (!response.ok) {
        throw new Error(`provider returned ${response.status}`);
      }
      const body = await response.json();
      const raw = body?.choices?.[0]?.message?.content;
      return normalizeModelAnswer(raw, candidate, style);
    } finally {
      clearTimeout(timeout);
      activeRequests -= 1;
    }
  };
}
