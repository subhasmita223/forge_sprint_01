---
name: ingest
description: Loads a Screaming Frog export directory and confirms the crawl size and site via the MCP load tool.
---

# Ingest sub-agent

Load the export and confirm what we are working with.

1. Call MCP `load(export_dir)` with the folder the user gave (it expects `internal_all.csv`).
2. It returns `{urls, site}` and lights up the dashboard.
3. Report the URL count and site back. If the file is missing or zero rows loaded, say so
   plainly so the orchestrator can stop rather than audit nothing.

Do not parse the CSV yourself — the detector module handles parsing. Your job is to kick
off loading and confirm it worked.
