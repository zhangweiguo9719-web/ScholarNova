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

Use Python 3.12 and Node.js 22 (the desktop release CI toolchain).

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
pip install -c ../requirements-lock.txt -e ".[dev]"
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

Model configuration is also available in the Settings page. Server deployments should prefer `.env` so configuration survives container replacement.

For official registration links and provider-specific configuration, read the
[API key application guide](../docs/API_KEYS.md).

## Evaluation snapshot

An 18-query deterministic subset of the official Asta Paper Finder validation set was used for targeted regression testing:

Historical evaluation from 2026-07-02, **not re-run for v1.2.1**.

| Metric | Earlier historical run | Later historical run |
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

See [the benchmark report](../outputs/competition-benchmark-report-2026-07-02.md), [the v1.1.0 optimization report](../docs/reports/v1.1.0-optimization-test-report.zh-CN.md), [the v1.1.1 full-text, vision, and desktop test report](../docs/reports/v1.1.1-fulltext-vision-desktop-report.zh-CN.md), [the FTI-4 session and rate-governance report](../docs/reports/fti-4-session-and-rate-governance.zh-CN.md), and the committed [prediction artifact](../outputs/benchmarks/predictions/asta-s2-validation18-v3-2026-07-02.json).

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
- Review [SECURITY.md](../SECURITY.md) before a public deployment.

## Contributing

Issues and pull requests are welcome. Read [CONTRIBUTING.md](../CONTRIBUTING.md) before submitting changes.

## License

[MIT](../LICENSE) © 2026 Zhang Weiguo.
