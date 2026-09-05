# 面试 Agent 网站

基于 Streamlit + FastAPI + LangChain + LangSmith 的自部署面试对话网站。招聘方在 Streamlit 界面提问,FastAPI 后端用 LangChain 调用 OpenAI 兼容 LLM,LangSmith 全程追踪调用与回答质量。

## 架构

```
招聘方浏览器
    │
    ▼
Streamlit 前端 (streamlit_app.py, 端口 8501)
    │  chat_input → POST /api/chat
    │  渲染聊天消息 + 证据引用
    ▼
FastAPI 后端 (app/main.py, 端口 8787)
    │  输入校验 (app/policy.py)
    │  数据脱敏
    │  构建系统提示词
    ▼
LangChain Chain (app/provider.py)
    │  ChatOpenAI → PydanticOutputParser
    │  自动结构化输出 + 证据校验
    ▼
LLM API (OpenAI 兼容, MODEL_BASE_URL)
    │
    ▼
LangSmith (全程追踪:输入/输出/Token/延迟/回归)
```

## 目录结构

```
my-agent/
  app/
    __init__.py
    models.py        # Pydantic 数据模型 (Candidate / AgentStyle / Presentation / Chat)
    config.py        # 环境变量与路径
    policy.py        # 边界策略:脱敏 / 校验 / 系统提示词 / 回答规范化
    provider.py      # LangChain ChatOpenAI + PydanticOutputParser
    data_loader.py   # 加载 data/*.json + 配置 LangSmith
    main.py          # FastAPI 应用 (/api/health /api/profile /api/chat)
  streamlit_app.py   # Streamlit 前端
  tests/
    test_policy.py   # 边界策略测试
    test_api.py      # API 测试
  data/              # 候选人数据 (不进 Git 的隐私字段除外)
  public/            # 静态资源
  requirements.txt
  .env.example
  Dockerfile
  compose.yaml
```

## 本地运行

需要 Python 3.12+。

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
```

复制环境变量示例并填写模型配置：

```bash
cp .env.example .env
```

Windows PowerShell：

```powershell
Copy-Item .env.example .env
```

填好 `MODEL_BASE_URL` / `MODEL_API_KEY` / `MODEL_NAME` 后启动两个进程：

```bash
# 终端 1:FastAPI
uvicorn app.main:create_app --factory --reload --port 8787

# 终端 2:Streamlit
streamlit run streamlit_app.py
```

访问 `http://127.0.0.1:8501/`。模型 Key 只填在 `.env` 的 `MODEL_API_KEY`,不要写进 `app/`、`data/` 或任何代码。

## 测试

```bash
pytest tests/ -v
```

`npm run check` 对应的检查命令(测试 + 依赖审计):

```bash
pytest tests/ -v
pip audit -r requirements.txt
```

## Docker 部署

填写 `.env` 后运行：

```bash
docker compose up -d --build
```

容器同时暴露 `8787` (FastAPI) 与 `8501` (Streamlit),默认只绑定 `127.0.0.1`。生产容器只在 `candidate.json` 的 `privacy.publish_confirmed` 为 `true` 且 `privacy.confirmed_at` 已填写时启动。应通过 Nginx、Caddy 或现有网关反向代理,并在公网启用 HTTPS。健康检查地址为 `/api/health`。

停止服务：

```bash
docker compose down
```

## 修改候选人内容

- `data/candidate.json`：候选人事实、项目与证据。
- `data/agent-style.json`：开场白、推荐问题与回答表达。
- `data/presentation.json`：模板、强调色、密度和明暗主题。
- `privacy-review.md`：隐私与待确认信息记录。

## 回答边界

服务端只允许 Agent 回答候选人的公开经历、项目、技能、教育和岗位匹配问题。事实回答必须引用 `candidate.json` 中存在的证据 ID;资料不足时会明确说明,无关问题会返回固定边界提示。

公网部署前,请确认：

- 原始简历没有放进项目或静态目录。
- `privacy.publish_confirmed` 和 `privacy.confirmed_at` 已由候选人确认。
- 联系方式只包含候选人明确允许公开的字段。
- `.env`、密钥、服务器凭据和私人资料未进入 Git。
- 反向代理、HTTPS、限流和模型消费上限已经配置。
