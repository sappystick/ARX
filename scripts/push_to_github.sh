#!/bin/sh
# Run this yourself on your machine (nothing here has credentials). Creates the repo history and pushes to your GitHub.
set -e
REMOTE=${1:-https://github.com/sappystick/ARX.git}
git init -b main 2>/dev/null || true
git add -A
git commit -m "Arx: PHI-FOLD 233 repo (generators, data, docs, prompts, Claude Code config)" || true
git remote remove origin 2>/dev/null || true
git remote add origin "$REMOTE"
git push -u origin main
