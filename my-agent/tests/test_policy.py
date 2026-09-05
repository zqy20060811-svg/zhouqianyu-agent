"""边界策略测试:对齐原 policy.test.mjs 的覆盖范围。"""
from __future__ import annotations

import pytest

from app.models import AgentStyle, Candidate, ModelAnswer
from app.policy import (
    MAX_MESSAGE_LENGTH,
    sanitize_candidate,
    validate_chat_payload,
    normalize_model_answer,
)

STYLE_DICT = {
    "welcome_message": "hi",
    "suggested_questions": [],
    "out_of_scope_message": "OUT",
    "insufficient_evidence_message": "INSUFF",
    "voice": "steady-professional",
    "answer_depth": "balanced",
    "emphasis": ["project-evidence"],
}

CANDIDATE_DICT = {
    "profile": {
        "display_name": "测试",
        "headline": "测试 headline",
        "avatar_url": "not-a-url",
        "contact": {"phone": "13800000000", "email": "a@b.com"},
    },
    "privacy": {
        "publish_confirmed": False,
        "confirmed_at": None,
        "allowed_public_contact_fields": [],
        "hidden_fields": ["phone", "email"],
    },
    "links": [{"label": "bad", "url": "javascript:alert(1)"}, {"label": "ok", "url": "https://example.com"}],
    "projects": [{"id": "p1", "title": "P1", "links": [{"url": "https://good.example.com"}]}],
    "evidence_cards": [
        {"id": "ev-1", "category": "project", "title": "T1", "claim": "C1", "source_url": "ftp://x"},
        {"id": "ev-2", "category": "statement", "title": "T2", "claim": "C2", "source_url": None},
    ],
    "skills": [],
    "education": [],
    "target_roles": [],
    "experiences": [],
}


def test_sanitize_strips_unauthorized_contact():
    public = sanitize_candidate(CANDIDATE_DICT)
    assert public["profile"]["contact"] == {}
    assert public["profile"]["avatar_url"] is None


def test_sanitize_filters_invalid_links():
    public = sanitize_candidate(CANDIDATE_DICT)
    assert public["links"] == [{"label": "ok", "url": "https://example.com"}]
    assert public["projects"][0]["links"] == [{"label": None, "url": "https://good.example.com"}]


def test_sanitize_drops_privacy_audit_fields():
    public = sanitize_candidate(CANDIDATE_DICT)
    assert "confirmed_at" not in public["privacy"]
    assert "hidden_fields" not in public["privacy"]


def test_sanitize_strips_invalid_source_url():
    public = sanitize_candidate(CANDIDATE_DICT)
    cards = {c["id"]: c for c in public["evidence_cards"]}
    assert cards["ev-1"]["source_url"] is None  # ftp:// 非法
    assert cards["ev-2"]["source_url"] is None


def test_validate_empty_message():
    with pytest.raises(ValueError, match="问题不能为空"):
        validate_chat_payload({"message": "   ", "history": []})


def test_validate_too_long_message():
    with pytest.raises(ValueError, match="问题不能超过"):
        validate_chat_payload({"message": "x" * (MAX_MESSAGE_LENGTH + 1), "history": []})


def test_validate_bad_history_role():
    with pytest.raises(ValueError, match="history role"):
        validate_chat_payload({"message": "hi", "history": [{"role": "system", "content": "x"}]})


def test_validate_ok():
    message, history = validate_chat_payload({"message": " hello ", "history": [{"role": "user", "content": "x"}]})
    assert message == "hello"
    assert history == [{"role": "user", "content": "x"}]


def test_normalize_out_of_scope():
    raw = '{"scope":"out_of_scope","answer":"任意","citation_ids":[]}'
    result = normalize_model_answer(raw, CANDIDATE_DICT, STYLE_DICT)
    assert result.scope == "out_of_scope"
    assert result.answer == "OUT"
    assert result.citation_ids == []


def test_normalize_insufficient_evidence():
    raw = '{"scope":"insufficient_evidence","answer":"任意","citation_ids":["ev-1"]}'
    result = normalize_model_answer(raw, CANDIDATE_DICT, STYLE_DICT)
    assert result.scope == "insufficient_evidence"
    assert result.answer == "INSUFF"


def test_normalize_in_scope_with_valid_citation():
    raw = '{"scope":"in_scope","answer":"事实回答","citation_ids":["ev-1"]}'
    result = normalize_model_answer(raw, CANDIDATE_DICT, STYLE_DICT)
    assert result.scope == "in_scope"
    assert result.answer == "事实回答"
    assert result.citation_ids == ["ev-1"]


def test_normalize_in_scope_with_invalid_citation_falls_back():
    raw = '{"scope":"in_scope","answer":"事实","citation_ids":["ev-999"]}'
    result = normalize_model_answer(raw, CANDIDATE_DICT, STYLE_DICT)
    assert result.scope == "insufficient_evidence"
    assert result.answer == "INSUFF"
    assert result.citation_ids == []


def test_normalize_invalid_json():
    with pytest.raises(ValueError):
        normalize_model_answer("not json at all", CANDIDATE_DICT, STYLE_DICT)
