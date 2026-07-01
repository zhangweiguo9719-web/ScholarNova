# 测试指南

本文档介绍 ScholarAgent 项目的测试策略、工具和最佳实践。

## 1. 测试策略

### 1.1 测试金字塔

```
         /\
        /  \        E2E 测试（少量）
       /----\
      /      \      集成测试（适量）
     /--------\
    /          \    单元测试（大量）
   /____________\
```

### 1.2 测试类型

| 测试类型 | 数量 | 速度 | 成本 | 说明 |
|----------|------|------|------|------|
| 单元测试 | 多 | 快 | 低 | 测试单个函数/类 |
| 集成测试 | 中 | 中 | 中 | 测试模块间交互 |
| E2E 测试 | 少 | 慢 | 高 | 测试完整流程 |

## 2. 后端测试

### 2.1 测试框架

**pytest**:
```bash
# 安装测试依赖
pip install pytest pytest-asyncio pytest-cov httpx

# 运行测试
pytest

# 运行特定测试
pytest tests/test_api/test_search.py

# 运行并生成覆盖率
pytest --cov=app --cov-report=html
```

### 2.2 测试结构

```
backend/tests/
├── conftest.py              # 测试配置和 fixtures
├── test_api/                # API 测试
│   ├── test_health.py
│   ├── test_search.py
│   ├── test_papers.py
│   └── test_model_config.py
├── test_services/           # 服务测试
│   ├── test_query_planner.py
│   ├── test_deduplicator.py
│   ├── test_ranker.py
│   └── test_llm_gateway.py
├── test_sources/            # 数据源测试
│   ├── test_semantic_scholar.py
│   └── test_openalex.py
└── mocks/                   # Mock 数据
    └── __init__.py
```

### 2.3 测试配置

**conftest.py**:
```python
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db

# 测试数据库 URL
TEST_DATABASE_URL = "postgresql+asyncpg://scholar:scholar_password@localhost:5432/scholar_agent_test"

# 创建测试引擎
engine = create_async_engine(TEST_DATABASE_URL, echo=True)
TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def setup_database():
    """设置测试数据库"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session(setup_database):
    """创建数据库会话"""
    async with TestingSessionLocal() as session:
        yield session

@pytest.fixture
async def client(db_session):
    """创建测试客户端"""
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()
```

### 2.4 单元测试示例

**测试服务层**:
```python
import pytest
from unittest.mock import Mock, AsyncMock
from app.services.query_planner import QueryPlanner

class TestQueryPlanner:
    @pytest.fixture
    def planner(self):
        return QueryPlanner(llm_client=Mock())
    
    async def test_parse_query(self, planner):
        """测试查询解析"""
        query = "近两年有实验对比的联邦学习隐私保护方法"
        result = await planner.parse_query(query)
        
        assert result.topic == "联邦学习隐私保护"
        assert "2024" in result.constraints["time_range"]
        assert "实验对比" in result.constraints["content"]
    
    async def test_generate_sub_queries(self, planner):
        """测试子查询生成"""
        parsed_query = Mock(
            topic="联邦学习隐私保护",
            constraints={"time_range": "2024-2025"}
        )
        sub_queries = await planner.generate_sub_queries(parsed_query)
        
        assert len(sub_queries) > 0
        assert any("federated learning" in q.query for q in sub_queries)
```

**测试数据访问层**:
```python
import pytest
from app.models.paper import PaperEntity
from app.repositories.paper_repository import PaperRepository

class TestPaperRepository:
    @pytest.fixture
    def repository(self, db_session):
        return PaperRepository(db_session)
    
    async def test_create_paper(self, repository):
        """测试创建论文"""
        paper_data = {
            "title": "Test Paper",
            "authors": ["Author 1"],
            "abstract": "Test abstract",
            "year": 2024
        }
        paper = await repository.create(paper_data)
        
        assert paper.id is not None
        assert paper.title == "Test Paper"
    
    async def test_get_paper(self, repository):
        """测试获取论文"""
        # 创建论文
        paper = await repository.create({
            "title": "Test Paper",
            "authors": ["Author 1"],
            "year": 2024
        })
        
        # 获取论文
        result = await repository.get(paper.id)
        
        assert result is not None
        assert result.title == "Test Paper"
```

### 2.5 集成测试示例

