# API 契约文档

本文档详细描述 ScholarAgent 各 API 端点的请求/响应格式和错误处理。

## 1. API 基础信息

### 1.1 基础 URL

- 开发环境: `http://localhost:8000`
- 生产环境: `https://api.scholar-agent.dev`

### 1.2 请求格式

- Content-Type: `application/json`
- Accept: `application/json`

### 1.3 认证方式

- API Key: `Authorization: Bearer <api_key>`
- 会话认证: Cookie-based session

### 1.4 响应格式

**成功响应**:
```json
{
  "success": true,
  "data": { ... },
  "message": "操作成功"
}
```

**错误响应**:
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述",
    "details": { ... }
  }
}
```

---

## 2. 搜索 API

### 2.1 创建搜索

**端点**: `POST /api/v1/search`

**描述**: 创建复杂查询搜索，返回搜索运行 ID

**请求体**:
```json
{
  "query": "近两年有实验对比的联邦学习隐私保护方法",
  "max_results": 50,
  "sources": ["semantic_scholar", "openalex", "arxiv"],
  "date_from": "2024-01-01",
  "date_to": "2025-12-31",
  "min_citations": 10,
  "open_access_only": false
}
```

**请求参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| query | string | 是 | 用户的自然查询，1-2000 字符 |
| max_results | integer | 否 | 最大返回结果数，默认 50，范围 1-500 |
| sources | array | 否 | 数据源列表，默认 ["semantic_scholar", "openalex"] |
| date_from | string | 否 | 起始日期，格式 YYYY-MM-DD |
| date_to | string | 否 | 结束日期，格式 YYYY-MM-DD |
| min_citations | integer | 否 | 最小引用数，默认 0 |
| open_access_only | boolean | 否 | 仅开放获取论文，默认 false |

**成功响应 (202)**:
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "query_plan": {
    "sub_queries": [
      {
        "query": "federated learning privacy protection",
        "source": "semantic_scholar",
        "rationale": "获取联邦学习隐私保护的基础论文"
      },
      {
        "query": "federated learning experiment comparison",
        "source": "openalex",
        "rationale": "查找包含实验对比的论文"
      }
    ],
    "strategy": "并行查询多个数据源，合并去重后按相关性排序"
  },
  "message": "搜索任务已创建，请通过 SSE 获取实时进度"
}
```

**错误响应**:

| 状态码 | 错误代码 | 说明 |
|--------|----------|------|
| 400 | BAD_REQUEST | 请求参数错误 |
| 422 | VALIDATION_ERROR | 数据验证失败 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

---

### 2.2 获取搜索详情

**端点**: `GET /api/v1/search/{run_id}`

**描述**: 获取指定搜索运行的状态、进度和结果

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| run_id | string (uuid) | 搜索运行 ID |

