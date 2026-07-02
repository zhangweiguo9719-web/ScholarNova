# ScholarNova — AI 学术论文检索与研究工作台

ScholarNova 面向复杂科研查询，提供查询理解与分解、多源论文检索、综合排序、论文质量分析、AI 深度分析、证据整理和个人研究知识库。

项目支持自行部署和 BYOK（Bring Your Own Key）。API Key 只保存在部署者自己的 `.env` 或本地设置文件中，不应提交到 Git。

## 功能

- 复杂自然语言查询解析、子查询分解和有界迭代检索
- Semantic Scholar、OpenAlex、Crossref、arXiv 多源检索
- 标题、摘要、年份、引用、venue 和约束综合排序
- 引用量、引用速度、影响力标签等论文质量信号
- AI 论文摘要、研究亮点、局限与方法分析
- 论文知识库、研究路线和框架图
- 中文/英文界面、浅色/深色主题
- API 调用次数、端到端延时和 LLM Token 统计

## 最快部署：Docker Compose

### 1. 环境要求

- Git
- Docker Engine 24+ 与 Docker Compose v2
- 至少 4 GB 可用内存

### 2. 克隆并配置

```bash
git clone https://github.com/zhangweiguo9719-web/ScholarNova.git
cd ScholarNova
cp .env.example .env
```

Windows PowerShell：

```powershell
git clone https://github.com/zhangweiguo9719-web/ScholarNova.git
Set-Location ScholarNova
Copy-Item .env.example .env
```

编辑 `.env`，至少填写一个 LLM：

```dotenv
OPENAI_API_KEY=your-key
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_DEFAULT_MODEL=gpt-4o
DEFAULT_LLM_PROVIDER=openai
```

任何兼容 OpenAI Chat Completions 协议的模型服务都可以通过上述三个变量接入。例如 MiMo：

```dotenv
OPENAI_API_KEY=your-mimo-key
OPENAI_API_BASE=https://token-plan-cn.xiaomimimo.com/v1
OPENAI_DEFAULT_MODEL=mimo-v2.5-pro
DEFAULT_LLM_PROVIDER=openai
```

建议同时配置学术数据源：

```dotenv
SEMANTIC_SCHOLAR_API_KEY=your-semantic-scholar-key
OPENALEX_EMAIL=you@example.com
CROSSREF_EMAIL=you@example.com
```

研究路线框架图为可选功能：

```dotenv
SENSENOVA_API_KEY=your-sensenova-key
SENSENOVA_API_BASE=https://token.sensenova.cn/v1
SENSENOVA_DEFAULT_MODEL=sensenova-u1-fast
```

部署到公网前，务必修改：

```dotenv
POSTGRES_PASSWORD=replace-with-a-strong-password
SECRET_KEY=replace-with-a-long-random-value
```

### 3. 启动

```bash
docker compose up -d --build
```

首次构建通常需要数分钟。启动后访问：

- Web：<http://localhost:5173>
- API：<http://localhost:8000/api/v1>
- Swagger：<http://localhost:8000/docs>
- 健康检查：<http://localhost:8000/api/v1/health>

查看状态和日志：

```bash
docker compose ps
docker compose logs -f backend
```

停止服务：

```bash
docker compose down
```

删除服务及数据库卷（会清除本地数据）：

```bash
docker compose down -v
```

## 本地开发：无需 Docker

本地模式默认使用 SQLite 和内存缓存，因此不要求 PostgreSQL 或 Redis。

### 1. 环境要求

- Python 3.11 或 3.12
- Node.js 20+
- Git

### 2. 后端

```bash
git clone https://github.com/zhangweiguo9719-web/ScholarNova.git
cd ScholarNova/backend
python -m venv .venv
```

激活虚拟环境：

```bash
# Linux / macOS
source .venv/bin/activate

# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

安装、配置并启动：

```bash
python -m pip install --upgrade pip
pip install -e .
cp .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Windows PowerShell 将复制命令替换为：

```powershell
Copy-Item .env.example .env
```

