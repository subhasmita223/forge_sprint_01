#!/usr/bin/env bash
# export-transcript.sh — saves your Claude Code session transcript to agent-log.md.
# Claude Code writes a full JSONL transcript per project under ~/.claude/projects/.
# This finds the most recent one and renders it to a readable agent-log.md to commit.
set -euo pipefail

OUT="agent-log.md"
PROJDIR="$HOME/.claude/projects"

if [ ! -d "$PROJDIR" ]; then
  echo "No transcript directory found at $PROJDIR." > "$OUT"
  echo "Wrote a placeholder $OUT. Make sure you ran this from the machine you built on."
  exit 0
fi

LATEST=$(find "$PROJDIR" -name "*.jsonl" -print0 2>/dev/null | xargs -0 ls -t 2>/dev/null | head -1 || true)
if [ -z "${LATEST:-}" ]; then
  echo "No .jsonl transcript found." > "$OUT"; exit 0
fi

{
  echo "# Agent log — Forge Sprint 01 build transcript"
  echo ""
  echo "Source transcript: \`$LATEST\`"
  echo ""
  if command -v jq >/dev/null 2>&1; then
    jq -r 'select(.type=="user" or .type=="assistant") |
           if .type=="user" then "## You\n" + ((.message.content // .content // "") | tostring)
           else "## Claude\n" + (([.message.content[]? | select(.type=="text") | .text] | join("\n")) // "") +
                "\n" + (([.message.content[]? | select(.type=="tool_use") | "→ tool: " + .name] | join("\n")) // "")
           end' "$LATEST" 2>/dev/null || cat "$LATEST"
  else
    echo "(jq not installed — raw transcript below)"
    echo '```'
    cat "$LATEST"
    echo '```'
  fi
} > "$OUT"

echo "Wrote $OUT from $LATEST"
