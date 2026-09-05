"""Pydantic 数据模型,对应 data/*.json 的 schema。"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(extra="allow")


class Contact(_Base):
    phone: Optional[str] = None
    email: Optional[str] = None
    wechat: Optional[str] = None


class Profile(_Base):
    display_name: Optional[str] = None
    headline: Optional[str] = None
    location: Optional[str] = None
    years_experience: Optional[int] = None
    avatar_url: Optional[str] = None
    contact: Contact = Field(default_factory=Contact)


class Skill(_Base):
    name: str
    level: Optional[str] = None
    evidence_ids: list[str] = Field(default_factory=list)


class Link(_Base):
    label: Optional[str] = None
    url: Optional[str] = None


class Project(_Base):
    id: str
    title: str
    context: Optional[str] = None
    role: Optional[str] = None
    problem: Optional[str] = None
    actions: list[str] = Field(default_factory=list)
    results: list[str] = Field(default_factory=list)
    stack: list[str] = Field(default_factory=list)
    links: list[Link] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class Education(_Base):
    id: str
    school: str
    degree: Optional[str] = None
    major: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    evidence_ids: list[str] = Field(default_factory=list)


class EvidenceCard(_Base):
    id: str
    category: str
    title: str
    claim: str
    source_ref: Optional[str] = None
    source_url: Optional[str] = None


class Privacy(_Base):
    publish_confirmed: bool = False
    confirmed_at: Optional[str] = None
    allowed_public_contact_fields: list[str] = Field(default_factory=list)
    hidden_fields: list[str] = Field(default_factory=list)


class Candidate(_Base):
    schema_version: Optional[str] = None
    profile: Profile = Field(default_factory=Profile)
    target_roles: list[str] = Field(default_factory=list)
    summary: Optional[str] = None
    skills: list[Skill] = Field(default_factory=list)
    experiences: list[dict] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    links: list[Link] = Field(default_factory=list)
    evidence_cards: list[EvidenceCard] = Field(default_factory=list)
    privacy: Privacy = Field(default_factory=Privacy)


class AgentStyle(_Base):
    schema_version: Optional[str] = None
    site_template_version: Optional[str] = None
    voice: str = "steady-professional"
    answer_depth: Literal["concise", "balanced", "detailed"] = "balanced"
    emphasis: list[str] = Field(default_factory=list)
    language: str = "zh-CN"
    welcome_message: str = ""
    suggested_questions: list[str] = Field(default_factory=list)
    out_of_scope_message: str = ""
    insufficient_evidence_message: str = ""


class Presentation(_Base):
    schema_version: Optional[str] = None
    preset: Optional[str] = None
    accent: Optional[str] = None
    density: Optional[str] = None
    theme: Optional[str] = None


# ---- Chat 请求/响应 ----

class ChatHistoryItem(_Base):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(_Base):
    message: str
    history: list[ChatHistoryItem] = Field(default_factory=list)


class ModelAnswer(_Base):
    scope: Literal["in_scope", "out_of_scope", "insufficient_evidence"]
    answer: str
    citation_ids: list[str] = Field(default_factory=list)


class LLMOutput(_Base):
    """LLM 原始输出,供 PydanticOutputParser 解析。"""
    scope: Literal["in_scope", "out_of_scope", "insufficient_evidence"]
    answer: str
    citation_ids: list[str] = Field(default_factory=list)
