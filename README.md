# ScholarNova — 学术新星

面向复杂科研场景的智能论文搜索与推荐系统。将自然语言查询转化为可执行检索计划，多源聚合搜索，AI 深度分析，构建个人研究知识库。

## ✨ 核心功能

- 🔍 **复杂查询理解**：支持 Level 1-5 的学术查询，从简单关键词到复杂多约束查询
- 🌐 **多源聚合**：Semantic Scholar + OpenAlex + Crossref + arXiv 四大学术数据库
- ✅ **约束验证**：硬约束满足率 ≥ 85%，确保推荐结果符合查询要求
- 📊 **证据级推荐**：每篇推荐附带原文证据片段，支持溯源验证
- 🤖 **BYOK 模型网关**：支持 OpenAI / Anthropic / Ollama，灵活切换
- 📈 **实时进度**：SSE 实时推送检索进度，用户体验流畅
- 🔄 **个性化推荐**：基于用户反馈的智能推荐系统

## 🚀 快速开始

### 环境要求

| 组件 | 版本要求 | 说明 |
|------|----------|------|
| Python | 3.11+ | 后端运行环境 |
| Node.js | 18+ | 前端构建环境 |
| PostgreSQL | 16+ | 主数据库 |
| Redis | 7+ | 缓存和消息队列 |
| Docker | 20.10+ | 容器化部署（可选） |

### 方式一：Docker 快速启动（推荐）

```bash
# 1. 克隆项目
git clone <repository-url>
cd scholar-agent

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入必要的 API Keys

# 3. 一键启动
docker-compose up -d --build

# 4. 访问应用
# 前端: http://localhost:5173
# API 文档: http://localhost:8000/docs
# 健康检查: http://localhost:8000/api/v1/health
```

### 方式二：本地开发环境

#### 1. 后端环境

```bash
# 进入后端目录
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp ../.env.example ../.env
# 编辑 .env 文件

# 运行数据库迁移
alembic upgrade head

# 启动后端服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 2. 前端环境

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

#### 3. 基础服务

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

### 方式三：使用 Makefile

```bash
# 查看所有可用命令
make help

# 安装依赖
make install

# 启动开发环境
make dev

# 运行测试
make test

# 代码检查
make lint

# 格式化代码
make format
```

## 📖 API 文档

启动后端服务后，访问以下地址查看 API 文档：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI 规范**: [docs/api/openapi.yaml](docs/api/openapi.yaml)

### 主要 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/search` | POST | 创建复杂查询搜索 |
| `/api/v1/search/{run_id}` | GET | 获取搜索运行详情 |
| `/api/v1/papers/{paper_id}` | GET | 获取论文详情 |
| `/api/v1/papers/{paper_id}/analyze` | POST | 单篇论文分析 |
| `/api/v1/papers/compare` | POST | 多篇论文对比 |
| `/api/v1/recommendations` | POST | 获取文献推荐 |
| `/api/v1/recommendations/feedback` | POST | 提交推荐反馈 |
| `/api/v1/evidence/{run_id}/{paper_id}` | GET | 获取证据 |
| `/api/v1/model/config` | POST | 保存模型配置 |
| `/api/v1/model/test` | POST | 测试模型连通性 |
| `/api/v1/health` | GET | 健康检查 |

## 🏗️ 项目结构

