# Search and Evidence Protocol

Use this reference when a task requires recent literature, top venue coverage, novelty judgment, current baselines, SOTA scores, or cross-field inspiration for stronger novelty construction.

## Search Window

- For "近三年" or "last three years", compute the exact date window from the current date and state it.
- Search the recent window first for direct same-field priors, baselines, benchmarks, and SOTA claims. Add older canonical papers only when they created the task, dataset, metric, or core method family.
- Prefer publication year over arXiv submission year when a venue version exists.

## Source Hierarchy

Use two evidence streams and keep them separate.

### Direct Same-Field Evidence

Use this stream to decide novelty, baselines, datasets, metrics, and whether the research thesis is already covered.

1. Official top conference and journal pages for the field.
2. OpenReview pages for ICLR, NeurIPS, ICML, and other venues that use it.
3. ACL Anthology, CVF Open Access, ACM DL, IEEE Xplore, Springer, PMLR, USENIX, ACM CCS, NDSS, SIGCOMM, SIGMOD, VLDB, KDD, WWW, and other field-relevant top venues.
4. SCI Q1/TOP journals or authoritative journal pages when the target is a journal paper.
5. arXiv for preprints, accepted versions not yet indexed, or fields where arXiv is the primary discovery layer.
6. Project pages, GitHub, papers-with-code pages, benchmark leaderboards, and blogs as supporting evidence only.

### Cross-Field Inspiration Evidence

Use this stream to construct stronger novelty by analogy or transfer, not to replace direct same-task evidence.

1. Nature, Science, Cell, PNAS, and high-impact Nature/Science/Cell subjournals when they contain transferable mechanisms, measurement protocols, scientific framing, or system insights.
2. Authoritative technical reports from major labs, standards bodies, public-sector scientific agencies, or industrial research groups.
3. Field-defining surveys, consensus statements, benchmarks, or competition reports from adjacent disciplines.
4. High-quality forums or reports only when they are traceable, technically specific, and relevant to the proposed mechanism or evaluation.

Label cross-field evidence as `Inspiration` or `Analogy`. Do not cite it as proof that a same-field task gap exists unless direct same-field evidence also supports that claim.

## Query Strategy

Start broad, then triangulate:

- `"<task>" "<method family>" 2024 2025 2026`
- `"<task>" "SOTA" "<dataset>" "<metric>"`
- `"<task>" "state of the art" "<dataset>" 2024 2025 2026`
- `site:openreview.net <task> <core terms>`
- `site:proceedings.neurips.cc <task> <core terms>`
- `site:proceedings.mlr.press <task> <core terms>`
- `site:aclanthology.org <task> <core terms>`
- `site:openaccess.thecvf.com <task> <core terms>`
- `site:dl.acm.org <task> <core terms>`
- `site:ieeexplore.ieee.org <task> <core terms>`
- `site:nature.com <adjacent mechanism> <domain analogy>`
- `site:science.org <adjacent mechanism> <domain analogy>`
- `site:cell.com <adjacent mechanism> <domain analogy>`
- `"<dataset>" "<metric>" "<task>"`
- `"<benchmark>" leaderboard "<task>"`
- `"<claimed novelty phrase>" arxiv`

Search by synonyms for the user idea. For machine learning topics, map across task, architecture, training signal, inference procedure, benchmark, application domain, measurement protocol, failure mode, and deployment constraint. For cross-field inspiration, search by mechanism rather than surface application, such as active sensing, uncertainty-aware decision making, causal intervention, adaptive sampling, robustness certification, multi-agent coordination, or human-in-the-loop triage.

## Evidence Ledger Schema

Use a compact table. Include:

| Field | Meaning |
| --- | --- |
| Paper | Title with link |
| Year/Venue | Accepted venue if known, otherwise arXiv/status |
| Problem | Task and setting |
| Method | Mechanism, not marketing name |
| Evidence | Datasets, metrics, main result type |
| Limitation | Claimed limitation or inferred gap |
| Relation | Direct prior, adjacent, baseline, threat, benchmark, enabling technique |

## Baseline/SOTA Ledger Schema

For full plans, add a second compact table for the current benchmark landscape:

| Field | Meaning |
| --- | --- |
| Method/Baseline | Name with link |
| Year/Venue | Accepted venue or source status |
| Task/Dataset | Dataset, split, benchmark version, or realistic proxy |
| Metric | Important metric and direction |
| Reported score | Current reported number, confidence interval, or leaderboard value |
| Backbone/setting | Model size, retriever, data regime, prompt, hardware, or other comparability settings |
| Notes | SOTA status, reproducibility caveat, license/access issue, or why it is a required baseline |

If exact SOTA scores are unavailable, mark the row `Unverified` and state the search still needed. Do not compare proposed gains against stale or incompatible settings without saying so.

## Coverage Targets

For a full plan, aim for:

- 6-12 recent direct/adjacent papers from the exact three-year window, prioritizing top conferences, top journals, and direct benchmark papers.
- 2-4 canonical older papers or benchmarks if needed.
- At least one strong baseline paper from each relevant method family.
- At least one paper that could threaten the user's novelty claim.
- 1-3 cross-field inspiration sources from Nature/Science/Cell family journals, authoritative technical reports, standards, or adjacent top journals when they can strengthen the research mechanism, evaluation protocol, or framing.
- A baseline/SOTA ledger covering the main datasets, metrics, and current strong methods that a reviewer would expect.

## Claim Discipline

Use these labels:

- `Verified`: supported by the cited source.
- `Inferred`: reasonable synthesis across sources; state why.
- `Inspiration`: cross-field source suggests a transferable mechanism, metric, or framing but does not prove the same-field gap.
- `Unverified`: plausible but not yet checked.
- `Contradicted`: source evidence conflicts with the claim.

Do not cite a paper for a claim that only appears in your synthesis unless the distinction is explicit.
