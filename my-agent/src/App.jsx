import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowDown,
  ArrowUpRight,
  Bot,
  BriefcaseBusiness,
  CircleAlert,
  FileCheck2,
  GraduationCap,
  MapPin,
  Moon,
  Send,
  Sun,
} from "lucide-react";

const API_PROFILE = "/api/profile";
const API_CHAT = "/api/chat";

function initials(name = "候选人") {
  return name.trim().slice(0, 2).toUpperCase();
}

function formatPeriod(start, end) {
  if (!start && !end) return "";
  return `${start || ""} — ${end || "至今"}`;
}

function evidenceLabel(card) {
  return card?.title || "候选人证据";
}

function safeHttpUrl(value) {
  if (typeof value !== "string") return null;
  try {
    const url = new URL(value);
    const http = url.protocol === "http:" || url.protocol === "https:";
    return http && !url.username && !url.password ? url.href : null;
  } catch {
    return null;
  }
}

function LoadingPage() {
  return (
    <main className="state-page" aria-live="polite">
      <div className="state-mark"><Bot size={24} /></div>
      <strong>正在加载候选人资料</strong>
      <span className="state-line" />
    </main>
  );
}

function ErrorPage({ onRetry }) {
  return (
    <main className="state-page" role="alert">
      <div className="state-mark is-error"><CircleAlert size={24} /></div>
      <strong>暂时无法读取候选人资料</strong>
      <p>请检查服务状态后重试。</p>
      <button type="button" className="command-button" onClick={onRetry}>重新加载</button>
    </main>
  );
}

function ThemeButton({ theme, onToggle }) {
  const dark = theme === "dark";
  return (
    <button
      type="button"
      className="icon-button"
      onClick={onToggle}
      aria-label={dark ? "切换为浅色模式" : "切换为深色模式"}
      title={dark ? "浅色模式" : "深色模式"}
    >
      {dark ? <Sun size={18} /> : <Moon size={18} />}
    </button>
  );
}

function Identity({ candidate, evidenceCount, theme, onToggleTheme }) {
  const { profile, target_roles: roles = [] } = candidate;
  return (
    <header className="identity-bar">
      <div className="identity-main">
        {profile.avatar_url ? (
          <img className="identity-avatar" src={profile.avatar_url} alt={`${profile.display_name}的头像`} />
        ) : (
          <div className="identity-avatar is-initials" aria-hidden="true">{initials(profile.display_name)}</div>
        )}
        <div className="identity-copy">
          <span>{roles[0] || "求职候选人"}</span>
          <strong>{profile.display_name}</strong>
        </div>
      </div>
      <div className="identity-meta">
        <span><FileCheck2 size={15} />{evidenceCount} 条公开证据</span>
        {profile.location ? <span><MapPin size={15} />{profile.location}</span> : null}
        <ThemeButton theme={theme} onToggle={onToggleTheme} />
      </div>
    </header>
  );
}

function ChatMessage({ message, evidenceById, onEvidence }) {
  const assistant = message.role === "assistant";
  return (
    <article className={`chat-message ${assistant ? "is-assistant" : "is-user"}`}>
      {assistant ? <div className="message-avatar" aria-hidden="true"><Bot size={16} /></div> : null}
      <div className="message-body">
        <span className="message-role">{assistant ? "面试 Agent" : "招聘方"}</span>
        <p>{message.content}</p>
        {message.citations?.length ? (
          <div className="message-citations" aria-label="回答依据">
            {message.citations.map((id) => (
              <button type="button" key={id} onClick={() => onEvidence(id)}>
                <FileCheck2 size={14} />
                <span>{evidenceLabel(evidenceById.get(id))}</span>
                <ArrowDown size={13} />
              </button>
            ))}
          </div>
        ) : null}
      </div>
    </article>
  );
}

function ThinkingMessage() {
  return (
    <article className="chat-message is-assistant" aria-live="polite">
      <div className="message-avatar" aria-hidden="true"><Bot size={16} /></div>
      <div className="message-body is-thinking">
        <span className="message-role">正在核对候选人证据</span>
        <div className="thinking-dots" aria-hidden="true"><i /><i /><i /></div>
      </div>
    </article>
  );
}

