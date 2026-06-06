---
description: Audit a Screaming Frog export — detect SEO issues, prioritize, write fixes, and produce a live dashboard + client report.
argument-hint: <export-folder>   e.g. /seo-audit sample-export/
---

# /seo-audit

Run a full technical-SEO audit on the Screaming Frog export folder the user names in
`$ARGUMENTS` (it should contain `internal_all.csv`).

Invoke the **seo-command-center skill** to run the pipeline: ingest → audit → fix →
recommend → report.

Tell the user to open **http://localhost:7700** to watch the live cockpit, and that the
final shareable deliverable is **outputs/report.html**.

Example:
`/seo-audit sample-export/`

If the MCP server is not running, it should start with the plugin; otherwise start it with
`python mcp/server.py`.
