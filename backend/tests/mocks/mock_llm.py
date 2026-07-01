"""
模拟 LLM 响应

为 LLM 网关提供预设的 Mock 响应，覆盖查询规划、论文分析等场景。
"""

import json


# 查询规划响应
QUERY_PLAN_RESPONSE = json.dumps({
    "intent": "literature_search",
    "keywords": ["attention", "mechanism", "transformer", "self-attention", "NLP"],
    "sub_queries": [
        {
            "query": "attention mechanism transformer self-attention",
            "source": "semantic_scholar",
            "rationale": "Search for core attention mechanism papers on Semantic Scholar",
        },
        {
            "query": "attention mechanism deep learning",
            "source": "openalex",
            "rationale": "Broader search on OpenAlex for attention-related papers",
        },
    ],
    "strategy": "Search for attention mechanism papers across multiple sources with keyword variations",
})

# 论文分析响应
PAPER_ANALYSIS_RESPONSE = json.dumps({
    "summary": "This paper introduces the Transformer architecture based on self-attention mechanisms.",
    "methodology": "The authors propose a novel architecture that replaces recurrence with attention.",
    "key_findings": [
        "Self-attention can replace recurrence for sequence modeling",
        "Multi-head attention allows attending to different representation subspaces",
        "Positional encodings provide sequence order information",
    ],
    "strengths": [
        "Simple and elegant architecture",
        "Highly parallelizable training",
        "State-of-the-art results on machine translation",
    ],
    "weaknesses": [
        "Quadratic complexity with sequence length",
        "Requires large amounts of training data",
    ],
})

# 论文对比响应
PAPER_COMPARE_RESPONSE = json.dumps({
    "methodology": "Paper A uses self-attention while Paper B uses recurrent networks.",
    "results": "Paper A achieves better performance on translation tasks.",
    "strengths_weaknesses": "Paper A is more parallelizable but requires more memory.",
    "recommendation": "For new projects, prefer the Transformer architecture.",
})

# 连通性测试响应
CONNECTION_TEST_RESPONSE = "Hello!"

# 错误响应
LLM_ERROR_RESPONSE = "Error: Model unavailable"

# 空响应
EMPTY_RESPONSE = ""

# 超长响应
LONG_RESPONSE = "A" * 10000


def get_mock_llm_response(scenario: str) -> str:
    """
    根据场景获取 Mock LLM 响应

    Args:
        scenario: 场景名称

    Returns:
        预设的 LLM 响应文本
    """
    responses = {
        "query_plan": QUERY_PLAN_RESPONSE,
        "paper_analysis": PAPER_ANALYSIS_RESPONSE,
        "paper_compare": PAPER_COMPARE_RESPONSE,
        "connection_test": CONNECTION_TEST_RESPONSE,
        "error": LLM_ERROR_RESPONSE,
        "empty": EMPTY_RESPONSE,
        "long": LONG_RESPONSE,
    }
    return responses.get(scenario, CONNECTION_TEST_RESPONSE)
