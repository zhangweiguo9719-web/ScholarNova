# 开发环境搭建

本文档介绍如何搭建 ScholarAgent 的开发环境。

## 前置要求

| 工具 | 版本 | 说明 |
|------|------|------|
| Python | 3.11+ | 后端运行环境 |
| Node.js | 18+ | 前端构建环境 |
| PostgreSQL | 16+ | 主数据库 |
| Redis | 7+ | 缓存服务 |
| Git | 2.30+ | 版本控制 |
| Docker | 20.10+ | 容器化（可选） |

## 1. 获取代码

```bash
# 克隆项目
git clone <repository-url>
cd scholar-agent

# 查看项目结构
ls -la
```

## 2. 后端环境搭建

### 2.1 Python 环境

```bash
# 进入后端目录
cd backend

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

# 安装开发依赖
pip install -r requirements-dev.txt
```

### 2.2 数据库配置

**方式一：使用 Docker**
```bash
# 启动 PostgreSQL
docker run -d --name postgres \
  -e POSTGRES_USER=scholar \
  -e POSTGRES_PASSWORD=scholar_password \
  -e POSTGRES_DB=scholar_agent \
  -p 5432:5432 \
  postgres:16-alpine

# 启动 Redis
docker run -d --name redis \
  -p 6379:6379 \
  redis:7-alpine
```

**方式二：本地安装**

参考 [本地部署文档](../deployment/local.md) 安装 PostgreSQL 和 Redis。

### 2.3 环境变量配置

```bash
# 复制环境变量示例
cp ../.env.example ../.env

# 编辑环境变量
nano ../.env
```

**最小配置**:
```bash
# 数据库配置
DATABASE_URL=postgresql+asyncpg://scholar:scholar_password@localhost:5432/scholar_agent

# Redis 配置
REDIS_URL=redis://localhost:6379/0

# LLM 配置（至少配置一个）
OPENAI_API_KEY=sk-your-api-key
DEFAULT_LLM_PROVIDER=openai

# 应用配置
APP_ENV=development
DEBUG=true
SECRET_KEY=dev-secret-key
```

### 2.4 数据库迁移

```bash
# 运行迁移
alembic upgrade head

# 创建新迁移（如果需要）
alembic revision --autogenerate -m "描述信息"

# 回滚迁移
alembic downgrade -1
```

### 2.5 启动后端

```bash
# 开发模式启动
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 或使用 Makefile
make dev-backend
```

**验证启动**:
```bash
# 访问健康检查
curl http://localhost:8000/api/v1/health

# 访问 API 文档
open http://localhost:8000/docs
```

## 3. 前端环境搭建

### 3.1 Node.js 环境

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 或使用 yarn
yarn install
```

### 3.2 环境变量配置

创建 `.env.local` 文件：
```bash
# API 基础 URL
VITE_API_BASE_URL=http://localhost:8000
```

### 3.3 启动前端

```bash
# 开发模式启动
npm run dev

# 或使用 Makefile
make dev-frontend
```

**验证启动**:
```bash
# 访问前端
open http://localhost:5173
```

## 4. 开发工具配置

### 4.1 VS Code 配置

**推荐扩展**:
- Python
- Pylance
- ESLint
- Prettier
- GitLens
- Docker

**settings.json**:
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/backend/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  }
}
```

### 4.2 PyCharm 配置

1. 打开项目目录
2. 配置 Python 解释器：`backend/venv/bin/python`
3. 配置数据库连接
4. 配置运行配置

### 4.3 Git 配置

```bash
# 配置 Git 用户
git config user.name "Your Name"
git config user.email "your.email@example.com"

# 安装 pre-commit hooks
pre-commit install
```

## 5. 数据库管理

### 5.1 使用 Alembic

```bash
# 进入后端目录
cd backend

# 创建新迁移
alembic revision --autogenerate -m "add new table"

# 运行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1

# 查看迁移历史
alembic history

# 查看当前版本
alembic current
```

### 5.2 使用 pgAdmin

