# 数据流文档

本文档详细描述 ScholarAgent 中的核心数据处理流程。

## 1. 查询处理流程

### 1.1 流程概述

```
用户输入 → 查询解析 → 约束提取 → 子查询生成 → 数据源选择
```

### 1.2 详细流程

#### 步骤 1: 用户输入接收

**输入格式**:
```json
{
  "query": "近两年有实验对比的联邦学习隐私保护方法",
  "max_results": 50,
  "sources": ["semantic_scholar", "openalex", "arxiv"]
}
```

**处理逻辑**:
1. 验证输入参数
2. 记录用户查询
3. 初始化搜索运行

#### 步骤 2: LLM 查询解析

**调用 LLM**:
```python
prompt = f"""
请分析以下学术查询，提取关键信息：

查询: {query}

请输出：
1. 主题关键词
2. 约束条件（时间、方法、数据集等）
3. 查询复杂度级别（1-5）
4. 建议的子查询列表
"""
```

**LLM 输出示例**:
```json
{
  "topic": "联邦学习隐私保护",
  "constraints": [
    {"type": "time", "value": "2024-2025"},
    {"type": "content", "value": "包含实验对比"}
  ],
  "complexity_level": 4,
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
    },
    {
      "query": "federated learning privacy 2024 2025",
      "source": "arxiv",
      "rationale": "获取最新的预印本论文"
    }
  ]
}
```

#### 步骤 3: 约束提取与验证

**约束类型**:

| 约束类型 | 描述 | 验证方式 |
|----------|------|----------|
| 时间约束 | 发表时间范围 | 比较 publication_date |
| 内容约束 | 包含实验/方法 | LLM 分析摘要 |
| 来源约束 | 期刊/会议 | 匹配 venue 字段 |
| 引用约束 | 最小引用数 | 比较 citation_count |
| 开放获取 | 是否 OA | 检查 is_open_access |

#### 步骤 4: 子查询生成

**生成策略**:
1. 主题查询：提取核心关键词
2. 扩展查询：添加同义词、相关词
3. 约束查询：添加时间、来源等限定

**示例**:
```
原始查询: "近两年有实验对比的联邦学习隐私保护方法"

子查询 1: "federated learning privacy protection"
子查询 2: "federated learning experiment comparison"
子查询 3: "federated learning privacy 2024 2025"
子查询 4: "federated learning differential privacy"
子查询 5: "federated learning secure aggregation"
```

#### 步骤 5: 数据源选择

**选择策略**:

| 数据源 | 适用场景 | 优先级 |
|--------|----------|--------|
| Semantic Scholar | 计算机科学、AI | 高 |
| OpenAlex | 全学科、开放数据 | 中 |
| Crossref | DOI 解析、元数据 | 中 |
| arXiv | 预印本、最新研究 | 高 |

**选择逻辑**:
1. 根据查询主题选择数据源
2. 根据时间要求调整优先级
3. 并行查询多个数据源

---

## 2. 检索排序流程

### 2.1 流程概述

```
并行检索 → 结果合并 → 去重 → 约束验证 → 相关性排序 → 分页输出
```

### 2.2 详细流程

#### 步骤 1: 并行检索

**实现方式**:
```python
async def parallel_search(sub_queries):
    tasks = []
    for sub_query in sub_queries:
        source = get_source(sub_query.source)
        tasks.append(source.search(sub_query.query))
    
    results = await asyncio.gather(*tasks)
    return results
```

**数据源 API 调用**:

| 数据源 | API 端点 | 限制 |
|--------|----------|------|
| Semantic Scholar | /graph/v1/paper/search | 100 req/5min |
| OpenAlex | /works | 100K req/day |
| Crossref | /works | 50 req/sec |
| arXiv | /api/query | 3 req/sec |

#### 步骤 2: 结果合并

**合并策略**:
1. 收集所有数据源的结果
2. 统一数据格式
3. 合并到单一列表

**数据标准化**:
```python
def normalize_paper(raw_paper, source):
    return {
        "title": raw_paper.get("title"),
        "authors": raw_paper.get("authors", []),
        "abstract": raw_paper.get("abstract"),
        "year": raw_paper.get("year"),
        "venue": raw_paper.get("venue"),
        "citation_count": raw_paper.get("citationCount", 0),
        "doi": raw_paper.get("doi"),
        "url": raw_paper.get("url"),
        "source": source
    }
```

#### 步骤 3: 智能去重

**去重策略**:

| 匹配方式 | 权重 | 阈值 |
|----------|------|------|
| DOI 匹配 | 1.0 | 精确匹配 |
| 标题相似度 | 0.8 | > 0.9 |
| 作者+年份 | 0.6 | 精确匹配 |

**去重算法**:
```python
def deduplicate_papers(papers):
    unique_papers = []
    seen_dois = set()
    seen_titles = set()
    
    for paper in papers:
        # DOI 精确匹配
        if paper.doi and paper.doi in seen_dois:
            continue
        
        # 标题相似度匹配
        title_key = normalize_title(paper.title)
        if title_key in seen_titles:
            continue
        
        # 添加到结果
        unique_papers.append(paper)
        if paper.doi:
            seen_dois.add(paper.doi)
        seen_titles.add(title_key)
    
    return unique_papers
```

