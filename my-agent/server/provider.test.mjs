import assert from "node:assert/strict";
import test from "node:test";

import { createModelAnswerer } from "./provider.mjs";


const candidate = {
  profile: { display_name: "测试候选人", contact: {} },
  evidence_cards: [{ id: "ev-project", claim: "完成项目" }],
  privacy: { allowed_public_contact_fields: [] },
};

const style = {
  voice: "steady-professional",
  answer_depth: "balanced",
  emphasis: ["project-evidence"],
  insufficient_evidence_message: "候选人未提供相关信息。",
  out_of_scope_message: "只回答面试问题。",
};

test("model provider rejects non-local HTTP endpoints", async () => {
  const answerQuestion = createModelAnswerer({
    candidate,
    style,
    env: {
      MODEL_BASE_URL: "http://model.example.com/v1",
      MODEL_API_KEY: "test-key",
      MODEL_NAME: "test-model",
    },
    fetchImpl: async () => {
      throw new Error("fetch must not be called");
    },
  });

  await assert.rejects(
    answerQuestion({ message: "介绍项目", history: [] }),
    /must use HTTPS/,
  );
});

test("model provider permits a local HTTP endpoint", async () => {
  let requestUrl = "";
  const answerQuestion = createModelAnswerer({
    candidate,
    style,
    env: {
      MODEL_BASE_URL: "http://127.0.0.1:11434/v1/",
      MODEL_API_KEY: "test-key",
      MODEL_NAME: "test-model",
    },
    fetchImpl: async (url) => {
      requestUrl = url;
      return new Response(
        JSON.stringify({
          choices: [
            {
              message: {
                content: JSON.stringify({
                  scope: "in_scope",
                  answer: "候选人完成了项目。",
                  citation_ids: ["ev-project"],
                }),
              },
            },
          ],
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      );
    },
  });

  const result = await answerQuestion({ message: "介绍项目", history: [] });

  assert.equal(requestUrl, "http://127.0.0.1:11434/v1/chat/completions");
  assert.deepEqual(result, {
    scope: "in_scope",
    answer: "候选人完成了项目。",
    citation_ids: ["ev-project"],
  });
});
