import assert from "node:assert/strict";
import test from "node:test";

import { createApp } from "./app.mjs";

const candidate = {
  profile: {
    display_name: "林小明",
    headline: "AI 应用开发工程师",
    contact: { email: "public@example.com", phone: "13800138000" },
  },
  target_roles: ["AI 应用开发工程师"],
  summary: "用项目证据说明能力。",
  skills: [],
  experiences: [],
  projects: [],
  education: [],
  links: [],
  evidence_cards: [{ id: "ev-project", title: "项目证据", claim: "完成项目" }],
  privacy: { allowed_public_contact_fields: ["email"], hidden_fields: ["phone"] },
};

const style = {
  welcome_message: "你好，我是候选人的 AI 面试助理。",
  suggested_questions: ["介绍项目"],
  out_of_scope_message: "只回答面试问题。",
  insufficient_evidence_message: "候选人未提供相关信息。",
};

const presentation = { preset: "engineer-grid", accent: "teal", density: "comfortable", theme: "dark" };

async function withServer(app, callback) {
  const server = app.listen(0, "127.0.0.1");
  await new Promise((resolve) => server.once("listening", resolve));
  const address = server.address();
  try {
    await callback(`http://127.0.0.1:${address.port}`);
  } finally {
    await new Promise((resolve, reject) => server.close((error) => (error ? reject(error) : resolve())));
  }
}

test("GET /api/profile returns sanitized public data", async () => {
  const app = createApp({ candidate, style, presentation, answerQuestion: async () => null });

  await withServer(app, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/profile`);
    const body = await response.json();

    assert.equal(response.status, 200);
    assert.deepEqual(body.candidate.profile.contact, { email: "public@example.com" });
    assert.equal(JSON.stringify(body).includes("13800138000"), false);
  });
});

test("POST /api/chat validates the question before calling the model", async () => {
  let calls = 0;
  const app = createApp({
    candidate,
    style,
    presentation,
    answerQuestion: async () => {
      calls += 1;
      return { scope: "in_scope", answer: "项目回答", citation_ids: ["ev-project"] };
    },
  });

  await withServer(app, async (baseUrl) => {
    const invalid = await fetch(`${baseUrl}/api/chat`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ message: "x".repeat(501) }),
    });
    assert.equal(invalid.status, 422);
    assert.equal(calls, 0);

    const valid = await fetch(`${baseUrl}/api/chat`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ message: "介绍项目", history: [] }),
    });
    assert.equal(valid.status, 200);
    assert.equal(calls, 1);
    assert.deepEqual(await valid.json(), {
      scope: "in_scope",
      answer: "项目回答",
      citation_ids: ["ev-project"],
    });
  });
});

test("provider failures return a generic error without leaking details", async () => {
  const app = createApp({
    candidate,
    style,
    presentation,
    answerQuestion: async () => {
      throw new Error("secret upstream detail");
    },
  });

  await withServer(app, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/chat`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ message: "介绍项目", history: [] }),
    });
    const body = await response.json();

    assert.equal(response.status, 502);
    assert.equal(JSON.stringify(body).includes("secret upstream detail"), false);
  });
});
