# 面试 Agent 网站

这是由 `interview-agent` Codex Skill 生成的自部署项目。首屏是招聘方可直接使用的面试对话，向下滚动可查看候选人的项目、技能、经历与公开证据。

## 本地运行

需要 Node.js 20 或更高版本。

```bash
npm ci
```

复制环境变量示例并填写模型配置：

```bash
cp .env.example .env
```

Windows PowerShell 可使用：

```powershell
Copy-Item .env.example .env
```

然后启动前端和接口：

```bash
npm run dev
```

访问 `http://127.0.0.1:5173/`。模型 Key 只填写在 `.env` 的 `MODEL_API_KEY`，不要写进 `src/`、`data/` 或任何 `VITE_` 环境变量。

## 修改候选人内容

- `data/candidate.json`：候选人事实、项目与证据。
- `data/agent-style.json`：开场白、推荐问题与回答表达。
- `data/presentation.json`：模板、强调色、密度和明暗主题。
- `privacy-review.md`：由 Skill 生成的隐私与待确认信息记录。

修改后先运行：

```bash
npm run check
```

该命令会执行服务端测试、生产构建和高危依赖审计。

## Docker 部署

填写 `.env` 后运行：

```bash
docker compose up -d --build
```

生产容器只会在 `candidate.json` 中的 `privacy.publish_confirmed` 为 `true` 且 `privacy.confirmed_at` 已填写时启动。服务默认只绑定 `127.0.0.1:8787`，应通过 Nginx、Caddy 或现有网关反向代理，并在公网启用 HTTPS。健康检查地址为 `/api/health`。

停止服务：

```bash
docker compose down
```

`docker compose down` 不会删除其他项目的容器、镜像或数据。不要使用全局 prune 命令。

## 回答边界

服务端只允许 Agent 回答候选人的公开经历、项目、技能、教育和岗位匹配问题。事实回答必须引用 `candidate.json` 中存在的证据 ID；资料不足时会明确说明，无关问题会返回固定边界提示。

公网部署前，请确认：

- 原始简历没有放进项目或静态目录。
- `privacy.publish_confirmed` 和 `privacy.confirmed_at` 已由候选人确认。
- 联系方式只包含候选人明确允许公开的字段。
- `.env`、密钥、服务器凭据和私人资料未进入 Git。
- 反向代理、HTTPS、限流和模型消费上限已经配置。
