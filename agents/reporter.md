---
name: reporter
description: Writes the machine-readable report.json and the client-ready report.html via the MCP write_report and export_report tools.
---

# Reporter sub-agent

Produce the deliverables.

1. Call MCP `write_report()` → writes `outputs/report.json` (the grader reads this; it
   must match `report.schema.json`).
2. Call MCP `export_report()` → writes `outputs/report.html`, the standalone client
   report (issues prioritized by severity + recommendations).
3. Confirm both files exist and tell the user `report.html` is the file to send a client.

Do not invent numbers — the report is built from the detected issues and the fixes already
attached. Your job is to trigger the writes and confirm the artifacts landed.
