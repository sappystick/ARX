# Setting this project up in Claude Cowork
(Check the current Claude Desktop app for exact menu names: Cowork changes quickly.)
1. Install the Claude desktop app (claude.com/download), open it and choose Cowork.
2. Clone or copy this repo to a folder on your machine (for example ~/Arx). Point Cowork at THAT folder only (not your Desktop). Cowork can read and write everything inside it.
3. Global instructions (Settings -> Cowork): paste cowork/GLOBAL_INSTRUCTIONS.md. The folder's CLAUDE.md is read automatically from the folder root.
4. Skills: upload the zips in cowork/skill_zips (or run scripts/make_skill_zips.sh first) through the skills settings, or leave them in .claude/skills in the folder.
5. Start with prompts/cowork/C00_SETUP.md. It checks whether your Cowork session can run Python. If it can, `make verify-quick` works there; if not, use Claude Code for the compute (generators, simulations, routing) and Cowork for documents, spreadsheets, decks, datasheet and literature checks.
6. Outputs go to Outputs/ (not into src/, data/, stl/, docs/): that keeps the repo clean; move what you want to keep into docs/ yourself or ask Claude Code to do it.
7. Cowork needs the desktop app open and the computer awake while it works; use /schedule only for read-only tasks such as the weekly status review (C01).
Division of labour: Claude Code = generators, simulations, routing, Gerbers, regression, git. Cowork = reports, spreadsheets, decks, procedures, datasheet and literature verification, review of figures.
