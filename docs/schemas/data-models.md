# ScholarAgent 数据模型文档

## 概述

本文档定义了 ScholarAgent 系统的核心数据模型。所有模型使用 UUID 作为主键，时间字段使用 UTC 时区。

## 数据库表结构

### 1. search_runs - 搜索运行表

存储每次文献检索任务的信息。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PK | 主键 |
| original_query | TEXT | NOT NULL | 用户原始查询 |
| query_plan | JSONB | | LLM 生成的查询计划 |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'pending' | 状态: pending/running/completed/failed |
| sources | JSONB | | 请求的数据源列表 |
| max_results | INTEGER | DEFAULT 50 | 最大结果数 |
| filters | JSONB | | 过滤条件（日期、引用数等） |
| progress | JSONB | | 进度信息 |
| error_message | TEXT | | 错误信息（失败时） |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 创建时间 |
| started_at | TIMESTAMPTZ | | 开始执行时间 |
| completed_at | TIMESTAMPTZ | | 完成时间 |

**索引:**
- `idx_search_runs_status` ON (status)
- `idx_search_runs_created_at` ON (created_at DESC)

### 2. paper_entities - 论文实体表

存储论文的元数据信息。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PK | 主键 |
| external_id | VARCHAR(255) | UNIQUE | 外部数据源 ID (如 S2 ID, DOI) |
| title | TEXT | NOT NULL | 论文标题 |
| abstract | TEXT | | 摘要 |
| authors | JSONB | | 作者列表 |
| year | INTEGER | | 发表年份 |
| venue | VARCHAR(500) | | 发表期刊/会议 |
| doi | VARCHAR(255) | UNIQUE | DOI |
| url | TEXT | | 论文链接 |
| pdf_url | TEXT | | PDF 链接 |
| source | VARCHAR(50) | NOT NULL | 数据来源 |
| citation_count | INTEGER | DEFAULT 0 | 引用数 |
| is_open_access | BOOLEAN | DEFAULT FALSE | 是否开放获取 |
| fields_of_study | JSONB | | 研究领域 |
| keywords | JSONB | | 关键词 |
| publication_date | DATE | | 发表日期 |
| volume | VARCHAR(50) | | 卷号 |
| issue | VARCHAR(50) | | 期号 |
| pages | VARCHAR(50) | | 页码 |
| references | JSONB | | 参考文献列表 |
| metadata | JSONB | | 其他元数据 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 更新时间 |

**索引:**
- `idx_paper_entities_external_id` ON (external_id)
- `idx_paper_entities_doi` ON (doi)
- `idx_paper_entities_year` ON (year)
- `idx_paper_entities_citation_count` ON (citation_count DESC)
- `idx_paper_entities_title_trgm` GIN ON (title) - 用于模糊搜索

### 3. evidence_spans - 证据片段表

存储从论文中提取的证据片段。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PK | 主键 |
| run_id | UUID | FK -> search_runs.id, NOT NULL | 关联的搜索运行 |
| paper_id | UUID | FK -> paper_entities.id, NOT NULL | 关联的论文 |
| claim | TEXT | NOT NULL | 被验证的声明 |
| evidence_text | TEXT | NOT NULL | 原文证据片段 |
| verdict | VARCHAR(20) | NOT NULL | 结论: supports/contradicts/neutral/insufficient |
| confidence | FLOAT | NOT NULL | 置信度 (0-1) |
| page_number | INTEGER | | 页码 |
| section | VARCHAR(100) | | 所在章节 |
| context | TEXT | | 上下文信息 |
| llm_model | VARCHAR(100) | | 使用的 LLM 模型 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 创建时间 |

**索引:**
- `idx_evidence_spans_run_id` ON (run_id)
- `idx_evidence_spans_paper_id` ON (paper_id)
- `idx_evidence_spans_verdict` ON (verdict)
- `idx_evidence_spans_run_paper` ON (run_id, paper_id)

### 4. recommendations - 推荐表

存储系统生成的文献推荐。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PK | 主键 |
| user_id | UUID | | 用户 ID（可选，支持匿名） |
| paper_id | UUID | FK -> paper_entities.id, NOT NULL | 推荐的论文 |
| score | FLOAT | NOT NULL | 推荐分数 (0-1) |
| reason | TEXT | NOT NULL | 推荐理由 |
| context | JSONB | | 推荐上下文 |
| source_run_id | UUID | FK -> search_runs.id | 来源搜索运行 |
| is_dismissed | BOOLEAN | DEFAULT FALSE | 是否被忽略 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 创建时间 |

**索引:**
- `idx_recommendations_user_id` ON (user_id)
- `idx_recommendations_score` ON (score DESC)
- `idx_recommendations_created_at` ON (created_at DESC)

### 5. recommendation_feedback - 推荐反馈表

