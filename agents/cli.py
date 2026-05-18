"""Единственная точка входа для пайплайна — LangGraph supervisor.

Использование:
    python -m agents.cli --config data/seeds.yaml --out data/output

Опциональные источники boevых данных:
    --keycollector-csv keys.csv                 # импорт реальных volume
    --google-sheet-id ID --service-account-json sa.json
                                                # экспорт результата в Google Sheet
    --skip-competitors                          # без скрейпа конкурентов
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
from core import collect as collect_mod
from core import output as output_mod

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
    ap.add_argument("--skip-competitors", action="store_true",
                    help="Не скрейпить конкурентов (быстрый прогон).")
    ap.add_argument("--no-seo", action="store_true",
                    help="Не генерировать SEO-мету и брифы (быстрее на ~30-60с на 16 кластеров).")
    ap.add_argument("--keycollector-csv",
                    help="CSV из KeyCollector / TopVisor с volume — поднимает score_mode из demo в mixed.")
    ap.add_argument("--google-sheet-id",
                    help="ID Google Sheet для опционального экспорта результата.")
    ap.add_argument("--service-account-json",
                    help="Путь к JSON service-account для Google Sheets.")
    args = ap.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    competitors = [] if args.skip_competitors else cfg.get("competitors", [])

    # KeyCollector: если задан CSV — импортируем volume в metrics_by_query,
    # supervisor использует это в priority.py score_mode.
    metrics_by_query: dict[str, dict] = {}
    seed_overrides: list[str] = []
    if args.keycollector_csv:
        kc = collect_mod.import_keycollector_csv(args.keycollector_csv)
        for cand in kc:
            seed_overrides.append(cand.query)
            if cand.volume is not None:
                metrics_by_query[cand.query.lower()] = {
                    "search_volume": min(1.0, cand.volume / 10000)
                }
        console.print(f"keycollector: +{len(kc)} запросов с volume")

    initial = {
        "business_context": cfg["business_context"],
        "seeds": cfg["seeds"] + seed_overrides,
        "modifiers": cfg.get("modifiers", []),
        "competitors": competitors,
        "existing_pages": cfg.get("existing_pages", []),
        "distance_threshold": args.cluster_threshold,
        "apply_split": not args.no_split,
        "apply_merge": not args.no_merge,
        "max_queries": args.max_queries,
        "out_dir": args.out,
        "state_file": args.state,
        "metrics_by_query": metrics_by_query,
        "collect_retries": 0,
        "cluster_retries": 0,
        "skip_seo": args.no_seo,
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

    removed = final.get("removed_clusters", [])
    if removed:
        console.rule(f"[bold yellow]Кандидаты на дроп/архив ({len(removed)})")
        for r in removed[:10]:
            console.print(f"  • {r.get('label','?')} (sim={r.get('closest_curr_sim',0):.2f})")

    # Optional Google Sheets export
    if args.google_sheet_id and args.service_account_json:
        try:
            url = output_mod.write_google_sheet(
                rows,
                [c for c in final.get("cleaned", []) if isinstance(c, dict)],
                spreadsheet_id=args.google_sheet_id,
                service_account_json=args.service_account_json,
            )
            console.print(f"[bold green]Sheet:[/] {url}")
        except Exception as e:
            console.print(f"[red]Google Sheets export failed:[/] {e}")

    console.rule(f"[bold green]Готово за {dt:.1f}s")
    console.print(f"CSV:      {final.get('csv_path')}")
    console.print(f"MD:       {final.get('md_path')}")
    console.print(f"QUERIES:  {final.get('queries_path')}")
    console.print(f"RAW:      {final.get('raw_path')}")
    console.print(f"STATE:    {final.get('state_path')}")
    if final.get("briefs_dir"):
        console.print(f"BRIEFS:   {final['briefs_dir']}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
