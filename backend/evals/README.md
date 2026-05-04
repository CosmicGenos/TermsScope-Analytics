# TermsScope Evaluation Harness

LLM-as-judge validation framework for TermsScope Analytics.

## What it does

1. Fetches Terms of Service documents for a fixed corpus of 8 platforms (Discord, Spotify, OpenAI, Reddit, Netflix, GitHub, Notion, Substack).
2. Runs the production TermsScope pipeline on each document.
3. Runs **Pass 1**: a stronger independent judge LLM (Claude Sonnet 4.5 by default) reads each document blind and produces its own analysis in the same schema.
4. Runs **Pass 2**: the judge sees both analyses (A/B randomised) and the document, and labels matches, hallucinations, and quality scores.
5. Matches TermsScope and judge clauses via OpenAI embeddings + Hungarian assignment per category.
6. Computes the metrics below and writes a Markdown report with PNG plots.

## Metrics

| Category | Metric | Library |
|---|---|---|
| Score | Pearson r, Spearman ρ, MAE, RMSE, bias | `scipy.stats` |
| Score | per-category Pearson r | `scipy.stats` |
| Clause | precision, recall, F1 (micro + per-category) | `sklearn.metrics` |
| Clause | Cohen's κ on risk-level agreement | `sklearn.metrics` |
| Clause | 4×4 confusion matrix | `sklearn.metrics` |
| Pass 2 | hallucination rate (TS-side, judge-side) | this package |
| All | 95% bootstrap CIs on headline metrics | `scipy.stats.bootstrap` |

## Plots

- `score_scatter.png` — TS overall_score vs judge overall_score
- `category_heatmap.png` — per-category score difference
- `confusion_matrix.png` — risk-level agreement (raw + row-normalised)
- `prf1_bars.png` — precision/recall/F1 per category
- `coverage_stacked.png` — matched/missed/extra clauses per platform
- `radar.png` — per-platform 5-axis radar of category risk_scores

Each plot's source data is also saved as CSV next to the PNG.

## Prerequisites

```bash
cd backend
uv pip install -e ".[dev,evals]"
```

Required env (`backend/.env`):
- `OPENAI_API_KEY` — for the TermsScope pipeline (default GPT-4o-mini) and for embeddings
- `ANTHROPIC_API_KEY` — for the judge

## Usage

### One-time: fetch the corpus

```bash
cd backend
uv run python -m evals.cli fetch-corpus
```

This downloads each ToS, cleans it via the existing scraper, and writes plain-text fixtures to `evals/fixtures/raw/<slug>.txt`. **Commit the fixtures** so reruns are reproducible against the same snapshot.

### Run the eval suite

```bash
# All 8 platforms; will print cost (~$2.40) and prompt for confirmation
uv run python -m evals.cli run

# Bypass the confirmation prompt
uv run python -m evals.cli run --yes

# Subset for dev iteration
uv run python -m evals.cli run --platforms discord,spotify --skip-pass2 --yes

# Different judge
uv run python -m evals.cli run --judge-model claude-opus-4-5-20250929 --yes
```

Output lands in `reports/runs/<RUN_ID>/` with:
- `metrics.json` — full structured metrics
- `metrics.csv` — per-platform CSV (for spreadsheets)
- `manifest.json` — judge model, ts model, embedding model, git sha, seed
- `REPORT.md` — readable report with embedded plots
- `termsscope/<slug>.json`, `judge_pass1/<slug>.json`, `judge_pass2/<slug>.json` — raw outputs
- `matches/<slug>.json` — embedding-based pair assignments
- `plots/*.png` + `plots/*.csv` — figures and their source data

### Re-render plots without spending money

```bash
uv run python -m evals.cli replot --run-id 20260501-1430-sonnet45
```

Re-reads `metrics.json` and regenerates the plots and `REPORT.md`. Useful for iterating on plot styling.

## Caching

- ToS fixtures: `evals/fixtures/raw/*.txt` (committed)
- Embedding vectors: `evals/cache/embeddings.sqlite` (gitignored)
- Pass 1 / Pass 2 outputs: `evals/cache/passes/*.json` (gitignored), keyed by `(judge_model, doc_sha256)` so re-runs against the same document don't re-spend on the judge.

To force a fresh judge run, delete the relevant file under `evals/cache/passes/`.

## Cost (approximate)

Per platform, with `claude-sonnet-4-5-20250929`:
- Pass 1: ~$0.21 (30K input + 8K output)
- Pass 2: ~$0.08 (12K input + 3K output)
- Embeddings: <$0.001
- TermsScope pipeline (gpt-4o-mini): not counted here

**~$2.40 for the full 8-platform run.**

## Unit tests

The `tests/eval/` package contains tests with no API calls (mocked LLM clients, synthetic embeddings):

```bash
cd backend
uv run pytest tests/eval/ -v
```

Tests cover:
- Hungarian matcher: self-match identity, threshold monotonicity, cross-category enforcement, global-optimum vs greedy
- Metrics: hand-computed Pearson/Spearman/MAE, Cohen's κ at perfect/chance/anti-correlation
- Schema round-trip: Pass2Verdict, flat-index map ordering, slim-for-judge field stripping

## Methodology notes

**Why two passes?** Pass 1 is the rigorous independent reference (judge produces its own analysis). Pass 2 is the cross-check where the judge can declare TermsScope-only clauses as either valid findings TermsScope correctly caught or hallucinations. Pass 2 is what gives the hallucination rate a sound footing — it's not just "TS found something the judge didn't" but "the judge looked at the document and confirmed TS's finding is wrong."

**Why embeddings + Hungarian instead of LLM-as-matcher?** Embedding similarity is deterministic, cheap (~$0.0001 per platform), and well-calibrated for semantic equivalence on legal text. Hungarian assignment guarantees globally-optimal one-to-one matching, which matches the precision/recall semantics. Pass 2 still does its own LLM matching as a cross-check on the embedding-based pairs.

**Why per-category matching?** TermsScope's category routing is part of what we're evaluating. If TS puts a clause in `privacy` and the judge puts the same clause in `data_rights`, that's a categorisation error worth flagging — it counts as a TS miss in `data_rights` and a TS extra in `privacy`. A category-agnostic F1 is also reported for context.

**Why a stronger judge?** The judge needs to be at least as capable as the system under evaluation — otherwise the judge becomes the limiting factor. Using a different model family (Anthropic Claude vs TermsScope's OpenAI default) also reduces shared-failure-mode bias.

**Hard error if judge same family as TS.** Set `--judge-provider` deliberately; the harness does not currently fall back gracefully when both come from the same provider.

## Bias controls

- Judge runs at temperature 0.0 (reproducible)
- Pass 1 is blind (judge sees only the document)
- Pass 2 randomises A/B per platform via `random.Random(seed + hash(slug))`
- A/B mapping is recorded in `manifest.json` and used post-hoc to attribute hallucinations and quality scores
- The same fixed `seed=42` is used by default; override with `--seed`

## Limitations

- Single-judge bias: the framework reports judge-vs-TS agreement, not absolute correctness. A consensus across multiple judge models would be the next step.
- Embedding threshold of 0.75 was chosen via spot-check on legal text. The matcher accepts a `--threshold` override; consider sweeping `[0.65, 0.70, 0.75, 0.80]` if your corpus differs.
- Only English documents are tested. Non-English ToS is out of scope.
- The judge's `risk_score` per category is its own subjective calibration; the score-correlation metrics measure agreement, not ground truth.
