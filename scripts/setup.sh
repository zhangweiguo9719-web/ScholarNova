#!/bin/bash

# ScholarAgent 项目初始化脚本

set -e

echo "=========================================="
echo "ScholarAgent 项目初始化"
echo "=========================================="

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "错误: 未安装 Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "错误: 未安装 Docker Compose"
    exit 1
fi

# 创建 .env 文件
if [ ! -f .env ]; then
    echo "创建 .env 文件..."
    cp .env.example .env
    echo "请编辑 .env 文件填入实际配置"
else
    echo ".env 文件已存在"
fi

# 启动服务
echo "启动 Docker 服务..."
docker-compose up -d postgres redis

# 等待数据库就绪
echo "等待数据库就绪..."
sleep 10

# 运行数据库迁移
echo "运行数据库迁移..."
cd backend && alembic upgrade head && cd ..

# 启动所有服务
echo "启动所有服务..."
docker-compose up -d

echo ""
echo "=========================================="
echo "初始化完成！"
echo "=========================================="
echo ""
echo "访问地址:"
echo "  前端: http://localhost:5173"
echo "  API 文档: http://localhost:8000/docs"
echo "  健康检查: http://localhost:8000/api/v1/health"
echo ""
echo "常用命令:"
echo "  make logs       - 查看日志"
echo "  make down       - 停止服务"
echo "  make test       - 运行测试"
echo ""
