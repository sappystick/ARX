#!/bin/sh
# Zips each skill folder for upload to Claude (Cowork / claude.ai Skills) : one zip per skill, SKILL.md at the top of the folder.
set -e
mkdir -p cowork/skill_zips
for d in .claude/skills/*/; do n=$(basename "$d"); (cd .claude/skills && zip -qr "../../cowork/skill_zips/$n.zip" "$n"); done
ls cowork/skill_zips
