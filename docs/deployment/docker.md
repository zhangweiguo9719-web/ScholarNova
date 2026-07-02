# Docker Compose 部署

当前 `docker-compose.yml` 是唯一受支持的 Compose 配置，包含 PostgreSQL、Redis、FastAPI 后端和 Nginx 前端。

```bash
git clone https://github.com/zhangweiguo9719-web/ScholarNova.git
cd ScholarNova
cp .env.example .env
```

编辑 `.env`，填写自己的 LLM/API Key，并修改 `POSTGRES_PASSWORD` 与 `SECRET_KEY`。

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f backend
```

访问：

- Web：<http://localhost:5173>
- API：<http://localhost:8000/api/v1>
- Swagger：<http://localhost:8000/docs>

更新：

```bash
git pull
docker compose up -d --build
```

停止：

```bash
docker compose down
```

删除数据卷：

```bash
docker compose down -v
```

更完整的 API Key 与故障排查说明见 [README](../../README.md)。
