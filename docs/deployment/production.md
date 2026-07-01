# 生产环境部署指南

本文档介绍如何在生产环境部署 ScholarAgent。

## 1. 服务器要求

### 1.1 硬件要求

| 组件 | 最低配置 | 推荐配置 |
|------|----------|----------|
| CPU | 2 核 | 4 核+ |
| 内存 | 4GB | 8GB+ |
| 磁盘 | 50GB SSD | 100GB+ SSD |
| 网络 | 10Mbps | 100Mbps+ |

### 1.2 软件要求

| 组件 | 版本要求 |
|------|----------|
| 操作系统 | Ubuntu 22.04 LTS / CentOS 8+ |
| Docker | 20.10+ |
| Docker Compose | 2.0+ |
| Nginx | 1.24+ |
| SSL 证书 | Let's Encrypt 或其他 |

### 1.3 域名要求

- 域名已解析到服务器 IP
- 已开放 80 和 443 端口
- 已配置防火墙规则

## 2. 服务器初始化

### 2.1 系统更新

```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y

# CentOS/RHEL
sudo yum update -y
```

### 2.2 安装 Docker

```bash
# 安装依赖
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

# 添加 Docker GPG 密钥
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# 添加 Docker 仓库
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装 Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 启动 Docker
sudo systemctl start docker
sudo systemctl enable docker

# 将当前用户添加到 docker 组
sudo usermod -aG docker $USER
newgrp docker

# 验证安装
docker --version
docker compose version
```

### 2.3 安装 Nginx

```bash
# 安装 Nginx
sudo apt install -y nginx

# 启动 Nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# 验证安装
nginx -v
```

### 2.4 配置防火墙

```bash
# 启用防火墙
sudo ufw enable

# 允许 SSH
sudo ufw allow ssh

# 允许 HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 查看状态
sudo ufw status
```

## 3. 项目部署

### 3.1 克隆项目

```bash
# 创建项目目录
sudo mkdir -p /opt/scholar-agent
sudo chown $USER:$USER /opt/scholar-agent

# 克隆项目
cd /opt/scholar-agent
git clone <repository-url> .
```

### 3.2 配置环境变量

```bash
# 创建生产环境配置
cp .env.example .env

# 编辑配置文件
nano .env
```

**生产环境配置示例:**
```bash
# 应用配置
APP_NAME=ScholarAgent
APP_ENV=production
DEBUG=false
SECRET_KEY=<生成随机密钥>

# 数据库配置
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=scholar
POSTGRES_PASSWORD=<强密码>
POSTGRES_DB=scholar_agent
DATABASE_URL=postgresql+asyncpg://scholar:<强密码>@postgres:5432/scholar_agent

# Redis 配置
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=<强密码>
REDIS_URL=redis://:<强密码>@redis:6379/0

# LLM 配置
OPENAI_API_KEY=<your-api-key>
DEFAULT_LLM_PROVIDER=openai

# 日志配置
LOG_LEVEL=WARNING
LOG_FORMAT=json

# CORS 配置
CORS_ORIGINS=["https://your-domain.com"]
```

### 3.3 创建生产配置文件

**docker-compose.prod.yml:**
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: scholar-postgres
    restart: always
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - scholar-network
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G

  redis:
    image: redis:7-alpine
    container_name: scholar-redis
    restart: always
    command: redis-server --requirepass ${REDIS_PASSWORD} --appendonly yes
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - scholar-network
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 2G

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: scholar-backend
    restart: always
    env_file:
      - .env
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
    volumes:
      - ./backend/logs:/app/logs
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
    networks:
      - scholar-network
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: scholar-frontend
    restart: always
    environment:
      VITE_API_BASE_URL: https://your-domain.com/api
    networks:
      - scholar-network
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G

volumes:
  postgres_data:
  redis_data:

networks:
  scholar-network:
    driver: bridge
```

### 3.4 启动服务

```bash
# 构建并启动服务
docker compose -f docker-compose.prod.yml up -d --build

# 查看服务状态
docker compose -f docker-compose.prod.yml ps

