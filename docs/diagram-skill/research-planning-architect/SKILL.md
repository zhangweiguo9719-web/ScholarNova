---
name: research-planning-architect
description: Research-plan design for ML/AI or scientific project ideas that need evidence-backed novelty diagnosis, cross-field inspiration, top-venue/journal positioning, baseline/SOTA tables, method design, tiered experiment matrices, compute planning, and reviewer red-team. Use when Codex must turn a raw or partial idea into an experiment-ready plan, compare it against recent top conferences/journals, audit novelty and rigor, or upgrade after feedback. Do not use for generic literature summaries, single-paper explanations, routine writing polish, grant/admin planning, or implementation-only coding tasks unless they directly feed a research plan. Inputs may include an idea, draft plan, target venue, constraints, datasets/models, or reviewer feedback.
---

# Research Planning Architect

## Purpose

Turn a raw or partial research idea into a defensible, experiment-ready research plan. Keep the work anchored in evidence, novelty risk, method mechanism, feasible experiments, and reviewer objections rather than producing a generic literature review.

Default to the user's language. If the user writes in Chinese, answer in Chinese unless they request otherwise. Treat target venue, compute budget, datasets, codebase, deadline, privacy, licensing, and collaboration constraints as hard constraints unless evidence shows they conflict.

## When To Use This Skill

Use this skill for:

- Raw ideas that need a publishable research thesis.
- Draft plans that need novelty, experiment, or reviewer-risk audit.
- Requests involving recent top-venue/top-journal papers, cross-field novelty inspiration, SOTA/baseline tables, target venues, datasets, ablations, tiered experiment matrices, or compute planning.
- Feedback-driven upgrades after the user says the plan is weak, not novel, too broad, under-tested, or reviewer-vulnerable.

Do not use it for:

- Pure single-paper explanation or bibliography generation.
- General academic writing polish without research-design decisions.
- Coding-only implementation tasks unless they are part of an experiment plan.
- Administrative grant, hiring, or project-management planning with no scientific contribution design.

## Inputs Expected

Extract or infer:

- One-sentence idea, field, task family, and target venue or journal family.
- Claimed gap, intended contribution, and closest known priors.
- Available datasets, models, code, GPUs/API budget, timeline, and collaborators.
- Desired bar, such as SCI Q1/TOP journal, CCF-A conference, or a medium-strong novelty threshold.
- Hard exclusions: licenses, privacy, ethics, methods, data, deployment setting, or compute.
- Existing draft sections, reviewer feedback, or failed experiments when provided.

Ask at most three high-value questions only when missing information would change the plan materially. Otherwise proceed with explicit assumptions.

## Workflow

1. **Frame the research question.** State the precise setting, central hypothesis, constraints, and what would falsify the idea.
2. **Build an evidence map.** Read `references/search-and-evidence.md` before current-paper search. Use web search for recent top conferences/journals, current baselines, SOTA scores, new datasets, target-venue norms, and novelty threats. State the exact date window; for "近三年", compute it from the current date. Separate direct same-field evidence from broader cross-field inspiration sources such as Nature, Science, high-impact subjournals, authoritative forums, standards, and technical reports.
3. **Report the baseline/SOTA landscape.** For the target task and datasets, produce a compact table of current baseline and SOTA methods, important metrics, reported scores, backbones/settings, and source links. Use it to set realistic target gains and decide which comparisons are mandatory.
4. **Diagnose novelty.** Read `references/novelty-and-positioning.md`. Separate verified facts, inference, and unverified hypotheses. Judge novelty across problem, method, data, evaluation, theory, empirical finding, system, and cross-domain transfer dimensions. Aim for at least medium-strong novelty for SCI Q1/TOP or CCF-A positioning; if the evidence does not support that bar, narrow the setting, add a benchmark/stress protocol, or redesign the mechanism before moving on.
5. **Design the method.** Specify inputs, outputs, objective, training or inference pipeline, modules, alternatives, smallest publishable version, higher-risk extension, and failure modes.
6. **Plan data, models, compute, and experiments.** Read `references/experiment-design.md` when choosing datasets, baselines, metrics, ablations, resource budgets, or reproducibility controls. Build three practical tiers: a minimum feasibility-validation matrix, a fast framework-improvement matrix, and a full comparison matrix. Every claimed contribution needs at least one validating experiment, one stress test, and a decision gate that reflects the user's actual data, model, compute, and timeline constraints.
7. **Red-team the plan.** Read `references/reviewer-red-team.md`. Predict attacks on novelty, baselines/SOTA coverage, realism, scale/tuning, cherry-picking, over-engineering, insight, reproducibility, metrics, and ethics; convert each into an experiment, scope change, or wording change.
8. **Iterate once.** Remove weak claims, strengthen the central thesis, add one decisive experiment or analysis, and report a concise v1-to-upgraded-plan delta. For feedback-driven revisions, use `references/validation-and-iteration.md`.