1. 打开 pgAdmin
2. 连接到 PostgreSQL
3. 创建数据库 `scholar_agent`
4. 创建用户 `scholar`

### 5.3 数据库备份

```bash
# 备份数据库
pg_dump -U scholar -h localhost scholar_agent > backup.sql

# 恢复数据库
psql -U scholar -h localhost scholar_agent < backup.sql
```

## 6. 测试环境

### 6.1 后端测试

```bash
# 进入后端目录
cd backend

# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_api/test_health.py

# 运行测试并生成覆盖率报告
pytest --cov=app --cov-report=html

# 运行测试并显示详细输出
pytest -v
```

### 6.2 前端测试

```bash
# 进入前端目录
cd frontend

# 运行测试
npm test

# 运行测试并生成覆盖率
npm test -- --coverage
```

### 6.3 集成测试

```bash
# 启动测试环境
docker-compose -f docker-compose.test.yml up -d

# 运行集成测试
pytest tests/integration/

# 清理测试环境
docker-compose -f docker-compose.test.yml down
```

## 7. 代码质量

### 7.1 Python 代码检查

```bash
# 进入后端目录
cd backend

# 使用 flake8 检查
flake8 app/

# 使用 black 格式化
black app/

# 使用 isort 排序导入
isort app/

# 使用 mypy 类型检查
mypy app/
```

### 7.2 前端代码检查

```bash
# 进入前端目录
cd frontend

# 使用 ESLint 检查
npm run lint

# 使用 Prettier 格式化
npm run format
```

### 7.3 使用 Makefile

```bash
# 代码检查
make lint

# 代码格式化
make format

# 运行所有检查
make check
```

## 8. 调试技巧

### 8.1 后端调试

**使用 VS Code 调试**:

创建 `.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"],
      "cwd": "${workspaceFolder}/backend",
      "env": {
        "PYTHONPATH": "${workspaceFolder}/backend"
      }
    }
  ]
}
```

**使用 pdb 调试**:
```python
# 在代码中添加断点
import pdb; pdb.set_trace()

# 或使用 breakpoint()
breakpoint()
```

### 8.2 前端调试

**使用浏览器开发者工具**:
1. 打开 Chrome DevTools (F12)
2. 使用 Console 查看日志
3. 使用 Network 查看请求
4. 使用 Sources 设置断点

**使用 React DevTools**:
1. 安装 React DevTools 扩展
2. 查看组件树和状态

### 8.3 数据库调试

**使用 SQLAlchemy 日志**:
```python
# 在配置中启用 SQL 日志
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

**使用 pgAdmin**:
1. 连接到数据库
2. 使用查询工具执行 SQL
3. 查看表结构和数据

## 9. 常见问题

### 9.1 Python 虚拟环境问题

**问题**: `python3 -m venv venv` 失败

**解决方案**:
```bash
# 安装 venv 模块
sudo apt install python3.11-venv

# 或使用 virtualenv
pip install virtualenv
virtualenv venv
```

### 9.2 依赖安装失败

**问题**: `pip install` 失败

**解决方案**:
```bash
# 升级 pip
pip install --upgrade pip

# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 清除缓存
pip cache purge
```

### 9.3 数据库连接失败

**问题**: 无法连接到 PostgreSQL

**解决方案**:
```bash
# 检查 PostgreSQL 服务状态
sudo systemctl status postgresql

# 检查端口是否监听
sudo netstat -tlnp | grep 5432

# 测试连接
psql -U scholar -h localhost -d scholar_agent
```

### 9.4 前端依赖问题

**问题**: `npm install` 失败

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

### 9.5 端口占用

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

## 10. 下一步

环境搭建完成后，可以：

1. 阅读 [代码规范](coding-standards.md) 了解代码风格
2. 查看 [测试指南](testing-guide.md) 了解测试方法
3. 阅读 [贡献指南](contributing.md) 了解贡献流程
4. 查看 [架构文档](../architecture/system-overview.md) 了解系统设计