**测试 API 端点**:
```python
import pytest
from httpx import AsyncClient

class TestSearchAPI:
    async def test_create_search(self, client: AsyncClient):
        """测试创建搜索"""
        response = await client.post("/api/v1/search", json={
            "query": "transformer model",
            "max_results": 10
        })
        
        assert response.status_code == 202
        data = response.json()
        assert "run_id" in data
        assert data["status"] == "pending"
    
    async def test_get_search_run(self, client: AsyncClient):
        """测试获取搜索运行"""
        # 创建搜索
        create_response = await client.post("/api/v1/search", json={
            "query": "test query"
        })
        run_id = create_response.json()["run_id"]
        
        # 获取搜索运行
        response = await client.get(f"/api/v1/search/{run_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == run_id
```

### 2.6 Mock 和 Stub

**使用 unittest.mock**:
```python
from unittest.mock import Mock, AsyncMock, patch

# Mock LLM 客户端
mock_llm = Mock()
mock_llm.generate = AsyncMock(return_value="mocked response")

# Mock 数据源
mock_source = Mock()
mock_source.search = AsyncMock(return_value=[
    {"title": "Paper 1", "authors": ["Author 1"]},
    {"title": "Paper 2", "authors": ["Author 2"]}
])

# 使用 patch
@patch('app.services.llm.client.OpenAIClient')
async def test_with_mock(mock_client_class):
    mock_client = Mock()
    mock_client_class.return_value = mock_client
    mock_client.generate = AsyncMock(return_value="response")
    
    # 测试代码
    ...
```

## 3. 前端测试

### 3.1 测试框架

**Jest + React Testing Library**:
```bash
# 安装测试依赖
npm install --save-dev @testing-library/react @testing-library/jest-dom

# 运行测试
npm test

# 运行并生成覆盖率
npm test -- --coverage
```

### 3.2 测试结构

```
frontend/src/
├── components/
│   └── SearchBar/
│       ├── SearchBar.tsx
│       ├── SearchBar.test.tsx
│       └── SearchBar.css
├── hooks/
│   ├── useSearch.ts
│   └── useSearch.test.ts
└── utils/
    ├── api.ts
    └── api.test.ts
```

### 3.3 组件测试示例

```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { SearchBar } from './SearchBar';

describe('SearchBar', () => {
  it('renders correctly', () => {
    render(<SearchBar onSearch={() => {}} />);
    
    expect(screen.getByPlaceholderText('输入搜索查询')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '搜索' })).toBeInTheDocument();
  });
  
  it('handles input change', () => {
    render(<SearchBar onSearch={() => {}} />);
    
    const input = screen.getByPlaceholderText('输入搜索查询');
    fireEvent.change(input, { target: { value: 'test query' } });
    
    expect(input).toHaveValue('test query');
  });
  
  it('calls onSearch on submit', async () => {
    const onSearch = jest.fn();
    render(<SearchBar onSearch={onSearch} />);
    
    const input = screen.getByPlaceholderText('输入搜索查询');
    const button = screen.getByRole('button', { name: '搜索' });
    
    fireEvent.change(input, { target: { value: 'test query' } });
    fireEvent.click(button);
    
    await waitFor(() => {
      expect(onSearch).toHaveBeenCalledWith('test query');
    });
  });
});
```

### 3.4 Hook 测试示例

```typescript
import { renderHook, act } from '@testing-library/react';
import { useSearch } from './useSearch';

describe('useSearch', () => {
  it('initializes with default values', () => {
    const { result } = renderHook(() => useSearch());
    
    expect(result.current.results).toEqual([]);
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });
  
  it('handles search', async () => {
    const { result } = renderHook(() => useSearch());
    
    await act(async () => {
      await result.current.search('test query');
    });
    
    expect(result.current.results).toBeDefined();
    expect(result.current.loading).toBe(false);
  });
});
```

## 4. 测试数据管理

### 4.1 测试数据工厂

**使用 factory_boy**:
```python
import factory
from app.models.paper import PaperEntity

class PaperFactory(factory.Factory):
    class Meta:
        model = PaperEntity
    
    id = factory.Sequence(lambda n: f"paper-{n}")
    title = factory.Faker('sentence')
    authors = factory.LazyFunction(lambda: [factory.Faker('name').generate()])
    abstract = factory.Faker('paragraph')
    year = factory.Faker('year')
    citation_count = factory.Faker('random_int', min=0, max=1000)
```

### 4.2 测试 Fixtures

**pytest fixtures**:
```python
@pytest.fixture
def sample_paper():
    """示例论文数据"""
    return {
        "title": "Test Paper",
        "authors": ["Author 1", "Author 2"],
        "abstract": "This is a test abstract.",
        "year": 2024,
        "citation_count": 10
    }

@pytest.fixture
def sample_papers():
    """示例论文列表"""
    return [
        {"title": "Paper 1", "authors": ["Author 1"], "year": 2024},
        {"title": "Paper 2", "authors": ["Author 2"], "year": 2023},
        {"title": "Paper 3", "authors": ["Author 3"], "year": 2022}
    ]
```