# 查看日志
docker compose -f docker-compose.prod.yml logs -f
```

## 4. Nginx 反向代理配置

### 4.1 创建 Nginx 配置

```bash
# 创建配置文件
sudo nano /etc/nginx/sites-available/scholar-agent
```

**配置内容:**
```nginx
# 重定向 HTTP 到 HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS 配置
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL 证书配置
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # SSL 安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # 前端
    location / {
        proxy_pass http://localhost:5173;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API 代理
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # SSE 支持
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
        
        # 超时配置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 300s;
    }

    # 静态文件缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        proxy_pass http://localhost:5173;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # 日志配置
    access_log /var/log/nginx/scholar-agent.access.log;
    error_log /var/log/nginx/scholar-agent.error.log;
}
```

### 4.2 启用配置

```bash
# 创建符号链接
sudo ln -s /etc/nginx/sites-available/scholar-agent /etc/nginx/sites-enabled/

# 删除默认配置
sudo rm /etc/nginx/sites-enabled/default

# 测试配置
sudo nginx -t

# 重载 Nginx
sudo systemctl reload nginx
```

## 5. HTTPS 配置

### 5.1 安装 Certbot

```bash
# 安装 Certbot
sudo apt install -y certbot python3-certbot-nginx
```

### 5.2 获取 SSL 证书

```bash
# 获取证书
sudo certbot --nginx -d your-domain.com

# 测试自动续期
sudo certbot renew --dry-run
```

### 5.3 配置自动续期

```bash
# 创建续期脚本
sudo nano /etc/cron.d/certbot-renew
```

**内容:**
```
0 0 1 * * root certbot renew --quiet --post-hook "systemctl reload nginx"
```

## 6. 数据库备份

### 6.1 创建备份脚本

```bash
# 创建备份目录
sudo mkdir -p /opt/backups/scholar-agent
sudo chown $USER:$USER /opt/backups/scholar-agent

# 创建备份脚本
nano /opt/backups/scholar-agent/backup.sh
```

**备份脚本内容:**
```bash
#!/bin/bash

# 配置
BACKUP_DIR="/opt/backups/scholar-agent"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份 PostgreSQL
echo "备份 PostgreSQL..."
docker compose -f /opt/scholar-agent/docker-compose.prod.yml exec -T postgres \
    pg_dump -U scholar scholar_agent | gzip > $BACKUP_DIR/postgres_$TIMESTAMP.sql.gz

# 备份 Redis
echo "备份 Redis..."
docker cp scholar-redis:/data/dump.rdb $BACKUP_DIR/redis_$TIMESTAMP.rdb

# 删除旧备份
echo "删除 $RETENTION_DAYS 天前的备份..."
find $BACKUP_DIR -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "*.rdb" -mtime +$RETENTION_DAYS -delete

echo "备份完成: $TIMESTAMP"
```

### 6.2 设置定时任务

```bash
# 添加执行权限
chmod +x /opt/backups/scholar-agent/backup.sh

# 添加定时任务
crontab -e

# 添加以下行（每天凌晨 2 点备份）
0 2 * * * /opt/backups/scholar-agent/backup.sh >> /var/log/scholar-agent-backup.log 2>&1
```

### 6.3 恢复数据

```bash
# 恢复 PostgreSQL
gunzip < /opt/backups/scholar-agent/postgres_20240101_020000.sql.gz | \
    docker compose -f /opt/scholar-agent/docker-compose.prod.yml exec -T postgres \
    psql -U scholar scholar_agent

# 恢复 Redis
docker compose -f /opt/scholar-agent/docker-compose.prod.yml stop redis
docker cp /opt/backups/scholar-agent/redis_20240101_020000.rdb scholar-redis:/data/dump.rdb
docker compose -f /opt/scholar-agent/docker-compose.prod.yml start redis
```

## 7. 监控配置

### 7.1 系统监控

**安装监控工具:**
```bash
# 安装 htop 和 iotop
sudo apt install -y htop iotop

# 查看系统资源
htop
iotop
```

### 7.2 Docker 监控

```bash
# 查看容器资源使用
docker stats

# 查看容器日志
docker compose -f /opt/scholar-agent/docker-compose.prod.yml logs -f --tail=100
```

### 7.3 应用监控

**健康检查脚本:**
```bash
#!/bin/bash

