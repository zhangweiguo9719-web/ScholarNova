# Docker 部署指南

本文档介绍如何使用 Docker 和 Docker Compose 部署 ScholarAgent。

## 前置要求

- Docker 20.10+
- Docker Compose 2.0+
- 至少 4GB 可用内存
- 至少 10GB 可用磁盘空间

## 1. Docker Compose 配置说明

### 1.1 服务架构

```yaml
# docker-compose.yml 服务架构
services:
  postgres:    # PostgreSQL 数据库
  redis:       # Redis 缓存
  backend:     # FastAPI 后端
  frontend:    # React 前端
```

### 1.2 配置文件详解

**PostgreSQL 配置:**
```yaml
postgres:
  image: postgres:16-alpine
  container_name: scholar-postgres
  restart: unless-stopped
  ports:
    - "5432:5432"
  environment:
    POSTGRES_USER: ${POSTGRES_USER:-scholar}
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-scholar_password}
    POSTGRES_DB: ${POSTGRES_DB:-scholar_agent}
  volumes:
    - postgres_data:/var/lib/postgresql/data  # 数据持久化
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-scholar}"]
    interval: 10s
    timeout: 5s
    retries: 5
```

**Redis 配置:**
```yaml
redis:
  image: redis:7-alpine
  container_name: scholar-redis
  restart: unless-stopped
  ports:
    - "6379:6379"
  command: redis-server --appendonly yes  # 启用持久化
  volumes:
    - redis_data:/data
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 10s
    timeout: 5s
    retries: 5
```

**后端配置:**
```yaml
backend:
  build:
    context: ./backend
    dockerfile: Dockerfile
  container_name: scholar-backend
  restart: unless-stopped
  ports:
    - "8000:8000"
  env_file:
    - .env
  environment:
    DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER:-scholar}:${POSTGRES_PASSWORD:-scholar_password}@postgres:5432/${POSTGRES_DB:-scholar_agent}
    REDIS_URL: redis://redis:6379/0
  volumes:
    - ./backend:/app  # 开发模式挂载
  depends_on:
    postgres:
      condition: service_healthy
    redis:
      condition: service_healthy
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

**前端配置:**
```yaml
frontend:
  build:
    context: ./frontend
    dockerfile: Dockerfile
  container_name: scholar-frontend
  restart: unless-stopped
  ports:
    - "5173:5173"
  environment:
    VITE_API_BASE_URL: http://localhost:8000
  volumes:
    - ./frontend:/app
    - /app/node_modules  # 匿名卷，避免覆盖容器内的 node_modules
  depends_on:
    - backend
```

## 2. 启动命令

### 2.1 首次启动

```bash
# 克隆项目
git clone <repository-url>
cd scholar-agent

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入必要的配置

# 构建并启动所有服务
docker-compose up -d --build

# 查看启动日志
docker-compose logs -f
```

### 2.2 常用命令

```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 重启所有服务
docker-compose restart

# 重启单个服务
docker-compose restart backend

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
docker-compose logs -f backend  # 查看后端日志
docker-compose logs -f postgres # 查看数据库日志

# 进入容器
docker-compose exec backend bash
docker-compose exec postgres psql -U scholar -d scholar_agent

# 查看资源使用
docker stats
```

### 2.3 开发模式启动

```bash
# 仅启动基础服务（数据库和缓存）
docker-compose up -d postgres redis

# 本地启动后端
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 本地启动前端
cd frontend
npm install
npm run dev
```

## 3. 数据持久化

### 3.1 Docker 卷

```yaml
volumes:
  postgres_data:  # PostgreSQL 数据
  redis_data:     # Redis 数据
```

### 3.2 备份数据

**备份 PostgreSQL:**
```bash
# 备份数据库
docker-compose exec postgres pg_dump -U scholar scholar_agent > backup_$(date +%Y%m%d_%H%M%S).sql

# 压缩备份
docker-compose exec postgres pg_dump -U scholar scholar_agent | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

**备份 Redis:**
```bash
# 备份 Redis 数据
docker cp scholar-redis:/data/dump.rdb ./redis_backup_$(date +%Y%m%d_%H%M%S).rdb
```

### 3.3 恢复数据

**恢复 PostgreSQL:**
```bash
# 从备份恢复
docker-compose exec -T postgres psql -U scholar scholar_agent < backup.sql

# 从压缩备份恢复
gunzip < backup.sql.gz | docker-compose exec -T postgres psql -U scholar scholar_agent
```

