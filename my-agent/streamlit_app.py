"""Streamlit 前端：档案式个人主页 + 面试助理对话（证据引用展示）。

视觉方向为「可对话的档案卷宗」：纸白底、墨蓝正文、深青强调，
姓名用衬线大字作为全页唯一的大胆元素，其余保持克制。
"""
from __future__ import annotations

import os

import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
FASTAPI_BASE_URL = os.environ.get("FASTAPI_BASE_URL", "http://127.0.0.1:8787").rstrip("/")

st.set_page_config(page_title="周黔豫 · AI 面试助理", page_icon="🗂", layout="centered")

# ---- 全局主题：档案卷宗 ----
st.markdown(
    """
    <style>
    :root {
        --ink: #17242E;        /* 墨蓝正文 */
        --paper: #FFFFFF;      /* 纸白底 */
        --accent: #0F766E;     /* 深青强调 */
        --accent-ink: #0B5A54;
        --accent-tint: #EEF6F4;
        --muted: #64748B;      /* 冷灰辅助 */
        --line: #E2E8F0;       /* 细规则线 */
    }
    .stApp {background: var(--paper); color: var(--ink);}
    .block-container {padding-top: 3rem; max-width: 46rem;}
    /* 隐藏默认标题与 Deploy */
    .block-container h1 {display: none !important;}
    [data-testid='stAppDeployButton'] {display: none !important;}

    /* 卷宗头：衬线大字姓名 + 规则线 */
    .dossier-name {
        font-family: "Noto Serif SC", "Source Han Serif SC", "STSong", "SimSun", Georgia, serif;
        font-size: 42px; font-weight: 700; letter-spacing: .05em;
        color: var(--ink); line-height: 1.2; margin: 0;
    }
    .dossier-headline {font-size: 16px; color: var(--ink); margin-top: 10px;}
    .dossier-meta {font-size: 13px; color: var(--muted); margin-top: 4px;}
    .dossier-rule {height: 2px; background: var(--ink); margin-top: 18px;}
    .dossier-rule-accent {height: 2px; width: 72px; background: var(--accent); margin-bottom: 22px;}

    /* 推荐问题：安静的描边按钮 */
    div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"] button[kind="secondary"] {
        font-size: 13px !important; font-weight: 400 !important;
        padding: 6px 14px !important; min-height: 0 !important;
        border-radius: 4px !important; background: var(--paper) !important;
        border: 1px solid var(--line) !important; color: var(--ink) !important;
        transition: border-color .15s, color .15s;
    }
    div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"] button[kind="secondary"]:hover {
        border-color: var(--accent) !important; color: var(--accent-ink) !important;
    }

    /* 对话：用户消息浅青底，助手消息直接落在纸面上 */
    div[data-testid="chatmessage-user"] [data-testid="stMarkdown"] {
        background: var(--accent-tint); border-radius: 6px; padding: 10px 14px;
    }
    [data-testid="stChatMessage"] {background: transparent;}

    /* 证据卡：左侧深青竖线 */
    .evidence-card {
        border-left: 3px solid var(--accent);
        background: #F8FAFA;
        padding: 8px 12px; margin: 6px 0;
    }
    .evidence-card .ev-title {font-weight: 600; font-size: 14px; color: var(--ink);}
    .evidence-card .ev-claim {font-size: 13px; color: var(--muted); margin-top: 2px;}

    /* 技能标签：中性描边，不做胶囊墙 */
    .skill-tag {
        display: inline-block; border: 1px solid var(--line); border-radius: 4px;
        padding: 1px 8px; font-size: 12px; color: var(--muted); margin: 2px 4px 2px 0;
    }

    [data-testid="stExpander"] details summary {font-weight: 600;}
    hr {border-color: var(--line); margin: 12px 0;}
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
            source = ""
            if card.get("source_url"):
                source = f'<a href="{card["source_url"]}">来源</a>'
            st.markdown(
                f"""<div class="evidence-card">
                    <div class="ev-title">{card.get('title', '')}</div>
                    <div class="ev-claim">{card.get('claim', '')} {source}</div>
                </div>""",
                unsafe_allow_html=True,
            )


def render_intro(candidate: dict) -> None:
    """页面底部：档案全文，默认折叠。"""
    p = candidate.get("profile", {})

    st.divider()
    with st.expander("🗂 档案全文", expanded=False):
        name = p.get("display_name", "")
        headline = p.get("headline", "")
        location = p.get("location", "")
        parts = [f"**{name}**"] if name else []
        if headline:
            parts.append(headline)
        if location:
            parts.append(f"{location}")
        st.markdown("，".join(parts))

        contact = p.get("contact", {}) or {}
        contact_parts = []
        if contact.get("phone"):
            contact_parts.append(f"📱 {contact['phone']}")
        if contact.get("email"):
            contact_parts.append(f"✉️ {contact['email']}")
        if contact_parts:
            st.markdown(" ｜ ".join(contact_parts))

        summary = candidate.get("summary")
        if summary:
            st.write(summary)

        links = candidate.get("links", []) or []
        if links:
            st.write("**个人作品**")
            for lk in links:
                label = lk.get("label", "链接")
                url = lk.get("url", "")
                if url:
                    st.markdown(f"- [{label}]({url})")

        skills = candidate.get("skills", [])
        if skills:
            tags = " ".join(
                f"<span class='skill-tag'>{s.get('name','')}</span>" for s in skills
            )
            st.markdown(f"<div style='margin:8px 0;'>{tags}</div>", unsafe_allow_html=True)

        projects = candidate.get("projects", [])
        if projects:
            st.write("**项目经历**")
            for proj in projects:
                title = proj.get("title", "")
                stack = " / ".join(proj.get("stack", []))
                line = f"- **{title}**"
                if stack:
                    line += f" — {stack}"
                for lk in proj.get("links", []) or []:
                    if lk.get("url"):
                        line += f" · [{lk.get('label', '链接')}]({lk['url']})"
                st.write(line)

        edu = candidate.get("education", [])
        if edu:
            e = edu[0]
            period = f"{e.get('start','')}–{e.get('end','')}"
            st.write(f"**教育**：{e.get('school','')}，{e.get('major','')}，{e.get('degree','')}，{period}")


def render_dossier_header(candidate: dict) -> None:
    profile_data = candidate.get("profile", {})
    name = profile_data.get("display_name", "候选人")
    headline = profile_data.get("headline", "")
    location = profile_data.get("location", "")
    target_roles = candidate.get("target_roles", [])

    meta_bits = []
    if location:
        meta_bits.append(f"坐标 {location}")
    if target_roles:
        meta_bits.append(f"目标岗位：{'、'.join(target_roles)}")
    st.markdown(
        f"""
        <div class="dossier-name">{name}</div>
        <div class="dossier-headline">{headline}</div>
        <div class="dossier-meta">{'，'.join(meta_bits)}</div>
        <div class="dossier-rule"></div>
        <div class="dossier-rule-accent"></div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    try:
        profile = fetch_profile()
    except Exception:
        st.error("无法连接后端服务，请确认 FastAPI 已启动。")
        return

    candidate = profile["candidate"]
    style = profile["style"]

    render_dossier_header(candidate)

    st.session_state.setdefault("history", [])

    with st.chat_message("assistant"):
        st.markdown(style.get("welcome_message", ""))

    suggested = style.get("suggested_questions", [])
    if suggested:
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

    question = st.chat_input("向 AI 面试助理提问…") or pending

    if question:
        st.session_state["history"].append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        history_payload = [
            {"role": m["role"], "content": m["content"]} for m in st.session_state["history"]
        ]
        with st.chat_message("assistant"):
            with st.spinner("正在检索档案并生成回答…"):
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
                        "answer": "面试助理暂时无法回答，你仍可以继续浏览候选人资料。",
                        "citation_ids": [],
                    }
            st.markdown(data.get("answer", ""))
            render_citations(data.get("citation_ids", []), candidate)

        st.session_state["history"].append(
            {
                "role": "assistant",
                "content": data.get("answer", ""),
                "citation_ids": data.get("citation_ids", []),
            }
        )

    render_intro(candidate)


if __name__ == "__main__":
    main()
