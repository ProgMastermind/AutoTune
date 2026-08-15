#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 <iterations>" >&2
  echo "Runs one open ready-for-agent GitHub issue per fresh Codex instance." >&2
}

if [[ $# -ne 1 || ! "$1" =~ ^[1-9][0-9]*$ ]]; then
  usage
  exit 2
fi

if ! command -v gh >/dev/null 2>&1 || ! gh auth status >/dev/null 2>&1; then
  echo "afk.sh requires an authenticated GitHub CLI to select and close tickets." >&2
  exit 2
fi

repo="${GITHUB_REPOSITORY:-ProgMastermind/AutoTune}"
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

for ((iteration = 1; iteration <= $1; iteration++)); do
  issue_number="$(gh issue list --repo "$repo" --state open --label ready-for-agent \
    --limit 100 --json number --jq '.[].number' | sort -n | head -n 1)"

  if [[ -z "$issue_number" ]]; then
    echo "<promise>NO MORE TASKS</promise>"
    exit 0
  fi

  echo "Starting iteration $iteration with issue #$issue_number."
  "$script_dir/once.sh" "$issue_number"
done
