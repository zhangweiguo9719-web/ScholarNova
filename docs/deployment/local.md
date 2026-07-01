# 本地开发环境搭建

本文档详细介绍如何在本地搭建 ScholarAgent 开发环境。

## 环境要求

| 组件 | 版本要求 | 说明 |
|------|----------|------|
| Python | 3.11+ | 后端运行环境 |
| Node.js | 18+ | 前端构建环境 |
| PostgreSQL | 16+ | 主数据库 |
| Redis | 7+ | 缓存服务 |
| Git | 2.30+ | 版本控制 |

## 1. Python 环境配置

### 1.1 安装 Python

**Windows:**
```powershell
# 使用 winget 安装
winget install Python.Python.3.11

# 或从官网下载安装
# https://www.python.org/downloads/
```

**macOS:**
```bash
# 使用 Homebrew 安装
brew install python@3.11

# 或使用 pyenv 安装
pyenv install 3.11.0
pyenv global 3.11.0
```

**Linux (Ubuntu/Debian):**
```bash
# 添加 deadsnakes PPA
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update

# 安装 Python 3.11
sudo apt install python3.11 python3.11-venv python3.11-dev

# 设置为默认版本
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
```

### 1.2 验证安装

```bash
python3 --version
# 输出: Python 3.11.x

pip3 --version
# 输出: pip 23.x.x from ...
```

### 1.3 创建虚拟环境

```bash
# 进入后端目录
cd scholar-agent/backend

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 升级 pip
pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt
```

## 2. Node.js 环境配置

### 2.1 安装 Node.js

**Windows:**
```powershell
# 使用 winget 安装
winget install OpenJS.NodeJS.LTS

# 或从官网下载安装
# https://nodejs.org/
```

**macOS:**
```bash
# 使用 Homebrew 安装
brew install node@18

# 或使用 nvm 安装
nvm install 18
nvm use 18
```

**Linux (Ubuntu/Debian):**
```bash
# 使用 NodeSource 安装
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

### 2.2 验证安装

```bash
node --version
# 输出: v18.x.x

npm --version
# 输出: 9.x.x
```

### 2.3 安装前端依赖

```bash
# 进入前端目录
cd scholar-agent/frontend

# 安装依赖
npm install

# 或使用 yarn
yarn install
```

## 3. PostgreSQL 安装配置

### 3.1 安装 PostgreSQL

**Windows:**
```powershell
# 使用 winget 安装
winget install PostgreSQL.PostgreSQL.16

# 或从官网下载安装
# https://www.postgresql.org/download/windows/
```

**macOS:**
```bash
# 使用 Homebrew 安装
brew install postgresql@16

# 启动服务
brew services start postgresql@16
```

**Linux (Ubuntu/Debian):**
```bash
# 添加 PostgreSQL 官方仓库
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt update

# 安装 PostgreSQL 16
sudo apt install postgresql-16

# 启动服务
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 3.2 配置数据库

```bash
# 切换到 postgres 用户
sudo -u postgres psql

# 创建数据库和用户
CREATE USER scholar WITH PASSWORD 'scholar_password';
CREATE DATABASE scholar_agent OWNER scholar;
GRANT ALL PRIVILEGES ON DATABASE scholar_agent TO scholar;

# 退出
\q
```

### 3.3 配置远程访问（可选）

编辑 PostgreSQL 配置文件：

```bash
# 找到配置文件位置
sudo -u postgres psql -c "SHOW config_file"

# 编辑 postgresql.conf
sudo nano /etc/postgresql/16/main/postgresql.conf

# 修改以下行
listen_addresses = '*'
```

编辑 `pg_hba.conf`：

```bash
# 编辑 pg_hba.conf
sudo nano /etc/postgresql/16/main/pg_hba.conf

# 添加以下行
host    scholar_agent    scholar    0.0.0.0/0    md5
```

重启 PostgreSQL：

```bash
sudo systemctl restart postgresql
```

### 3.4 验证连接

```bash
# 使用 psql 连接
psql -U scholar -d scholar_agent -h localhost

# 或使用命令行
PGPASSWORD=scholar_password psql -U scholar -d scholar_agent -h localhost -c "SELECT version();"
```

## 4. Redis 安装配置

### 4.1 安装 Redis

**Windows:**
```powershell
# 使用 winget 安装
winget install Redis.Redis

# 或使用 Docker
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

**macOS:**
```bash
# 使用 Homebrew 安装
brew install redis

# 启动服务
brew services start redis
```

**Linux (Ubuntu/Debian):**
```bash
# 安装 Redis
sudo apt install redis-server

# 启动服务
sudo systemctl start redis
sudo systemctl enable redis
```

### 4.2 配置 Redis

编辑 Redis 配置文件：

```bash
# 编辑配置文件
sudo nano /etc/redis/redis.conf

# 修改以下配置
# 绑定地址（允许远程访问）
bind 0.0.0.0

