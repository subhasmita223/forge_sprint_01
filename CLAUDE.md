# SEO Command Center — Project Memory

## Project Context
A Claude Code plugin that ingests a Screaming Frog SEO export (internal_all.csv),
detects SEO issues per rulebook.md, prioritizes them by severity, generates fixes,
and produces report.json + report.html plus a live dashboard at localhost:7700.
Graded on: detection accuracy (vs hidden export), process quality, and demo.
The hidden test export is a DIFFERENT site of similar size — build generically.

## Architecture (where each thing lives)
- run.py — headless entry point. Grader runs `python run.py sample-export/`.
  Orchestrates: seo_load → seo_detect → seo_recommend → seo_report → seo_export.
- mcp/server.py — the hub. Holds RUN{} shared state, emits SSE events to the
  dashboard, hosts HTTP on :7700, writes report.json/html. RARELY edit this.
- seo/detector.py — ★ THE BRAIN. Three functions:
    load_rows(export_dir) -> list[dict]   (reads internal_all.csv)
    detect(rows) -> list[issue dict]       (all rulebook detectors live here)
    summarize(issues) -> {total_issues, by_severity}
  Detection accuracy (the biggest score) is entirely in this file.
- seo/fixer.py — (to build) model-driven title/meta rewrites + redirect map.
- dashboard/ — index.html + app.js, the live cockpit.
- agents/, skills/, commands/ — the plugin wiring (mostly complete).

## Data Flow
internal_all.csv → load_rows → list of row dicts → detect() runs ~17 rules →
each rule returns {type, severity, affected_urls, count, explanation} →
server assembles report.json → renders report.html → dashboard streams events.

## Issue dict contract (every detector MUST return this shape)
{ "type": "<exact rulebook string>", "severity": "High|Medium|Low",
  "affected_urls": [<url strings>], "count": <int>, "explanation": "<short>" }

## Code Style
- Standard library + pandas only. Pure functions, no globals in detector.py.
- One detector = one clear block using the existing add() helper in detect().
- Reuse helpers: is_html(r), is_200(r), indexable(r), _int(v), _float(v).
- Precompute filtered lists once: html = [...], idx200 = [...]. Don't refilter.
- Cast every count/integer with int() before it reaches report.json.
- Readable over clever — I must explain any line in the live demo.
- Comment each detector with the rulebook rule it implements.

## ALWAYS
- Detect in plain Python. Counting rows is code's job, never the model's.
- Pre-filter title/meta/H1 checks to Content Type containing 'text/html'.
- Duplicate checks only on Indexable + Status 200 pages.
- Severity strings exactly "High" | "Medium" | "Low".
- Match the exact `type` strings from rulebook.md.
- After any change, re-run `python run.py sample-export/` and verify output.
- Commit after each working detector with a meaningful message.

## NEVER
- NEVER feed raw CSV rows to the model (OOM, wasted quota, no accuracy gain).
- NEVER hard-code sample URLs or counts — hidden export is a different site.
- NEVER use split(',') on CSV — use csv.DictReader (load_rows already does).
- The model (qwen) is ONLY for judgment: rewriting titles/metas, redirect targets.

## Rulebook quick-ref (type → rule → severity)
missing_title: Title 1 empty, indexable 200 → High
duplicate_title: same Title 1 on 2+ indexable → High
title_too_long: Pixel Width>561 OR Length>60 → Medium
title_too_short: Length<30 and not empty → Low
missing_meta_description: empty, indexable 200 → Medium
duplicate_meta_description: same on 2+ indexable → Medium
meta_description_too_long: Length>155 → Low
missing_h1: H1-1 empty on 200 page → Medium
duplicate_h1: same H1-1 on 2+ indexable → Low
broken_link: Status 400–499 → High
server_error: Status 500–599 → High
redirect: Status 300–399 → Medium
redirect_chain: a 3xx whose Redirect URL is itself a 3xx → High
thin_content: Word Count<200 on indexable → Low
orphan_page: Inlinks=0 on indexable 200 → Medium
non_indexable_but_linked: Non-Indexable AND Inlinks>0 → Medium
slow_page: Response Time>1.0 → Low

## Model usage
Ollama local, qwen3.5:9b (OLLAMA_CONTEXT_LENGTH=65536). Keep model_calls LOW
(efficiency score + tiebreaker): batch all title rewrites into one call, then a
code-side length-validation loop that re-asks only the ones over the limit.