# Experiment Design Reference

Use this reference when selecting datasets, models, baselines, metrics, ablations, tiered experiment matrices, compute, and reproducibility details.

## Dataset Selection

For each dataset, specify:

- Why it tests the thesis.
- License/access constraints.
- Train/validation/test split and leakage risks.
- Preprocessing and annotation assumptions.
- Expected difficulty and known saturation.
- Whether it supports pilot experiments and full-scale claims.

Prefer a mix:

- Standard benchmark for comparability.
- Stress or out-of-distribution benchmark for mechanism validation.
- Realistic or domain-specific dataset for relevance.

## Baseline Ladder

Include:

1. Simple sanity baseline: random, majority, heuristic, BM25, linear model, or small backbone when appropriate.
2. Classical or widely used baseline.
3. Strong recent baseline from the evidence ledger.
4. Current SOTA method or a clearly justified proxy from the baseline/SOTA ledger.
5. Same-backbone baseline to control for capacity.
6. Oracle or upper-bound baseline if feasible.
7. Ablated versions of the proposed method.

Weak baseline design is a top rejection risk. If compute prevents full SOTA comparison, state a defensible proxy and plan a limited reproduction or citation-based comparison. For every main dataset, report the current best known score or explain why the score is unavailable, stale, or incomparable.

## SOTA Reference Targets

Before defining improvement targets:

- Identify the main metric used by recent top papers for each dataset or benchmark.
- Record the current SOTA or strongest credible baseline score, including setting differences.
- Note whether the proposed method must beat SOTA, improve robustness/efficiency at similar quality, or win under a new stress protocol.
- Avoid claiming paper-grade gains when improvements are only over weak, stale, or incomparable baselines.
- If the thesis is not a leaderboard claim, still use the SOTA ledger to set a realistic quality floor and justify why a different metric matters.

## Metrics

Choose metrics aligned with the claim:

- Predictive quality: accuracy, F1, AUROC, mAP, BLEU/ROUGE only when field-appropriate, task-specific metrics.
- Calibration/reliability: ECE, Brier score, selective risk, coverage-risk curves.
- Robustness: corruption accuracy, OOD gap, worst-group performance.
- Efficiency: FLOPs, latency, memory, throughput, training cost, annotation cost.
- Human-facing quality: agreement, preference, error taxonomy, blinded rating where necessary.

Avoid optimizing one metric while claiming a different contribution.

## Ablation Pattern

Every module needs:

- Remove it.
- Replace it with a simple alternative.
- Vary its strength or hyperparameter.
- Test where it should fail.

Use ablations to answer mechanism questions, not just to add rows.

## Tiered Experiment Matrix

Build experiments in three tiers so the plan can survive real limits on data, code maturity, compute, and time.

### Tier 1: Minimum Feasibility Validation

Purpose: decide whether the idea deserves more engineering.

Include:

- Smallest dataset slice or synthetic probe that tests the central mechanism.
- One simple sanity baseline and one same-setting baseline.
- One primary metric tied to the central claim and one failure metric.
- One or two ablations that isolate the proposed mechanism.
- A strict stop/continue gate, such as minimum lift, acceptable cost, or failure-mode reduction.

Keep this tier small enough to run first, usually before full data cleaning, large sweeps, or multi-dataset comparisons.

### Tier 2: Fast Framework Improvement

Purpose: improve the method quickly after the first signal without overfitting to a final benchmark.

Include:

- The most informative validation split, stress slice, or error bucket from Tier 1.
- Cheap variants of modules, prompts, objectives, thresholds, or data construction choices.
- Equal-budget comparisons so gains cannot be explained by scale or tuning.
- Diagnostic metrics, failure taxonomies, and latency/cost checks.
- Decision rules for which components enter the full comparison matrix.

This tier should optimize the framework and reveal failure modes, not chase leaderboard numbers.

### Tier 3: Full Comparison

Purpose: support paper-grade claims against credible alternatives.

Include:

- Standard benchmarks for comparability plus stress or realistic datasets for the thesis.
- Simple, classical, strong recent, current SOTA/proxy, same-backbone, and oracle baselines where feasible.
- Full ablations of modules retained from Tier 2.
- Robustness/generalization, efficiency, qualitative failure analysis, and statistical protocol.
- Reporting artifacts: main table, ablation table, stress table, efficiency table, and failure cases.

This tier should be run only after Tier 1 passes and Tier 2 identifies a compact, defensible method.

### Matrix Columns

For each tier, specify:

| Column | Meaning |
| --- | --- |
| Claim tested | Contribution or risk the experiment validates or falsifies |
| Experiment | Concrete run, comparison, stress test, or analysis |
| Data/model scope | Dataset split, model/backbone, sample size, and preprocessing assumptions |
| Baselines/controls | Sanity, recent, SOTA/proxy, same-backbone, oracle, or ablated controls |
| Metrics | Primary metric plus failure, robustness, cost, or calibration metrics |
| Budget | GPU/API/time/storage estimate and number of seeds |
| Decision gate | Continue, revise, or stop criterion |

## Practical Fit

Before finalizing the matrices, adapt them to the user's constraints:

- If data is scarce, use a pilot subset, synthetic perturbations, or public proxy data, and mark which conclusions remain limited.
- If compute is scarce, reduce sweep width first, then seeds, then dataset count; keep at least one same-backbone control.
- If full SOTA reproduction is too expensive, keep a citation-based SOTA row, reproduce a smaller same-backbone proxy, and state which conclusion remains limited.
- If deadline is short, prioritize Tier 1 and the highest-risk Tier 2 diagnostics before full comparison.
- If implementation is immature, test module interfaces and logging before adding complex baselines.
- If a dataset, model, or API has licensing or privacy constraints, move it into the risk register and choose a feasible substitute.
- If the plan is for a paper, keep a path from every experiment row to a likely table, figure, or reviewer objection.

## Compute Plan

Provide:

- Feasibility budget: minimum run to falsify the idea.
- Fast-improvement budget: bounded sweeps and diagnostics after the first signal.
- Full-comparison budget: runs needed for a credible paper.
- GPU type/count, memory, estimated wall-clock, storage.
- Number of seeds and sweep size.
- Checkpointing and logging plan.

If using foundation models, include API/local cost, context length, quantization, batching, caching, and reproducibility issues.

## Tables and Figures

Predefine expected paper artifacts:

- Main result table.
- Baseline/SOTA landscape table.
- Ablation table.
- Robustness/generalization table.
- Efficiency table.
- Method diagram.
- Failure case figure.
- Qualitative examples or case studies.

Each artifact should support a claim in the contribution statement.

## Reproducibility

Specify:

- Seeds and variance reporting.
- Hyperparameter budget fairness.
- Data version and preprocessing hash where possible.
- Code release feasibility.
- Hardware and software versions.
- Statistical test or confidence interval for close results.
