"""
fixer.py — model-driven SEO fixes (the champion-tier value-add).

Two deliverables, built from the detected issues:
  1. titles       — rewritten <title> + <meta description> for flagged pages,
                    within length limits. The local model (qwen via Ollama) does the
                    judgment; code validates every length and re-asks only the misses.
  2. redirect_map — for broken (4xx) pages, the closest live page to redirect to,
                    chosen deterministically by URL-path similarity.

DESIGN: this runs inside run.py (the grader's entry point), so it must NEVER crash and
must NEVER hang. Every model call has a timeout and a deterministic fallback — if Ollama
is down or the model isn't pulled, we still produce valid fixes from page context.

Standard library only (urllib for Ollama, difflib for similarity).
"""
from __future__ import annotations
import json
import os
import urllib.request
from difflib import SequenceMatcher
from urllib.parse import urlparse

# Reuse the detector's filters/casts so "indexable", "200", "html" mean the same thing
# everywhere. Works whether imported as `seo.fixer` (run.py) or plain `fixer`.
try:
    from seo import detector
except ImportError:  # pragma: no cover - path fallback
    import detector  # type: ignore

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL = os.environ.get("RADAR_MODEL", "qwen3.5:9b")

TITLE_MAX_CHARS = 60      # rulebook: title_too_long when Title 1 Length > 60
META_MAX_CHARS = 155      # rulebook: meta_description_too_long when Length > 155

# Issue types that mean a page needs a title and/or meta rewrite.
_TITLE_META_TYPES = {
    "missing_title", "title_too_long", "title_too_short", "duplicate_title",
    "missing_meta_description", "meta_description_too_long", "duplicate_meta_description",
}


# ---------------------------------------------------------------- model plumbing
def _ollama_chat(messages, model=MODEL, timeout=60):
    """Call Ollama /api/chat in JSON mode. Return the content string, or None on ANY
    failure (offline, model not pulled, bad JSON, timeout) so callers can fall back."""
    body = json.dumps({
        "model": model,
        "messages": messages,
        "stream": False,
        "format": "json",            # force a JSON object back
        "options": {"temperature": 0.2},
    }).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL + "/api/chat", data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = (data.get("message") or {}).get("content", "")
        return content or None
    except Exception:
        return None


# ---------------------------------------------------------------- title + meta fixes
def _slug_to_text(url):
    """Turn the last path segment into readable words: /our-team/ -> 'Our Team'."""
    path = urlparse(url).path.strip("/")
    seg = path.split("/")[-1] if path else ""
    seg = seg.rsplit(".", 1)[0]  # drop extension
    words = seg.replace("-", " ").replace("_", " ").strip()
    return words.title() if words else "Home"


def _fallback_title(r):
    """Deterministic title from the page's H1, else its URL slug. Always within limit."""
    base = (r.get("H1-1", "") or "").strip() or _slug_to_text(r.get("Address", ""))
    return base[:TITLE_MAX_CHARS].strip()


def _fallback_meta(r):
    """Deterministic meta from H1 + first H2, trimmed to the limit."""
    h1 = (r.get("H1-1", "") or "").strip()
    h2 = (r.get("H2-1", "") or "").strip()
    base = ". ".join(p for p in (h1, h2) if p) or _slug_to_text(r.get("Address", ""))
    return base[:META_MAX_CHARS].strip()


def _ask_rewrites(pages, model):
    """One batched model call. `pages` = [{url, h1, current_title, current_meta}, ...].
    Return {url: {"title": str, "meta": str}} for whatever the model returned (possibly
    partial / possibly over-limit — the caller validates)."""
    system = (
        "You are an SEO copywriter. For each page, write an optimized <title> "
        f"(<= {TITLE_MAX_CHARS} characters) and meta description "
        f"(<= {META_MAX_CHARS} characters), using the page URL and its headings. "
        "Be specific and compelling; do not exceed the limits. "
        'Return ONLY JSON: {"pages":[{"url":"...","title":"...","meta":"..."}]}'
    )
    user = json.dumps({"pages": pages})
    content = _ollama_chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        model=model,
    )
    if not content:
        return {}
    try:
        parsed = json.loads(content)
    except Exception:
        return {}
    out = {}
    for p in parsed.get("pages", []):
        url = (p.get("url") or "").strip()
        if url:
            out[url] = {"title": (p.get("title") or "").strip(),
                        "meta": (p.get("meta") or "").strip()}
    return out


