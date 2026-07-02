.PHONY: help install dev up down logs test lint format clean

# 默认目标
help: ## 显示帮助信息
	@echo "ScholarAgent - 学术智能体"
	@echo "=========================="
	@echo ""
	@echo "可用命令:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# =============================================================================
# 环境设置
# =============================================================================
install: ## 安装所有依赖
	@echo "安装后端依赖..."
	cd backend && pip install -e ".[dev]"
	@echo "安装前端依赖..."
	cd frontend && npm ci

setup: ## 初始化项目（创建 .env、数据库等）
	@if [ ! -f .env ]; then cp .env.example .env; echo "已创建 .env 文件"; fi
	@echo "请编辑 .env 文件填入实际配置"

# =============================================================================
# Docker 命令
# =============================================================================
up: ## 启动所有服务
	docker compose up -d

up-build: ## 构建并启动所有服务
	docker compose up -d --build

down: ## 停止所有服务
	docker compose down

down-volumes: ## 停止服务并删除数据卷
	docker compose down -v

logs: ## 查看所有服务日志
	docker compose logs -f

logs-backend: ## 查看后端日志
	docker compose logs -f backend

logs-frontend: ## 查看前端日志
	docker compose logs -f frontend

# =============================================================================
# 开发命令
# =============================================================================
dev: ## 启动开发环境（前台运行）
	docker compose up

dev-backend: ## 仅启动后端开发服务器
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## 仅启动前端开发服务器
	cd frontend && npm run dev

# =============================================================================
# 数据库命令
# =============================================================================
db-migrate: ## 运行数据库迁移
	cd backend && alembic upgrade head

db-revision: ## 创建新的迁移版本
	cd backend && alembic revision --autogenerate -m "$(message)"

db-reset: ## 重置数据库（危险！）
	cd backend && alembic downgrade base && alembic upgrade head

# =============================================================================
# 测试命令
# =============================================================================
test: test-backend test-frontend ## 运行所有测试

test-backend: ## 运行后端测试
	cd backend && pytest

test-frontend: ## 运行前端测试
	cd frontend && npm test

test-cov: ## 生成覆盖率报告
	cd backend && pytest --cov=app --cov-report=html --cov-report=term-missing
	cd frontend && npm run test:coverage

test-api: ## 运行 API 测试
	cd backend && pytest tests/test_api/

test-services: ## 运行服务层测试
	cd backend && pytest tests/test_services/

test-sources: ## 运行数据源适配器测试
	cd backend && pytest tests/test_sources/

test-evaluation: ## 运行评测测试
	cd backend && pytest tests/evaluation/

# =============================================================================
# 代码质量
# =============================================================================
lint: ## 运行代码检查
	cd backend && ruff check .
	cd frontend && npm run lint

format: ## 格式化代码
	cd backend && ruff format .
	cd frontend && npm run format

type-check: ## 运行类型检查
	cd backend && mypy app

# =============================================================================
# 清理命令
# =============================================================================
clean: ## 清理构建产物和缓存
	@echo "清理 Python 缓存..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "清理 Node 缓存..."
	rm -rf frontend/node_modules/.cache
	@echo "清理完成"

clean-all: clean ## 清理所有（包括 node_modules 和虚拟环境）
	rm -rf backend/.venv
	rm -rf frontend/node_modules

# =============================================================================
# 生产部署
# =============================================================================
build: ## 构建部署镜像
	docker compose build

deploy: ## 启动部署
	docker compose up -d --build

# =============================================================================
# 工具命令
# =============================================================================
seed: ## 填充测试数据
	cd backend && python ../scripts/seed_data.py

shell-backend: ## 进入后端容器 shell
	docker compose exec backend bash

shell-db: ## 进入数据库 shell
	docker compose exec postgres psql -U scholar -d scholar_agent

shell-redis: ## 进入 Redis shell
	docker compose exec redis redis-cli