编辑 `backend/.env` 并填写自己的 API Key。数据库表会在后端首次启动时自动创建。

### 3. 前端

另开一个终端：

```bash
cd ScholarNova/frontend
npm ci
npm run dev
```

访问 <http://localhost:5173>。

## API Key 配置说明

| 用途 | 变量 | 是否必需 |
| --- | --- | --- |
| 默认 LLM | `OPENAI_API_KEY` | 至少配置一个 LLM |
| OpenAI 兼容地址 | `OPENAI_API_BASE` | 使用兼容服务时填写 |
| 默认模型 | `OPENAI_DEFAULT_MODEL` | 是 |
| Semantic Scholar | `SEMANTIC_SCHOLAR_API_KEY` | 推荐；无 Key 时限流更严格 |
| OpenAlex 礼貌池 | `OPENALEX_EMAIL` | 推荐 |
| Crossref 礼貌池 | `CROSSREF_EMAIL` | 推荐 |
| SenseNova 框架图 | `SENSENOVA_API_KEY` | 可选 |
| Hugging Face 评测集 | `HF_ACCESS_TOKEN` / `HF_TOKEN` | 仅官方评测需要 |

也可以在 Web 的“设置”页面配置模型。服务端部署更建议使用 `.env`，便于容器重启后保持一致。

安全要求：

- 不要把真实 Key 写进源码、README、Issue、截图或提交记录。
- `.env`、`backend/.env`、本地模型配置、授权数据集和运行日志均已加入 `.gitignore`。
- 如果 Key 曾经公开，应立即在对应平台撤销并重新生成。

## 验证安装

后端健康检查：

```bash
curl http://localhost:8000/api/v1/health
```

运行测试：

```bash
cd backend
pytest

cd ../frontend
npm test
npm run build
```

## 更新部署

```bash
git pull
docker compose up -d --build
```

本地开发模式更新依赖：

```bash
cd backend
pip install -e .

cd ../frontend
npm ci
```

## 目录

```text
ScholarNova/
├── backend/                 FastAPI 后端、检索、排序、LLM 和评测
│   ├── app/
│   ├── scripts/
│   ├── tests/
│   └── .env.example        本地 SQLite 配置模板
├── frontend/                React + TypeScript 前端
├── docs/                    架构、API、部署与演示文档
├── outputs/                 可公开的评测结果与报告
├── .env.example             Docker 部署配置模板
└── docker-compose.yml       PostgreSQL、Redis、后端和前端
```

## 当前评测说明

仓库包含可复现的 Asta 官方验证子集结果和质量报告。当前公开的 18 条确定性验证子集结果为：

- Precision：0.259434
- Recall：0.367893
- F1：0.304288
- 平均 API 调用数：3.667
- 平均端到端延时：5.904 秒

这是官方验证集的 18 条子集结果，不代表完整赛事总分，也不能与不同数据集上的论文指标直接等同。

详细报告见：

`outputs/ScholarNova-质量分析与比赛对标报告-2026-07-01.md`

## 常见问题

### 搜索可以用，但 AI 分析失败

确认 LLM 的 Key、Base URL 和模型名称属于同一服务，并查看：

```bash
docker compose logs -f backend
```

### Semantic Scholar 返回 429

配置自己的 `SEMANTIC_SCHOLAR_API_KEY`。项目已包含全局 1 RPS 节流、重试、缓存和熔断，但仍应遵守账户限额。

### 不想安装 Redis 或 PostgreSQL

使用“本地开发”方式；`backend/.env.example` 已默认配置 SQLite，Redis 留空时使用内存缓存。

### Docker 页面能打开但 API 不通

确认 8000 端口可访问，且 `.env` 中：

```dotenv
VITE_API_BASE_URL=http://localhost:8000
CORS_ORIGINS=["http://localhost:5173"]
```

如果部署在服务器域名上，应改成浏览器能够访问的后端公网地址，并重新执行 `docker compose up -d --build`。

## 许可证

当前仓库尚未附带开源许可证。默认保留全部权利；如需允许第三方复制、修改或再发布，请由仓库所有者明确添加许可证。