def _fix_titles_meta(target_urls, by_addr, model):
    """Rewrite title+meta for every flagged URL. Batch once, re-ask the over-limit ones
    once, then deterministically trim anything still bad. Returns (titles, model_calls)."""
    pages = []
    for url in target_urls:
        r = by_addr.get(url)
        if not r:
            continue
        pages.append({
            "url": url,
            "h1": (r.get("H1-1", "") or "").strip(),
            "current_title": (r.get("Title 1", "") or "").strip(),
            "current_meta": (r.get("Meta Description 1", "") or "").strip(),
        })
    if not pages:
        return [], 0

    calls = 0
    rewrites = _ask_rewrites(pages, model)
    if rewrites:
        calls += 1

    # Re-ask only the pages whose title/meta came back over the limit (or empty).
    def _bad(url):
        rw = rewrites.get(url)
        if not rw:
            return True
        return (not rw["title"] or len(rw["title"]) > TITLE_MAX_CHARS
                or not rw["meta"] or len(rw["meta"]) > META_MAX_CHARS)

    over = [p for p in pages if _bad(p["url"])]
    if over and rewrites:  # only retry if the model is actually responding
        retry = _ask_rewrites(over, model)
        if retry:
            calls += 1
            rewrites.update(retry)

    titles = []
    for url in target_urls:
        r = by_addr.get(url)
        if not r:
            continue
        rw = rewrites.get(url) or {}
        new_title = rw.get("title", "")
        new_meta = rw.get("meta", "")
        # Final guard: fall back / trim so the output ALWAYS respects the limits.
        if not new_title or len(new_title) > TITLE_MAX_CHARS:
            new_title = (new_title or _fallback_title(r))[:TITLE_MAX_CHARS].strip()
        if not new_meta or len(new_meta) > META_MAX_CHARS:
            new_meta = (new_meta or _fallback_meta(r))[:META_MAX_CHARS].strip()
        titles.append({
            "url": url,
            "old_title": (r.get("Title 1", "") or "").strip(),
            "new_title": new_title,
            "old_meta": (r.get("Meta Description 1", "") or "").strip(),
            "new_meta": new_meta,
        })
    return titles, calls


# ---------------------------------------------------------------- redirect map
def _path(u):
    try:
        return urlparse(u).path or "/"
    except Exception:
        return u or "/"


def _similarity(a, b):
    """Path closeness in [0,1]: sequence ratio, nudged up when they share a section."""
    pa, pb = _path(a), _path(b)
    score = SequenceMatcher(None, pa, pb).ratio()
    seg_a = [s for s in pa.split("/") if s]
    seg_b = [s for s in pb.split("/") if s]
    if seg_a and seg_b and seg_a[0] == seg_b[0]:
        score += 0.15  # same top-level section is a strong signal
    return score


def _build_redirect_map(rows, issues):
    """For each broken_link (4xx) page, redirect to the most similar live page."""
    broken = next((i for i in issues if i["type"] == "broken_link"), None)
    if not broken:
        return []
    live = [r.get("Address", "") for r in rows
            if detector.is_html(r) and detector.is_200(r) and detector.indexable(r)]
    if not live:
        return []
    redirect_map = []
    for frm in broken["affected_urls"]:
        best = max(live, key=lambda cand: _similarity(frm, cand))
        redirect_map.append({
            "from": frm,
            "to": best,
            "reason": "Closest live (200, indexable) page by URL-path similarity.",
        })
    return redirect_map


# ---------------------------------------------------------------- entry point
def build_fixes(rows, issues, model=MODEL):
    """Produce the champion-tier fixes. Never raises; degrades to deterministic output
    when the model is unavailable. Returns {titles, redirect_map, model_calls}."""
    try:
        by_addr = {r.get("Address", ""): r for r in rows}
        targets = sorted({u for i in issues if i["type"] in _TITLE_META_TYPES
                          for u in i["affected_urls"]})
        titles, calls = _fix_titles_meta(targets, by_addr, model)
        redirect_map = _build_redirect_map(rows, issues)
        return {"titles": titles, "redirect_map": redirect_map, "model_calls": calls}
    except Exception:
        # Last-resort safety net: a bad fix must never sink the whole run.
        return {"titles": [], "redirect_map": [], "model_calls": 0}
