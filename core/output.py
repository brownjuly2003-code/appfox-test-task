"""Export: CSV + Markdown table per ТЗ output model (Cluster → Page → Action)."""
from __future__ import annotations
import csv
from pathlib import Path

import numpy as np

from .cluster import Cluster, embed
from .priority import INTENT_PAGE_TYPE, decide_action, score_cluster


def _cluster_centroid(c: Cluster) -> np.ndarray:
    """Mean of query embeddings → cluster centroid (normalized)."""
    emb = embed(c.queries)
    centroid = emb.mean(axis=0)
    n = np.linalg.norm(centroid)
    return centroid / n if n else centroid


def build_decision_rows(
    clusters: list[Cluster],
    existing_pages: list[str],
    *,
    site_root: str = "",
    metrics_by_cluster: dict[int, dict] | None = None,
) -> list[dict]:
    """Build decision map with embedding-based page matching + cannibalization scoring.

    metrics_by_cluster: optional dict cluster_id → {search_volume, keyword_difficulty, ...}
                        — реальные данные из Wordstat/Ahrefs если доступны.
    """
    rows: list[dict] = []
    metrics_by_cluster = metrics_by_cluster or {}

    # Pre-compute centroids
    cluster_centroids = {c.cluster_id: _cluster_centroid(c) for c in clusters}

    # Embed existing pages (use slug+last-segment as text proxy)
    page_texts = [_page_to_text(p) for p in existing_pages]
    page_embeddings = embed(page_texts) if page_texts else np.zeros((0, 384), dtype=np.float32)

    # Cannibalization: pairwise similarity между кластерами; risk = max(sim) с другими кластерами
    centroids_matrix = np.stack(list(cluster_centroids.values())) if cluster_centroids else np.zeros((0, 384))
    cluster_ids_ordered = list(cluster_centroids.keys())
    sim_matrix = centroids_matrix @ centroids_matrix.T if len(centroids_matrix) else np.zeros((0, 0))
    np.fill_diagonal(sim_matrix, 0.0)

    for idx, c in enumerate(clusters):
        centroid = cluster_centroids[c.cluster_id]
        action, matched, page_sim = decide_action(
            c,
            existing_pages,
            page_embeddings=page_embeddings,
            cluster_embedding=centroid,
        )

        slug = getattr(c, "slug", "")
        if action == "Обновить" and matched:
            recommended = matched
        elif action == "Не брать":
            recommended = "—"
        elif action == "Создать статью":
            recommended = f"{site_root}/blog/{slug}/" if site_root else f"/blog/{slug}/"
        elif action == "Создать FAQ":
            recommended = f"{site_root}/faq/{slug}/" if site_root else f"/faq/{slug}/"
        else:
            recommended = f"{site_root}/catalog/{slug}/" if site_root else f"/catalog/{slug}/"

        # Cannibalization: similarity к другому кластеру с тем же recommended_page либо высокая близость
        canniball = 0.0
        if len(cluster_ids_ordered) > 1:
            i_in_ordered = cluster_ids_ordered.index(c.cluster_id)
            canniball = float(sim_matrix[i_in_ordered].max())

        scoring = score_cluster(
            c,
            action=action,
            metrics=metrics_by_cluster.get(c.cluster_id),
            cannibalization_risk=canniball,
        )
        rows.append(
            {
                "cluster_id": c.cluster_id,
                "cluster": c.label,
                "intent": c.intent,
                "page_type": INTENT_PAGE_TYPE.get(c.intent, ""),
                "recommended_page": recommended,
                "action": action,
                "priority": scoring["score"],
                "confidence": scoring["confidence"],
                "score_mode": scoring["score_mode"],
                "queries_count": len(c.queries),
                "factors": scoring["factors"],
                "sources": scoring["sources"],
                "page_similarity": round(page_sim, 3),
                "cannibal_risk": round(canniball, 3),
                "queries_sample": " | ".join(c.queries[:5]),
                "all_queries": c.queries,
                # gap-fields заполняются в run.py (закрывает Critical #2 от ревью)
                "gap_status": "unknown",
                "competitor_coverage": "unknown",
                "matched_prev_label": "",
                "new_queries": [],
                "lost_queries": [],
            }
        )
    rows.sort(key=lambda r: -r["priority"])
    return rows


def _page_to_text(url_or_slug: str) -> str:
    """Convert /catalog/uglovye-divany/ → 'угловые диваны' (back-translit + dehyphen)."""
    import re
    slug = url_or_slug.strip("/").split("/")[-1]
    # crude translit
    lat_to_ru = {
        "sh": "ш", "ch": "ч", "yu": "ю", "ya": "я", "zh": "ж",
        "yo": "ё", "a": "а", "b": "б", "v": "в", "g": "г", "d": "д",
        "e": "е", "z": "з", "i": "и", "y": "ы", "k": "к", "l": "л",
        "m": "м", "n": "н", "o": "о", "p": "п", "r": "р", "s": "с",
        "t": "т", "u": "у", "f": "ф", "h": "х", "c": "ц",
    }
    text = slug.lower().replace("-", " ")
    for src, dst in sorted(lat_to_ru.items(), key=lambda kv: -len(kv[0])):
        text = text.replace(src, dst)
    return text