**恢复 Redis:**
```bash
# 停止 Redis
docker-compose stop redis

# 恢复数据文件
docker cp ./redis_backup.rdb scholar-redis:/data/dump.rdb

# 启动 Redis
docker-compose start redis
```

### 3.4 清理数据

```bash
# 停止服务并删除数据卷
docker-compose down -v

# 仅删除数据卷
docker volume rm scholar-agent_postgres_data scholar-agent_redis_data
```

## 4. 日志查看

### 4.1 实时日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
docker-compose logs -f redis
```

### 4.2 日志配置

**后端日志配置（.env）:**
```bash
# 日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# 日志格式: json, text
LOG_FORMAT=json
```

**Docker 日志驱动配置:**
```yaml
# docker-compose.yml
services:
  backend:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### 4.3 日志分析

```bash
# 查看错误日志
docker-compose logs backend | grep -i error

# 查看最近 100 行日志
docker-compose logs --tail 100 backend

# 查看指定时间后的日志
docker-compose logs --since 2024-01-01T00:00:00 backend
```

## 5. 常见问题

### 5.1 端口冲突

**问题**: 端口已被占用

**解决方案**:
```bash
# 查找占用端口的进程
# Windows:
netstat -ano | findstr :5432
# macOS/Linux:
lsof -i :5432

# 修改 docker-compose.yml 中的端口映射
ports:
  - "5433:5432"  # 使用其他端口
```

### 5.2 内存不足

**问题**: 容器启动失败，内存不足

**解决方案**:
```bash
# 增加 Docker 内存限制
# Docker Desktop: Settings -> Resources -> Memory

# 或限制服务内存使用
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
```

### 5.3 数据库连接失败

**问题**: 后端无法连接数据库

**解决方案**:
```bash
# 检查数据库服务状态
docker-compose ps postgres

# 查看数据库日志
docker-compose logs postgres

# 检查健康检查状态
docker inspect scholar-postgres | grep -A 10 Health

# 手动测试连接
docker-compose exec postgres psql -U scholar -d scholar_agent
```

### 5.4 构建失败

**问题**: Docker 构建失败

**解决方案**:
```bash
# 清除构建缓存
docker-compose build --no-cache

# 查看构建日志
docker-compose build 2>&1 | tee build.log

# 检查 Dockerfile 语法
docker build --check -f backend/Dockerfile backend/
```

### 5.5 卷权限问题

**问题**: 容器无法写入卷

**解决方案**:
```bash
# 检查卷权限
docker volume inspect scholar-agent_postgres_data

# 修改卷权限
docker-compose exec postgres chown -R postgres:postgres /var/lib/postgresql/data

# 使用 tmpfs 临时文件系统
services:
  backend:
    tmpfs:
      - /tmp
```

### 5.6 网络问题

**问题**: 容器间无法通信

**解决方案**:
```bash
# 检查网络
docker network ls
docker network inspect scholar-agent_scholar-network

# 测试容器间通信
docker-compose exec backend ping postgres
docker-compose exec backend ping redis
```

## 6. 生产环境优化

### 6.1 使用生产配置

```bash
# 使用生产配置文件
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

**docker-compose.prod.yml:**
```yaml
version: '3.8'

services:
  backend:
    restart: always
    environment:
      - APP_ENV=production
      - DEBUG=false
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G

  frontend:
    restart: always
    environment:
      - NODE_ENV=production
```

### 6.2 配置反向代理

**Nginx 配置示例:**
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://frontend:5173;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 6.3 配置 HTTPS

```bash
# 使用 Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## 7. 监控和维护

### 7.1 健康检查

```bash
# 检查所有服务健康状态
docker-compose ps

# 手动健康检查
curl http://localhost:8000/api/v1/health
```

### 7.2 性能监控

```bash
# 查看资源使用
docker stats

# 查看容器详情
docker inspect scholar-backend
```

### 7.3 定期维护

```bash
# 清理未使用的镜像
docker image prune -a

# 清理未使用的卷
docker volume prune

# 清理未使用的网络
docker network prune
```

## 8. 升级指南

### 8.1 升级步骤

```bash
# 拉取最新代码
git pull

# 重新构建镜像
docker-compose build

# 停止旧服务
docker-compose down

# 启动新服务
docker-compose up -d

# 运行数据库迁移
docker-compose exec backend alembic upgrade head
```

### 8.2 回滚步骤

```bash
# 恢复代码
git checkout <previous-version>

# 重新构建
docker-compose build

# 恢复数据库备份
docker-compose exec -T postgres psql -U scholar scholar_agent < backup.sql

# 重启服务
docker-compose down
docker-compose up -d
```
