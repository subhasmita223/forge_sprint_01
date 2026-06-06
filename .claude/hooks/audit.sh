#!/usr/bin/env bash
# audit.sh — Forge Sprint 01 process recorder.
# Appends one JSON line per lifecycle event to .claude/audit.jsonl.
# This is your tamper-evident build log and is part of your score. Do not edit it.
# Wired by .claude/settings.json to: SessionStart, UserPromptSubmit, PreToolUse,
# PostToolUse, SubagentStop, Stop. Runs async so it never blocks your work.
set -euo pipefail

INPUT=$(cat || true)
HOOK_EVENT="${HOOK_EVENT:-unknown}"
DIR="${CLAUDE_PROJECT_DIR:-.}"
AUDIT_FILE="$DIR/.claude/audit.jsonl"
TS=$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ" 2>/dev/null || date -u +"%Y-%m-%dT%H:%M:%SZ")

# jq is preferred; fall back to a minimal echo if jq is unavailable.
if command -v jq >/dev/null 2>&1; then
  SID=$(printf '%s' "$INPUT" | jq -r '.session_id // "unknown"' 2>/dev/null || echo unknown)
  TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // ""' 2>/dev/null || echo "")
  CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // .tool_input.file_path // .prompt // ""' 2>/dev/null | head -c 300)
  EXIT=$(printf '%s' "$INPUT" | jq -r '.tool_response.exit_code // ""' 2>/dev/null || echo "")
  OUT=$(printf '%s' "$INPUT" | jq -r '.tool_response.stdout // .tool_response.content // ""' 2>/dev/null | head -c 200)
  jq -nc --arg ts "$TS" --arg sid "$SID" --arg hook "$HOOK_EVENT" --arg tool "$TOOL" \
        --arg cmd "$CMD" --arg exit "$EXIT" --arg out "$OUT" \
    '{ts:$ts, session_id:$sid, hook:$hook, tool:$tool, command:$cmd, exit_code:$exit, output_preview:$out}' \
    >> "$AUDIT_FILE"
else
  printf '{"ts":"%s","hook":"%s","note":"jq not installed; install jq for full process capture"}\n' \
    "$TS" "$HOOK_EVENT" >> "$AUDIT_FILE"
fi
exit 0