**成功响应 (200)**:
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "original_query": "近两年有实验对比的联邦学习隐私保护方法",
  "query_plan": {
    "sub_queries": [
      {
        "query": "federated learning privacy protection",
        "source": "semantic_scholar",
        "rationale": "获取联邦学习隐私保护的基础论文"
      }
    ],
    "strategy": "并行查询多个数据源，合并去重后按相关性排序"
  },
  "progress": {
    "total_sources": 3,
    "completed_sources": 3,
    "total_papers": 150,
    "deduplicated_papers": 120,
    "current_phase": "completed"
  },
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "title": "Federated Learning with Differential Privacy: A Survey",
      "authors": ["Zhang Wei", "Li Ming"],
      "abstract": "本文综述了联邦学习中的差分隐私保护方法...",
      "year": 2024,
      "venue": "IEEE TPAMI",
      "citation_count": 45,
      "doi": "10.1109/TPAMI.2024.1234567",
      "url": "https://ieeexplore.ieee.org/document/1234567",
      "pdf_url": "https://arxiv.org/pdf/2401.12345.pdf",
      "source": "semantic_scholar",
      "relevance_score": 0.95,
      "is_open_access": true
    }
  ],
  "created_at": "2025-06-27T10:00:00Z",
  "completed_at": "2025-06-27T10:00:30Z"
}
```

**错误响应**:

| 状态码 | 错误代码 | 说明 |
|--------|----------|------|
| 404 | NOT_FOUND | 搜索运行不存在 |

---

## 3. 论文 API

### 3.1 获取论文详情

**端点**: `GET /api/v1/papers/{paper_id}`

**描述**: 获取指定论文的详细信息

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| paper_id | string (uuid) | 论文 ID |

**成功响应 (200)**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "title": "Federated Learning with Differential Privacy: A Survey",
  "authors": ["Zhang Wei", "Li Ming"],
  "abstract": "本文综述了联邦学习中的差分隐私保护方法...",
  "year": 2024,
  "venue": "IEEE TPAMI",
  "citation_count": 45,
  "doi": "10.1109/TPAMI.2024.1234567",
  "url": "https://ieeexplore.ieee.org/document/1234567",
  "pdf_url": "https://arxiv.org/pdf/2401.12345.pdf",
  "source": "semantic_scholar",
  "relevance_score": 0.95,
  "is_open_access": true,
  "references": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440002",
      "title": "Deep Learning with Differential Privacy",
      "year": 2016,
      "citation_count": 1200
    }
  ],
  "citations": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440003",
      "title": "Recent Advances in Federated Learning Privacy",
      "year": 2025,
      "citation_count": 12
    }
  ],
  "fields_of_study": ["Computer Science", "Machine Learning"],
  "keywords": ["federated learning", "differential privacy", "privacy preservation"],
  "publication_date": "2024-03-15",
  "volume": "46",
  "issue": "3",
  "pages": "1234-1256"
}
```

**错误响应**:

| 状态码 | 错误代码 | 说明 |
|--------|----------|------|
| 404 | NOT_FOUND | 论文不存在 |

---

## 4. 分析 API

### 4.1 单篇论文分析

**端点**: `POST /api/v1/papers/{paper_id}/analyze`

**描述**: 对单篇论文进行深度分析

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| paper_id | string (uuid) | 论文 ID |

**请求体**:
```json
{
  "query": "该论文的主要贡献是什么？",
  "analysis_type": "full"
}
```

**请求参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| query | string | 是 | 分析上下文/问题 |
| analysis_type | string | 否 | 分析类型：summary/methodology/findings/pros_cons/full |

**成功响应 (200)**:
```json
{
  "paper_id": "550e8400-e29b-41d4-a716-446655440001",
  "analysis_type": "full",
  "summary": "本文系统综述了联邦学习中的差分隐私保护方法，分析了各类方法的优缺点...",
  "methodology": "采用系统文献综述方法，对 2016-2024 年的相关论文进行分类分析...",
  "key_findings": [
    "差分隐私在联邦学习中的应用可分为三类：本地差分隐私、全局差分隐私和混合差分隐私",
    "隐私预算的分配策略对模型性能有显著影响",
    "现有的隐私保护方法在通信效率和隐私保护强度之间存在权衡"
  ],
  "strengths": [
    "综述范围全面，涵盖了主要的隐私保护方法",
    "提供了清晰的分类框架",
    "包含了详细的实验对比"
  ],
  "weaknesses": [
    "对新兴的隐私保护技术（如联邦学习中的同态加密）讨论不足",
    "缺乏对实际部署场景的分析"
  ],
  "relevance_to_query": "该论文直接回答了关于联邦学习隐私保护方法的问题，提供了全面的方法对比",
  "created_at": "2025-06-27T10:01:00Z"
}
```

**错误响应**:

| 状态码 | 错误代码 | 说明 |
|--------|----------|------|
| 404 | NOT_FOUND | 论文不存在 |
| 422 | VALIDATION_ERROR | 请求参数验证失败 |

---

### 4.2 多篇论文对比

**端点**: `POST /api/v1/papers/compare`

**描述**: 对多篇论文进行对比分析

**请求体**:
```json
{
  "paper_ids": [
    "550e8400-e29b-41d4-a716-446655440001",
    "550e8400-e29b-41d4-a716-446655440004",
    "550e8400-e29b-41d4-a716-446655440005"
  ],
  "query": "对比这些论文的隐私保护方法"
}
```

**请求参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| paper_ids | array | 是 | 论文 ID 列表，2-10 个 |
| query | string | 是 | 对比的上下文/问题 |

