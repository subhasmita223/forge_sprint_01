"""
detector.py — deterministic SEO issue detection from a Screaming Frog internal_all.csv.

STARTER IMPLEMENTATION. It already detects several issues so the pipeline runs end to
end. Your job in the Sprint is to COMPLETE the rulebook (see rulebook.md): add the
missing detectors, handle edge cases, and improve accuracy against the hidden export.

Standard library only (csv). Detection is plain Python on purpose — the model is for
judgment (rewriting titles, choosing redirect targets), not for counting rows.
"""

from __future__ import annotations
import csv
import os
from collections import defaultdict


def load_rows(export_dir: str) -> list[dict]:
    path = os.path.join(export_dir, "internal_all.csv")
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _int(v, default=0):
    try:
        return int(float(str(v).strip()))
    except Exception:
        return default


def _float(v, default=0.0):
    try:
        return float(str(v).strip())
    except Exception:
        return default


def is_html(r):  return "text/html" in (r.get("Content Type", "") or "").lower()
def is_200(r):   return _int(r.get("Status Code")) == 200
def indexable(r): return (r.get("Indexability", "") or "").strip().lower() == "indexable"


def detect(rows: list[dict]) -> list[dict]:
    """Return a list of issue dicts: {type, severity, affected_urls, count, explanation}.
    STARTER set — extend to the full rulebook for a high score."""
    issues = []

    def add(t, sev, urls, explanation):
        urls = sorted(set(urls))
        if urls:
            issues.append({"type": t, "severity": sev, "affected_urls": urls,
                           "count": len(urls), "explanation": explanation})

    html = [r for r in rows if is_html(r)]
    idx200 = [r for r in html if is_200(r) and indexable(r)]

    # --- Titles ---
    add("missing_title", "High",
        [r["Address"] for r in idx200 if not (r.get("Title 1", "") or "").strip()],
        "Indexable pages with no title tag.")

    # duplicate titles (indexable only)
    by_title = defaultdict(list)
    for r in idx200:
        t = (r.get("Title 1", "") or "").strip()
        if t:
            by_title[t].append(r["Address"])
    dup_t = [u for urls in by_title.values() if len(urls) > 1 for u in urls]
    add("duplicate_title", "High", dup_t, "Pages sharing an identical title.")

    add("title_too_long", "Medium",
        [r["Address"] for r in idx200
         if _int(r.get("Title 1 Pixel Width")) > 561 or _int(r.get("Title 1 Length")) > 60],
        "Titles likely truncated in search results.")

    # --- Response codes ---
    add("broken_link", "High",
        [r["Address"] for r in rows if 400 <= _int(r.get("Status Code")) <= 499],
        "URLs returning a client error (4xx).")
    add("server_error", "High",
        [r["Address"] for r in rows if 500 <= _int(r.get("Status Code")) <= 599],
        "URLs returning a server error (5xx).")
    add("redirect", "Medium",
        [r["Address"] for r in rows if 300 <= _int(r.get("Status Code")) <= 399],
        "URLs that redirect (3xx).")

    # redirect_chain: a 3xx whose Redirect URL is itself a 3xx (chain), or loops back → High
    redirect_map = {}
    for r in rows:
        if 300 <= _int(r.get("Status Code")) <= 399:
            target = (r.get("Redirect URL", "") or "").strip()
            if target:
                redirect_map[r["Address"]] = target
    flagged = []
    for start in redirect_map:
        visited = {start}
        current = start
        while current in redirect_map:
            target = redirect_map[current]
            if target in visited:          # loop back to an already-seen URL
                flagged.append(start)
                break
            if target in redirect_map:      # target is itself a redirect → chain
                flagged.append(start)
                break
            visited.add(target)
            current = target
    add("redirect_chain", "High", flagged,
        "Redirects that point to another redirect (chain) or loop back (loop).")

    # --- Orphan pages ---
    add("orphan_page", "Medium",
        [r["Address"] for r in idx200 if _int(r.get("Inlinks")) == 0],
        "Indexable pages with zero internal links in.")

    # title_too_short: Length<30 and not empty, indexable 200 → Low
    add("title_too_short", "Low",
        [r["Address"] for r in idx200
         if (r.get("Title 1", "") or "").strip() and _int(r.get("Title 1 Length")) < 30],
        "Titles shorter than 30 characters.")

    # missing_meta_description: empty, indexable 200 → Medium
    add("missing_meta_description", "Medium",
        [r["Address"] for r in idx200 if not (r.get("Meta Description 1", "") or "").strip()],
        "Indexable pages with no meta description.")

    # meta_description_too_long: Length>155 → Low
    add("meta_description_too_long", "Low",
        [r["Address"] for r in idx200 if _int(r.get("Meta Description 1 Length")) > 155],
        "Meta descriptions likely truncated in search results.")

    # duplicate_meta_description: same Meta Description 1 on 2+ indexable → Medium
    by_meta = defaultdict(list)
    for r in idx200:
        m = (r.get("Meta Description 1", "") or "").strip()
        if m:
            by_meta[m].append(r["Address"])
    dup_m = [u for urls in by_meta.values() if len(urls) > 1 for u in urls]
    add("duplicate_meta_description", "Medium", dup_m,
        "Pages sharing an identical meta description.")

    # missing_h1: H1-1 empty on 200 page → Medium (html+200, not idx200)
    add("missing_h1", "Medium",
        [r["Address"] for r in html if is_200(r) and not (r.get("H1-1", "") or "").strip()],
        "200 pages with no H1 heading.")

    # duplicate_h1: same H1-1 on 2+ indexable → Low
    by_h1 = defaultdict(list)
    for r in idx200:
        h = (r.get("H1-1", "") or "").strip()
        if h:
            by_h1[h].append(r["Address"])
    dup_h = [u for urls in by_h1.values() if len(urls) > 1 for u in urls]
    add("duplicate_h1", "Low", dup_h, "Pages sharing an identical H1 heading.")

    # thin_content: Word Count<200 on indexable → Low
    add("thin_content", "Low",
        [r["Address"] for r in idx200 if _int(r.get("Word Count")) < 200],
        "Indexable pages with fewer than 200 words.")

    # non_indexable_but_linked: Non-Indexable AND Inlinks>0 → Medium
    add("non_indexable_but_linked", "Medium",
        [r["Address"] for r in rows
         if (r.get("Indexability", "") or "").strip().lower() == "non-indexable"
         and _int(r.get("Inlinks")) > 0],
        "Non-indexable pages that still receive internal links.")

    # slow_page: Response Time>1.0 → Low
    add("slow_page", "Low",
        [r["Address"] for r in rows if _float(r.get("Response Time")) > 1.0],
        "Pages with a response time over 1.0 seconds.")

    return issues


def summarize(issues: list[dict]) -> dict:
    by_sev = defaultdict(int)
    for i in issues:
        by_sev[i["severity"]] += 1
    return {"total_issues": len(issues),
            "by_severity": {"High": by_sev["High"], "Medium": by_sev["Medium"], "Low": by_sev["Low"]}}


if __name__ == "__main__":
    import sys, json
    d = sys.argv[1] if len(sys.argv) > 1 else "../sample-export"
    rows = load_rows(d)
    iss = detect(rows)
    print(f"Loaded {len(rows)} rows, detected {len(iss)} issue types.")
    print(json.dumps(summarize(iss), indent=2))
    for i in iss:
        print(f"  [{i['severity']:<6}] {i['type']:<24} x{i['count']}")
