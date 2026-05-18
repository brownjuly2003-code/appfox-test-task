"""Запуск LangGraph supervisor pipeline.

Аналог run.py, но через граф агентов. Использование:
    python -m agents.cli --config data/seeds.yaml --out data/output
"""
from __future__ import annotations
import argparse
import sys
import time
from pathlib import Path

import yaml
from rich.console import Console
from rich.table import Table

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.graph import build_graph

console = Console()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="data/seeds.yaml")
    ap.add_argument("--out", default="data/output")
    ap.add_argument("--state", default="data/state/core.json")
    ap.add_argument("--cluster-threshold", type=float, default=0.20)
    ap.add_argument("--max-queries", type=int, default=200)
    ap.add_argument("--no-split", action="store_true")
    ap.add_argument("--no-merge", action="store_true")
    args = ap.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))

    initial = {
        "business_context": cfg["business_context"],
        "seeds": cfg["seeds"],
        "modifiers": cfg.get("modifiers", []),
        "competitors": cfg.get("competitors", []),
        "existing_pages": cfg.get("existing_pages", []),
        "distance_threshold": args.cluster_threshold,
        "apply_split": not args.no_split,
        "apply_merge": not args.no_merge,
        "max_queries": args.max_queries,
        "out_dir": args.out,
        "state_file": args.state,
        "metrics_by_query": {},
        "collect_retries": 0,
        "cluster_retries": 0,
        "decisions": [],
    }

    graph = build_graph()
    console.rule("[bold]LangGraph supervisor")
    t0 = time.time()
    final = graph.invoke(initial)
    dt = time.time() - t0

    console.rule("[bold]Decision log")
    for d in final.get("decisions", []):
        console.print(f"  • {d}")

    rows = final.get("rows", [])
    t = Table(title=f"Top-15 кластеров (всего {len(rows)})", show_lines=False)
    for col in ("#", "Кластер", "Intent", "Page", "Action", "Priority", "Q", "gap", "comp"):
        t.add_column(col)
    for r in rows[:15]:
        t.add_row(
            str(r["cluster_id"]),
            r["cluster"],
            r["intent"],
            r["recommended_page"],
            r["action"],
            f"{r['priority']:.3f}",
            str(r["queries_count"]),
            r["gap_status"][:8],
            r["competitor_coverage"][:8],
        )
    console.print(t)

    console.rule(f"[bold green]Готово за {dt:.1f}s")
    console.print(f"CSV:      {final.get('csv_path')}")
    console.print(f"MD:       {final.get('md_path')}")
    console.print(f"QUERIES:  {final.get('queries_path')}")
    console.print(f"RAW:      {final.get('raw_path')}")
    console.print(f"STATE:    {final.get('state_path')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