**成功响应 (200)**:
```json
{
  "papers": [
    {
      "paper_id": "550e8400-e29b-41d4-a716-446655440001",
      "title": "Federated Learning with Differential Privacy: A Survey"
    },
    {
      "paper_id": "550e8400-e29b-41d4-a716-446655440004",
      "title": "Secure Aggregation for Federated Learning"
    },
    {
      "paper_id": "550e8400-e29b-41d4-a716-446655440005",
      "title": "Homomorphic Encryption in Federated Learning"
    }
  ],
  "comparison": {
    "methodology": "论文 A 采用差分隐私方法，论文 B 采用安全聚合方法，论文 C 采用同态加密方法。三种方法在隐私保护强度、计算开销和通信效率方面各有优劣。",
    "results": "差分隐私方法在隐私保护强度上表现最好，但计算开销较大；安全聚合方法在通信效率上最优；同态加密方法在安全性上最强，但计算开销最大。",
    "strengths_weaknesses": "论文 A 的优势是综述全面，劣势是缺乏实际部署分析；论文 B 的优势是通信效率高，劣势是隐私保护强度有限；论文 C 的优势是安全性强，劣势是计算开销大。",
    "recommendation": "根据具体应用场景选择方法：对隐私要求高的场景选择同态加密；对通信效率要求高的场景选择安全聚合；对综合性能要求高的场景选择差分隐私。"
  },
  "created_at": "2025-06-27T10:02:00Z"
}
```

**错误响应**:

| 状态码 | 错误代码 | 说明 |
|--------|----------|------|
| 400 | BAD_REQUEST | 论文数量不在 2-10 范围内 |
| 404 | NOT_FOUND | 论文不存在 |

---

## 5. 推荐 API

### 5.1 获取推荐

**端点**: `POST /api/v1/recommendations`

**描述**: 基于用户历史和偏好获取个性化文献推荐

