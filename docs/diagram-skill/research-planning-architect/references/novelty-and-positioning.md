# Novelty and Positioning Rubric

Use this reference after the evidence ledger and baseline/SOTA ledger exist.

## Novelty Dimensions

Score each dimension from 0 to 3:

- `0`: already common or directly covered.
- `1`: minor recombination or engineering change.
- `2`: clear new angle with plausible empirical value.
- `3`: strong conceptual, technical, or empirical departure likely to interest top venues.

Dimensions:

1. Problem formulation: new setting, assumptions, constraints, or objective.
2. Method mechanism: new algorithmic component, optimization, inference, architecture, or training signal.
3. Data or benchmark: new dataset, split, annotation, protocol, metric, or stress setting.
4. Theory or analysis: guarantee, explanation, scaling law, causal account, or failure taxonomy.
5. Empirical finding: surprising, general, reproducible result that changes practice.
6. System contribution: deployable capability, efficiency breakthrough, toolchain, or reproducible infrastructure.
7. Cross-domain transfer: credible transfer from one domain to another with nontrivial adaptation.

## Verdict Bands

- `Strong`: at least two dimensions score 2+ and one is central to the thesis; direct priors do not already claim it.
- `Medium-strong`: one central dimension scores 3 or at least two dimensions score 2+, with direct-prior threats handled by a sharper setting, mechanism, benchmark, or analysis.
- `Medium`: one central dimension scores 2+ but proof requires decisive experiments or tighter scope.
- `Weak`: mostly recombination, weak evidence gap, or novelty depends on missing/fragile comparison.
- `Not novel enough`: a recent direct prior already makes the same claim under comparable assumptions.

For SCI Q1/TOP journals or CCF-A conferences, treat `Medium-strong` as the normal minimum target. If the plan is only `Medium`, explicitly state which experiment, benchmark, theory/analysis, or cross-domain transfer would raise it. If it is `Weak`, revise the project before presenting it as a top-tier plan.

## Cross-Field Novelty Construction

Use cross-field evidence to generate stronger hypotheses, not as a substitute for same-field novelty proof.

- Extract mechanism analogies: how another field measures, controls, samples, verifies, or adapts under similar constraints.
- Translate the analogy into a precise method component, data protocol, objective, or evaluation stress test.
- Check direct same-field priors again after translation; the novelty may disappear under different terminology.
- Mark the resulting claim as `Inferred` until direct experiments validate the transfer.
- Prefer analogies that add a falsifiable mechanism or measurement protocol over vague "inspired by" framing.

## Venue Contribution Archetypes

Choose one primary archetype and optionally one secondary:

- New problem or setting: sell importance, formal definition, first benchmark, and strong initial methods.
- New method: sell mechanism, why existing methods fail, and broad empirical validation.
- New benchmark/dataset: sell need, construction quality, leakage controls, annotation reliability, and baseline suite.
- New theory/analysis: sell insight, assumptions, proof relevance, and empirical alignment.
- New system/tool: sell capability, reliability, usability, efficiency, and reproducibility.
- Strong empirical finding: sell surprising result, careful controls, and implications for the field.

## Contribution Statement Formula

Use:

`We study [precise setting] where [important constraint/gap]. We propose [mechanism] that [technical action]. Unlike [closest prior/SOTA baseline], it [novel distinction]. On [datasets/protocols], it tests [hypothesis] through [decisive experiments] against [required baselines/SOTA].`

## Scope Control

If novelty is weak, upgrade by:

- Narrowing to a sharper underexplored setting.
- Adding a new benchmark or stress protocol.
- Turning an engineering trick into a falsifiable mechanism.
- Adding theory, analysis, or principled diagnostics.
- Importing a mechanism, measurement protocol, or evaluation design from a high-quality adjacent field source and translating it into a testable same-field contribution.
- Reframing around a strong empirical finding instead of a broad method claim.

Avoid claiming "first" unless the evidence ledger supports it strongly.
