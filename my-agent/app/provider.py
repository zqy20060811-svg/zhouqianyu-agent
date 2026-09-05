"""LangChain 调用层:ChatOpenAI + PydanticOutputParser。

替代原 Node 版 server/provider.mjs,语义等价:
- OpenAI 兼容 /chat/completions
- 非 localhost 强制 HTTPS
- 并发限制 + 超时
- 结构化输出解析后交由 policy.normalize_model_answer 做证据校验
"""
from __future__ import annotations

import threading
from typing import Any
from urllib.parse import urlparse

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI

from .config import model_api_key, model_base_url, model_name, model_timeout_ms
from .models import AgentStyle, Candidate, LLMOutput, ModelAnswer
from .policy import build_system_prompt, normalize_model_answer

DEFAULT_TIMEOUT_MS = 45_000
MAX_ACTIVE_REQUESTS = 4
_semaphore = threading.Semaphore(MAX_ACTIVE_REQUESTS)


def _provider_config() -> dict:
    base_url = model_base_url()
    api_key = model_api_key()
    model = model_name()
    if not base_url or not api_key or not model:
        raise RuntimeError("MODEL_BASE_URL, MODEL_API_KEY and MODEL_NAME are required")
    parsed = urlparse(base_url)
    local_hosts = {"127.0.0.1", "localhost", "::1"}
    if parsed.scheme != "https" and parsed.hostname not in local_hosts:
        raise RuntimeError("MODEL_BASE_URL must use HTTPS outside localhost")
    return {"base_url": base_url, "api_key": api_key, "model": model, "timeout": model_timeout_ms() / 1000}


def _output_token_limit(depth: str | None) -> int:
    if depth == "concise":
        return 500
    if depth == "detailed":
        return 1200
    return 800


def _build_messages(system_prompt: str, message: str, history: list[dict]) -> list:
    messages: list = [SystemMessage(content=system_prompt)]
    for item in history:
        content = item.get("content", "")
        if item.get("role") == "user":
            messages.append(HumanMessage(content=content))
        else:
            messages.append(AIMessage(content=content))
    messages.append(HumanMessage(content=message))
    return messages


def create_model_answerer(candidate: Candidate, style: AgentStyle) -> callable:
    system_prompt = build_system_prompt(candidate, style)
    config = _provider_config()
    llm = ChatOpenAI(
        model=config["model"],
        base_url=config["base_url"],
        api_key=config["api_key"],
        temperature=0.2,
        max_tokens=_output_token_limit(getattr(style, "answer_depth", "balanced")),
        timeout=config["timeout"],
    )
    parser = PydanticOutputParser(pydantic_object=LLMOutput)
    chain = llm | parser

    def answer_question(message: str, history: list[dict]) -> ModelAnswer:
        if not _semaphore.acquire(blocking=False):
            raise RuntimeError("model concurrency limit reached")
        try:
            messages = _build_messages(system_prompt, message, history)
            llm_output: LLMOutput = chain.invoke(messages)
            return normalize_model_answer(llm_output.model_dump_json(), candidate, style)
        finally:
            _semaphore.release()

    return answer_question