function ChatConsole({ candidate, style, evidenceById, onEvidence }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const listRef = useRef(null);

  useEffect(() => {
    setMessages([
      {
        id: "welcome",
        role: "assistant",
        content: style.welcome_message,
        citations: [],
      },
    ]);
  }, [style.welcome_message]);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, sending]);

  async function sendQuestion(rawQuestion) {
    const question = rawQuestion.trim();
    if (!question || sending) return;

    const userMessage = { id: crypto.randomUUID(), role: "user", content: question, citations: [] };
    const history = messages
      .filter((message) => !message.isError)
      .slice(-8)
      .map(({ role, content }) => ({ role, content }));

    setMessages((current) => [...current, userMessage]);
    setInput("");
    setError("");
    setSending(true);

    try {
      const response = await fetch(API_CHAT, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ message: question, history }),
      });
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body?.error?.message || "面试助理暂时无法回答。");
      }
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: body.answer,
          citations: body.citation_ids || [],
        },
      ]);
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : "面试助理暂时无法回答。";
      setError(message);
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: message,
          citations: [],
          isError: true,
        },
      ]);
    } finally {
      setSending(false);
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    void sendQuestion(input);
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  const showSuggestions = messages.filter((message) => message.role === "user").length === 0;

  return (
    <section className="chat-console" aria-label={`${candidate.profile.display_name}的面试对话`}>
      <div className="chat-console-head">
        <div>
          <span className="online-dot" />
          <strong>向 {candidate.profile.display_name} 的面试 Agent 提问</strong>
        </div>
        <small>回答以公开证据为准</small>
      </div>

      <div className="chat-history" ref={listRef} aria-live="polite">
        {messages.map((message) => (
          <ChatMessage
            key={message.id}
            message={message}
            evidenceById={evidenceById}
            onEvidence={onEvidence}
          />
        ))}
        {sending ? <ThinkingMessage /> : null}
      </div>

      <div className="chat-actions">
        {showSuggestions ? (
          <div className="suggested-questions" aria-label="推荐问题">
            {style.suggested_questions.map((question) => (
              <button type="button" key={question} onClick={() => void sendQuestion(question)}>
                <span>{question}</span><ArrowUpRight size={14} />
              </button>
            ))}
          </div>
        ) : null}
        <form className="composer" onSubmit={handleSubmit}>
          <label htmlFor="interview-question" className="sr-only">向面试 Agent 提问</label>
          <textarea
            id="interview-question"
            value={input}
            onChange={(event) => setInput(event.target.value.slice(0, 500))}
            onKeyDown={handleKeyDown}
            placeholder="询问项目职责、技术取舍或岗位匹配度"
            rows={1}
            disabled={sending}
          />
          {input.length >= 420 ? <span className="character-count">{input.length}/500</span> : null}
          <button type="submit" className="send-button" disabled={!input.trim() || sending} aria-label="发送问题">
            <Send size={18} />
          </button>
        </form>
        {error ? <p className="composer-status" role="status">资料页面仍可继续浏览。</p> : null}
      </div>
    </section>
  );
}

function EvidenceButtons({ ids = [], evidenceById, onEvidence }) {
  if (!ids.length) return null;
  return (
    <div className="inline-evidence" aria-label="相关证据">
      {ids.map((id) => (
        <button type="button" key={id} onClick={() => onEvidence(id)}>
          <FileCheck2 size={13} />{evidenceLabel(evidenceById.get(id))}
        </button>
      ))}
    </div>
  );
}

function PublicLinks({ links = [] }) {
  const publicLinks = links
    .map((link) => ({ ...link, safeUrl: safeHttpUrl(link?.url) }))
    .filter((link) => link.safeUrl);
  if (!publicLinks.length) return null;

  return (
    <div className="public-links" aria-label="公开链接">
      {publicLinks.map((link) => (
        <a key={`${link.label || "link"}-${link.safeUrl}`} href={link.safeUrl} target="_blank" rel="noreferrer">
          <span>{link.label || "查看公开链接"}</span><ArrowUpRight size={14} />
        </a>
      ))}
    </div>
  );
}

