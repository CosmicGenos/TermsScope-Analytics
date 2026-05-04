"""Per-platform eval runner — wires everything together for one platform."""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import logging
import subprocess
from pathlib import Path

from app.config import get_settings
from app.schemas.output import AnalysisResult
from evals.config import (CACHE_DIR, EMBEDDINGS_DB, JudgeConfig, PASS_CACHE_DIR,
                          REPORTS_DIR, PlatformSpec)
from evals.fetcher import doc_sha256, load_text
from evals.judge.client import JudgeClient
from evals.judge.pass1 import judge_pass1_chunked
from evals.judge.pass2 import assign_ab, judge_pass2
from evals.judge.schemas import Pass2Verdict
from evals.matching.embeddings import EmbeddingCache
from evals.matching.matcher import flatten, match_clauses
from evals.metrics.aggregate import PlatformMetrics, build_suite_metrics
from evals.metrics.clause_metrics import (coverage_breakdown, per_category_prf1,
                                           precision_recall_f1, risk_level_agreement)
from evals.metrics.hallucination import attribute_hallucinations
from evals.metrics.scoring import collect_score_rows
from evals.termsscope_runner import run_termsscope_on_text

logger = logging.getLogger(__name__)


def make_run_id(judge_model: str) -> str:
    short = judge_model.replace("claude-", "").split("-")[0:2]
    short = "-".join(short)
    return dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S") + f"-{short}"


def _git_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return None


def _ensure_run_dirs(run_dir: Path) -> None:
    for sub in ["termsscope", "judge_pass1", "judge_pass2", "matches", "plots"]:
        (run_dir / sub).mkdir(parents=True, exist_ok=True)


async def _get_or_run_termsscope(slug: str, text: str, run_dir: Path) -> AnalysisResult:
    cached = run_dir / "termsscope" / f"{slug}.json"
    if cached.exists():
        return AnalysisResult.model_validate_json(cached.read_text(encoding="utf-8"))
    settings = get_settings()
    result = await run_termsscope_on_text(
        text, llm_provider=settings.default_llm_provider,
        llm_model=settings.default_llm_model,
    )
    cached.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return result


async def _get_or_run_pass1(
    slug: str, text: str, run_dir: Path, client: JudgeClient,
) -> AnalysisResult:
    PASS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    doc_hash = doc_sha256(slug)
    cache_key = f"pass1__{client.cfg.judge_model}__{doc_hash[:16]}.json"
    persistent_cache = PASS_CACHE_DIR / cache_key
    run_copy = run_dir / "judge_pass1" / f"{slug}.json"
    if persistent_cache.exists():
        result = AnalysisResult.model_validate_json(persistent_cache.read_text(encoding="utf-8"))
        run_copy.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        return result
    result = await judge_pass1_chunked(text, client)
    payload = result.model_dump_json(indent=2)
    persistent_cache.write_text(payload, encoding="utf-8")
    run_copy.write_text(payload, encoding="utf-8")
    return result


async def _get_or_run_pass2(
    slug: str, text: str, ts: AnalysisResult, judge: AnalysisResult,
    a_is_termsscope: bool, run_dir: Path, client: JudgeClient,
) -> Pass2Verdict:
    PASS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    doc_hash = doc_sha256(slug)
    a_label = "TS-A" if a_is_termsscope else "Judge-A"
    cache_key = f"pass2__{client.cfg.judge_model}__{doc_hash[:16]}__{a_label}.json"
    persistent_cache = PASS_CACHE_DIR / cache_key
    run_copy = run_dir / "judge_pass2" / f"{slug}.json"
    if persistent_cache.exists():
        verdict = Pass2Verdict.model_validate_json(persistent_cache.read_text(encoding="utf-8"))
        run_copy.write_text(verdict.model_dump_json(indent=2), encoding="utf-8")
        return verdict
    verdict = await judge_pass2(text, ts, judge,
                                a_is_termsscope=a_is_termsscope, client=client)
    payload = verdict.model_dump_json(indent=2)
    persistent_cache.write_text(payload, encoding="utf-8")
    run_copy.write_text(payload, encoding="utf-8")
    return verdict