When web access is unavailable, continue with an offline scaffold but label literature, SOTA, and novelty conclusions as unverified and list the searches still required.

## Quality Criteria

- The contribution statement is narrow, falsifiable, and tied to evidence.
- Recent direct priors from top conferences/journals and at least one novelty threat are represented.
- Cross-field inspiration is used to construct novelty, but not misrepresented as direct same-task evidence.
- A baseline/SOTA table reports current important metrics, scores, settings, and links for the target datasets or closest proxies.
- Baselines include simple sanity checks, strong recent methods, same-backbone controls when relevant, SOTA comparisons or defensible proxies, and ablations of the proposed mechanism.
- Experiments are tiered into minimum feasibility validation, fast framework improvement, and full comparison, with each tier listing purpose, datasets/models, baselines or controls, metrics, budget, and stop/continue criteria.
- Datasets, metrics, and stress tests measure the actual claim rather than a convenient proxy.
- Compute estimates distinguish feasibility-validation, fast-improvement, and full paper-grade runs.
- Reviewer attacks produce concrete mitigation actions, not only prose defenses.
- Ethical, legal, licensing, and reproducibility risks are stated when relevant.

## Validation

Use the bundled tools when useful:

- `scripts/research_plan_scaffold.py`: generate a Markdown planning scaffold from an idea.
- `scripts/audit_research_plan.py`: audit whether a draft plan covers required sections, evidence fields, baseline/SOTA fields, links, recent-year markers, tiered experiment fields, and reviewer-risk coverage.
- `scripts/validate_skill.py`: validate this skill folder's frontmatter, references, examples, and Python scripts.
- `examples/smoke-research-plan.md`: minimal smoke example for the audit script.

For a full deliverable, self-check that each claim has evidence, each module has an ablation, each baseline/SOTA entry has a rationale and metric setting, each experiment tier has a practical decision gate, and each high-risk reviewer objection has an action.

## Failure Handling

- If the idea is too broad, narrow the setting before adding method details.
- If novelty is weak or below the requested SCI Q1/TOP or CCF-A bar, do not inflate claims; reposition as a benchmark, analysis, empirical finding, or narrower setting only if evidence supports it.
- If evidence is missing or web search is blocked, mark affected conclusions as `Unverified` or `待验证`.
- If compute is insufficient, produce a feasibility-only plan, a fast-improvement plan, a paper-grade full plan, and decision gates between tiers.
- If user feedback says the format or result is wrong, preserve useful sections, identify the smallest failing assumption or output section, revise only that part first, and add the new rule to the relevant reference if it should recur.

## Output Expectations

For full planning tasks, deliver:

1. `Research thesis`
2. `Recent-paper evidence ledger`
3. `Baseline/SOTA benchmark ledger`
4. `Novelty verdict`
5. `Top-venue contribution positioning`
6. `Method blueprint`
7. `Dataset/model/compute plan`
8. `Tiered experiment matrix`
9. `Reviewer red-team`
10. `Iteration plan`
11. `Risk register`

For smaller tasks, compress the same reasoning into the requested shape. The output should let a researcher immediately start paper collection, baseline implementation, pilot experiments, and contribution-risk reduction.

## References To Read When Needed

- `references/search-and-evidence.md`: search protocol, evidence ledger schema, baseline/SOTA ledger schema, cross-field inspiration sources, source hierarchy, claim labels.
- `references/novelty-and-positioning.md`: novelty scoring rubric and venue contribution archetypes.
- `references/experiment-design.md`: dataset, baseline, metric, ablation, tiered experiment matrix, compute, and reproducibility design.
- `references/reviewer-red-team.md`: reviewer attack library and mitigation patterns.
- `references/validation-and-iteration.md`: feedback triage, regression checks, and plan-audit checklist.
- `assets/templates/research-plan-template.md`: reusable Markdown deliverable template.