function ProfileDocument({ candidate, evidenceById, activeEvidence, onEvidence }) {
  const { profile } = candidate;
  const contacts = Object.entries(profile.contact || {});

  return (
    <section className="profile-document" id="profile" aria-labelledby="profile-title">
      <div className="profile-shell">
        <main className="profile-main">
          <header className="profile-intro">
            <span className="section-kicker">候选人公开资料</span>
            <h1 id="profile-title">{profile.display_name}</h1>
            <p className="profile-headline">{profile.headline}</p>
            <p className="profile-summary">{candidate.summary}</p>
            <div className="profile-facts">
              {profile.location ? <span><MapPin size={16} />{profile.location}</span> : null}
              {profile.years_experience != null ? <span><BriefcaseBusiness size={16} />{profile.years_experience} 年相关经历</span> : null}
              {candidate.target_roles?.map((role) => <span key={role}>{role}</span>)}
            </div>
            {contacts.length ? (
              <div className="public-contact">
                {contacts.map(([key, value]) => (
                  <a key={key} href={key === "email" ? `mailto:${value}` : key === "phone" ? `tel:${value}` : undefined}>
                    {key}: {value}
                  </a>
                ))}
              </div>
            ) : null}
            <PublicLinks links={candidate.links} />
          </header>

          {candidate.skills?.length ? (
            <section className="profile-section" aria-labelledby="skills-title">
              <div className="section-heading"><span>能力与证据</span><h2 id="skills-title">实际使用过的技能</h2></div>
              <div className="skill-list">
                {candidate.skills.map((skill) => (
                  <article key={skill.name} data-evidence={skill.evidence_ids?.join(" ")} className={skill.evidence_ids?.includes(activeEvidence) ? "is-highlighted" : ""}>
                    <strong>{skill.name}</strong>
                    {skill.level ? <span>{skill.level}</span> : null}
                    <EvidenceButtons ids={skill.evidence_ids} evidenceById={evidenceById} onEvidence={onEvidence} />
                  </article>
                ))}
              </div>
            </section>
          ) : null}

          {candidate.projects?.length ? (
            <section className="profile-section" aria-labelledby="projects-title">
              <div className="section-heading"><span>代表项目</span><h2 id="projects-title">做了什么，为什么这样做</h2></div>
              <div className="project-list">
                {candidate.projects.map((project, index) => (
                  <article
                    className={`project-item ${project.evidence_ids?.includes(activeEvidence) ? "is-highlighted" : ""}`}
                    key={project.id}
                    data-evidence={project.evidence_ids?.join(" ")}
                  >
                    <header>
                      <span>{String(index + 1).padStart(2, "0")}</span>
                      <div><h3>{project.title}</h3><p>{project.role}</p></div>
                    </header>
                    <p className="project-context">{project.context}</p>
                    <div className="project-detail">
                      <div><span>问题</span><p>{project.problem}</p></div>
                      <div><span>行动</span><ul>{project.actions?.map((item) => <li key={item}>{item}</li>)}</ul></div>
                      <div><span>结果</span><ul>{project.results?.map((item) => <li key={item}>{item}</li>)}</ul></div>
                    </div>
                    {project.stack?.length ? <div className="stack-list">{project.stack.map((item) => <span key={item}>{item}</span>)}</div> : null}
                    <PublicLinks links={project.links} />
                    <EvidenceButtons ids={project.evidence_ids} evidenceById={evidenceById} onEvidence={onEvidence} />
                  </article>
                ))}
              </div>
            </section>
          ) : null}

          {candidate.experiences?.length ? (
            <section className="profile-section" aria-labelledby="experience-title">
              <div className="section-heading"><span>工作经历</span><h2 id="experience-title">角色与责任边界</h2></div>
              <div className="timeline">
                {candidate.experiences.map((experience) => (
                  <article key={experience.id} data-evidence={experience.evidence_ids?.join(" ")} className={experience.evidence_ids?.includes(activeEvidence) ? "is-highlighted" : ""}>
                    <div className="timeline-period">{formatPeriod(experience.start, experience.end)}</div>
                    <div><h3>{experience.role}</h3><strong>{experience.organization}</strong><ul>{experience.highlights?.map((item) => <li key={item}>{item}</li>)}</ul><EvidenceButtons ids={experience.evidence_ids} evidenceById={evidenceById} onEvidence={onEvidence} /></div>
                  </article>
                ))}
              </div>
            </section>
          ) : null}

          {candidate.education?.length ? (
            <section className="profile-section" aria-labelledby="education-title">
              <div className="section-heading"><span>教育背景</span><h2 id="education-title">学习经历</h2></div>
              <div className="education-list">
                {candidate.education.map((item) => (
                  <article key={`${item.school}-${item.start}`}>
                    <GraduationCap size={20} />
                    <div><h3>{item.school}</h3><p>{item.degree} · {item.field}</p></div>
                    <span>{formatPeriod(item.start, item.end)}</span>
                  </article>
                ))}
              </div>
            </section>
          ) : null}
        </main>

        <aside className="evidence-rail" aria-labelledby="evidence-title">
          <header><span>Evidence rail</span><h2 id="evidence-title">公开证据</h2><p>Agent 的事实回答只能引用这里的内容。</p></header>
          <div>
            {candidate.evidence_cards?.map((card) => {
              const sourceUrl = safeHttpUrl(card.source_url);
              return (
                <article
                  id={`evidence-${card.id}`}
                  key={card.id}
                  className={activeEvidence === card.id ? "is-active" : ""}
                >
                  <button type="button" onClick={() => onEvidence(card.id)}>
                    <span>{card.category}</span><strong>{card.title}</strong><p>{card.claim}</p>
                  </button>
                  {sourceUrl ? <a href={sourceUrl} target="_blank" rel="noreferrer">查看公开来源<ArrowUpRight size={14} /></a> : null}
                </article>
              );
            })}
          </div>
        </aside>
      </div>
    </section>
  );
}

