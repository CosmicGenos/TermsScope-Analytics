"""Command-line entry point for the eval harness.

Usage:
  uv run python -m evals.cli fetch-corpus [--refresh] [--platforms slug1,slug2,...]
  uv run python -m evals.cli run [--platforms all|slug1,slug2,...] [--judge-model NAME]
                          [--skip-pass2] [--concurrency N] [--threshold 0.75] [--yes]
  uv run python -m evals.cli replot --run-id 20260501-1430-...
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from evals.config import (CORPUS, JudgeConfig, REPORTS_DIR, get_platform,
                          select_platforms)
from evals.fetcher import fetch_corpus
from evals.report import render_report
from evals.runner import run_suite

logger = logging.getLogger(__name__)

# Cost model — Claude Sonnet 4.5 pricing as of 2026-04
_COST_PASS1 = 0.21
_COST_PASS2 = 0.08


def _parse_platforms(raw: str | None) -> list[str] | None:
    if raw is None or raw == "all":
        return None
    return [s.strip() for s in raw.split(",") if s.strip()]


def cmd_fetch_corpus(args: argparse.Namespace) -> int:
    slugs = _parse_platforms(args.platforms)
    specs = [get_platform(s) for s in slugs] if slugs else list(CORPUS)
    results = asyncio.run(fetch_corpus(specs, refresh=args.refresh))
    print("Fetched corpus:")
    for r in results:
        if r.get("error"):
            print(f"  ✗ {r['slug']:12} {r['error']}")
        else:
            mark = "•" if r.get("skipped") else "✓"
            print(f"  {mark} {r['slug']:12} {r['length']:>7} chars  sha={r['sha256'][:10]}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    slugs = _parse_platforms(args.platforms)
    specs = select_platforms(slugs)
    cfg = JudgeConfig(
        judge_provider=args.judge_provider,
        judge_model=args.judge_model,
        embedding_model=args.embedding_model,
        match_threshold=args.threshold,
        seed=args.seed,
    )
    cost = len(specs) * (_COST_PASS1 + (0 if args.skip_pass2 else _COST_PASS2))
    print(f"Eval plan: {len(specs)} platforms × judge={cfg.judge_model} "
          f"(skip_pass2={args.skip_pass2}) ≈ ${cost:.2f}")
    if not args.yes:
        ans = input("Proceed? [y/N]: ").strip().lower()
        if ans not in ("y", "yes"):
            print("Aborted.")
            return 1
    run_dir, suite = asyncio.run(run_suite(
        specs, cfg, skip_pass2=args.skip_pass2, concurrency=args.concurrency,
    ))
    report_path = render_report(run_dir)
    print(f"\nDone. Run dir: {run_dir}")
    print(f"      Report:  {report_path}")
    g = suite["global"]
    sm = g["score_summary"]
    if sm.get("pearson_r") is not None:
        print(f"  Pearson r = {sm['pearson_r']:.2f}, MAE = {sm['mae']:.1f}, "
              f"micro F1 = {g['micro_f1']:.2f}, κ = "
              f"{g.get('aggregate_kappa', 0) or 0:.2f}")
    return 0


def cmd_replot(args: argparse.Namespace) -> int:
    run_dir = REPORTS_DIR / args.run_id
    if not run_dir.exists():
        print(f"Run not found: {run_dir}", file=sys.stderr)
        return 2
    if not (run_dir / "metrics.json").exists():
        print(f"metrics.json missing in {run_dir}", file=sys.stderr)
        return 2
    report_path = render_report(run_dir)
    print(f"Re-rendered report: {report_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="evals.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)

    fc = sub.add_parser("fetch-corpus", help="Download ToS texts to fixtures/raw/")
    fc.add_argument("--refresh", action="store_true", help="Re-fetch even if cached")
    fc.add_argument("--platforms", default=None, help="Comma list of slugs (default: all)")

    rn = sub.add_parser("run", help="Run the eval suite")
    rn.add_argument("--platforms", default="all")
    rn.add_argument("--judge-provider", default="claude")
    rn.add_argument("--judge-model", default="claude-sonnet-4-5-20250929")
    rn.add_argument("--embedding-model", default="text-embedding-3-small")
    rn.add_argument("--threshold", type=float, default=0.75)
    rn.add_argument("--seed", type=int, default=42)
    rn.add_argument("--skip-pass2", action="store_true")
    rn.add_argument("--concurrency", type=int, default=2)
    rn.add_argument("--yes", action="store_true", help="Skip cost confirmation")

    rp = sub.add_parser("replot", help="Re-render plots and REPORT.md from existing metrics.json")
    rp.add_argument("--run-id", required=True)

    return parser


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = build_parser()
    args = parser.parse_args()
    if args.cmd == "fetch-corpus":
        return cmd_fetch_corpus(args)
    if args.cmd == "run":
        return cmd_run(args)
    if args.cmd == "replot":
        return cmd_replot(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
