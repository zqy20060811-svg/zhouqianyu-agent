"""Streamlit 前端:招聘方对话界面 + 证据引用展示。"""
from __future__ import annotations

import os

import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
FASTAPI_BASE_URL = os.environ.get("FASTAPI_BASE_URL", "http://127.0.0.1:8787").rstrip("/")

st.set_page_config(page_title="AI 面试助理", page_icon="💼", layout="centered")


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


def render_resume(candidate: dict) -> None:
    """页面底部展示候选人简历基本信息（脱敏后无联系方式）。"""
    profile_data = candidate.get("profile", {})

    st.divider()
    st.header("个人简历")

    col1, col2, col3 = st.columns(3)
    col1.metric("姓名", profile_data.get("display_name") or "-")
    col2.metric("所在地", profile_data.get("location") or "-")
    years = profile_data.get("years_experience")
    col3.metric("工作年限", years if years else "在校")
    if profile_data.get("headline"):
        st.caption(profile_data["headline"])

    summary = candidate.get("summary")
    if summary:
        st.subheader("个人简介")
        st.write(summary)

    skills = candidate.get("skills", [])
    if skills:
        st.subheader("技能")
        cols = st.columns(min(len(skills), 4))
        for col, sk in zip(cols, skills):
            col.write(f"- {sk.get('name', '')} · {sk.get('level', '')}")

    projects = candidate.get("projects", [])
    if projects:
        st.subheader("项目经历")
        for p in projects:
            title = f"{p.get('title', '')} · {p.get('role', '')}"
            with st.expander(title, expanded=False):
                if p.get("context"):
                    st.write(p["context"])
                if p.get("stack"):
                    st.write("**技术栈：** " + " / ".join(p["stack"]))
                results = p.get("results", [])
                if results:
                    st.write("**成果：**")
                    for r in results:
                        st.write(f"- {r}")

    education = candidate.get("education", [])
    if education:
        st.subheader("教育背景")
        for e in education:
            period = f"{e.get('start', '')} - {e.get('end', '')}".strip(" -")
            st.write(
                f"- {e.get('school', '')} · {e.get('major', '')} · {e.get('degree', '')}"
                + (f"  ({period})" if period else "")
            )


def main() -> None:
    try:
        profile = fetch_profile()
    except Exception:
        st.error("无法连接后端服务,请确认 FastAPI 已启动。")
        return

    candidate = profile["candidate"]
    style = profile["style"]

    profile_data = candidate.get("profile", {})
    st.title(f"{profile_data.get('display_name', '候选人')} · AI 面试助理")
    if profile_data.get("headline"):
        st.caption(profile_data["headline"])

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

    render_resume(candidate)


if __name__ == "__main__":
    main()
