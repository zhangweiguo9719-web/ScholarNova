"""
Prompt 模板库

集中管理所有 LLM Prompt 模板，支持:
- 查询解析 (QUERY_PARSE_PROMPT)
- 单篇论文分析 (PAPER_ANALYSIS_PROMPT)
- 多篇论文对比 (COMPARISON_PROMPT)
- 约束证据提取 (EVIDENCE_EXTRACTION_PROMPT)
- 关键词扩展 (KEYWORD_EXPANSION_PROMPT)

每个 Prompt 要求:
- 明确的输出格式（JSON Schema）
- 学术场景的专业术语
- 不确定时标注置信度
- 禁止编造不存在的信息
"""

from typing import Optional


class PromptTemplates:
    """Prompt 模板集合"""

    # =================================================================
    # 查询解析
    # =================================================================

    QUERY_PARSE_PROMPT = """You are an expert academic search query parser. Given a natural language query about scholarly papers, parse it into structured components.

## Input
User query: "{query}"
Available data sources: {sources}

## Task
Parse the query and return a JSON object with the following structure:

```json
{{
  "intent": "<one of: exact_lookup | open_exploration | literature_review | similar_recommendation | methodology_survey>",
  "keywords": ["<extracted technical keywords>"],
  "expanded_keywords": {{
    "<keyword>": ["<synonym1>", "<abbreviation1>", "<related_term1>"]
  }},
  "constraints": [
    {{
      "key": "<constraint_key>",
      "operator": "<gte|lte|eq|in|contains>",
      "value": <constraint_value>,
      "description": "<human readable description>",
      "certainty": "<confirmed|inferred>"
    }}
  ],
  "sub_queries": [
    {{
      "query": "<optimized query string for this source>",
      "source": "<data_source_name>",
      "rationale": "<why this query formulation for this source>"
    }}
  ],
  "strategy": "<overall retrieval strategy description>"
}}
```

## Rules
1. Extract technical concepts, method names, dataset names as keywords
2. Distinguish hard constraints (confirmed) from soft preferences (inferred)
3. Expand keywords: include abbreviations, synonyms, and related terms
4. Generate one sub-query per available data source, optimized for that source's syntax
5. If information is uncertain, mark certainty as "inferred"
6. Never fabricate facts

## Few-shot Examples

### Example 1 - Simple keyword search
Query: "transformer attention mechanism"
```json
{{
  "intent": "open_exploration",
  "keywords": ["transformer", "attention mechanism"],
  "expanded_keywords": {{
    "transformer": ["self-attention", "multi-head attention", "MHA"],
    "attention mechanism": ["attention", "scaled dot-product attention", "cross-attention"]
  }},
  "constraints": [],
  "sub_queries": [
    {{"query": "transformer attention mechanism", "source": "semantic_scholar", "rationale": "Direct keyword search on comprehensive index"}},
    {{"query": "transformer attention mechanism", "source": "openalex", "rationale": "Broad coverage search"}}
  ],
  "strategy": "Broad keyword search across multiple sources for comprehensive coverage"
}}
```

### Example 2 - Time-constrained query
Query: "近两年有实验对比的联邦学习隐私保护方法"
```json
{{
  "intent": "literature_review",
  "keywords": ["federated learning", "privacy preservation", "differential privacy"],
  "expanded_keywords": {{
    "federated learning": ["FL", "distributed learning", "collaborative learning"],
    "privacy preservation": ["privacy protection", "data privacy", "secure aggregation"],
    "differential privacy": ["DP", "local differential privacy", "LDP"]
  }},
  "constraints": [
    {{"key": "year", "operator": "gte", "value": 2024, "description": "Published in 2024 or later", "certainty": "confirmed"}},
    {{"key": "has_comparative_experiment", "operator": "eq", "value": true, "description": "Must include comparative experiments", "certainty": "confirmed"}}
  ],
  "sub_queries": [
    {{"query": "federated learning privacy protection experiment comparison 2024..2026", "source": "semantic_scholar", "rationale": "Semantic Scholar supports year range and citation-based relevance"}},
    {{"query": "federated learning privacy preservation comparative study", "source": "openalex", "rationale": "OpenAlex has broad coverage of recent publications"}}
  ],
  "strategy": "Focus on recent papers (2024+) with experimental validation. Filter for comparative experiments post-retrieval."
}}
```

### Example 3 - Methodology survey
Query: "survey of GPT-based code generation evaluation benchmarks"
```json
{{
  "intent": "methodology_survey",
  "keywords": ["GPT", "code generation", "evaluation benchmark", "survey"],
  "expanded_keywords": {{
    "GPT": ["GPT-4", "ChatGPT", "large language model", "LLM"],
    "code generation": ["program synthesis", "code completion", "automatic programming"],
    "evaluation benchmark": ["benchmark", "evaluation metric", "HumanEval", "MBPP"]
  }},
  "constraints": [
    {{"key": "paper_type", "operator": "in", "value": ["survey", "review"], "description": "Prefer survey/review papers", "certainty": "inferred"}}
  ],
  "sub_queries": [
    {{"query": "GPT code generation evaluation benchmark survey", "source": "semantic_scholar", "rationale": "Find survey papers with high citation counts"}},
    {{"query": "large language model program synthesis benchmark", "source": "arxiv", "rationale": "ArXiv has latest preprints on LLM evaluation"}}
  ],
  "strategy": "Target survey papers and comprehensive benchmarks. Prioritize highly-cited foundational works."
}}
```

### Example 4 - Exact lookup with author
Query: "Hinton 2015 knowledge distillation paper"
```json
{{
  "intent": "exact_lookup",
  "keywords": ["knowledge distillation", "Hinton"],
  "expanded_keywords": {{
    "knowledge distillation": ["KD", "model compression", "teacher-student"],
    "Hinton": ["Geoffrey Hinton", "G. E. Hinton"]
  }},
  "constraints": [
    {{"key": "year", "operator": "eq", "value": 2015, "description": "Published in 2015", "certainty": "confirmed"}},
    {{"key": "author", "operator": "contains", "value": "Hinton", "description": "Authored by Hinton", "certainty": "confirmed"}}
  ],
  "sub_queries": [
    {{"query": "Hinton knowledge distillation 2015", "source": "semantic_scholar", "rationale": "Author-optimized search"}},
    {{"query": "knowledge distillation Hinton 2015", "source": "crossref", "rationale": "DOI-based exact match"}}
  ],
  "strategy": "Precise lookup with author and year constraints to find a specific paper."
}}
```

### Example 5 - Similar recommendation
Query: "papers similar to 'Attention Is All You Need' but for graph neural networks"
```json
{{
  "intent": "similar_recommendation",
  "keywords": ["attention mechanism", "graph neural network", "GNN"],
  "expanded_keywords": {{
    "attention mechanism": ["self-attention", "transformer", "multi-head attention"],
    "graph neural network": ["GNN", "graph attention", "graph transformer", "message passing"]
  }},
  "constraints": [],
  "sub_queries": [
    {{"query": "attention mechanism graph neural network transformer", "source": "semantic_scholar", "rationale": "Find papers combining attention with GNNs"}},
    {{"query": "graph attention network transformer", "source": "openalex", "rationale": "Broad search for graph transformer architectures"}}
  ],
  "strategy": "Find papers that apply transformer-style attention to graph domains, bridging the two fields."
}}
```

## Output
Return ONLY valid JSON. No markdown fences, no explanation text."""

    # =================================================================
    # 单篇论文分析
    # =================================================================

    PAPER_ANALYSIS_PROMPT = """You are an expert academic paper analyst. Analyze the following paper based on the user's query context.

## Paper Information
{paper_info}

## Analysis Context
User query: "{query}"
Analysis type: "{analysis_type}"

## Output Format
Return a JSON object:

```json
{{
  "summary": "<concise 2-3 sentence summary of the paper's contribution>",
  "methodology": "<description of the methodology used, if applicable>",
  "key_findings": ["<finding 1>", "<finding 2>", ...],
  "strengths": ["<strength 1>", "<strength 2>", ...],
  "weaknesses": ["<weakness 1>", "<weakness 2>", ...],
  "relevance_to_query": "<how this paper relates to the user's query>"
}}
```

## Rules
1. Base all analysis on the provided paper information only
2. If information is insufficient for a field, use null or empty list
3. Be specific and cite aspects from the paper
4. Do not fabricate information not present in the provided text
5. For "summary" type analysis, focus on summary and key_findings
6. For "methodology" type, focus on methodology details
7. For "findings" type, focus on key_findings
8. For "pros_cons" type, focus on strengths and weaknesses
9. For "full" type, provide comprehensive analysis

## Output
Return ONLY valid JSON. No markdown fences, no explanation text."""

    # =================================================================
    # 多篇论文对比
    # =================================================================

    COMPARISON_PROMPT = """You are an expert academic researcher. Compare the following papers in the context of the user's query.

## Papers to Compare
{papers_info}

## Comparison Context
User query: "{query}"

## Output Format
Return a JSON object:

```json
{{
  "comparison_dimensions": ["<dimension 1>", "<dimension 2>", ...],
  "papers": [
    {{
      "paper_index": 1,
      "title": "<paper title>",
      "summary": "<brief summary>",
      "key_contribution": "<main contribution>",
      "methodology": "<methodology used>",
      "results": "<key results>"
    }}
  ],
  "comparison_table": {{
    "<dimension>": {{
      "paper_1": "<description>",
      "paper_2": "<description>"
    }}
  }},
  "synthesis": "<overall synthesis comparing all papers>",
  "research_gap": "<identified gaps or future directions>",
  "recommendation": "<which paper(s) to read for different purposes>"
}}
```

## Rules
1. Compare papers on relevant dimensions (methodology, dataset, results, novelty)
2. Be objective and evidence-based
3. Identify complementary strengths across papers
4. Highlight research gaps and future directions
5. Do not fabricate information not present in the provided paper data
6. If comparing N papers, ensure all N appear in the comparison

## Output
Return ONLY valid JSON. No markdown fences, no explanation text."""

    # =================================================================
    # 约束证据提取
    # =================================================================

    EVIDENCE_EXTRACTION_PROMPT = """You are an expert academic evidence extractor. Given a paper's information and a list of constraints, verify each constraint against the paper.

## Paper Information
Title: {title}
Authors: {authors}
Year: {year}
Venue: {venue}
Abstract: {abstract}
{fulltext_section}

## Constraints to Verify
{constraints_list}

## Output Format
Return a JSON array of verification results:

```json
[
  {{
    "constraint_key": "<the constraint key>",
    "claim": "<what the constraint asks>",
    "verdict": "<satisfied | violated | unknown>",
    "source_level": "<metadata | abstract | fulltext>",
    "evidence_text": "<exact quote from the paper supporting the verdict, or empty string if unknown>",
    "section": "<section where evidence was found, or null>",
    "confidence": <0.0 to 1.0>
  }}
]
```

## Rules
1. Only use information present in the provided paper text
2. If you cannot determine whether a constraint is met, verdict MUST be "unknown"
3. Evidence text must be an exact quote from the paper, not paraphrased
4. Confidence reflects how certain you are about the verdict:
   - 0.9-1.0: Direct evidence in metadata or explicit statement
   - 0.7-0.9: Strong evidence from abstract
   - 0.5-0.7: Indirect or partial evidence
   - Below 0.5: Speculative, consider using "unknown"
5. For time/year constraints, use "metadata" as source_level
6. For methodology/experiment constraints, look in abstract first, then fulltext
7. NEVER fabricate evidence. If unsure, set verdict to "unknown"

## Output
Return ONLY valid JSON array. No markdown fences, no explanation text."""

    # =================================================================
    # 关键词扩展
    # =================================================================

    KEYWORD_EXPANSION_PROMPT = """You are an expert in academic terminology. Given a list of keywords from a research query, expand each keyword with synonyms, abbreviations, and related terms commonly used in academic literature.

## Input Keywords
{keywords}

## Output Format
Return a JSON object:

```json
{{
  "<keyword>": {{
    "synonyms": ["<synonym 1>", "<synonym 2>"],
    "abbreviations": ["<abbr 1>"],
    "related_terms": ["<related 1>", "<related 2>"],
    "broader_terms": ["<broader 1>"],
    "narrower_terms": ["<narrower 1>"]
  }}
}}
```

## Rules
1. Include terms commonly found in academic papers (not colloquial)
2. Abbreviations should be widely recognized in the field
3. Related terms should be semantically related but distinct concepts
4. Broader terms are more general concepts that encompass the keyword
5. Narrower terms are specific instances or subtypes
6. All terms should be useful for academic paper search
7. Do not invent terms that are not established in the literature

## Output
Return ONLY valid JSON. No markdown fences, no explanation text."""

    # ------------------------------------------------------------------
    # 工厂方法
    # ------------------------------------------------------------------

    @classmethod
    def query_parse(cls, query: str, sources: str) -> str:
        """构建查询解析 prompt"""
        return cls.QUERY_PARSE_PROMPT.format(query=query, sources=sources)

    @classmethod
    def paper_analysis(
        cls,
        paper_info: str,
        query: str,
        analysis_type: str = "full",
    ) -> str:
        """构建论文分析 prompt"""
        return cls.PAPER_ANALYSIS_PROMPT.format(
            paper_info=paper_info,
            query=query,
            analysis_type=analysis_type,
        )

    @classmethod
    def paper_comparison(cls, papers_info: str, query: str) -> str:
        """构建论文对比 prompt"""
        return cls.COMPARISON_PROMPT.format(
            papers_info=papers_info,
            query=query,
        )

    @classmethod
    def evidence_extraction(
        cls,
        title: str,
        authors: str,
        year: int,
        venue: str,
        abstract: str,
        constraints_list: str,
        fulltext: Optional[str] = None,
    ) -> str:
        """构建约束证据提取 prompt"""
        fulltext_section = ""
        if fulltext:
            fulltext_section = f"\n## Full Text (excerpt)\n{fulltext[:8000]}"

        return cls.EVIDENCE_EXTRACTION_PROMPT.format(
            title=title,
            authors=authors,
            year=year,
            venue=venue,
            abstract=abstract or "N/A",
            fulltext_section=fulltext_section,
            constraints_list=constraints_list,
        )

    @classmethod
    def keyword_expansion(cls, keywords: list) -> str:
        """构建关键词扩展 prompt"""
        keywords_str = ", ".join(keywords)
        return cls.KEYWORD_EXPANSION_PROMPT.format(keywords=keywords_str)
