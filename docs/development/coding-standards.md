# 代码规范

本文档定义 ScholarAgent 项目的代码规范和最佳实践。

## 1. Python 代码规范

### 1.1 代码风格

**遵循 PEP 8**:
- 使用 4 空格缩进
- 行长度限制：88 字符（Black 默认）
- 使用双引号字符串
- 函数和变量使用 snake_case
- 类名使用 PascalCase
- 常量使用 UPPER_SNAKE_CASE

**格式化工具**:
```bash
# 使用 Black 格式化
black app/

# 使用 isort 排序导入
isort app/
```

### 1.2 导入规范

**导入顺序**:
1. 标准库导入
2. 相关第三方库导入
3. 本地应用/库导入

**示例**:
```python
# 标准库
import asyncio
import logging
from datetime import datetime
from typing import List, Optional

# 第三方库
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

# 本地导入
from app.core.config import settings
from app.models.paper import PaperEntity
from app.schemas.paper import PaperResponse
```

### 1.3 类型注解

**使用类型注解**:
```python
# 函数签名
async def get_paper(paper_id: str) -> Optional[PaperEntity]:
    ...

# 变量注解
papers: List[PaperEntity] = []
count: int = 0

# 复杂类型
from typing import Dict, List, Optional, Union

ResponseData = Dict[str, Union[str, int, List[str]]]
```

### 1.4 文档字符串

**使用 Google 风格**:
```python
async def search_papers(
    query: str,
    max_results: int = 50,
    sources: List[str] = None
) -> List[PaperEntity]:
    """搜索学术论文。

    Args:
        query: 用户的搜索查询
        max_results: 最大返回结果数
        sources: 数据源列表

    Returns:
        论文列表

    Raises:
        ValueError: 查询为空时抛出
        ConnectionError: 数据源连接失败时抛出
    """
    ...
```

### 1.5 错误处理

**使用特定异常**:
```python
# 定义自定义异常
class PaperNotFoundError(Exception):
    """论文未找到异常"""
    pass

class DataSourceError(Exception):
    """数据源错误"""
    pass

# 使用异常
async def get_paper(paper_id: str) -> PaperEntity:
    paper = await repository.get(paper_id)
    if not paper:
        raise PaperNotFoundError(f"Paper {paper_id} not found")
    return paper

# 捕获异常
try:
    paper = await get_paper(paper_id)
except PaperNotFoundError as e:
    raise HTTPException(status_code=404, detail=str(e))
except DataSourceError as e:
    raise HTTPException(status_code=503, detail=str(e))
```

### 1.6 日志规范

**使用结构化日志**:
```python
import logging

logger = logging.getLogger(__name__)

async def search_papers(query: str):
    logger.info("开始搜索论文", extra={
        "query": query,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    try:
        results = await do_search(query)
        logger.info("搜索完成", extra={
            "query": query,
            "result_count": len(results)
        })
        return results
    except Exception as e:
        logger.error("搜索失败", extra={
            "query": query,
            "error": str(e)
        }, exc_info=True)
        raise
```

### 1.7 异步编程

**使用 async/await**:
```python
# 异步函数
async def fetch_papers(query: str) -> List[Paper]:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()

# 并发执行
async def search_multiple_sources(queries: List[str]):
    tasks = [fetch_papers(q) for q in queries]
    results = await asyncio.gather(*tasks)
    return results
```

### 1.8 配置管理

**使用 Pydantic Settings**:
```python
from pydantic import BaseSettings

class Settings(BaseSettings):
    # 应用配置
    app_name: str = "ScholarAgent"
    debug: bool = False
    secret_key: str
    
    # 数据库配置
    database_url: str
    redis_url: str
    
    # LLM 配置
    openai_api_key: Optional[str] = None
    default_llm_provider: str = "openai"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

## 2. TypeScript/React 代码规范

### 2.1 代码风格

**使用 ESLint + Prettier**:
```bash
# 检查代码
npm run lint

# 格式化代码
npm run format
```

**配置文件**:
```json
// .eslintrc.json
{
  "extends": [
    "eslint:recommended",
    "plugin:react/recommended",
    "plugin:react-hooks/recommended",
    "plugin:@typescript-eslint/recommended"
  ],
  "rules": {
    "react/react-in-jsx-scope": "off",
    "@typescript-eslint/explicit-function-return-type": "off"
  }
}
```

### 2.2 命名规范

**组件命名**:
```typescript
// 使用 PascalCase
const SearchBar: React.FC = () => {
  return <div>SearchBar</div>;
};

