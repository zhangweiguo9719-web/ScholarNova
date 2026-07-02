# 公网部署注意事项

仓库提供的 `docker-compose.yml` 可用于单机部署。正式公网环境还应由部署者配置 HTTPS、域名、备份与防火墙。

## 必做配置

1. 复制 `.env.example` 为 `.env`。
2. 修改 `POSTGRES_PASSWORD` 和 `SECRET_KEY`。
3. 填写自己的 LLM 与学术数据源 API Key。
4. 将 `VITE_API_BASE_URL` 改成浏览器可访问的后端 HTTPS 地址。
5. 将 `CORS_ORIGINS` 改成真实前端域名。
6. 只在防火墙或反向代理后暴露必要端口。

示例：

```dotenv
APP_ENV=production
DEBUG=false
VITE_API_BASE_URL=https://api.example.com
CORS_ORIGINS=["https://scholar.example.com"]
ALLOWED_HOSTS=["api.example.com","localhost","127.0.0.1"]
```

修改构建期前端地址后必须重新构建：

```bash
docker compose up -d --build
```

## 反向代理

建议：

- `https://scholar.example.com` 代理到宿主机 `5173`
- `https://api.example.com` 代理到宿主机 `8000`
- 由 Caddy、Nginx、Traefik 或云负载均衡器负责 TLS

## 数据备份

```bash
docker compose exec -T postgres \
  pg_dump -U scholar scholar_agent > scholarnova-backup.sql
```

恢复前应停止写入，并在测试环境验证备份：

```bash
docker compose exec -T postgres \
  psql -U scholar scholar_agent < scholarnova-backup.sql
```

不要提交 `.env`、数据库备份、模型配置或授权评测数据。
