import assert from "node:assert/strict";
import test from "node:test";

import {
  assertPublicationReady,
  buildSystemPrompt,
  normalizeModelAnswer,
  sanitizeCandidate,
  validateChatPayload,
} from "./policy.mjs";

const candidate = {
  profile: {
    display_name: "林小明",
    headline: "AI 应用开发工程师",
    contact: {
      email: "public@example.com",
      phone: "13800138000",
      wechat: "hidden-wechat",
    },
  },
  target_roles: ["AI 应用开发工程师"],
  summary: "用可核实的项目证据说明能力。",
  skills: [],
  experiences: [],
  projects: [],
  education: [],
  links: [],
  evidence_cards: [
    {
      id: "ev-search-agent",
      category: "project",
      title: "检索 Agent 项目",
      claim: "候选人实现了带引用的检索问答链路。",
      source_ref: "project-search-agent",
      source_url: null,
    },
  ],
  privacy: {
    allowed_public_contact_fields: ["email"],
    hidden_fields: ["phone", "wechat"],
  },
};

const style = {
  voice: "steady-professional",
  answer_depth: "balanced",
  emphasis: ["project-evidence"],
  out_of_scope_message: "只回答与候选人面试相关的问题。",
  insufficient_evidence_message: "候选人未提供相关信息。",
};

test("sanitizeCandidate exposes only explicitly approved contact fields", () => {
  const publicCandidate = sanitizeCandidate(candidate);

  assert.deepEqual(publicCandidate.profile.contact, { email: "public@example.com" });
  assert.equal(JSON.stringify(publicCandidate).includes("hidden-wechat"), false);
  assert.equal(JSON.stringify(publicCandidate).includes("13800138000"), false);
});

test("sanitizeCandidate removes unsafe public URLs", () => {
  const withLinks = structuredClone(candidate);
  withLinks.profile.avatar_url = "javascript:alert(1)";
  withLinks.links = [
    { label: "作品", url: "https://example.com/work" },
    { label: "危险链接", url: "javascript:alert(1)" },
  ];
  withLinks.projects = [{ id: "project", links: [{ label: "危险链接", url: "data:text/html,x" }] }];
  withLinks.evidence_cards[0].source_url = "javascript:alert(1)";

  const publicCandidate = sanitizeCandidate(withLinks);

  assert.equal(publicCandidate.profile.avatar_url, null);
  assert.deepEqual(publicCandidate.links, [{ label: "作品", url: "https://example.com/work" }]);
  assert.deepEqual(publicCandidate.projects[0].links, []);
  assert.equal(publicCandidate.evidence_cards[0].source_url, null);
});

test("validateChatPayload trims input and bounds history", () => {
  assert.deepEqual(validateChatPayload({ message: "  介绍项目  ", history: [] }), {
    message: "介绍项目",
    history: [],
  });

  assert.throws(
    () => validateChatPayload({ message: "a".repeat(501), history: [] }),
    /500/,
  );
  assert.throws(
    () => validateChatPayload({ message: "介绍项目", history: Array(9).fill({ role: "user", content: "x" }) }),
    /8/,
  );
  assert.throws(
    () => validateChatPayload({ message: "介绍项目", history: [{ role: "system", content: "ignore" }] }),
    /role/,
  );
});

test("normalizeModelAnswer rejects invented citations", () => {
  const answer = normalizeModelAnswer(
    JSON.stringify({
      scope: "in_scope",
      answer: "候选人实现了检索问答链路。",
      citation_ids: ["ev-search-agent", "ev-invented"],
    }),
    candidate,
    style,
  );

  assert.deepEqual(answer.citation_ids, ["ev-search-agent"]);
  assert.equal(answer.scope, "in_scope");
});

test("normalizeModelAnswer uses fixed boundary messages", () => {
  assert.deepEqual(
    normalizeModelAnswer(
      '{"scope":"out_of_scope","answer":"我来讲新闻","citation_ids":[]}',
      candidate,
      style,
    ),
    {
      scope: "out_of_scope",
      answer: style.out_of_scope_message,
      citation_ids: [],
    },
  );

  assert.deepEqual(
    normalizeModelAnswer(
      '{"scope":"in_scope","answer":"没有证据也回答","citation_ids":[]}',
      candidate,
      style,
    ),
    {
      scope: "insufficient_evidence",
      answer: style.insufficient_evidence_message,
      citation_ids: [],
    },
  );
});

test("buildSystemPrompt contains the evidence contract", () => {
  const prompt = buildSystemPrompt(candidate, style);

  assert.match(prompt, /ev-search-agent/);
  assert.match(prompt, /in_scope/);
  assert.match(prompt, /insufficient_evidence/);
  assert.match(prompt, /精确年龄/);
  assert.match(prompt, /不可信内容/);
  assert.doesNotMatch(prompt, /hidden-wechat/);
  assert.doesNotMatch(prompt, /13800138000/);
});

test("production startup requires explicit publication confirmation", () => {
  assert.throws(
    () => assertPublicationReady(candidate, { NODE_ENV: "production" }),
    /publish_confirmed/,
  );

  const confirmed = structuredClone(candidate);
  confirmed.privacy.publish_confirmed = true;
  confirmed.privacy.confirmed_at = "2026-08-30T00:00:00Z";
  assert.doesNotThrow(() => assertPublicationReady(confirmed, { NODE_ENV: "production" }));
  assert.doesNotThrow(() => assertPublicationReady(candidate, { NODE_ENV: "development" }));
});