# 检查后端健康状态
HEALTH_STATUS=$(curl -s http://localhost:8000/api/v1/health | jq -r '.status')

if [ "$HEALTH_STATUS" != "healthy" ]; then
    echo "后端服务异常: $HEALTH_STATUS"
    # 发送告警（可配置邮件、短信等）
fi
```

### 7.4 日志监控

**配置日志轮转:**
```bash
sudo nano /etc/logrotate.d/scholar-agent
```

**内容:**
```
/var/log/scholar-agent/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        systemctl reload nginx
    endscript
}
```

## 8. 性能优化

### 8.1 数据库优化

**PostgreSQL 配置优化:**
```bash
# 编辑 PostgreSQL 配置
docker compose -f /opt/scholar-agent/docker-compose.prod.yml exec postgres \
    nano /var/lib/postgresql/data/postgresql.conf
```

**关键配置:**
```
# 内存配置
shared_buffers = 2GB
effective_cache_size = 6GB
work_mem = 64MB
maintenance_work_mem = 512MB

# 连接配置
max_connections = 200

# WAL 配置
wal_buffers = 64MB
checkpoint_completion_target = 0.9
```

### 8.2 Redis 优化

**Redis 配置优化:**
```bash
# 编辑 Redis 配置
docker compose -f /opt/scholar-agent/docker-compose.prod.yml exec redis \
    redis-cli CONFIG SET maxmemory 2gb
docker compose -f /opt/scholar-agent/docker-compose.prod.yml exec redis \
    redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

### 8.3 Nginx 优化

**Nginx 配置优化:**
```nginx
# /etc/nginx/nginx.conf

worker_processes auto;
worker_rlimit_nofile 65535;

events {
    worker_connections 4096;
    multi_accept on;
    use epoll;
}

http {
    # 开启 gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # 开启缓存
    proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=my_cache:10m max_size=10g inactive=60m use_temp_path=off;
}
```

## 9. 安全加固

### 9.1 系统安全

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 配置自动安全更新
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### 9.2 Docker 安全

```bash
# 限制容器资源
docker compose -f /opt/scholar-agent/docker-compose.prod.yml up -d

# 定期更新镜像
docker compose -f /opt/scholar-agent/docker-compose.prod.yml pull
docker compose -f /opt/scholar-agent/docker-compose.prod.yml up -d
```

### 9.3 网络安全

```bash
# 配置防火墙
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

## 10. 故障排查

### 10.1 服务无法启动

```bash
# 查看服务日志
docker compose -f /opt/scholar-agent/docker-compose.prod.yml logs

# 检查端口占用
sudo netstat -tlnp | grep -E ':(80|443|5432|6379|8000|5173)'

# 检查磁盘空间
df -h

# 检查内存使用
free -h
```

### 10.2 数据库连接失败

```bash
# 检查数据库状态
docker compose -f /opt/scholar-agent/docker-compose.prod.yml ps postgres

# 测试数据库连接
docker compose -f /opt/scholar-agent/docker-compose.prod.yml exec postgres \
    psql -U scholar -d scholar_agent -c "SELECT 1;"

# 检查数据库日志
docker compose -f /opt/scholar-agent/docker-compose.prod.yml logs postgres
```

### 10.3 性能问题

```bash
# 查看资源使用
docker stats

# 查看慢查询
docker compose -f /opt/scholar-agent/docker-compose.prod.yml exec postgres \
    psql -U scholar -d scholar_agent -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"

# 查看 Redis 使用
docker compose -f /opt/scholar-agent/docker-compose.prod.yml exec redis \
    redis-cli INFO memory
```

## 11. 升级指南

### 11.1 备份数据

```bash
# 执行备份
/opt/backups/scholar-agent/backup.sh
```

### 11.2 升级步骤

```bash
# 拉取最新代码
cd /opt/scholar-agent
git pull

# 重新构建镜像
docker compose -f docker-compose.prod.yml build

# 停止服务
docker compose -f /opt/scholar-agent/docker-compose.prod.yml down

# 启动新服务
docker compose -f /opt/scholar-agent/docker-compose.prod.yml up -d

# 运行数据库迁移
docker compose -f /opt/scholar-agent/docker-compose.prod.yml exec backend \
    alembic upgrade head

# 验证服务
curl http://localhost:8000/api/v1/health
```

### 11.3 回滚步骤

```bash
# 恢复代码
cd /opt/scholar-agent
git checkout <previous-version>

# 恢复数据库
/opt/backups/scholar-agent/restore.sh

# 重新构建并启动
docker compose -f /opt/scholar-agent/docker-compose.prod.yml build
docker compose -f /opt/scholar-agent/docker-compose.prod.yml up -d
```
