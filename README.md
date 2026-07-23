<p align="center">
  <img src="docs/assets/scholarnova-cover-en.svg" alt="ScholarNova — AI Academic Search and Evidence Workspace" width="100%">
</p>

<p align="center">
  <a href="https://github.com/zhangweiguo9719-web/ScholarNova/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/zhangweiguo9719-web/ScholarNova/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/zhangweiguo9719-web/ScholarNova/releases/latest"><img alt="Windows release" src="https://img.shields.io/github/v/release/zhangweiguo9719-web/ScholarNova?label=Windows%20download"></a>
  <img alt="Python 3.11+" src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white">
  <img alt="React 18" src="https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=08111f">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi&logoColor=white">
  <img alt="Docker Compose" src="https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white">
  <a href="LICENSE"><img alt="MIT License" src="https://img.shields.io/badge/License-MIT-d4a84f"></a>
</p>

<p align="center">
  <strong>English</strong> · <a href="README.zh-CN.md">简体中文</a>
</p>

ScholarNova is a Windows desktop application and self-hostable academic discovery workspace for complex research questions. It turns a natural-language request into a query plan, retrieves papers from multiple scholarly indexes, ranks and explains the results, exposes evidence and quality signals, and organizes findings into a personal knowledge base.

The public edition is **BYOK (Bring Your Own Key)**: this repository contains no private API keys or licensed benchmark data. You choose the model provider, scholarly data sources, and deployment environment.

## Download ScholarNova for Windows (recommended)

**You do not need to install Python, Node.js, Docker, or a separate database.** The Windows edition contains the desktop interface and local backend service in one application.

### Current release: v1.1.1

