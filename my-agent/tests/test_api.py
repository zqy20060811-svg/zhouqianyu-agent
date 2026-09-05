"""API 测试:健康检查、profile、chat 校验与成功路径(mock LLM)。"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.models import AgentStyle, Candidate, ModelAnswer, Presentation

CANDIDATE_DICT = {
    "profile": {"display_name": "测试", "headline": "headline", "contact": {"phone": "13800000000"}},
    "privacy": {"publish_confirmed": False, "confirmed_at": None, "allowed_public_contact_fields": [], "hidden_fields": ["phone"]},
    "evidence_cards": [{"id": "ev-1", "category": "project", "title": "T", "claim": "C", "source_url": None}],
    "projects": [], "skills": [], "education": [], "links": [], "target_roles": [], "experiences": [],
}
STYLE_DICT = {
    "welcome_message": "hi", "suggested_questions": [], "out_of_scope_message": "OUT",
    "insufficient_evidence_message": "INSUFF", "voice": "steady-professional",
    "answer_depth": "balanced", "emphasis": [],
}
PRESENTATION_DICT = {"preset": "p"}


def _fake_answer(message: str, history: list):
    return ModelAnswer(scope="in_scope", answer=f"回答:{message}", citation_ids=["ev-1"])


@pytest.fixture
def client(monkeypatch):
    def fake_load():
        return (
            Candidate.model_validate(CANDIDATE_DICT),
            AgentStyle.model_validate(STYLE_DICT),
            Presentation.model_validate(PRESENTATION_DICT),
            _fake_answer,
        )
    monkeypatch.setattr("app.main.data_loader.load", fake_load)
    from app.main import create_app
    return TestClient(create_app())


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_profile(client):
    r = client.get("/api/profile")
    assert r.status_code == 200
    body = r.json()
    assert "candidate" in body and "style" in body and "presentation" in body
    assert body["candidate"]["profile"]["contact"] == {}  # 脱敏后空


def test_chat_empty_message_422(client):
    r = client.post("/api/chat", json={"message": "", "history": []})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "INVALID_QUESTION"


def test_chat_invalid_json_400(client):
    r = client.post("/api/chat", content="not json", headers={"content-type": "application/json"})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_JSON"


def test_chat_ok(client):
    r = client.post("/api/chat", json={"message": "你好", "history": []})
    assert r.status_code == 200
    body = r.json()
    assert body["scope"] == "in_scope"
    assert body["answer"] == "回答:你好"
    assert body["citation_ids"] == ["ev-1"]
