---
run_id: 20260503-185952-sonnet-4
judge: claude-sonnet-4-5-20250929
ts: gpt-5.4-2026-03-05
embedding_model: text-embedding-3-small
git_sha: c51df883e4f61f2708663952cca9b4e08dc66731
n_platforms: 0/1
---

# TermsScope LLM-as-Judge Validation Report

_Generated 2026-05-03T19:00:55Z_

## Headline numbers

| Metric | Value | 95% CI |
|---|---|---|
| Overall-score Pearson r | — | — |
| Overall-score Spearman ρ | — | — |
| Overall-score MAE | — | — |
| Overall-score bias (TS−Judge) | — | — |
| Clause F1 (micro, flagged-only) | 0.00 | — |
| Clause precision (micro) | 0.00 | — |
| Clause recall (micro) | 0.00 | — |
| Risk-level Cohen's κ | — | — |

## Per-category macro F1

| Category | macro F1 |
|---|---|

## Per-platform breakdown

| Platform | TS score | Judge score | Δ | Precision | Recall | F1 | κ | Halluc% |
|---|---|---|---|---|---|---|---|---|
| discord | error | — | — | — | — | — | — | RuntimeError: ANTHROPIC_API_KEY is not set. Configure it in backend/.env before running evals. |

## Plots

## Methodology

- **Pass 1 (blind)**: judge sees only the document and produces an analysis in the same schema as TermsScope.
- **Pass 2 (A/B verdict)**: judge sees both analyses (random A/B assignment) and decides matches, hallucinations, and quality scores.
- **Clause matching** for precision/recall: OpenAI text-embedding-3-small + Hungarian assignment per category, threshold 0.75.
- **Headline F1** is on flagged clauses only (risk_level ≠ neutral).
- **Hallucination** = clauses that, in Pass 2, the judge labels as not actually present in the document or materially misinterpreted.
- All judge calls use temperature 0.0; A/B assignment per platform is deterministic from seed=42.
