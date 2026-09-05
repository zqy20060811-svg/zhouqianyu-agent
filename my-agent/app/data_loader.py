"""加载 data/*.json 并初始化 LangSmith 追踪。"""
from __future__ import annotations

import json
import os

from .config import DATA_DIR, langsmith_enabled, load_env
from .models import AgentStyle, Candidate, Presentation
from .provider import create_model_answerer


def _read_json(name: str) -> dict:
    with open(DATA_DIR / name, "r", encoding="utf-8") as f:
        return json.load(f)


def _configure_langsmith() -> None:
    if not langsmith_enabled():
        return
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    project = os.environ.get("LANGSMITH_PROJECT", "zhouqianyu-agent")
    os.environ.setdefault("LANGCHAIN_PROJECT", project)
    if os.environ.get("LANGSMITH_API_KEY"):
        os.environ.setdefault("LANGCHAIN_API_KEY", os.environ["LANGSMITH_API_KEY"])


class DataLoader:
    def __init__(self) -> None:
        self._loaded = False
        self.candidate: Candidate | None = None
        self.style: AgentStyle | None = None
        self.presentation: Presentation | None = None
        self.answer_question: callable | None = None

    def load(self) -> tuple[Candidate, AgentStyle, Presentation, callable]:
        if self._loaded:
            return self.candidate, self.style, self.presentation, self.answer_question
        load_env()
        _configure_langsmith()
        self.candidate = Candidate.model_validate(_read_json("candidate.json"))
        self.style = AgentStyle.model_validate(_read_json("agent-style.json"))
        self.presentation = Presentation.model_validate(_read_json("presentation.json"))
        self.answer_question = create_model_answerer(self.candidate, self.style)
        self._loaded = True
        return self.candidate, self.style, self.presentation, self.answer_question


data_loader = DataLoader()
