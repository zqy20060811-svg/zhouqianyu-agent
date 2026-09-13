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
TOP_K = 10


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

    # 技能合并为一篇清单文档：避免十几条短切片挤占 top-k，稀释项目详情的召回
    skills = candidate.get("skills", []) or []
    if skills:
        skill_lines = [
            f"{s.get('name', '')}（{s.get('level', '')}，证据ID：{'、'.join(s.get('evidence_ids', []))}）"
            for s in skills
        ]
        add(
            "doc-skills",
            "skills",
            f"技能清单：{'；'.join(skill_lines)}",
        )

    for proj in candidate.get("projects", []) or []:
        pid = proj.get("id", "project")
        evidence_note = f"证据ID：{'、'.join(proj.get('evidence_ids', []))}"
        add(
            f"doc-{pid}-overview",
            "projects",
            f"项目：{proj.get('title', '')}。角色：{proj.get('role', '')}。"
            f"背景：{proj.get('context', '')} 要解决的问题：{proj.get('problem', '')} "
            f"技术栈：{'、'.join(proj.get('stack', []))}。{evidence_note}",
        )
        add(
            f"doc-{pid}-actions",
            "projects",
            f"项目 {proj.get('title', '')} 中负责的工作：{'；'.join(proj.get('actions', []))}。{evidence_note}",
        )
        add(
            f"doc-{pid}-results",
            "projects",
            f"项目 {proj.get('title', '')} 的成果：{'；'.join(proj.get('results', []))}。{evidence_note}",
        )

    for edu in candidate.get("education", []) or []:
        add(
            f"doc-{edu.get('id', 'education')}",
            "education",
            f"教育经历：{edu.get('school', '')}，{edu.get('degree', '')}，"
            f"专业 {edu.get('major', '')}，{edu.get('start', '')} 至 {edu.get('end', '')}。"
            f"证据ID：{'、'.join(edu.get('evidence_ids', []))}",
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
    """启动时重建索引（语料极小，重建成本可忽略），每次提问返回 top-k 文本片段。

    检索采用混合打分：向量相似度 + 查询字符二元组词法覆盖率各占一半。
    默认 embedding 对中文排序不稳定，词法信号能可靠地把含关键词的片段排上来。
    """

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

    @staticmethod
    def _grams(text: str) -> set[str]:
        """字符单字 + 二元组集合，兼顾中文关键词的鲁棒匹配。"""
        text = "".join(text.split()).lower()
        return set(text) | {text[i : i + 2] for i in range(len(text) - 1)}

    def retrieve(self, query: str, k: int = TOP_K) -> list[str]:
        total = self.collection.count()
        if total == 0:
            return []
        # 语料极小，直接取全部文档做混合打分，再截取 top-k
        result = self.collection.query(query_texts=[query], n_results=total)
        docs = list(result["documents"][0])
        dists = list(result["distances"][0])

        d_min, d_max = min(dists), max(dists)
        span = d_max - d_min or 1.0
        q_grams = self._grams(query)

        scored: list[tuple[float, str]] = []
        for doc, dist in zip(docs, dists):
            vector_score = (d_max - dist) / span  # 0-1，越大越相似
            lexical_score = len(q_grams & self._grams(doc)) / len(q_grams) if q_grams else 0.0
            scored.append((0.4 * vector_score + 0.6 * lexical_score, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored[:k]]
