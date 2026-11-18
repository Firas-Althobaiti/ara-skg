"""``python -m ara.eval`` — run the evaluation metrics and print a rich table.

Exit code is 0 when every metric meets its threshold (see ``THRESHOLDS``),
1 otherwise — so CI can gate on ``make eval``.
"""

from __future__ import annotations

import sys

from rich.console import Console
from rich.table import Table

from ara.eval import run_eval

THRESHOLDS: dict[str, float] = {"extraction_f1": 0.6, "grounding": 1.0}


def main() -> int:
    """Run :func:`ara.eval.run_eval`, print a rich table, return 0 on PASS."""
    metrics = run_eval()
    console = Console()
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