// 文件名与组件名一致
// SearchBar.tsx
```

**变量和函数命名**:
```typescript
// 使用 camelCase
const searchQuery = 'transformer model';
const handleSubmit = () => {};

// 常量使用 UPPER_SNAKE_CASE
const API_BASE_URL = 'http://localhost:8000';
const MAX_RESULTS = 50;
```

### 2.3 TypeScript 规范

**使用严格类型**:
```typescript
// 接口定义
interface Paper {
  id: string;
  title: string;
  authors: string[];
  abstract: string;
  year: number;
  citationCount: number;
}

// 类型别名
type SearchStatus = 'pending' | 'running' | 'completed' | 'failed';

// 泛型
interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
}
```

### 2.4 组件规范

**使用函数组件**:
```typescript
// 函数组件
const PaperCard: React.FC<{ paper: Paper }> = ({ paper }) => {
  return (
    <div className="paper-card">
      <h3>{paper.title}</h3>
      <p>{paper.abstract}</p>
    </div>
  );
};

// 使用 React.memo 优化
const PaperCard = React.memo<{ paper: Paper }>(({ paper }) => {
  return (
    <div className="paper-card">
      <h3>{paper.title}</h3>
      <p>{paper.abstract}</p>
    </div>
  );
});
```

### 2.5 Hooks 规范

**自定义 Hooks**:
```typescript
// 自定义 Hook
const useSearch = () => {
  const [results, setResults] = useState<Paper[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const search = useCallback(async (query: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.search(query);
      setResults(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  return { results, loading, error, search };
};
```

### 2.6 状态管理

**使用 Zustand**:
```typescript
import { create } from 'zustand';

interface SearchState {
  query: string;
  results: Paper[];
  loading: boolean;
  setQuery: (query: string) => void;
  search: (query: string) => Promise<void>;
}

const useSearchStore = create<SearchState>((set) => ({
  query: '',
  results: [],
  loading: false,
  setQuery: (query) => set({ query }),
  search: async (query) => {
    set({ loading: true });
    try {
      const results = await api.search(query);
      set({ results, loading: false });
    } catch (error) {
      set({ loading: false });
      throw error;
    }
  },
}));
```

## 3. 数据库规范

### 3.1 模型定义

**使用 SQLAlchemy**:
```python
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class PaperEntity(Base):
    __tablename__ = "papers"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False, index=True)
    authors = Column(JSON, nullable=False)
    abstract = Column(Text)
    year = Column(Integer, index=True)
    citation_count = Column(Integer, default=0)
    
    # 关系
    evidence_spans = relationship("EvidenceSpan", back_populates="paper")
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
```

### 3.2 迁移规范

**Alembic 迁移**:
```bash
# 创建迁移
alembic revision --autogenerate -m "add papers table"

# 运行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

**迁移文件命名**:
```
alembic/versions/
├── 001_initial_tables.py
├── 002_add_papers_table.py
└── 003_add_evidence_table.py
```

## 4. API 规范

### 4.1 RESTful 设计

**URL 命名**:
```
# 资源使用复数名词
GET /api/v1/papers
GET /api/v1/papers/{id}
POST /api/v1/papers
PUT /api/v1/papers/{id}
DELETE /api/v1/papers/{id}

# 操作使用动词
POST /api/v1/search
POST /api/v1/papers/{id}/analyze
POST /api/v1/papers/compare
```

### 4.2 请求/响应格式

**请求格式**:
```json
{
  "query": "transformer model",
  "max_results": 50,
  "sources": ["semantic_scholar", "openalex"]
}
```

**响应格式**:
```json
{
  "success": true,
  "data": { ... },
  "message": "操作成功"
}
```

### 4.3 错误处理

**错误响应**:
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数验证失败",
    "details": {
      "field": "query",
      "message": "查询不能为空"
    }
  }
}
```

## 5. 测试规范

### 5.1 测试命名

**Python 测试**:
```python
# 测试文件命名
tests/test_api/test_search.py
tests/test_services/test_query_planner.py

# 测试函数命名
def test_search_returns_results():
    ...

def test_search_with_empty_query_raises_error():
    ...
```

**前端测试**:
```typescript
// 测试文件命名
src/components/SearchBar/SearchBar.test.tsx

// 测试用例命名
describe('SearchBar', () => {
  it('renders correctly', () => {});
  it('handles input change', () => {});
  it('submits search query', () => {});
});
```

### 5.2 测试结构

**Arrange-Act-Assert**:
```python
def test_search_returns_results():
    # Arrange
    query = "transformer model"
    mock_source = MockDataSource()
    
    # Act
    results = await search_papers(query, sources=[mock_source])
    
    # Assert
    assert len(results) > 0
    assert results[0].title is not None
```

## 6. Git 规范

### 6.1 分支命名

```
# 功能分支
feature/add-search-api
feature/implement-recommendation

# 修复分支
fix/search-timeout
fix/database-connection

# 发布分支
release/v1.0.0

# 热修复分支
hotfix/critical-bug
```

### 6.2 提交信息

**Conventional Commits**:
```
# 格式
<type>(<scope>): <description>

# 示例
feat(api): add search endpoint
fix(database): fix connection timeout
docs(readme): update installation guide
test(search): add unit tests
refactor(services): extract query planner
```

**类型说明**:
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `test`: 测试相关
- `refactor`: 代码重构
- `style`: 代码格式调整
- `perf`: 性能优化
- `chore`: 构建/工具相关

## 7. 文档规范

### 7.1 代码注释

**Python 注释**:
```python
# 单行注释
x = x + 1  # 行内注释

"""
多行注释
用于复杂逻辑说明
"""

# TODO: 待实现功能
# FIXME: 需要修复的问题
# HACK: 临时解决方案
```

### 7.2 README 规范

**README 结构**:
1. 项目标题和简介
2. 功能特性
3. 快速开始
4. 安装步骤
5. 使用说明
6. API 文档
7. 贡献指南
8. 许可证

### 7.3 API 文档

**使用 OpenAPI**:
```yaml
# openapi.yaml
openapi: 3.1.0
info:
  title: ScholarAgent API
  version: 1.0.0
paths:
  /api/v1/search:
    post:
      summary: 创建搜索
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SearchRequest'
      responses:
        '202':
          description: 搜索任务已创建
```

## 8. 安全规范

### 8.1 敏感信息

**不要提交敏感信息**:
```bash
# .gitignore
.env
*.pem
*.key
```

### 8.2 输入验证

**使用 Pydantic 验证**:
```python
from pydantic import BaseModel, validator

class SearchRequest(BaseModel):
    query: str
    max_results: int = 50
    
    @validator('query')
    def query_not_empty(cls, v):
        if not v.strip():
            raise ValueError('查询不能为空')
        return v
    
    @validator('max_results')
    def max_results_in_range(cls, v):
        if not 1 <= v <= 500:
            raise ValueError('max_results 必须在 1-500 之间')
        return v
```

### 8.3 SQL 注入防护

**使用 ORM**:
```python
# 正确：使用参数化查询
async def get_paper(paper_id: str):
    query = select(PaperEntity).where(PaperEntity.id == paper_id)
    result = await session.execute(query)
    return result.scalar_one_or_none()

# 错误：拼接 SQL
# query = f"SELECT * FROM papers WHERE id = '{paper_id}'"
```

## 9. 性能规范

### 9.1 异步编程

**使用 async/await**:
```python
# 并发执行
async def search_multiple(queries: List[str]):
    tasks = [search(q) for q in queries]
    return await asyncio.gather(*tasks)
```

### 9.2 数据库优化

**使用索引**:
```python
class PaperEntity(Base):
    title = Column(String, index=True)
    year = Column(Integer, index=True)
```

**批量操作**:
```python
# 批量插入
await session.execute(insert(PaperEntity), papers_data)
```

### 9.3 缓存策略

**使用 Redis 缓存**:
```python
async def get_paper(paper_id: str):
    # 先查缓存
    cached = await redis.get(f"paper:{paper_id}")
    if cached:
        return json.loads(cached)
    
    # 查数据库
    paper = await repository.get(paper_id)
    
    # 写入缓存
    await redis.setex(
        f"paper:{paper_id}",
        3600,  # 1 小时过期
        json.dumps(paper)
    )
    
    return paper
```

## 10. 代码审查清单

### 10.1 审查要点

- [ ] 代码风格是否符合规范
- [ ] 是否有类型注解
- [ ] 是否有文档字符串
- [ ] 是否有错误处理
- [ ] 是否有测试覆盖
- [ ] 是否有安全漏洞
- [ ] 是否有性能问题
- [ ] 是否有重复代码

### 10.2 审查流程

1. 提交 Pull Request
2. 自动运行 CI 检查
3. 人工代码审查
4. 修复审查意见
5. 合并代码
