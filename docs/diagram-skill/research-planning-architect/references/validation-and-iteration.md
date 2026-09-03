# Validation and Iteration Reference

Use this reference when auditing a draft plan, responding to user feedback, or deciding whether a revision preserved prior strengths.

## Audit Checklist

- Thesis: precise setting, central hypothesis, assumptions, and falsification condition.
- Evidence: recent date window, source links, direct priors from top venues/journals, adjacent priors, cross-field inspiration sources, baselines, current SOTA scores, and at least one novelty threat.
- Novelty: verdict with problem, method, data/evaluation, theory/analysis, empirical finding, system, and cross-domain transfer dimensions considered.
- Method: inputs, outputs, objective, modules, alternatives, minimal version, extension version, and failure modes.
- Experiments: minimum feasibility-validation matrix, fast framework-improvement matrix, full comparison matrix, ablations, robustness/generalization, efficiency, qualitative failure cases, and statistical protocol.
- Resources: feasibility budget, fast-improvement budget, full-comparison budget, model/data access, logging, seeds, and reproducibility controls.
- Reviewer risk: novelty, weak baselines, scale/tuning, cherry-picked data, unrealistic setting, over-engineering, missing insight, metric mismatch, and ethics.

## Feedback Triage

Map feedback to one of these failure types before editing:

| Feedback | Likely problem | First repair |
| --- | --- | --- |
| "不够新" / "not novel" | Evidence or contribution boundary is weak | Recheck closest priors, narrow the claim, change archetype, or add a testable cross-field mechanism |
| "实验不够" | Claims lack validating or falsifying tests | Add Tier 1 feasibility, Tier 2 improvement, and Tier 3 comparison rows with one ablation and one stress test per claim |
| "太泛" | Setting or thesis is underspecified | Define task, assumptions, target users/scenario, and exclusion scope |
| "baseline 弱" / "缺少 SOTA" | Comparisons do not isolate the mechanism or benchmark against current field strength | Add baseline/SOTA ledger with metrics/scores/settings, plus strong recent, same-backbone, simple sanity, and ablated baselines |
| "格式不对" | Output shape mismatches user need | Keep content, transform structure, and note the preferred format |
| "算力不现实" | Full plan exceeds resources | Split into feasibility, improvement, and full-comparison tiers with decision gates |
| "实验不贴合实际" | Experiment rows ignore data, code, time, or compute constraints | Add practical data/model scope, budget, and stop/continue gates to each tier |

## Minimal-Change Revision Loop

1. Identify the smallest section causing the failure.
2. Preserve verified evidence, user constraints, and useful experiment design.
3. Revise the failing claim, method component, table, or output shape.
4. Run the audit checklist again.
5. Record any reusable new rule in the most specific reference file.

## Regression Cases

Before finalizing, check that the revision did not:

- Remove source links or blur verified versus inferred claims.
- Drop the closest-prior threat.
- Drop the baseline/SOTA table, reported scores, or setting caveats.
- Treat cross-field inspiration as direct novelty proof.
- Add a method module with no ablation.
- Add a contribution claim with no validating experiment.
- Collapse feasibility, improvement, and full-comparison experiments into one vague list.
- Increase compute without updating the feasibility, improvement, and full-comparison tiers.
- Convert a real limitation into defensive wording instead of a mitigation.

## Expected Artifacts

For a full plan, expect a concise Markdown deliverable with the output sections named in `SKILL.md`, including a baseline/SOTA ledger. For an audit, expect findings ordered by severity, concrete repairs, and a short upgrade plan. For a scaffold, expect `TODO(user): ...` markers only where evidence or user constraints are genuinely missing.
