# 本地开发部署

完整的新用户说明以仓库根目录 [README](../../README.md) 为准。

## 后端

```bash
cd backend
python -m venv .venv
```

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

Windows 使用 `Copy-Item .env.example .env`。默认模板采用 SQLite 和内存缓存，无需 PostgreSQL/Redis。

## 前端

```bash
cd frontend
npm ci
npm run dev
```

访问：

- Web：<http://localhost:5173>
- API 文档：<http://localhost:8000/docs>
- 健康检查：<http://localhost:8000/api/v1/health>

API Key 配置见 [README 的 API Key 章节](../../README.md#api-key-配置说明)。
