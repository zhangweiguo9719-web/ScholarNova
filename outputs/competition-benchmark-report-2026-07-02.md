# ScholarNova competition benchmark report — 2026-07-02

## Scope

This report covers 18 deterministic Paper Finder queries selected from the official Asta validation set: 10 specific-paper queries and 8 metadata/citation-graph queries. It is a targeted regression subset, not the full competition score.

The authorized source dataset remains local and is excluded from Git. The committed prediction artifact contains retrieved public paper metadata only.

## Results

| Metric | Baseline | Semantic Scholar v2 | Current v3 |
| --- | ---: | ---: | ---: |
| Precision | 0.004762 | 0.259434 | **0.352313** |
| Recall | 0.006689 | **0.367893** | 0.331104 |
| F1 | 0.005563 | 0.304288 | **0.341379** |
| Recall@20 | 0.006689 | 0.160535 | **0.163880** |
| Recall@50 | 0.006689 | **0.204013** | 0.200669 |
| Recall@100 | 0.006689 | **0.274247** | 0.254181 |
| Average API calls | 3.889 | **3.667** | 7.333 |
| Average latency | 10.685 s | **5.904 s** | 15.139 s |
| Average LLM tokens | 0 | 0 | 0 |

Current v3 improves F1 by 12.19% relative to v2 and by approximately 60.36 times relative to the original baseline. Precision improved because structured citation queries now limit noisy result sets. Recall decreased because the same limit removes some valid long-tail papers.

## What changed

- Expanded canonical aliases for named papers such as MS².
- Resolved BibTeX-style paper references before exact-title retrieval.
- Added result budgets for broad citation-threshold and multi-paper citation queries.
- Preserved Semantic Scholar account-wide rate limiting, retry behavior, cache use, and circuit breaking.
- Added regression tests for alias resolution and structured result limits.

## Token accounting

Zero tokens in this run is intentional and verifiable: these 18 deterministic queries use rule-based planning and citation-graph operations, so no LLM request is made. Product queries that need model-assisted decomposition or analysis record provider-reported prompt, completion, total-token, and request counts.

This design supports the competition efficiency objective: do not spend model tokens when exact rules and scholarly graph APIs can answer the query.

## Interpretation and remaining work

- `specific_9` improved from 0/1 to 1/1 after canonical alias expansion.
- Exact paper lookup is strong on the covered aliases.
- High-cardinality citation queries remain the main precision/recall tradeoff.
- v3 does not exceed the cited SPAR F1=0.38 reference. That published number uses a different evaluation setup, so it is context rather than a directly comparable leaderboard target.
- The next defensible improvement is snapshot-aware citation ranking and broader official-set validation, not hard-coding validation answers or maximizing API calls.

## Reproduction artifact

`outputs/benchmarks/predictions/asta-s2-validation18-v3-2026-07-02.json`

The benchmark script is:

`backend/scripts/run_official_benchmark.py`

## Expanded 66-query execution

The complete validation file contains 66 queries:

- 48 semantic-relevance queries.
- 10 specific-paper queries.
- 8 metadata/citation-graph queries.

All 66 queries were executed. Only 27 provide binary paper identifiers that can
be scored with the repository's deterministic Precision/Recall/F1 evaluator.
The other 39 provide textual relevance criteria and require the official or an
LLM-based relevance judge. They are not silently treated as zero-relevance
cases.

| Binary-gold scope | Cases | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: |
| All binary-labelled cases | 27 | 0.321429 | 0.253918 | 0.283713 |
| Semantic | 9 | 0.073171 | 0.150000 | 0.098361 |
| Specific paper | 10 | 0.473684 | 0.600000 | 0.529412 |
| Metadata / citation graph | 8 | 0.359375 | 0.242958 | 0.289916 |

The 27-case average was 5.185 API calls and 3.446 seconds in the cached
verification run. Deterministic planning used zero LLM tokens.

Semantic queries are now capped at Top-5 for the benchmark output. On the same
retrieval results, this raised the 27-case F1 from 0.127962 to 0.283713 by
removing low-ranked noise without changing recall. This is a selection-budget
improvement, not a claim that all 39 criteria-only queries are solved.

Expanded artifact:

`outputs/benchmarks/predictions/asta-s2-validation66-v6-2026-07-02.json`

## Model-planning cost gate

A controlled MiMo planning experiment was started on the nine semantic queries
with binary gold labels. It was stopped after two cases because the provider
used reasoning tokens but did not return parseable planning JSON:

- Completed cases: 2/9.
- Model requests: 6.
- Total tokens: 16,185.
- Average tokens per case: 8,092.5.
- Average latency: 104.582 seconds.
- F1 on those two cases: 0.

Both cases fell back to deterministic planning, so continuing would have added
cost without improving retrieval. The experiment is retained as evidence for
the cost gate, but its partial artifact is not presented as a benchmark score.