def write_csv(rows: list[dict], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "cluster_id", "cluster", "intent", "page_type",
        "recommended_page", "action", "priority", "score_mode", "confidence",
        "queries_count",
        "page_similarity", "cannibal_risk",
        "gap_status", "competitor_coverage", "matched_prev_label",
        "new_queries_count", "lost_queries_count",
        "queries_sample",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            row_out = {k: r.get(k, "") for k in fieldnames}
            row_out["new_queries_count"] = len(r.get("new_queries", []) or [])
            row_out["lost_queries_count"] = len(r.get("lost_queries", []) or [])
            w.writerow(row_out)
    return path


def write_google_sheet(
    rows: list[dict],
    cleaned: list[dict],
    *,
    spreadsheet_id: str,
    service_account_json: str | Path | None = None,
) -> str:
    """Push decisions + queries в Google Sheets (2 листа: decisions, queries).

    Требует gspread + service account с правом на запись.
    Setup: 1) Create service account, download JSON. 2) Share sheet с service account email.
    3) pip install gspread google-auth.
    """
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError as e:
        raise NotImplementedError(
            "Google Sheets экспорт требует gspread: pip install gspread google-auth. "
            "Затем service account JSON: console.cloud.google.com → IAM → Service accounts. "
            "Дать sheet'у право Edit для email сервис-аккаунта."
        ) from e

    if not service_account_json:
        raise ValueError("service_account_json обязателен для Google Sheets export")

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(str(service_account_json), scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(spreadsheet_id)

    # Sheet 1: decisions
    try:
        ws = sh.worksheet("decisions")
        ws.clear()
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet("decisions", rows=max(len(rows) + 5, 50), cols=15)
    headers = ["cluster_id", "cluster", "intent", "page_type", "recommended_page",
               "action", "priority", "queries_count", "page_similarity",
               "cannibalization_risk", "queries_sample"]
    ws.append_row(headers)
    for r in rows:
        ws.append_row([r.get(k, "") for k in headers])

    # Sheet 2: queries (per-query audit trail)
    try:
        ws2 = sh.worksheet("queries")
        ws2.clear()
    except gspread.WorksheetNotFound:
        ws2 = sh.add_worksheet("queries", rows=max(len(cleaned) + 5, 100), cols=10)
    query_to_row: dict[str, dict] = {}
    for r in rows:
        for q in r.get("all_queries", []):
            query_to_row[q.lower()] = r
    q_headers = ["query", "intent", "keep", "reason", "cluster_id", "cluster", "action", "recommended_page"]
    ws2.append_row(q_headers)
    for c in cleaned:
        r = query_to_row.get(c["query"].lower())
        ws2.append_row([
            c["query"], c["intent"], c["keep"], c["reason"],
            r["cluster_id"] if r else "",
            r["cluster"] if r else "",
            r["action"] if r else "—",
            r["recommended_page"] if r else "—",
        ])
    return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"


def write_queries_csv(
    cleaned: list[dict],
    rows: list[dict],
    path: str | Path,
) -> Path:
    """Per-query audit trail: query + intent + keep + reason + cluster + action + page.

    cleaned: list of CleanedQuery.to_dict() — все запросы из чистки (kept + dropped)
    rows:    результат build_decision_rows — для маппинга cluster → action/page
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Build query → cluster_row map
    query_to_row: dict[str, dict] = {}
    for r in rows:
        for q in r["all_queries"]:
            query_to_row[q.lower()] = r

    fieldnames = [
        "query", "intent", "keep", "reason",
        "cluster_id", "cluster", "action", "recommended_page",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for c in cleaned:
            q = c["query"]
            r = query_to_row.get(q.lower())
            w.writerow({
                "query": q,
                "intent": c["intent"],
                "keep": c["keep"],
                "reason": c["reason"],
                "cluster_id": r["cluster_id"] if r else "",
                "cluster": r["cluster"] if r else "",
                "action": r["action"] if r else "—",
                "recommended_page": r["recommended_page"] if r else "—",
            })
    return path


def write_markdown(rows: list[dict], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# Карта посадочных страниц\n")
    lines.append("| # | Кластер | Интент | Страница | Действие | Priority | Mode | Q | page_sim | cannib | gap | competitors |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        lines.append(
            f"| {r['cluster_id']} | {r['cluster']} | {r['intent']} | "
            f"`{r['recommended_page']}` | {r['action']} | {r['priority']:.3f} | "
            f"{r.get('score_mode','-')} | {r['queries_count']} | "
            f"{r['page_similarity']:.2f} | {r['cannibal_risk']:.2f} | "
            f"{r.get('gap_status','-')} | {r.get('competitor_coverage','-')} |"
        )
    lines.append("\n## Кластеры по запросам\n")
    for r in rows:
        lines.append(f"### {r['cluster']} → {r['action']}  (priority {r['priority']:.3f}, mode {r.get('score_mode','-')}, confidence {r.get('confidence','-')})")
        lines.append(f"- intent: **{r['intent']}**, page: `{r['recommended_page']}`")
        lines.append(f"- факторы: {r['factors']}")
        lines.append(f"- источники: {r['sources']}")
        lines.append(f"- page_similarity (matched existing): {r['page_similarity']:.3f}; cannibal_risk: {r['cannibal_risk']:.3f}")
        if r.get("matched_prev_label"):
            lines.append(f"- gap: **{r['gap_status']}** vs prev `{r['matched_prev_label']}`; new {len(r.get('new_queries') or [])}, lost {len(r.get('lost_queries') or [])}")
        else:
            lines.append(f"- gap: **{r.get('gap_status','unknown')}**; competitors: {r.get('competitor_coverage','unknown')}")
        if r.get("new_queries"):
            lines.append(f"- новые запросы: {', '.join(r['new_queries'][:10])}")
        if r.get("lost_queries"):
            lines.append(f"- потерянные: {', '.join(r['lost_queries'][:10])}")
        lines.append("- запросы:")
        for q in r["all_queries"]:
            lines.append(f"  - {q}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