export default function App() {
  const [profileData, setProfileData] = useState(null);
  const [loadError, setLoadError] = useState(false);
  const [theme, setTheme] = useState("dark");
  const [activeEvidence, setActiveEvidence] = useState("");
  const highlightTimer = useRef(null);

  async function loadProfile() {
    setLoadError(false);
    try {
      const response = await fetch(API_PROFILE, { headers: { accept: "application/json" } });
      if (!response.ok) throw new Error("profile unavailable");
      const body = await response.json();
      setProfileData(body);
      const storedTheme = localStorage.getItem("interview-agent-theme");
      setTheme(storedTheme === "light" || storedTheme === "dark" ? storedTheme : body.presentation.theme);
    } catch {
      setLoadError(true);
    }
  }

  useEffect(() => {
    void loadProfile();
    return () => clearTimeout(highlightTimer.current);
  }, []);

  useEffect(() => {
    if (!profileData) return;
    const root = document.documentElement;
    root.dataset.theme = theme;
    root.dataset.preset = profileData.presentation.preset;
    root.dataset.accent = profileData.presentation.accent;
    root.dataset.density = profileData.presentation.density;
    root.style.colorScheme = theme;
    document.title = `${profileData.candidate.profile.display_name}｜面试 Agent`;
  }, [profileData, theme]);

  const evidenceById = useMemo(
    () => new Map((profileData?.candidate.evidence_cards || []).map((card) => [card.id, card])),
    [profileData],
  );

  function toggleTheme() {
    setTheme((current) => {
      const next = current === "dark" ? "light" : "dark";
      localStorage.setItem("interview-agent-theme", next);
      return next;
    });
  }

  function revealEvidence(id) {
    setActiveEvidence(id);
    clearTimeout(highlightTimer.current);
    const target = document.getElementById(`evidence-${id}`) || document.querySelector(`[data-evidence~="${CSS.escape(id)}"]`);
    target?.scrollIntoView({ behavior: "smooth", block: "center" });
    highlightTimer.current = setTimeout(() => setActiveEvidence(""), 2_400);
  }

  if (loadError) return <ErrorPage onRetry={() => void loadProfile()} />;
  if (!profileData) return <LoadingPage />;

  const { candidate, style } = profileData;
  return (
    <main>
      <section className="chat-stage" id="top">
        <Identity
          candidate={candidate}
          evidenceCount={candidate.evidence_cards?.length || 0}
          theme={theme}
          onToggleTheme={toggleTheme}
        />
        <div className="chat-stage-inner">
          <ChatConsole candidate={candidate} style={style} evidenceById={evidenceById} onEvidence={revealEvidence} />
        </div>
        <a className="profile-jump" href="#profile"><span>查看候选人完整资料</span><ArrowDown size={17} /></a>
      </section>

      <ProfileDocument candidate={candidate} evidenceById={evidenceById} activeEvidence={activeEvidence} onEvidence={revealEvidence} />
      <footer className="site-footer"><span>{candidate.profile.display_name} · Interview Agent</span><a href="#top">返回对话</a></footer>
    </main>
  );
}
