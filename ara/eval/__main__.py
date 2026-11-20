"""``python -m ara.eval`` — run the evaluation metrics and print a rich table.

Default (``make eval``, CI): mock mode only, exits non-zero when thresholds
are missed. With ``--live`` or ``EXTRACTION_MODE=live`` (``make eval-live``,
manual / workflow_dispatch only): prints mock AND live extraction scores
against the real-abstract gold set side-by-side and writes a markdown report
under ``artifacts/eval_live_<date>.md``.
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table

from ara.eval import run_eval
from ara.eval.extraction_f1 import eval_with_mode

THRESHOLDS: dict[str, float] = {"extraction_f1": 0.6, "grounding": 1.0}


def _mode_table(console: Console, title: str, rows: list[dict[str, object]]) -> None:
    table = Table(title=title, header_style="bold cyan")
    for col in (
        "mode",
        "gold",
        "f1",
        "precision",
        "recall",
        "distractor_rejection",
        "n_predicted",
        "n_gold",
    ):
        table.add_column(col, justify="right" if col not in ("mode", "gold") else "left")
    for r in rows:
        table.add_row(
            *[
                str(r.get(c, ""))
                for c in (
                    "mode",
                    "gold",
                    "f1",
                    "precision",
                    "recall",
                    "distractor_rejection",
                    "n_predicted",
                    "n_gold",
                )
            ]
        )
    console.print(table)


def main() -> int:
    """Run the eval; in live mode print both modes and save a report."""
    console = Console()
    mode = os.environ.get("EXTRACTION_MODE", "mock")
    live = "--live" in sys.argv or mode == "live"

    if live:
        mock_res = asyncio.run(eval_with_mode("mock"))
        live_res = asyncio.run(eval_with_mode("live"))
        _mode_table(console, "ARA-SKG extraction eval (real-abstract gold)", [mock_res, live_res])
        j = live_res.get("judge") or {}
        console.print(
            "judge calls: {total} (rule-matched: {rule_matched}, llm-judged: {llm_judged}, "
            "llm-accepted: {llm_accepted}, cache-hits: {cache_hits}, max: {max_calls})".format(
                total=j.get("total", 0),
                rule_matched=j.get("rule_matched", 0),
                llm_judged=j.get("llm_judged", 0),
                llm_accepted=j.get("llm_accepted", 0),
                cache_hits=j.get("cache_hits", 0),
                max_calls=j.get("max_calls", "-"),
            )
        )

        artifacts = Path("artifacts")
        artifacts.mkdir(exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%d")
        report = artifacts / f"eval_live_{stamp}.md"
        report.write_text(
            "# Live eval report — "
            + datetime.now(UTC).isoformat()
            + "\n\n| mode | gold | f1 | precision | recall | distractor_rejection | n_predicted | n_gold |\n"
            + "|---|---|---|---|---|---|---|---|\n"
            + f"| {mock_res['mode']} | {mock_res['gold']} | {mock_res['f1']:.4f} | {mock_res['precision']:.4f} | {mock_res['recall']:.4f} | {mock_res['distractor_rejection']:.4f} | {mock_res['n_predicted']} | {mock_res['n_gold']} |\n"
            + f"| {live_res['mode']} | {live_res['gold']} | {live_res['f1']:.4f} | {live_res['precision']:.4f} | {live_res['recall']:.4f} | {live_res['distractor_rejection']:.4f} | {live_res['n_predicted']} | {live_res['n_gold']} |\n"
            + "\njudge calls: {total} (rule-matched: {rule_matched}, llm-judged: {llm_judged}, "
            "llm-accepted: {llm_accepted}, cache-hits: {cache_hits}, max: {max_calls})\n".format(
                **{
                    k: j.get(k, 0)
                    for k in ("total", "rule_matched", "llm_judged", "llm_accepted", "cache_hits")
                },
                **{"max_calls": j.get("max_calls", "-")},
            ),
            encoding="utf-8",
        )
        console.print(f"[bold]report saved:[/bold] {report}")
        return 0

    metrics = run_eval()
    table = Table(title="ARA-SKG evaluation metrics", header_style="bold cyan")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_column("Threshold", justify="right")
    table.add_column("Status")
    ok = True
    for name, value in metrics.items():
        threshold = THRESHOLDS.get(name)
        passed = threshold is None or value >= threshold
        ok = ok and passed
        table.add_row(
            name,
            f"{value:.4f}",
            "-" if threshold is None else f">= {threshold}",
            "[green]PASS[/green]" if passed else "[red]FAIL[/red]",
        )
    console.print(table)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
