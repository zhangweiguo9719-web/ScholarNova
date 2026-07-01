# ADR-001: 技术栈选择

## 状态

已接受

## 日期

2024-01-15

## 背景

ScholarAgent 是一个学术智能体系统，需要支持：
- 高并发的学术数据源检索
- LLM 调用和流式响应
- 实时进度推送（SSE）
- 复杂的查询规划和证据验证
- 用户交互和反馈收集

需要选择合适的技术栈来满足这些需求。

## 决策

### 后端：FastAPI + Python

**选择理由：**
1. **异步支持**: FastAPI 原生支持 async/await，适合 IO 密集型操作（API 调用、数据库查询）
2. **类型安全**: 基于 Pydantic 的请求/响应校验，减少运行时错误
3. **自动文档**: 自动生成 OpenAPI/Swagger 文档，降低前后端协作成本
4. **SSE 支持**: 原生支持 Server-Sent Events，实现实时进度推送
5. **Python 生态**: 丰富的 NLP/ML 库（transformers, spaCy），便于后续扩展

**备选方案：**
- Node.js + Express: 缺乏成熟的 NLP 库支持
- Go + Gin: 学习曲线较陡，Python 生态优势明显

### 前端：React + Vite + TypeScript

**选择理由：**
1. **组件生态**: React 拥有最丰富的组件库（shadcn/ui, Tailwind CSS）
2. **开发体验**: Vite 提供极快的 HMR，提升开发效率
3. **类型安全**: TypeScript 提供编译时类型检查
4. **社区支持**: 最大的前端社区，问题容易解决

**备选方案：**
- Vue 3 + Vite: 生态相对较小
- Next.js: 无需 SSR，Vite 更轻量

### 数据库：PostgreSQL + SQLAlchemy

**选择理由：**
1. **JSON 支持**: PostgreSQL 的 JSONB 类型适合存储灵活的查询计划、元数据
2. **全文搜索**: 内置全文搜索功能，可满足基础搜索需求
3. **扩展性**: 支持 pgvector 扩展，未来可添加向量搜索
4. **SQLAlchemy**: 成熟的 ORM，支持异步（asyncpg），迁移工具 Alembic

**备选方案：**
- MongoDB: 缺乏 ACID 事务支持
- MySQL: JSON 支持较弱

### 缓存：Redis

**选择理由：**
1. **性能**: 内存数据库，读写延迟极低
2. **数据结构**: 支持多种数据结构（String, Hash, List, Set）
3. **过期策略**: 内置 TTL 支置，适合缓存场景
4. **发布订阅**: 可用于实时消息推送

### LLM 网关：多模型支持

**选择理由：**
1. **灵活性**: 支持 OpenAI、Anthropic、本地 Ollama 等多种模型
2. **可切换性**: 用户可根据需求选择不同的模型
3. **容错性**: 一个提供商不可用时可切换到其他提供商
4. **成本控制**: 支持本地模型，降低 API 调用成本

### 部署：Docker Compose

**选择理由：**
1. **一致性**: 开发、测试、生产环境一致
2. **简易性**: 单命令启动所有服务
3. **可移植性**: 支持任何 Docker 环境
4. **扩展性**: 可轻松迁移到 Kubernetes

## 后果

### 正面影响

1. **开发效率**: Python + TypeScript 全栈开发，代码复用率高
2. **类型安全**: 前后端都有类型检查，减少运行时错误
3. **实时性**: SSE 支持实时进度推送，提升用户体验
4. **可扩展性**: 模块化设计，易于添加新的数据源和功能
5. **文档自动化**: OpenAPI 自动生成，降低维护成本

### 负面影响

1. **GIL 限制**: Python 的 GIL 可能影响 CPU 密集型任务（可通过多进程缓解）
2. **前端复杂度**: React 状态管理需要额外工具（Zustand）
3. **部署复杂度**: 多服务架构增加运维复杂度

### 风险缓解

1. **性能问题**: CPU 密集型任务使用 Celery 异步处理
2. **状态管理**: 使用 Zustand 轻量级状态管理，降低复杂度
3. **运维复杂度**: 使用 Docker Compose 和 Makefile 简化操作

## 相关文档

- [OpenAPI 规范](../api/openapi.yaml)
- [数据模型](../schemas/data-models.md)
