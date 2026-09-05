import path from "node:path";

import express from "express";
import rateLimit from "express-rate-limit";
import helmet from "helmet";

import { sanitizeCandidate, validateChatPayload } from "./policy.mjs";

const DEFAULT_CHAT_LIMIT = 20;
const DEFAULT_CHAT_WINDOW_MS = 10 * 60 * 1_000;

export function createApp({
  candidate,
  style,
  presentation,
  answerQuestion,
  staticDir = null,
  trustProxy = false,
  chatLimit = DEFAULT_CHAT_LIMIT,
  chatWindowMs = DEFAULT_CHAT_WINDOW_MS,
}) {
  const app = express();
  const publicCandidate = sanitizeCandidate(candidate);

  app.disable("x-powered-by");
  if (trustProxy) {
    app.set("trust proxy", trustProxy);
  }
  app.use(
    helmet({
      contentSecurityPolicy: {
        directives: {
          defaultSrc: ["'self'"],
          baseUri: ["'self'"],
          connectSrc: ["'self'"],
          fontSrc: ["'self'", "data:"],
          formAction: ["'self'"],
          frameAncestors: ["'none'"],
          imgSrc: ["'self'", "data:", "https:"],
          objectSrc: ["'none'"],
          scriptSrc: ["'self'"],
          styleSrc: ["'self'"],
        },
      },
      crossOriginEmbedderPolicy: false,
    }),
  );
  app.use(express.json({ limit: "16kb", strict: true }));

  app.get("/api/health", (_request, response) => {
    response.set("cache-control", "no-store").json({ status: "ok" });
  });

  app.get("/api/profile", (_request, response) => {
    response.set("cache-control", "no-store").json({
      candidate: publicCandidate,
      style,
      presentation,
    });
  });

  const chatLimiter = rateLimit({
    windowMs: chatWindowMs,
    limit: chatLimit,
    standardHeaders: "draft-8",
    legacyHeaders: false,
    handler: (_request, response) => {
      response.status(429).json({
        error: {
          code: "RATE_LIMITED",
          message: "提问有些频繁，请稍后再试。",
        },
      });
    },
  });

  app.post("/api/chat", chatLimiter, async (request, response) => {
    let input;
    try {
      input = validateChatPayload(request.body);
    } catch (error) {
      response.status(422).json({
        error: {
          code: "INVALID_QUESTION",
          message: error.message,
        },
      });
      return;
    }

    try {
      const result = await answerQuestion(input);
      response.set("cache-control", "no-store").json(result);
    } catch {
      response.status(502).json({
        error: {
          code: "ASSISTANT_UNAVAILABLE",
          message: "面试助理暂时无法回答，你仍可以继续浏览候选人资料。",
        },
      });
    }
  });

  if (staticDir) {
    app.use(
      express.static(staticDir, {
        index: false,
        setHeaders(response, filePath) {
          if (filePath.includes(`${path.sep}assets${path.sep}`)) {
            response.setHeader("cache-control", "public, max-age=31536000, immutable");
          }
        },
      }),
    );
    app.use((request, response, next) => {
      if (request.method !== "GET" || !request.accepts("html")) {
        next();
        return;
      }
      response.set("cache-control", "no-cache").sendFile(path.join(staticDir, "index.html"));
    });
  }

  app.use((error, _request, response, _next) => {
    if (error?.type === "entity.parse.failed" || error?.type === "entity.too.large") {
      response.status(400).json({
        error: {
          code: "INVALID_JSON",
          message: "请求格式无效。",
        },
      });
      return;
    }
    response.status(500).json({
      error: {
        code: "INTERNAL_ERROR",
        message: "服务暂时不可用。",
      },
    });
  });

  return app;
}
