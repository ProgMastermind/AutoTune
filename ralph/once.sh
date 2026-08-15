#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 <issue-number>" >&2
  echo "Runs one ready-for-agent GitHub issue in a fresh Codex instance." >&2
}

if [[ $# -ne 1 || ! "$1" =~ ^[0-9]+$ ]]; then
  usage
  exit 2
fi

if ! command -v codex >/dev/null 2>&1; then
  echo "codex is required. Install and authenticate the Codex CLI first." >&2
  exit 2
fi

repo="${GITHUB_REPOSITORY:-ProgMastermind/AutoTune}"
issue_number="$1"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -n "${AUTOTUNE_REPO_DIR:-}" ]]; then
  repo_root="$AUTOTUNE_REPO_DIR"
else
  repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" || {
    echo "Run this script from a Git checkout or set AUTOTUNE_REPO_DIR." >&2
    exit 2
  }
fi
cd "$repo_root"

if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  issue_json="$(gh issue view "$issue_number" --repo "$repo" --json number,title,body,state,labels)"
else
  issue_json="$(curl --fail --silent --show-error \
    "https://api.github.com/repos/${repo}/issues/${issue_number}")"
fi

issue_state="$(printf '%s' "$issue_json" | jq -r '.state')"
if [[ "$issue_state" != "OPEN" && "$issue_state" != "open" ]]; then
  echo "Issue #$issue_number is not open; nothing to run." >&2
  exit 2
fi

issue_title="$(printf '%s' "$issue_json" | jq -r '.title')"
issue_body="$(printf '%s' "$issue_json" | jq -r '.body // ""')"
commits="$(git log -n 5 --format='%H%n%ad%n%B---' --date=short 2>/dev/null || true)"
runner_prompt="$(cat "$script_dir/prompt.md")"

log_dir="${RALPH_LOG_DIR:-.ralph/logs}"
mkdir -p "$log_dir"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
event_log="$log_dir/issue-${issue_number}-${stamp}.jsonl"
last_message="$log_dir/issue-${issue_number}-${stamp}.final.md"
input_file="$(mktemp)"
trap 'rm -f "$input_file"' EXIT

cat >"$input_file" <<EOF
# Ticket

Repository: $repo
Issue: #$issue_number — $issue_title

$issue_body

# Recent commits

$commits

# Runner instructions

$runner_prompt
EOF

set +e
codex exec --ephemeral --json --output-last-message "$last_message" - <"$input_file" \
  | tee "$event_log"
codex_status="${PIPESTATUS[0]}"
set -e

if [[ "$codex_status" -ne 0 ]]; then
  echo "Codex exited with status $codex_status. Logs: $event_log" >&2
  exit "$codex_status"
fi

if grep -Fq '<promise>TICKET COMPLETE</promise>' "$last_message"; then
  if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    gh issue comment "$issue_number" --repo "$repo" \
      --body "Completed by a fresh Codex run. Final report: ${last_message}"
    gh issue close "$issue_number" --repo "$repo"
  else
    echo "Ticket completed, but GitHub CLI authentication is unavailable; close #$issue_number manually." >&2
  fi
  echo "TICKET_COMPLETE issue=$issue_number log=$last_message"
  exit 0
fi

echo "Ticket #$issue_number did not declare completion. Final report: $last_message" >&2
exit 1
