# SEO Command Center — Forge Sprint 01 starter

A Claude Code **plugin** that ingests a **Screaming Frog SEO export**, audits it against
the rulebook, prioritizes the issues, writes fixes, and renders a **live dashboard** plus
an exportable client report. The plumbing works out of the box — you implement the SEO
logic and push accuracy on the hidden export.

## Quick start (headless, proves it runs)
```bash
pip install mcp          # exposes MCP tools to Claude Code (dashboard works without it too)
python run.py sample-export/
# open the live cockpit:
#   http://localhost:7700
# outputs land in outputs/report.json and outputs/report.html
```

## Inside Claude Code
```
/seo-audit sample-export/
```

## What's here
```
seo-command-center/
├── .claude-plugin/plugin.json   plugin manifest (skill + command + agents + MCP)
├── .claude/                     audit hooks (settings.json + hooks/audit.sh) → records your process
├── skills/seo-audit/SKILL.md    orchestrator
├── agents/                      ingest, auditor, fixer, reporter (sub-agents)
├── commands/seo-audit.md        the /seo-audit command
├── mcp/server.py                local MCP server + live dashboard host (localhost:7700)
├── seo/detector.py              deterministic issue detection  ← EXTEND THIS to the full rulebook
├── dashboard/                   index.html + app.js (the cockpit)
├── scripts/export-transcript.sh saves your session transcript to agent-log.md (commit it)
├── run.py                       headless runner (the grader's entry point)
└── outputs/                     report.json + report.html (generated)
```

## Your job in the Sprint
1. **Complete `seo/detector.py`** to cover the full `rulebook.md` (the starter only does a
   few issue types). Accuracy on the hidden export is the biggest part of your score.
2. **Implement the fixer** (titles/meta rewrites within limits + a redirect map) for the
   champion tier — see `agents/fixer.md`.
3. **Improve the dashboard / report** to be genuinely client-ready.
4. **Commit incrementally** (≥10 commits) and let the audit hooks record your process.

## Process + memory files you must maintain (graded — see challenge brief section 08)
These are how the judges assess *how you worked with the AI*, not just the result:
- `.claude/audit.jsonl` — auto-written by the hooks (every tool call). Commit it. Keep
  `.claude/settings.json` in place so the hooks keep recording.
- `agent-log.md` — run `bash scripts/export-transcript.sh` at the end to export your session
  transcript. Commit it.
- `CLAUDE.md` — your project memory / instructions for the agent. **Edit this as you build** —
  good context engineering is the clearest signal of good practice.
- `PROMPTS.md` — log your key prompts (the ones that moved the build).
- `DECISIONS.md` — log your real decisions and what you learned / fixed.

The three records (audit log, transcript, git history) must agree — that is how a real process
is told apart from a fabricated one. Do not edit or fake the logs.

## The model
Run on the free local stack (Claude Code + Ollama). Set `OLLAMA_CONTEXT_LENGTH=65536`,
use a tool-trained model (`qwen3.5:9b` or `gemma4:31b-cloud`), not `qwen2.5-coder`.

## Note
The dashboard renders the operator's own crawl data on localhost; it is a local cockpit,
not a hardened public server. The shareable artifact is the exported `report.html`.