```
scholar-agent/
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── api/               # API 路由
│   │   │   ├── v1/           # v1 版本 API
│   │   │   └── deps.py       # 依赖注入
│   │   ├── models/           # SQLAlchemy 数据模型
│   │   │   ├── paper.py      # 论文模型
│   │   │   ├── search_run.py # 搜索运行模型
│   │   │   ├── evidence.py   # 证据模型
│   │   │   └── recommendation.py # 推荐模型
│   │   ├── schemas/          # Pydantic 数据模式
│   │   ├── services/         # 业务逻辑服务
│   │   │   ├── evidence/     # 证据验证服务
│   │   │   ├── llm/          # LLM 网关服务
│   │   │   └── pdf/          # PDF 处理服务
│   │   └── core/             # 核心工具
│   │       └── cache.py      # Redis 缓存
│   ├── alembic/              # 数据库迁移
│   ├── tests/                # 测试用例
│   │   ├── test_api/         # API 测试
│   │   ├── test_services/    # 服务测试
│   │   └── test_sources/     # 数据源测试
│   └── Dockerfile            # 后端容器配置
├── frontend/                   # React 前端
│   ├── src/
│   │   ├── api/              # API 客户端
│   │   ├── components/       # UI 组件
│   │   │   ├── Layout/       # 布局组件
│   │   │   ├── SearchBar/    # 搜索栏
│   │   │   ├── ResultsList/  # 结果列表
│   │   │   ├── PaperDetail/  # 论文详情
│   │   │   ├── EvidencePanel/# 证据面板
│   │   │   └── ModelConfig/  # 模型配置
│   │   ├── pages/            # 页面组件
│   │   ├── stores/           # Zustand 状态管理
│   │   └── styles/           # 样式文件
│   └── Dockerfile            # 前端容器配置
├── docs/                       # 项目文档
│   ├── api/                   # API 文档
│   ├── schemas/               # 数据模型文档
│   ├── adr/                   # 架构决策记录
│   ├── architecture/          # 架构文档
│   ├── deployment/            # 部署文档
│   ├── development/           # 开发指南
│   └── demo/                  # 演示材料
├── scripts/                    # 工具脚本
│   ├── setup.sh              # 项目初始化
│   └── seed_data.py          # 数据种子
├── docker-compose.yml          # Docker 编排
├── Makefile                    # 常用命令
├── .env.example                # 环境变量示例
└── README.md                   # 项目说明
```

## 🧪 测试

### 运行测试

```bash
# 运行所有测试
make test

# 运行后端测试
cd backend && pytest

# 运行前端测试
cd frontend && npm test

# 运行测试并生成覆盖率报告
cd backend && pytest --cov=app --cov-report=html
```

### 测试结构

```
backend/tests/
├── test_api/           # API 端点测试
│   ├── test_health.py
│   ├── test_search.py
│   ├── test_papers.py
│   └── test_model_config.py
├── test_services/      # 业务逻辑测试
│   ├── test_query_planner.py
│   ├── test_deduplicator.py
│   ├── test_ranker.py
│   └── test_llm_gateway.py
├── test_sources/       # 数据源测试
└── conftest.py         # 测试配置
```

## 📦 部署

### Docker 部署（推荐）

```bash
# 构建生产镜像
docker-compose -f docker-compose.prod.yml build

# 启动生产环境
docker-compose -f docker-compose.prod.yml up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 生产环境配置

1. **环境变量**: 配置 `.env` 文件中的生产环境变量
2. **数据库**: 使用外部 PostgreSQL 实例
3. **缓存**: 使用外部 Redis 实例
4. **反向代理**: 配置 Nginx 反向代理
5. **HTTPS**: 配置 SSL 证书
6. **监控**: 配置日志收集和监控告警

详细部署指南请参考 [docs/deployment/](docs/deployment/)

## 🤝 贡献指南

我们欢迎所有形式的贡献！

### 贡献流程

1. **Fork** 项目到你的 GitHub
2. **创建** 功能分支 (`git checkout -b feature/amazing-feature`)
3. **提交** 更改 (`git commit -m 'feat: add amazing feature'`)
4. **推送** 到分支 (`git push origin feature/amazing-feature`)
5. **创建** Pull Request

### 开发规范

- 遵循 [代码规范](docs/development/coding-standards.md)
- 编写测试用例
- 更新相关文档
- 使用 Conventional Commits 规范

### 问题反馈

- 提交 [Issue](https://github.com/your-org/scholar-agent/issues)
- 描述问题现象和复现步骤
- 提供环境信息和日志

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 高性能 Python Web 框架
- [React](https://react.dev/) - 用户界面库
- [Semantic Scholar](https://www.semanticscholar.org/) - 学术搜索 API
- [OpenAlex](https://openalex.org/) - 开放学术数据
- [shadcn/ui](https://ui.shadcn.com/) - UI 组件库

## 📞 联系方式

- **项目主页**: [GitHub](https://github.com/your-org/scholar-agent)
- **问题反馈**: [Issues](https://github.com/your-org/scholar-agent/issues)
- **邮箱**: team@scholar-agent.dev

---

**ScholarNova** — 让学术检索更智能、更高效