async def run_platform(
    spec: PlatformSpec,
    cfg: JudgeConfig,
    run_dir: Path,
    *,
    skip_pass2: bool,
) -> PlatformMetrics:
    """Full pipeline for one platform. Errors are caught and stored on the metrics."""
    text = load_text(spec.slug)
    logger.info("=== %s (%d chars) ===", spec.slug, len(text))

    try:
        ts_result = await _get_or_run_termsscope(spec.slug, text, run_dir)
        client = JudgeClient(cfg)
        judge_result = await _get_or_run_pass1(spec.slug, text, run_dir, client)

        # Embed and match clauses
        emb_cache = EmbeddingCache(EMBEDDINGS_DB, model=cfg.embedding_model)
        ts_flat = flatten(ts_result)
        judge_flat = flatten(judge_result)
        ts_emb = await emb_cache.embed([f.clause.clause_text for f in ts_flat])
        jg_emb = await emb_cache.embed([f.clause.clause_text for f in judge_flat])
        emb_cache.close()

        match = match_clauses(
            ts_flat, judge_flat, ts_emb, jg_emb,
            threshold=cfg.match_threshold, cross_category=False,
        )

        # Persist matches for inspection
        match_path = run_dir / "matches" / f"{spec.slug}.json"
        match_path.write_text(json.dumps({
            "pairs": [{"ts": a, "judge": b, "sim": s} for a, b, s in match.pairs],
            "unmatched_ts": match.unmatched_ts,
            "unmatched_judge": match.unmatched_judge,
            "threshold": cfg.match_threshold,
        }, indent=2), encoding="utf-8")

        prf1 = precision_recall_f1(match, ts_flat, judge_flat, flagged_only=True)
        prf1_per_cat = per_category_prf1(match, ts_flat, judge_flat, flagged_only=True)
        agreement = risk_level_agreement(match, ts_flat, judge_flat)
        coverage = coverage_breakdown(match, ts_flat, judge_flat)
        score_rows = collect_score_rows(spec.slug, ts_result, judge_result)

        halluc: dict = {}
        if not skip_pass2:
            a_is_ts = assign_ab(cfg.seed, spec.slug)
            verdict = await _get_or_run_pass2(
                spec.slug, text, ts_result, judge_result,
                a_is_termsscope=a_is_ts, run_dir=run_dir, client=client,
            )
            halluc = attribute_hallucinations(
                verdict, a_is_termsscope=a_is_ts,
                n_ts_clauses=len(ts_flat), n_judge_clauses=len(judge_flat),
            )

        return PlatformMetrics(
            platform=spec.slug,
            ts_overall_score=ts_result.overall_score,
            judge_overall_score=judge_result.overall_score,
            ts_clause_count=len(ts_flat),
            judge_clause_count=len(judge_flat),
            score_metrics={
                "ts_overall_score": ts_result.overall_score,
                "judge_overall_score": judge_result.overall_score,
                "diff": ts_result.overall_score - judge_result.overall_score,
            },
            clause_metrics=prf1,
            per_category_clause_metrics=prf1_per_cat,
            per_category_scores=score_rows,
            risk_level_agreement=agreement,
            coverage=coverage,
            hallucination=halluc,
            error=None,
        )

    except Exception as exc:
        logger.exception("Platform %s failed: %s", spec.slug, exc)
        return PlatformMetrics(
            platform=spec.slug,
            ts_overall_score=0,
            judge_overall_score=0,
            ts_clause_count=0,
            judge_clause_count=0,
            error=f"{type(exc).__name__}: {exc}",
        )


async def run_suite(
    specs: list[PlatformSpec],
    cfg: JudgeConfig,
    *,
    skip_pass2: bool = False,
    concurrency: int = 2,
    run_id: str | None = None,
) -> tuple[Path, dict]:
    """Run the eval over all specs. Returns (run_dir, suite_metrics)."""
    run_id = run_id or make_run_id(cfg.judge_model)
    run_dir = REPORTS_DIR / run_id
    _ensure_run_dirs(run_dir)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    sem = asyncio.Semaphore(concurrency)

    async def _bounded(spec: PlatformSpec) -> PlatformMetrics:
        async with sem:
            return await run_platform(spec, cfg, run_dir, skip_pass2=skip_pass2)

    results = await asyncio.gather(*[_bounded(s) for s in specs])

    settings = get_settings()
    suite = build_suite_metrics(
        results,
        run_id=run_id,
        judge_model=cfg.judge_model,
        ts_model=settings.default_llm_model,
        embedding_model=cfg.embedding_model,
        git_sha=_git_sha(),
        seed=cfg.seed,
    )
    (run_dir / "metrics.json").write_text(json.dumps(suite, indent=2, default=str), encoding="utf-8")
    _write_manifest(run_dir, cfg, run_id)
    _write_metrics_csv(run_dir, suite)
    return run_dir, suite


def _write_manifest(run_dir: Path, cfg: JudgeConfig, run_id: str) -> None:
    settings = get_settings()
    manifest = {
        "run_id": run_id,
        "generated_at": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "judge_provider": cfg.judge_provider,
        "judge_model": cfg.judge_model,
        "ts_provider": settings.default_llm_provider,
        "ts_model": settings.default_llm_model,
        "embedding_model": cfg.embedding_model,
        "match_threshold": cfg.match_threshold,
        "temperature": cfg.temperature,
        "seed": cfg.seed,
        "git_sha": _git_sha(),
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _write_metrics_csv(run_dir: Path, suite: dict) -> None:
    import csv
    rows = []
    for p in suite["platforms"]:
        rows.append({
            "platform": p["platform"],
            "error": p.get("error") or "",
            "ts_overall_score": p["ts_overall_score"],
            "judge_overall_score": p["judge_overall_score"],
            "ts_clause_count": p["ts_clause_count"],
            "judge_clause_count": p["judge_clause_count"],
            "precision": p.get("clause_metrics", {}).get("precision"),
            "recall": p.get("clause_metrics", {}).get("recall"),
            "f1": p.get("clause_metrics", {}).get("f1"),
            "kappa": p.get("risk_level_agreement", {}).get("kappa"),
            "ts_hallucination_rate": p.get("hallucination", {}).get("ts_hallucination_rate"),
        })
    with open(run_dir / "metrics.csv", "w", newline="", encoding="utf-8") as fh:
        if not rows:
            return
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
