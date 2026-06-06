---
name: seo-command-center
description: >
  Audit a website from a Screaming Frog SEO export. Use this whenever the user wants to
  analyze a crawl, find SEO issues, run a technical SEO audit, prioritize site problems,
  or turn a Screaming Frog internal_all.csv into a fix list and report. Trigger it for
  "audit this export", "find the SEO issues", "/seo-audit", or any request to process a
  Screaming Frog / crawl export. It runs an autonomous pipeline through the
  seo-command-center MCP server and renders a live dashboard plus an exportable report.
---

# SEO Command Center — orchestrator

Given a Screaming Frog export folder, run an autonomous technical-SEO audit and ship a
prioritized report plus fixes. A live dashboard shows the work at http://localhost:7700.

The real work runs through tools on the **seo-command-center MCP server**. Delegate
focused steps to the sub-agents so each stays small (this also keeps you inside free-tier
quota). Detect issues in **code** (the detector module is deterministic); use the model
only for judgment, such as rewriting titles and choosing redirect targets.

## Pipeline (run in order)

1. **Ingest.** Delegate to the `ingest` sub-agent → call MCP `load(export_dir)`. Confirm
   the URL count and site. Tell the user to open http://localhost:7700.

2. **Audit.** Delegate to the `auditor` sub-agent → call MCP `detect_issues()`. This runs
   the rulebook detectors. Review the result. If you extended the detector, make sure the
   new issue types appear.

3. **Fix (champion).** Delegate to the `fixer` sub-agent. For pages with missing or bad
   titles/meta, have the model **write** an optimized title (≤60 chars / ≤561 px) and
   meta (≤155 chars). For broken links, build a **redirect map** to the closest live page.
   Validate every rewrite's length in code and re-ask if it's over. Call MCP
   `set_fixes(titles, redirect_map)`.

4. **Recommend.** Read the issue summary and write 3–6 **specific** recommendations, e.g.
   "Fix the 12 missing titles and 30 broken internal links first (all High severity)."
   Call MCP `recommend([...])`.

5. **Deliver.** Delegate to the `reporter` sub-agent → call MCP `write_report()` then
   `export_report()`. Tell the user report.html is the file to send a client.

## Output contract
The run must end with `outputs/report.json` matching `report.schema.json`. The grader
reads it. Every issue needs `type`, `severity`, `affected_urls`, `count`. Champion tier
also needs the `fixes` block.

## Notes
- Extend `seo/detector.py` to cover the full `rulebook.md` — accuracy on a hidden export
  is the largest part of your score.
- Filter to text/html and indexable pages before title/meta checks (see rulebook).
- Be honest in the run summary about which issue types you implemented.
