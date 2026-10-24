#!/bin/bash
# SessionStart hook for Claude Code cloud sessions: make the container identical every time (KiCad 9, Python packages, make setup).
# Synchronous on purpose: the session starts only once the tools exist, so nothing races the install. Local sessions are left alone.
set -euo pipefail
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then exit 0; fi
exec bash "${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}/scripts/bootstrap.sh"
