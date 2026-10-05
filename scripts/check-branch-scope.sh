#!/usr/bin/env bash
# usage: check-branch-scope.sh <branch> <allowed web-ui subfolder(s)...>
set -e
BR="$1"; shift
BAD=0
for f in $(git diff --name-only main..."$BR"); do
  ok=0
  for allowed in "$@"; do
    case "$f" in web-ui/$allowed/*|tests/web/*) ok=1 ;; esac
  done
  if [ $ok -eq 0 ]; then echo "OUT OF SCOPE: $f"; BAD=1; fi
done
# the invariants: nothing here may ever change on a UI branch
if git diff --name-only main..."$BR" | grep -E '^(src/ipsec_analyzer/(core|protocol|inference|assessment|output|synth|tui)/|tests/(core|protocol|inference|assessment|output|synth|tui|integration)/|CLAUDE.md|ARCHITECTURE.md|web-ui/package(-lock)?.json)'; then
  echo "FROZEN FILE TOUCHED"; BAD=1
fi
[ $BAD -eq 0 ] && echo "scope ok: $BR"
exit $BAD