#### 步骤 4: 约束验证

**验证流程**:
```python
def validate_constraints(paper, constraints):
    for constraint in constraints:
        if constraint.type == "time":
            if not validate_time(paper, constraint.value):
                return False
        elif constraint.type == "content":
            if not validate_content(paper, constraint.value):
                return False
        elif constraint.type == "venue":
            if not validate_venue(paper, constraint.value):
                return False
    return True
```

**时间约束验证**:
```python
def validate_time(paper, time_range):
    start_year, end_year = parse_time_range(time_range)
    return start_year <= paper.year <= end_year
```

**内容约束验证**:
```python
def validate_content(paper, content_type):
    # 使用 LLM 分析摘要
    prompt = f"""
    请判断以下论文是否包含{content_type}：
    
    标题: {paper.title}
    摘要: {paper.abstract}
    
    回答: 是/否
    """
    response = llm.generate(prompt)
    return response == "是"
```

#### 步骤 5: 相关性排序

**排序因子**:

| 因子 | 权重 | 说明 |
|------|------|------|
| 语义相似度 | 0.4 | 查询与论文的语义匹配度 |
| 引用数 | 0.2 | 论文的影响力 |
| 时间新鲜度 | 0.2 | 发表时间的新近程度 |
| 来源质量 | 0.1 | 数据源的权威性 |
| 开放获取 | 0.1 | 是否可免费获取 |

**排序算法**:
```python
def calculate_relevance_score(paper, query):
    # 语义相似度
    semantic_score = calculate_semantic_similarity(paper, query)
    
    # 引用数归一化
    citation_score = normalize_citations(paper.citation_count)
    
    # 时间新鲜度
    time_score = calculate_time_score(paper.year)
    
    # 来源质量
    source_score = get_source_quality(paper.source)
    
    # 开放获取
    oa_score = 1.0 if paper.is_open_access else 0.0
    
    # 加权求和
    total_score = (
        semantic_score * 0.4 +
        citation_score * 0.2 +
        time_score * 0.2 +
        source_score * 0.1 +
        oa_score * 0.1
    )
    
    return total_score
```

#### 步骤 6: 分页输出

**分页参数**:
```json
{
  "page": 1,
  "page_size": 20,
  "total": 150,
  "total_pages": 8
}
```

---

## 3. 证据验证流程

### 3.1 流程概述

```
论文全文 → 文本提取 → 段落分割 → 语义分析 → 证据提取 → 置信度评估
```

### 3.2 详细流程

#### 步骤 1: 论文全文获取

**获取方式**:
1. PDF 下载：从论文 URL 下载 PDF
2. HTML 解析：从论文网页提取文本
3. API 获取：使用数据源 API 获取全文

**PDF 文本提取**:
```python
def extract_text_from_pdf(pdf_path):
    # 使用 PyPDF2 或 pdfplumber
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
    return text
```

#### 步骤 2: 文本预处理

**预处理步骤**:
1. 去除特殊字符
2. 统一编码格式
3. 分段处理
4. 去除引用标记

```python
def preprocess_text(text):
    # 去除多余空白
    text = re.sub(r'\s+', ' ', text)
    
    # 去除引用标记 [1], [2] 等
    text = re.sub(r'\[\d+\]', '', text)
    
    # 分段
    paragraphs = text.split('\n\n')
    
    return paragraphs
```

#### 步骤 3: 段落分割

**分割策略**:
1. 按章节分割（Abstract, Introduction, Method, Results, Discussion）
2. 按段落分割
3. 按句子分割（用于精确定位）

**章节识别**:
```python
def identify_sections(text):
    sections = {
        "abstract": "",
        "introduction": "",
        "methodology": "",
        "results": "",
        "discussion": "",
        "conclusion": ""
    }
    
    # 使用正则表达式识别章节标题
    section_patterns = {
        "abstract": r"(?i)abstract",
        "introduction": r"(?i)introduction",
        "methodology": r"(?i)(method|methodology|approach)",
        "results": r"(?i)(results|experiments)",
        "discussion": r"(?i)discussion",
        "conclusion": r"(?i)conclusion"
    }
    
    return sections
```

#### 步骤 4: 语义分析

**LLM 分析**:
```python
def analyze_evidence(paragraph, claim):
    prompt = f"""
    请分析以下段落是否支持、反驳或中立于给定声明。
    
    声明: {claim}
    
    段落: {paragraph}
    
    请输出：
    1. 判断: supports/contradicts/neutral/insufficient
    2. 置信度: 0-1
    3. 关键证据句: 支持判断的原文句子
    """
    
    response = llm.generate(prompt)
    return parse_evidence_response(response)
```

#### 步骤 5: 证据提取

**证据类型**:

| 类型 | 描述 | 示例 |
|------|------|------|
| 支持证据 | 支持声明的证据 | "实验证明该方法有效" |
| 反驳证据 | 反驳声明的证据 | "该方法在某些场景下失效" |
| 中立证据 | 与声明无关的证据 | "该方法使用了神经网络" |

