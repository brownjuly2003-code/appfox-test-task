"""End-to-end pipeline runner.

Usage:
    python run.py --config data/seeds.yaml --out data/output
"""
from __future__ import annotations
import argparse
import json
import sys
import time
from pathlib import Path

import yaml
from rich.console import Console
from rich.table import Table

sys.path.insert(0, str(Path(__file__).parent))

from core import clean, cluster, collect, gap, output

console = Console()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="data/seeds.yaml")
    ap.add_argument("--out", default="data/output")
    ap.add_argument("--state", default="data/state/core.json")
    ap.add_argument("--skip-competitors", action="store_true", help="Не скрейпить конкурентов")
    ap.add_argument("--max-queries", type=int, default=200, help="Cap raw queries before clean")
    ap.add_argument("--cluster-threshold", type=float, default=0.20)
    ap.add_argument("--no-split", action="store_true", help="Отключить facet split кластеров")
    ap.add_argument("--keycollector-csv", help="Опц. CSV экспорт из KeyCollector/TopVisor с volume")
    ap.add_argument("--google-sheet-id", help="ID Google Sheet для дополнительного экспорта")
    ap.add_argument("--service-account-json", help="Путь к service account JSON для Google Sheets")
    ap.add_argument("--no-merge", action="store_true", help="Отключить post-merge дублей кластеров")
    args = ap.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    biz = cfg["business_context"]
    seeds = cfg["seeds"]
    modifiers = cfg.get("modifiers", [])
    competitors = [] if args.skip_competitors else cfg.get("competitors", [])
    existing_pages = cfg.get("existing_pages", [])

    t0 = time.time()

    # 1. Collect
    console.rule("[bold]Шаг 1: Сбор")
    console.print(f"seeds={len(seeds)}  modifiers={len(modifiers)}  competitors={len(competitors)}")
    raw = collect.collect_all(
        seeds=seeds,
        modifiers=modifiers,
        competitor_urls=competitors,
        autosuggest_per_seed=True,
        use_google=False,
    )

    # Optional: импорт KeyCollector с реальными volume
    metrics_by_query: dict[str, dict] = {}
    if args.keycollector_csv:
        kc = collect.import_keycollector_csv(args.keycollector_csv)
        for cand in kc:
            raw.append(cand.query)
            if cand.volume is not None:
                metrics_by_query[cand.query.lower()] = {"search_volume": min(1.0, cand.volume / 10000)}
        console.print(f"keycollector: +{len(kc)} запросов с volume")
        raw = sorted(set(raw))

    console.print(f"raw queries: [bold green]{len(raw)}[/]")
    if len(raw) > args.max_queries:
        raw = sorted(raw, key=lambda q: (-len(q.split()), q))[: args.max_queries]
        console.print(f"capped to {args.max_queries}")

    # 2. Clean: rule filter ⇒ LLM intent
    console.rule("[bold]Шаг 2: Чистка + интент")
    cleaned = clean.clean_batch(raw, biz, batch_size=25)
    kept = [c for c in cleaned if c.keep]
    dropped = [c for c in cleaned if not c.keep]
    console.print(f"kept: [bold green]{len(kept)}[/]  dropped: {len(dropped)}")
    if dropped[:5]:
        t = Table(title="Примеры отбракованных", show_lines=False)
        t.add_column("query"); t.add_column("intent"); t.add_column("reason")
        for d in dropped[:6]:
            t.add_row(d.query, d.intent, d.reason)
        console.print(t)

    # 3. Cluster + 4. Label
    console.rule("[bold]Шаг 3: Кластеризация")
    clusters = cluster.cluster_queries(
        [c.to_dict() for c in kept],
        distance_threshold=args.cluster_threshold,
        apply_split=not args.no_split,
    )
    console.print(f"clusters: [bold green]{len(clusters)}[/]")

    console.rule("[bold]Шаг 4: Названия кластеров")
    cluster.label_clusters(clusters, biz)

    if not args.no_merge:
        before = len(clusters)
        clusters = cluster.merge_duplicates(clusters)
        if before != len(clusters):
            console.print(f"merged duplicates: {before} → [bold green]{len(clusters)}[/]")

    # 5. Gap analysis vs previous state + competitors
    console.rule("[bold]Шаг 5: Gap analysis")
    prev_state = gap.load_state(args.state)
    prev_diff = gap.diff_with_previous(clusters, prev_state)
    competitor_pages: list[str] = []
    for url in competitors:
        competitor_pages.extend(collect.fetch_competitor_categories(url))
    comp_diff = gap.diff_with_competitors(clusters, competitor_pages)
    new_count = sum(1 for v in prev_diff.values() if v["gap_status"] == "new")
    competitor_gap = sum(1 for v in comp_diff.values() if v["competitor_coverage"] == "competitor_gap")
    console.print(
        f"prev: {sum(1 for v in prev_diff.values() if v['gap_status'] == 'existing')} existing, "
        f"{sum(1 for v in prev_diff.values() if v['gap_status'] == 'shifted')} shifted, "
        f"[bold yellow]{new_count} new[/]  |  competitors: {competitor_gap} competitor_gap"
    )

    # 6. Carry per-query metrics into per-cluster
    metrics_by_cluster: dict[int, dict] = {}
    for c in clusters:
        agg = {}
        vols = [metrics_by_query[q.lower()]["search_volume"] for q in c.queries if q.lower() in metrics_by_query]
        if vols:
            agg["search_volume"] = sum(vols) / len(vols)
        if agg:
            metrics_by_cluster[c.cluster_id] = agg

    # 7. Decisions + scoring + output
    console.rule("[bold]Шаг 6: Карта посадочных")
    rows = output.build_decision_rows(
        clusters,
        existing_pages,
        metrics_by_cluster=metrics_by_cluster,
    )
    # обогащаем строки gap-инфой — закрывает Critical #2 ревью (поля доедут до CSV/MD)
    for r in rows:
        gap_info = prev_diff.get(r["cluster_id"], {})
        comp_info = comp_diff.get(r["cluster_id"], {})
        r["gap_status"] = gap_info.get("gap_status", "new")
        r["competitor_coverage"] = comp_info.get("competitor_coverage", "unknown")
        r["matched_prev_label"] = gap_info.get("matched_prev_label", "") or ""
        r["new_queries"] = gap_info.get("new_queries", []) or []
        r["lost_queries"] = gap_info.get("lost_queries", []) or []

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output.write_csv(rows, out_dir / "decisions.csv")
    md_path = output.write_markdown(rows, out_dir / "decisions.md")
    queries_path = output.write_queries_csv(
        [c.to_dict() for c in cleaned],
        rows,
        out_dir / "queries.csv",
    )
    raw_path = out_dir / "raw_cleaned.json"
    raw_path.write_text(
        json.dumps([c.to_dict() for c in cleaned], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # save updated state
    state_path = gap.save_state(
        gap.build_state_from_clusters(clusters, version=prev_state.get("version", 0) + 1),
        args.state,
    )

    # optional Google Sheets export — закрывает Critical #4 ревью
    if args.google_sheet_id and args.service_account_json:
        try:
            url = output.write_google_sheet(
                rows,
                [c.to_dict() for c in cleaned],
                spreadsheet_id=args.google_sheet_id,
                service_account_json=args.service_account_json,
            )
            console.print(f"[bold green]Sheet:[/] {url}")
        except Exception as e:
            console.print(f"[red]Google Sheets export failed:[/] {e}")

    # Pretty table — top 15
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

    console.rule(f"[bold green]Готово за {time.time() - t0:.1f}s")
    console.print(f"CSV:      {csv_path}")
    console.print(f"MD:       {md_path}")
    console.print(f"QUERIES:  {queries_path}")
    console.print(f"RAW:      {raw_path}")
    console.print(f"STATE:    {state_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