# 设置密码（可选）
requirepass your_redis_password

# 持久化配置
appendonly yes
appendfsync everysec
```

重启 Redis：

```bash
sudo systemctl restart redis
```

### 4.3 验证连接

```bash
# 连接 Redis
redis-cli

# 测试连接
ping
# 输出: PONG

# 设置密码后连接
redis-cli -a your_redis_password
```

## 5. 环境变量配置

### 5.1 创建环境变量文件

```bash
# 复制示例文件
cp .env.example .env
```

### 5.2 配置环境变量

编辑 `.env` 文件：

```bash
# 应用配置
APP_NAME=ScholarAgent
APP_ENV=development
DEBUG=true
SECRET_KEY=your-random-secret-key-here

# 数据库配置
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=scholar
POSTGRES_PASSWORD=scholar_password
POSTGRES_DB=scholar_agent
DATABASE_URL=postgresql+asyncpg://scholar:scholar_password@localhost:5432/scholar_agent

# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_URL=redis://localhost:6379/0

# LLM 模型配置（选择一个）
# OpenAI
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_DEFAULT_MODEL=gpt-4o

# Anthropic
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key
ANTHROPIC_DEFAULT_MODEL=claude-3-5-sonnet-20241022

# 本地模型 (Ollama)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_DEFAULT_MODEL=qwen2.5:14b

# 默认 LLM 提供商
DEFAULT_LLM_PROVIDER=openai

# 学术数据源 API Keys（可选）
SEMANTIC_SCHOLAR_API_KEY=
OPENALEX_EMAIL=your-email@example.com
CROSSREF_EMAIL=your-email@example.com

# 前端配置
VITE_API_BASE_URL=http://localhost:8000

# 日志配置
LOG_LEVEL=DEBUG
LOG_FORMAT=json

# CORS 配置
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
```

### 5.3 生成 SECRET_KEY

```bash
# Python 生成
python3 -c "import secrets; print(secrets.token_hex(32))"

# OpenSSL 生成
openssl rand -hex 32
```

## 6. 启动步骤

### 6.1 启动后端服务

```bash
# 进入后端目录
cd scholar-agent/backend

# 激活虚拟环境
source venv/bin/activate  # Windows: venv\Scripts\activate

# 运行数据库迁移
alembic upgrade head

# 启动开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6.2 启动前端服务

```bash
# 进入前端目录
cd scholar-agent/frontend

# 启动开发服务器
npm run dev
```

### 6.3 访问应用

- **前端界面**: http://localhost:5173
- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/api/v1/health

## 7. 常见问题

### 7.1 Python 虚拟环境问题

**问题**: `python3 -m venv venv` 命令失败

**解决方案**:
```bash
# 安装 venv 模块
sudo apt install python3.11-venv

# 或使用 virtualenv
pip install virtualenv
virtualenv venv
```

### 7.2 PostgreSQL 连接问题

**问题**: 无法连接到 PostgreSQL

**解决方案**:
```bash
# 检查 PostgreSQL 服务状态
sudo systemctl status postgresql

# 检查端口是否监听
sudo netstat -tlnp | grep 5432

# 检查防火墙
sudo ufw allow 5432
```

### 7.3 Redis 连接问题

**问题**: 无法连接到 Redis

**解决方案**:
```bash
# 检查 Redis 服务状态
sudo systemctl status redis

# 检查端口是否监听
sudo netstat -tlnp | grep 6379

# 测试连接
redis-cli ping
```

### 7.4 npm 安装问题

**问题**: npm install 失败

**解决方案**:
```bash
# 清除缓存
npm cache clean --force

# 删除 node_modules 重新安装
rm -rf node_modules package-lock.json
npm install

# 使用淘宝镜像
npm config set registry https://registry.npmmirror.com
```

### 7.5 端口占用问题

**问题**: 端口已被占用

**解决方案**:
```bash
# 查找占用端口的进程
# Windows:
netstat -ano | findstr :8000
# macOS/Linux:
lsof -i :8000

# 终止进程
# Windows:
taskkill /PID <PID> /F
# macOS/Linux:
kill -9 <PID>
```

## 8. 开发工具推荐

### 8.1 IDE

- **VS Code**: 推荐使用，安装以下扩展：
  - Python
  - Pylance
  - ESLint
  - Prettier
  - GitLens

### 8.2 数据库管理

- **pgAdmin**: PostgreSQL 官方管理工具
- **DBeaver**: 通用数据库管理工具
- **DataGrip**: JetBrains 数据库 IDE

### 8.3 API 测试

- **Postman**: API 测试工具
- **Insomnia**: 轻量级 API 测试工具
- **curl**: 命令行 API 测试

## 9. 下一步

环境搭建完成后，可以：

1. 阅读 [架构文档](../architecture/system-overview.md) 了解系统设计
2. 查看 [API 文档](../api/openapi.yaml) 了解接口规范
3. 运行测试用例验证环境配置
4. 开始开发新功能
