## Docker Compose 源码部署（进阶）

需要 Git、Docker Engine 24+、Docker Compose v2 和至少 4 GB 空闲内存。

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

编辑 `.env`，配置至少一个 OpenAI 兼容 LLM：

```dotenv
OPENAI_API_KEY=your-key
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_DEFAULT_MODEL=gpt-4o
DEFAULT_LLM_PROVIDER=openai
```

推荐的学术数据源配置：

```dotenv
SEMANTIC_SCHOLAR_API_KEY=your-semantic-scholar-key
OPENALEX_API_KEY=your-openalex-key
OPENALEX_EMAIL=you@example.com
CROSSREF_EMAIL=you@example.com
```

可选：商汤研究架构图服务：

```dotenv
SENSENOVA_API_KEY=your-sensenova-key
SENSENOVA_API_BASE=https://token.sensenova.cn/v1
SENSENOVA_DEFAULT_MODEL=sensenova-u1-fast
```

对外部署前，请先替换 `.env` 中的 `POSTGRES_PASSWORD` 与 `SECRET_KEY`。

```bash
docker compose up -d --build
```

打开：

- Web UI：<http://localhost:5173>
- Swagger API：<http://localhost:8000/docs>
- 健康检查：<http://localhost:8000/api/v1/health>

常用运维：

```bash
docker compose ps
docker compose logs -f backend
docker compose down
```

## 无 Docker 源码开发（进阶）

建议使用 Python 3.12、Node.js 22，与桌面版发布流水线保持一致。

本地模式使用 SQLite 和内存缓存，无需 PostgreSQL 与 Redis。

```bash
git clone https://github.com/zhangweiguo9719-web/ScholarNova.git
cd ScholarNova/backend
python -m venv .venv
```

激活环境并启动后端：

```bash
# Linux / macOS
source .venv/bin/activate

# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```bash
python -m pip install --upgrade pip
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Windows 使用 `Copy-Item .env.example .env`。启动前编辑 `backend/.env`，数据库表在首次启动时自动创建。

另开一个终端：

```bash
cd ScholarNova/frontend
npm ci
npm run dev
```

打开 <http://localhost:5173>。

## 厂商配置环境变量

| 用途 | 变量 | 要求 |
| --- | --- | --- |
| 默认 LLM | `OPENAI_API_KEY` | 至少配置一个 LLM |
| 兼容端点 | `OPENAI_API_BASE` | 兼容厂商必填 |
| 默认模型 | `OPENAI_DEFAULT_MODEL` | 必填 |
| Semantic Scholar | `SEMANTIC_SCHOLAR_API_KEY` | 推荐；未认证限额更严 |
| OpenAlex API | `OPENALEX_API_KEY` | 推荐 |
| OpenAlex polite pool | `OPENALEX_EMAIL` | 推荐 |
| Crossref polite pool | `CROSSREF_EMAIL` | 推荐 |
| 商汤出图 | `SENSENOVA_API_KEY` | 可选 |

模型配置也可在设置页完成；服务端部署建议优先使用 `.env`，这样配置在容器重建后仍然保留。

各厂商官方注册入口与详细配置见 [API Key 申请指南](../docs/API_KEYS.md)。

## 评估快照

面向官方 Asta Paper Finder 验证集的可复现 18 题确定性子集用于定向回归测试：

以下是 2026-07-02 的历史评测，**不是 v1.2.1 的复测成绩**。

| 指标 | 历史较早运行 | 历史较晚运行 |
| --- | ---: | ---: |
| Precision | 0.259434 | **0.352313** |
| Recall | 0.367893 | 0.331104 |
| F1 | 0.304288 | **0.341379** |
| Recall@20 | 0.160535 | **0.163880** |

这是可复现的 **18 题验证子集**，不是完整比赛成绩；不得与不同数据集或评估协议的结果直接对比。确定性查询规划有意消耗 0 LLM Token；模型辅助的产品查询会如实上报供应商用量。

完整 66 题文件也已运行。其中 27 题含二元论文 ID 金标，F1=`0.283713`；其余 39 题需要文本相关性判定，单独报告，不强行纳入二元指标。

详见 [基准评测报告](../outputs/competition-benchmark-report-2026-07-02.md)、[v1.1.0 优化测试报告](../docs/reports/v1.1.0-optimization-test-report.zh-CN.md)、[v1.1.1 全文、视觉与桌面版测试报告](../docs/reports/v1.1.1-fulltext-vision-desktop-report.zh-CN.md)、[FTI-4 会话与速率治理报告](../docs/reports/fti-4-session-and-rate-governance.zh-CN.md) 与已提交的 [预测产物](../outputs/benchmarks/predictions/asta-s2-validation18-v3-2026-07-02.json)。

## 验证

```bash
cd backend
pytest -m "not integration"

cd ../frontend
npm test
npm run build
```

## 安全

- 不要提交 `.env`、API Key、模型配置文件、授权数据集或运行日志。
- 若 Key 曾泄露，请到厂商处撤销并重新生成。
- JCR / 中科院分区仅在拥有授权数据源时展示，ScholarNova 不会伪造。
- 对外部署前请阅读 [SECURITY.md](../SECURITY.md)。

## 参与贡献

欢迎提交 Issue 与 Pull Request。提交前请阅读 [CONTRIBUTING.md](../CONTRIBUTING.md)。

## License

[MIT](../LICENSE) © 2026 Zhang Weiguo.