## 5. 测试覆盖率

### 5.1 生成覆盖率报告

**后端**:
```bash
# 生成覆盖率报告
pytest --cov=app --cov-report=html

# 查看报告
open htmlcov/index.html
```

**前端**:
```bash
# 生成覆盖率报告
npm test -- --coverage

# 查看报告
open coverage/lcov-report/index.html
```

### 5.2 覆盖率目标

| 模块 | 目标覆盖率 | 说明 |
|------|------------|------|
| API 层 | 80% | 主要端点 |
| 服务层 | 90% | 核心业务逻辑 |
| 数据访问层 | 85% | 数据库操作 |
| 工具函数 | 95% | 纯函数 |

### 5.3 覆盖率配置

**pytest 配置**:
```ini
# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = --cov=app --cov-report=term-missing
```

## 6. 测试最佳实践

### 6.1 测试原则

1. **独立性**: 每个测试独立运行，不依赖其他测试
2. **可重复**: 测试结果一致，可重复运行
3. **快速性**: 测试执行速度快
4. **清晰性**: 测试意图清晰，易于理解

### 6.2 命名规范

**测试函数命名**:
```python
# 格式: test_<被测试功能>_<场景>_<预期结果>
def test_search_with_empty_query_returns_error():
    ...

def test_search_with_valid_query_returns_results():
    ...

def test_search_with_invalid_source_raises_error():
    ...
```

### 6.3 测试数据

**使用有意义的测试数据**:
```python
# 好的测试数据
def test_search_federated_learning():
    query = "federated learning privacy protection"
    results = search(query)
    assert any("federated" in r.title.lower() for r in results)

# 不好的测试数据
def test_search():
    query = "test"
    results = search(query)
    assert len(results) > 0
```

### 6.4 断言

**使用具体的断言**:
```python
# 好的断言
assert response.status_code == 200
assert "run_id" in response.json()
assert len(results) == 10

# 不好的断言
assert response.ok
assert response.json()
assert results
```

## 7. 持续集成

### 7.1 GitHub Actions

**配置文件**:
```yaml
# .github/workflows/test.yml
name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: scholar
          POSTGRES_PASSWORD: scholar_password
          POSTGRES_DB: scholar_agent_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7
        ports:
          - 6379:6379
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run tests
        run: |
          cd backend
          pytest --cov=app --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: backend/coverage.xml
  
  frontend-tests:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: |
          cd frontend
          npm install
      
      - name: Run tests
        run: |
          cd frontend
          npm test -- --coverage
```

## 8. 测试工具

### 8.1 Python 测试工具

| 工具 | 用途 | 安装 |
|------|------|------|
| pytest | 测试框架 | `pip install pytest` |
| pytest-asyncio | 异步测试 | `pip install pytest-asyncio` |
| pytest-cov | 覆盖率 | `pip install pytest-cov` |
| httpx | HTTP 测试 | `pip install httpx` |
| factory_boy | 测试数据 | `pip install factory_boy` |
| unittest.mock | Mock | 内置 |

### 8.2 前端测试工具

| 工具 | 用途 | 安装 |
|------|------|------|
| Jest | 测试框架 | 内置 |
| React Testing Library | 组件测试 | `npm install @testing-library/react` |
| jest-dom | DOM 断言 | `npm install @testing-library/jest-dom` |
| MSW | API Mock | `npm install msw` |

## 9. 常见问题

### 9.1 测试数据库

**问题**: 测试污染开发数据库

**解决方案**: 使用独立的测试数据库
```python
TEST_DATABASE_URL = "postgresql+asyncpg://scholar:scholar_password@localhost:5432/scholar_agent_test"
```

### 9.2 异步测试

**问题**: 异步测试不执行

**解决方案**: 使用 pytest-asyncio
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

### 9.3 Mock 外部服务

**问题**: 测试依赖外部服务

**解决方案**: 使用 Mock
```python
@patch('app.services.external_api.ExternalAPI.call')
async def test_with_mock(mock_call):
    mock_call.return_value = {"status": "ok"}
    result = await function_under_test()
    assert result["status"] == "ok"
```

## 10. 测试清单

### 10.1 新功能测试

- [ ] 单元测试覆盖核心逻辑
- [ ] 集成测试覆盖 API 端点
- [ ] 边界条件测试
- [ ] 错误处理测试
- [ ] 性能测试（如需要）

### 10.2 代码审查测试

- [ ] 测试覆盖率达标
- [ ] 测试命名清晰
- [ ] 测试独立可重复
- [ ] Mock 使用合理
- [ ] 断言具体明确
