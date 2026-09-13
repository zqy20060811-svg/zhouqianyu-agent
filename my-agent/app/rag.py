"""极简 RAG 链路：Chroma 持久化向量检索个人简历语料。

语料只有候选人自己的资料（data/candidate.json），链路只有三步：
1. 启动时把 candidate.json 切分成小文档，embedding 后存入本地 Chroma（data/chroma）
2. 每次提问用问题做相似度检索，取 top-k 片段
3. 片段注入 system prompt，替代全量简历
"""
from __future__ import annotations

import chromadb

from .config import DATA_DIR

CHROMA_DIR = DATA_DIR / "chroma"
COLLECTION_NAME = "resume"
TOP_K = 8


def build_documents(candidate: dict) -> tuple[list[str], list[str], list[dict]]:
    """把候选人资料切分成检索用小文档，返回 (documents, ids, metadatas)。"""
    docs: list[str] = []
    ids: list[str] = []
    metas: list[dict] = []

    def add(doc_id: str, section: str, text: str) -> None:
        text = " ".join(text.split())
        if not text.strip():
            return
        ids.append(doc_id)
        docs.append(text)
        metas.append({"section": section})

    profile = candidate.get("profile", {}) or {}
    add(
        "doc-profile",
        "profile",
        f"候选人 {profile.get('display_name', '')}，{profile.get('headline', '')}，"
        f"坐标 {profile.get('location', '')}。目标岗位：{'、'.join(candidate.get('target_roles', []))}。"
        f"个人总结：{candidate.get('summary', '')}",
    )

    for i, skill in enumerate(candidate.get("skills", []) or []):
        add(
            f"doc-skill-{i}",
            "skills",
            f"技能：{skill.get('name', '')}，熟练程度：{skill.get('level', '')}",
        )

    for proj in candidate.get("projects", []) or []:
        pid = proj.get("id", "project")
        add(
            f"doc-{pid}-overview",
            "projects",
            f"项目：{proj.get('title', '')}。角色：{proj.get('role', '')}。"
            f"背景：{proj.get('context', '')} 要解决的问题：{proj.get('problem', '')} "
            f"技术栈：{'、'.join(proj.get('stack', []))}",
        )
        add(
            f"doc-{pid}-actions",
            "projects",
            f"项目 {proj.get('title', '')} 中负责的工作：{'；'.join(proj.get('actions', []))}",
        )
        add(
            f"doc-{pid}-results",
            "projects",
            f"项目 {proj.get('title', '')} 的成果：{'；'.join(proj.get('results', []))}",
        )

    for edu in candidate.get("education", []) or []:
        add(
            f"doc-{edu.get('id', 'education')}",
            "education",
            f"教育经历：{edu.get('school', '')}，{edu.get('degree', '')}，"
            f"专业 {edu.get('major', '')}，{edu.get('start', '')} 至 {edu.get('end', '')}",
        )

    for card in candidate.get("evidence_cards", []) or []:
        add(
            f"doc-{card.get('id', 'evidence')}",
            "evidence_cards",
            f"证据卡 {card.get('id', '')}（{card.get('category', '')}）："
            f"{card.get('title', '')}。{card.get('claim', '')}",
        )

    return docs, ids, metas


class ResumeRetriever:
    """启动时重建索引（语料极小，重建成本可忽略），每次提问返回 top-k 文本片段。"""

    def __init__(self, candidate: dict) -> None:
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass  # 首次启动时集合不存在
        self.collection = client.get_or_create_collection(COLLECTION_NAME)
        docs, ids, metas = build_documents(candidate)
        if docs:
            self.collection.add(ids=ids, documents=docs, metadatas=metas)

    def retrieve(self, query: str, k: int = TOP_K) -> list[str]:
        total = self.collection.count()
        if total == 0:
            return []
        result = self.collection.query(query_texts=[query], n_results=min(k, total))
        return list(result["documents"][0])