- [Download the Windows installer (`ScholarNova-Setup-1.1.1-x64.exe`)](https://github.com/zhangweiguo9719-web/ScholarNova/releases/download/v1.1.1/ScholarNova-Setup-1.1.1-x64.exe)
- [Download the portable edition (`ScholarNova-Portable-1.1.1-x64.exe`)](https://github.com/zhangweiguo9719-web/ScholarNova/releases/download/v1.1.1/ScholarNova-Portable-1.1.1-x64.exe)
- [View all releases and release notes](https://github.com/zhangweiguo9719-web/ScholarNova/releases/latest)

### Start in three steps

1. Download and run the installer, or launch the portable `.exe` directly.
2. Open **Settings** and enter your own model and scholarly-data API keys.
3. Open **Search** to retrieve papers, run full-text AI analysis, save a knowledge base, and generate a research route.

Both editions create or update a ScholarNova desktop shortcut. The application automatically starts its bundled local service; there is no separate frontend or backend command to run.

- Desktop shell: Electron with an automatically started packaged FastAPI service.
- Local data: stored under the user's AppData directory.
- Credentials: users configure their own API keys in the settings page; private keys are never bundled.
- Updates: download the newest installer or portable build from GitHub Releases.

Developers who want to build the application themselves can use the [Windows desktop release guide](docs/desktop-release.zh-CN.md). Source deployment instructions are provided later in this README.

## Product preview

| Academic search workspace | Evidence-rich results |
| --- | --- |
| ![English dark home](docs/assets/screenshots/home-en-dark.png) | ![English search results](docs/assets/screenshots/search-results-en-dark.png) |

| Research knowledge base | BYOK model configuration |
| --- | --- |
| ![English knowledge base](docs/assets/screenshots/knowledge-en-dark.png) | ![English settings](docs/assets/screenshots/settings-en-dark.png) |

## What it does

- Understands and decomposes multi-constraint academic queries.
- Searches Semantic Scholar, OpenAlex, Crossref, and arXiv.
- Deduplicates and ranks papers using title, abstract, year, venue, citations, and query constraints.
- Displays abstracts, authors, metadata, relevance, citation percentile, citation velocity, and traceable quality signals.
- Shows live elapsed time, exact source API/query/call status, and supports an intentional re-run of the same query.
- Resolves legal open-access PDFs through direct links, arXiv, OpenAlex, Unpaywall, Semantic Scholar, Crossref, and PMC. When a publisher blocks automated access, users can import an authorized local PDF for persistent full-text, table, caption, and visual-page analysis.
- Clearly distinguishes full-text analysis from abstract-only fallback and shows the exact retrieval status instead of implying that unavailable source material was read.
- Figure pages are sent through the task-specific vision profile. Configure a multimodal model under **Settings → Task models → Vision**; if it rejects image input, ScholarNova transparently falls back to parsed full text, tables, and captions and reports that no page images were read.
- Completed paper analyses show provider-reported total Token usage, with prompt and completion counts also available in the API response.
- Provides a keyboard-accessible, drag-resizable paper detail panel and remembers its width.
- Produces AI summaries, contributions, limitations, methods, and evidence-oriented analysis; analysis is temporarily retained per paper within the current search run.
- Enriches visible results with clearly labelled OpenAlex journal metrics and accepts user-authorized JCR, historical CAS, or SJR CSV/JSON imports without guessing commercial quartiles.
- Opens an institutional library handoff with the query copied; institutional authentication is still required and is never bypassed.
- Saves discoveries into a knowledge base and generates research routes and framework diagrams.
- Supports English/Chinese UI, light/dark themes, rate limiting, retries, caching, and circuit breaking.
- Records API calls, end-to-end latency, and real LLM token usage when a model is invoked.

### Journal data and institutional access

Open **Settings → Journal quartiles** to import a CSV or JSON file that you are licensed to use. A minimal CSV is:

```csv
Journal,JCR Quartile,中科院分区,SJR Best Quartile,Year,Source
Nature Communications,Q1,1区,Q1,2025,my authorized dataset
```

Unknown values stay unknown. OpenAlex H-index, two-year mean citedness, and DOAJ status are labelled as open indicators and are not presented as JCR/CAS quartiles. The library button copies the active query and opens the configured portal; campus network, institutional VPN, or single sign-on is still required for subscribed resources.

## Architecture

```mermaid
flowchart LR
    U["Research question"] --> Q["Query planner"]
    Q --> S["Multi-source retrieval"]
    S --> D["Deduplication and ranking"]
    D --> R["Paper cards and quality signals"]
    R --> A["AI analysis and evidence"]
    A --> K["Knowledge base"]
    K --> G["Research route and diagram"]

    S --- SS["Semantic Scholar"]
    S --- OA["OpenAlex"]
    S --- CR["Crossref"]
    S --- AX["arXiv"]
    Q --- LLM["User-selected LLM"]
```

## Source deployment with Docker Compose (advanced)

Requirements: Git, Docker Engine 24+, Docker Compose v2, and at least 4 GB of free memory.

```bash
git clone https://github.com/zhangweiguo9719-web/ScholarNova.git
cd ScholarNova
cp .env.example .env
```

Windows PowerShell:

```powershell
git clone https://github.com/zhangweiguo9719-web/ScholarNova.git
Set-Location ScholarNova
Copy-Item .env.example .env
```

Edit `.env`. Configure at least one OpenAI-compatible LLM:

```dotenv
OPENAI_API_KEY=your-key
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_DEFAULT_MODEL=gpt-4o
DEFAULT_LLM_PROVIDER=openai
```

Recommended scholarly source configuration:

```dotenv
SEMANTIC_SCHOLAR_API_KEY=your-semantic-scholar-key
OPENALEX_API_KEY=your-openalex-key
OPENALEX_EMAIL=you@example.com
CROSSREF_EMAIL=you@example.com
```

Optional SenseNova research-framework diagram provider:

```dotenv
SENSENOVA_API_KEY=your-sensenova-key
SENSENOVA_API_BASE=https://token.sensenova.cn/v1
SENSENOVA_DEFAULT_MODEL=sensenova-u1-fast
```

Before an internet-facing deployment, replace `POSTGRES_PASSWORD` and `SECRET_KEY` in `.env`.

```bash
docker compose up -d --build
```

Open:

- Web UI: <http://localhost:5173>
- Swagger API: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/api/v1/health>

Operations:

```bash
docker compose ps
docker compose logs -f backend
docker compose down
```

## Source development without Docker (advanced)

Local mode uses SQLite and an in-memory cache, so PostgreSQL and Redis are optional.

```bash
git clone https://github.com/zhangweiguo9719-web/ScholarNova.git
cd ScholarNova/backend
python -m venv .venv
```

Activate the environment and start the backend:

```bash
# Linux / macOS
source .venv/bin/activate

# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```bash
python -m pip install --upgrade pip
pip install -e .
cp .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

On Windows, use `Copy-Item .env.example .env`. Edit `backend/.env` before starting. Database tables are created automatically on first startup.

In a second terminal:

```bash
cd ScholarNova/frontend
npm ci
npm run dev
```

Open <http://localhost:5173>.

## Provider configuration

| Purpose | Variable | Requirement |
| --- | --- | --- |
| Default LLM | `OPENAI_API_KEY` | Configure at least one LLM |
| Compatible endpoint | `OPENAI_API_BASE` | Required for compatible providers |
| Default model | `OPENAI_DEFAULT_MODEL` | Required |
| Semantic Scholar | `SEMANTIC_SCHOLAR_API_KEY` | Recommended; unauthenticated limits are stricter |
| OpenAlex API | `OPENALEX_API_KEY` | Recommended |
| OpenAlex polite pool | `OPENALEX_EMAIL` | Recommended |
| Crossref polite pool | `CROSSREF_EMAIL` | Recommended |
| SenseNova diagram | `SENSENOVA_API_KEY` | Optional |
| Gated benchmarks | `HF_ACCESS_TOKEN` / `HF_TOKEN` | Competition evaluation only |

Model configuration is also available in the Settings page. Server deployments should prefer `.env` so configuration survives container replacement.

For official registration links and provider-specific configuration, read the
[API key application guide](docs/API_KEYS.md).

## Public edition vs. competition environment

| Public GitHub edition | Local competition environment |
| --- | --- |
| Empty configuration templates | Private keys in ignored local `.env` files |
| Users provide their own API keys | Maintainer-selected model and data-source keys |
| No gated datasets in Git | Authorized PaSa/Asta data stored locally |
| Reproducible sample benchmark outputs | Full evaluation runs and private operational logs |
| Safe for forks and self-hosting | Optimized for the competition runtime and quotas |

The application code is shared. Credentials, licensed data, and private run artifacts are not.

## Evaluation snapshot

An 18-query deterministic subset of the official Asta Paper Finder validation set was used for targeted regression testing:

| Metric | Previous | Current |
| --- | ---: | ---: |
| Precision | 0.259434 | **0.352313** |
| Recall | 0.367893 | 0.331104 |
| F1 | 0.304288 | **0.341379** |
| Recall@20 | 0.160535 | **0.163880** |

This is a reproducible **18-query validation subset**, not a full competition score. It must not be directly compared with results reported on different datasets or evaluation protocols. Deterministic query planning intentionally consumes zero LLM tokens; model-assisted product queries report actual provider usage.

The complete 66-query file has also been executed. Of those queries, 27 expose
binary paper-ID gold labels and score F1=`0.283713`; the remaining 39 require a
textual relevance judge and are reported separately instead of being forced
into the binary metric.

See [the benchmark report](outputs/competition-benchmark-report-2026-07-02.md), [the v1.1.0 optimization report](docs/reports/v1.1.0-optimization-test-report.zh-CN.md), [the v1.1.1 full-text, vision, and desktop test report](docs/reports/v1.1.1-fulltext-vision-desktop-report.zh-CN.md), and the committed [prediction artifact](outputs/benchmarks/predictions/asta-s2-validation18-v3-2026-07-02.json).

## Verification

```bash
cd backend
pytest -m "not integration"

cd ../frontend
npm test
npm run build
```

## Security

- Never commit `.env`, API keys, model configuration files, gated datasets, or runtime logs.
- If a key has ever been exposed, revoke it at the provider and generate a replacement.
- JCR and CAS quartiles are shown only when backed by an authorized data source; ScholarNova does not fabricate them.
- Review [SECURITY.md](SECURITY.md) before a public deployment.

## Contributing

Issues and pull requests are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting changes.

## License

[MIT](LICENSE) © 2026 Zhang Weiguo.
