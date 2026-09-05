"""Streamlit 前端:招聘方对话界面 + 证据引用展示。"""
from __future__ import annotations

import os

import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
FASTAPI_BASE_URL = os.environ.get("FASTAPI_BASE_URL", "http://127.0.0.1:8787").rstrip("/")

st.set_page_config(page_title="AI 面试助理", page_icon="💼", layout="centered")

# ---- 全局主题 ----
st.markdown(
    """
    <style>
    :root {
        --brand: #4f46e5;
        --brand-light: #eef2ff;
        --text: #1f2937;
        --muted: #6b7280;
    }
    .stApp {background: linear-gradient(180deg,#f8f9ff 0%,#fafafa 60%);}
    /* 标题区卡片 */
    .hero-card {
        background: linear-gradient(135deg,#4f46e5,#7c3aed);
        color:#fff;
        padding:28px 32px;
        border-radius:16px;
        margin:0 0 16px 0;
        box-shadow:0 4px 20px rgba(79,70,229,.18);
    }
    .hero-card .name {font-size:26px;font-weight:700;margin-bottom:4px;}
    .hero-card .role {font-size:14px;opacity:.9;margin-bottom:10px;}
    .hero-card .meta {font-size:12px;opacity:.75;display:flex;gap:14px;}
    /* 隐藏默认 h1(用自定义 hero 代替) */
    .block-container h1 {display:none !important;}
    /* 推荐问题胶囊标签 */
    div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"] button[kind="secondary"] {
        font-size:12px !important;
        font-weight:500 !important;
        padding:3px 12px !important;
        min-height:30px !important;
        height:30px !important;
        border-radius:15px !important;
        background:#fff !important;
        border:1px solid #e0e0e0 !important;
        color:var(--text) !important;
        margin:0 3px 6px 0 !important;
        transition:all .15s;
    }
    div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"] button[kind="secondary"]:hover {
        background:var(--brand-light) !important;
        border-color:var(--brand) !important;
        color:var(--brand) !important;
        transform:translateY(-1px);
    }
    /* chat_input 紧贴推荐 */
    div[data-testid="stChatInput"] {margin-top:-8px !important;}
    /* 聊天消息气泡 */
    [data-testid="stChatMessage"] [data-testid="stMarkdown"] {
        background:#fff;
        padding:10px 14px;
        border-radius:12px;
        border:1px solid #f0f0f0;
    }
    div[data-testid="chatmessage-user"] [data-testid="stMarkdown"] {
        background:var(--brand-light);
        border-color:#e0e7ff;
    }
    /* expander */
    [data-testid="stExpander"] details summary {font-weight:600;}
    hr {border-color:#e5e7eb;margin:12px 0;}
    /* 隐藏 Deploy */
    [data-testid='stAppDeployButton']{display:none !important;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=60)
def fetch_profile() -> dict:
    r = httpx.get(f"{FASTAPI_BASE_URL}/api/profile", timeout=10)
    r.raise_for_status()
    return r.json()


def render_citations(citation_ids: list[str], candidate: dict) -> None:
    cards = {c["id"]: c for c in candidate.get("evidence_cards", []) if isinstance(c, dict) and c.get("id")}
    items = [cards[i] for i in citation_ids if i in cards]
    if not items:
        return
    with st.expander(f"证据引用（{len(items)}）", expanded=False):
        for card in items:
            st.write(f"**{card.get('title', '')}**")
            st.write(card.get("claim", ""))
            if card.get("source_url"):
                st.markdown(f"[来源]({card['source_url']})")


def render_intro(candidate: dict) -> None:
    """页面底部:紧凑的个人介绍卡片,默认折叠。"""
    p = candidate.get("profile", {})

    st.divider()
    with st.expander("👤 关于我", expanded=False):
        # 顶部:姓名 + headline + 地点,一行搞定
        name = p.get("display_name", "")
        headline = p.get("headline", "")
        location = p.get("location", "")
        parts = [f"**{name}**"] if name else []
        if headline:
            parts.append(headline)
        if location:
            parts.append(f"📍 {location}")
        st.markdown(" · ".join(parts))

        # 个人简介
        summary = candidate.get("summary")
        if summary:
            st.write(summary)

        # 技能标签(一行展示,每个技能一个小标签)
        skills = candidate.get("skills", [])
        if skills:
            tags = " ".join(
                f"<span style='background:#f0f2f6;padding:2px 8px;border-radius:8px;font-size:13px;margin:2px;'>{s.get('name','')}</span>"
                for s in skills
            )
            st.markdown(f"<div style='margin:8px 0;'>{tags}</div>", unsafe_allow_html=True)

        # 项目:简化一行一个
        projects = candidate.get("projects", [])
        if projects:
            st.write("**项目经历**")
            for proj in projects:
                title = proj.get("title", "")
                stack = " / ".join(proj.get("stack", []))
                line = f"- **{title}**"
                if stack:
                    line += f" — {stack}"
                st.write(line)

        # 教育:一行
        edu = candidate.get("education", [])
        if edu:
            e = edu[0]
            period = f"{e.get('start','')}–{e.get('end','')}"
            st.write(f"**教育**: {e.get('school','')} · {e.get('major','')} · {e.get('degree','')} · {period}")


def main() -> None:
    try:
        profile = fetch_profile()
    except Exception:
        st.error("无法连接后端服务,请确认 FastAPI 已启动。")
        return

    candidate = profile["candidate"]
    style = profile["style"]

    profile_data = candidate.get("profile", {})
    name = profile_data.get("display_name", "候选人")
    headline = profile_data.get("headline", "")
    location = profile_data.get("location", "")
    target_roles = candidate.get("target_roles", [])
    # 顶部卡片标题
    roles_str = " / ".join(target_roles[:2]) if target_roles else ""
    meta_parts = []
    if location:
        meta_parts.append(f"📍 {location}")
    if roles_str:
        meta_parts.append(f"🎯 {roles_str}")
    st.markdown(
        f"""
        <div class="hero-card">
            <div class="name">💼 {name} · AI 面试助理</div>
            <div class="role">{headline}</div>
            <div class="meta">{" ".join(meta_parts)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.session_state.setdefault("history", [])

    with st.chat_message("assistant"):
        st.markdown(style.get("welcome_message", ""))

    suggested = style.get("suggested_questions", [])
    if suggested:
        st.write("**推荐问题**")
        cols = st.columns(min(len(suggested), 3))
        for col, q in zip(cols, suggested):
            if col.button(q, key=f"sq-{q}"):
                st.session_state["pending_question"] = q

    for msg in st.session_state["history"]:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                st.markdown(msg["content"])
                render_citations(msg.get("citation_ids", []), candidate)
            else:
                st.markdown(msg["content"])

    pending = st.session_state.pop("pending_question", None)

    MAX_TURNS = 15
    user_turns = sum(1 for m in st.session_state["history"] if m["role"] == "user")
    if user_turns >= MAX_TURNS:
        st.info("本会话已达对话上限（15 轮），如需继续请刷新页面重开。")
        render_intro(candidate)
        return

    question = st.chat_input("向 AI 面试助理提问...") or pending

    if question:
        st.session_state["history"].append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        history_payload = [
            {"role": m["role"], "content": m["content"]} for m in st.session_state["history"]
        ]
        with st.chat_message("assistant"):
            with st.spinner("正在生成回答..."):
                try:
                    resp = httpx.post(
                        f"{FASTAPI_BASE_URL}/api/chat",
                        json={"message": question, "history": history_payload},
                        timeout=60,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                except Exception:
                    data = {
                        "scope": "insufficient_evidence",
                        "answer": "面试助理暂时无法回答,你仍可以继续浏览候选人资料。",
                        "citation_ids": [],
                    }
            st.markdown(data.get("answer", ""))
            citation_ids = data.get("citation_ids", [])
            render_citations(citation_ids, candidate)
            st.session_state["history"].append(
                {"role": "assistant", "content": data.get("answer", ""), "citation_ids": citation_ids}
            )

    render_intro(candidate)


if __name__ == "__main__":
    main()