存储用户对推荐的反馈。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PK | 主键 |
| recommendation_id | UUID | FK -> recommendations.id, NOT NULL | 关联的推荐 |
| user_id | UUID | | 用户 ID |
| feedback_type | VARCHAR(20) | NOT NULL | 反馈类型: helpful/not_helpful/saved/dismissed |
| comment | TEXT | | 评论 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 创建时间 |

**索引:**
- `idx_recommendation_feedback_recommendation_id` ON (recommendation_id)
- `idx_recommendation_feedback_user_id` ON (user_id)

## 关系图

```
┌─────────────────┐       ┌─────────────────┐
│   search_runs   │       │ paper_entities  │
├─────────────────┤       ├─────────────────┤
│ id (PK)         │◄──┐   │ id (PK)         │
│ original_query  │   │   │ external_id     │
│ query_plan      │   │   │ title           │
│ status          │   │   │ abstract        │
│ ...             │   │   │ ...             │
└────────┬────────┘   │   └────────┬────────┘
         │            │            │
         │            │            │
         ▼            │            ▼
┌─────────────────┐   │   ┌─────────────────┐
│ evidence_spans  │   │   │ recommendations │
├─────────────────┤   │   ├─────────────────┤
│ id (PK)         │   │   │ id (PK)         │
│ run_id (FK) ────┘   │   │ paper_id (FK) ──┘
│ paper_id (FK) ──────│──►│ score           │
│ claim               │   │ reason          │
│ evidence_text       │   │ ...             │
│ verdict             │   └────────┬────────┘
│ ...                 │            │
└─────────────────┘            │
                                    ▼
                         ┌─────────────────────┐
                         │ recommendation_     │
                         │ feedback            │
                         ├─────────────────────┤
                         │ id (PK)             │
                         │ recommendation_id   │
                         │ feedback_type       │
                         │ ...                 │
                         └─────────────────────┘
```

## JSON Schema 定义

### query_plan 结构

```json
{
  "sub_queries": [
    {
      "query": "transformer protein structure",
      "source": "semantic_scholar",
      "rationale": "搜索 Transformer 在蛋白质结构预测中的应用"
    },
    {
      "query": "protein folding deep learning",
      "source": "openalex",
      "rationale": "搜索深度学习蛋白质折叠相关研究"
    }
  ],
  "strategy": "将查询分解为技术方法和应用场景两个维度"
}
```

### progress 结构

```json
{
  "total_sources": 4,
  "completed_sources": 2,
  "total_papers": 150,
  "deduplicated_papers": 120,
  "current_phase": "searching",
  "source_progress": {
    "semantic_scholar": {"status": "completed", "count": 50},
    "openalex": {"status": "completed", "count": 45},
    "crossref": {"status": "running", "count": 0},
    "arxiv": {"status": "pending", "count": 0}
  }
}
```

### authors 结构

```json
[
  {
    "name": "John Doe",
    "affiliation": "MIT",
    "orcid": "0000-0001-2345-6789"
  },
  {
    "name": "Jane Smith",
    "affiliation": "Stanford University"
  }
]
```

### filters 结构

```json
{
  "date_from": "2020-01-01",
  "date_to": "2024-12-31",
  "min_citations": 10,
  "open_access_only": false,
  "fields_of_study": ["Computer Science", "Biology"],
  "languages": ["en"]
}
```

## 数据库约束

### 外键约束

1. `evidence_spans.run_id` -> `search_runs.id` (CASCADE DELETE)
2. `evidence_spans.paper_id` -> `paper_entities.id` (RESTRICT)
3. `recommendations.paper_id` -> `paper_entities.id` (RESTRICT)
4. `recommendations.source_run_id` -> `search_runs.id` (SET NULL)
5. `recommendation_feedback.recommendation_id` -> `recommendations.id` (CASCADE DELETE)

### 检查约束

1. `evidence_spans.confidence` >= 0 AND <= 1
2. `recommendations.score` >= 0 AND <= 1
3. `search_runs.status` IN ('pending', 'running', 'completed', 'failed')
4. `evidence_spans.verdict` IN ('supports', 'contradicts', 'neutral', 'insufficient')
5. `recommendation_feedback.feedback_type` IN ('helpful', 'not_helpful', 'saved', 'dismissed')

## 设计决策

1. **UUID 主键**: 所有表使用 UUID 作为主键，避免分布式环境下的 ID 冲突
2. **JSONB 字段**: 灵活存储结构化数据（如作者列表、查询计划），同时支持索引查询
3. **时间戳**: 所有时间字段使用 `TIMESTAMPTZ`，确保存储 UTC 时间
4. **软删除**: 未实现软删除，数据删除为物理删除（可通过 `is_dismissed` 标记忽略推荐）
5. **审计字段**: 所有表包含 `created_at`，需要时添加 `updated_at`