**请求体**:
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440010",
  "context": "推荐与联邦学习隐私保护相关的论文",
  "limit": 10
}
```

**请求参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| user_id | string (uuid) | 否 | 用户 ID |
| context | string | 否 | 推荐上下文 |
| limit | integer | 否 | 推荐数量，默认 10，范围 1-50 |

**成功响应 (200)**:
```json
{
  "recommendations": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440020",
      "paper": {
        "id": "550e8400-e29b-41d4-a716-446655440006",
        "title": "Privacy-Preserving Federated Learning: A Survey",
        "authors": ["Wang Lei", "Chen Xia"],
        "abstract": "本文综述了隐私保护联邦学习的最新进展...",
        "year": 2025,
        "venue": "ACM Computing Surveys",
        "citation_count": 25,
        "url": "https://dl.acm.org/doi/10.1145/1234567",
        "source": "semantic_scholar",
        "relevance_score": 0.92,
        "is_open_access": true
      },
      "score": 0.92,
      "reason": "基于您对联邦学习隐私保护的兴趣，推荐这篇最新的综述论文"
    }
  ],
  "has_more": true
}
```

**错误响应**:

| 状态码 | 错误代码 | 说明 |
|--------|----------|------|
| 422 | VALIDATION_ERROR | 请求参数验证失败 |

---

### 5.2 提交反馈

**端点**: `POST /api/v1/recommendations/feedback`

**描述**: 用户对推荐结果的反馈

**请求体**:
```json
{
  "recommendation_id": "550e8400-e29b-41d4-a716-446655440020",
  "feedback_type": "helpful",
  "comment": "这篇论文正是我需要的"
}
```

**请求参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| recommendation_id | string (uuid) | 是 | 推荐 ID |
| feedback_type | string | 是 | 反馈类型：helpful/not_helpful/saved/dismissed |
| comment | string | 否 | 反馈评论，最多 500 字符 |

**成功响应 (200)**:
```json
{
  "success": true,
  "message": "反馈已记录，感谢您的反馈！"
}
```

**错误响应**:

| 状态码 | 错误代码 | 说明 |
|--------|----------|------|
| 404 | NOT_FOUND | 推荐不存在 |
| 422 | VALIDATION_ERROR | 请求参数验证失败 |

---

## 6. 证据 API

### 6.1 获取证据

**端点**: `GET /api/v1/evidence/{run_id}/{paper_id}`

**描述**: 获取指定论文在特定搜索运行中的证据片段

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| run_id | string (uuid) | 搜索运行 ID |
| paper_id | string (uuid) | 论文 ID |

**成功响应 (200)**:
```json
{
  "paper_id": "550e8400-e29b-41d4-a716-446655440001",
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "evidence_spans": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440030",
      "paper_id": "550e8400-e29b-41d4-a716-446655440001",
      "run_id": "550e8400-e29b-41d4-a716-446655440000",
      "claim": "该论文包含实验对比",
      "evidence_text": "我们在三个基准数据集上进行了实验对比，包括 MNIST、CIFAR-10 和 Shakespeare 数据集。实验结果表明，本文提出的方法在隐私保护强度和模型性能之间取得了更好的平衡。",
      "verdict": "supports",
      "confidence": 0.95,
      "page_number": 8,
      "section": "Results",
      "created_at": "2025-06-27T10:00:15Z"
    },
    {
      "id": "550e8400-e29b-41d4-a716-446655440031",
      "paper_id": "550e8400-e29b-41d4-a716-446655440001",
      "run_id": "550e8400-e29b-41d4-a716-446655440000",
      "claim": "该论文是近两年发表的",
      "evidence_text": "本文于 2024 年 3 月发表在 IEEE TPAMI 上。",
      "verdict": "supports",
      "confidence": 1.0,
      "page_number": 1,
      "section": "Header",
      "created_at": "2025-06-27T10:00:15Z"
    }
  ]
}
```

**错误响应**:

| 状态码 | 错误代码 | 说明 |
|--------|----------|------|
| 404 | NOT_FOUND | 搜索运行或论文不存在 |

---

## 7. 模型 API

### 7.1 保存模型配置

**端点**: `POST /api/v1/model/config`

**描述**: 保存用户的 LLM 模型配置

**请求体**:
```json
{
  "provider": "openai",
  "model_name": "gpt-4o",
  "api_key": "sk-your-api-key",
  "base_url": "https://api.openai.com/v1",
  "temperature": 0.7,
  "max_tokens": 4096
}
```

**请求参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| provider | string | 是 | LLM 提供商：openai/anthropic/ollama |
| model_name | string | 是 | 模型名称 |
| api_key | string | 否 | API Key（使用环境变量则无需填写） |
| base_url | string | 否 | 自定义 API 地址 |
| temperature | number | 否 | 温度参数，默认 0.7，范围 0-2 |
| max_tokens | integer | 否 | 最大 token 数，默认 4096，范围 1-128000 |

**成功响应 (200)**:
```json
{
  "success": true,
  "message": "模型配置已保存"
}
```

**错误响应**:

| 状态码 | 错误代码 | 说明 |
|--------|----------|------|
| 422 | VALIDATION_ERROR | 请求参数验证失败 |

---

### 7.2 测试模型连通性

**端点**: `POST /api/v1/model/test`

**描述**: 测试 LLM 模型配置是否正确

**请求体**:
```json
{
  "provider": "openai",
  "model_name": "gpt-4o",
  "api_key": "sk-your-api-key",
  "base_url": "https://api.openai.com/v1"
}
```

**成功响应 (200)**:
```json
{
  "success": true,
  "latency_ms": 250,
  "model_info": {
    "provider": "openai",
    "model": "gpt-4o",
    "context_window": 128000
  },
  "error": null
}
```

**错误响应**:

| 状态码 | 错误代码 | 说明 |
|--------|----------|------|
| 400 | BAD_REQUEST | 配置错误 |
| 500 | INTERNAL_ERROR | 连接失败 |

---

## 8. 健康检查 API

### 8.1 健康检查

**端点**: `GET /api/v1/health`

**描述**: 检查服务及其依赖的健康状态

**成功响应 (200)**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-06-27T10:00:00Z",
  "services": {
    "database": "connected",
    "redis": "connected",
    "llm": "available"
  }
}
```

**状态说明**:

| 状态 | 说明 |
|------|------|
| healthy | 所有服务正常 |
| degraded | 部分服务异常 |
| unhealthy | 服务不可用 |

**服务状态**:

| 服务 | 状态 | 说明 |
|------|------|------|
| database | connected/disconnected | 数据库连接状态 |
| redis | connected/disconnected | Redis 连接状态 |
| llm | available/unavailable | LLM 服务可用性 |

**错误响应**:

| 状态码 | 错误代码 | 说明 |
|--------|----------|------|
| 503 | SERVICE_UNAVAILABLE | 服务不可用 |

---

## 9. 错误码说明

### 9.1 通用错误码

| 错误代码 | HTTP 状态码 | 说明 |
|----------|-------------|------|
| BAD_REQUEST | 400 | 请求参数错误 |
| UNAUTHORIZED | 401 | 未授权 |
| FORBIDDEN | 403 | 禁止访问 |
| NOT_FOUND | 404 | 资源不存在 |
| METHOD_NOT_ALLOWED | 405 | 方法不允许 |
| CONFLICT | 409 | 资源冲突 |
| VALIDATION_ERROR | 422 | 数据验证失败 |
| INTERNAL_ERROR | 500 | 服务器内部错误 |
| SERVICE_UNAVAILABLE | 503 | 服务不可用 |

### 9.2 业务错误码

| 错误代码 | HTTP 状态码 | 说明 |
|----------|-------------|------|
| SEARCH_FAILED | 500 | 搜索失败 |
| LLM_TIMEOUT | 504 | LLM 调用超时 |
| SOURCE_UNAVAILABLE | 503 | 数据源不可用 |
| QUOTA_EXCEEDED | 429 | 配额超限 |
| INVALID_QUERY | 400 | 无效查询 |
| PAPER_NOT_FOUND | 404 | 论文未找到 |
| EVIDENCE_NOT_FOUND | 404 | 证据未找到 |

### 9.3 错误响应示例

```json
{
  "detail": "Invalid request parameters",
  "code": "VALIDATION_ERROR",
  "timestamp": "2025-06-27T10:00:00Z"
}
```

```json
{
  "detail": "LLM service timeout",
  "code": "LLM_TIMEOUT",
  "timestamp": "2025-06-27T10:00:00Z"
}
```

---

## 10. 限流说明

### 10.1 限流策略

| 端点 | 限流 | 说明 |
|------|------|------|
| POST /api/v1/search | 10 req/min | 搜索请求 |
| GET /api/v1/search/{run_id} | 60 req/min | 查询状态 |
| POST /api/v1/papers/{id}/analyze | 5 req/min | 论文分析 |
| POST /api/v1/papers/compare | 5 req/min | 论文对比 |
| POST /api/v1/recommendations | 30 req/min | 获取推荐 |
| POST /api/v1/recommendations/feedback | 60 req/min | 提交反馈 |
| GET /api/v1/health | 120 req/min | 健康检查 |

### 10.2 限流响应

**HTTP 状态码**: 429

**响应头**:
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1624819200
Retry-After: 60
```

**响应体**:
```json
{
  "detail": "Rate limit exceeded",
  "code": "QUOTA_EXCEEDED",
  "retry_after": 60,
  "timestamp": "2025-06-27T10:00:00Z"
}
```

---

## 11. SSE 实时推送

### 11.1 搜索进度推送

**端点**: `GET /api/v1/search/{run_id}/stream`

**描述**: 通过 SSE 实时推送搜索进度

**事件类型**:

| 事件 | 说明 | 数据格式 |
|------|------|----------|
| progress | 进度更新 | `{ "phase": "searching", "progress": 50 }` |
| result | 结果更新 | `{ "papers": [...] }` |
| complete | 完成 | `{ "status": "completed" }` |
| error | 错误 | `{ "code": "ERROR", "message": "..." }` |

**示例**:
```
event: progress
data: {"phase": "searching", "progress": 30, "message": "正在查询 Semantic Scholar..."}

event: progress
data: {"phase": "searching", "progress": 60, "message": "正在查询 OpenAlex..."}

event: result
data: {"papers": [{"id": "...", "title": "..."}]}

event: complete
data: {"status": "completed", "total_papers": 120}
```