**证据定位**:
```python
def locate_evidence(paragraph, evidence_sentence):
    # 在段落中定位证据句子
    start_index = paragraph.find(evidence_sentence)
    end_index = start_index + len(evidence_sentence)
    
    # 计算页码（如果可获取）
    page_number = estimate_page_number(paragraph)
    
    # 计算章节
    section = identify_section(paragraph)
    
    return {
        "start_index": start_index,
        "end_index": end_index,
        "page_number": page_number,
        "section": section
    }
```

#### 步骤 6: 置信度评估

**评估因子**:

| 因子 | 权重 | 说明 |
|------|------|------|
| 证据明确性 | 0.4 | 证据是否明确支持/反驳声明 |
| 证据相关性 | 0.3 | 证据与声明的相关程度 |
| 证据来源 | 0.2 | 证据来自论文的哪个部分 |
| 证据数量 | 0.1 | 支持该判断的证据数量 |

**置信度计算**:
```python
def calculate_confidence(evidence):
    clarity_score = assess_clarity(evidence)
    relevance_score = assess_relevance(evidence)
    source_score = assess_source(evidence)
    quantity_score = assess_quantity(evidence)
    
    confidence = (
        clarity_score * 0.4 +
        relevance_score * 0.3 +
        source_score * 0.2 +
        quantity_score * 0.1
    )
    
    return min(confidence, 1.0)
```

---

## 4. 推荐系统流程

### 4.1 流程概述

```
用户行为 → 偏好学习 → 候选生成 → 相关性评分 → 排序输出 → 反馈收集
```

### 4.2 详细流程

#### 步骤 1: 用户行为收集

**行为类型**:

| 行为 | 权重 | 说明 |
|------|------|------|
| 搜索查询 | 0.3 | 用户的搜索历史 |
| 点击论文 | 0.4 | 用户点击的论文 |
| 收藏论文 | 0.6 | 用户收藏的论文 |
| 反馈评分 | 0.8 | 用户的显式反馈 |

#### 步骤 2: 偏好学习

**偏好模型**:
```python
def learn_preferences(user_behaviors):
    # 提取主题偏好
    topic_preferences = extract_topic_preferences(user_behaviors)
    
    # 提取作者偏好
    author_preferences = extract_author_preferences(user_behaviors)
    
    # 提取方法偏好
    method_preferences = extract_method_preferences(user_behaviors)
    
    return {
        "topics": topic_preferences,
        "authors": author_preferences,
        "methods": method_preferences
    }
```

#### 步骤 3: 候选生成

**候选来源**:
1. 基于内容的推荐：相似论文
2. 基于协同过滤的推荐：相似用户的喜好
3. 基于知识图谱的推荐：引用关系

#### 步骤 4: 相关性评分

**评分因子**:

| 因子 | 权重 | 说明 |
|------|------|------|
| 主题匹配 | 0.4 | 与用户兴趣的匹配度 |
| 作者匹配 | 0.2 | 与用户偏好的作者匹配 |
| 方法匹配 | 0.2 | 与用户偏好的方法匹配 |
| 论文质量 | 0.2 | 论文的引用数、影响力 |

#### 步骤 5: 推荐理由生成

**理由生成**:
```python
def generate_reason(paper, user_preferences):
    prompt = f"""
    请为以下推荐生成简洁的理由：
    
    论文: {paper.title}
    用户兴趣: {user_preferences.topics}
    
    推荐理由（一句话）:
    """
    
    return llm.generate(prompt)
```

#### 步骤 6: 反馈收集与更新

**反馈类型**:
- `helpful`: 正向反馈
- `not_helpful`: 负向反馈
- `saved`: 收藏
- `dismissed`: 忽略

**偏好更新**:
```python
def update_preferences(user_id, feedback):
    if feedback.type == "helpful":
        # 增强相关偏好
        enhance_preferences(user_id, feedback.paper)
    elif feedback.type == "not_helpful":
        # 削弱相关偏好
        weaken_preferences(user_id, feedback.paper)
```

---

## 5. 数据存储流程

### 5.1 数据库表结构

**核心表**:

| 表名 | 说明 | 主要字段 |
|------|------|----------|
| search_runs | 搜索运行记录 | id, query, status, created_at |
| papers | 论文信息 | id, title, authors, abstract, year |
| evidence_spans | 证据片段 | id, paper_id, claim, verdict |
| recommendations | 推荐记录 | id, paper_id, score, reason |
| recommendation_feedback | 推荐反馈 | id, recommendation_id, feedback_type |

### 5.2 缓存策略

**缓存类型**:

| 缓存对象 | TTL | 说明 |
|----------|-----|------|
| 搜索结果 | 1h | 相同查询的结果缓存 |
| 论文详情 | 24h | 论文元数据缓存 |
| LLM 响应 | 30min | LLM 调用结果缓存 |
| 用户会话 | 7d | 用户会话信息 |

### 5.3 数据一致性

**一致性保证**:
1. 数据库事务：ACID 保证
2. 缓存更新：写穿策略
3. 异步处理：消息队列保证最终一致性
