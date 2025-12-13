#!/usr/bin/env bash
set -euo pipefail

ROOT="$(pwd)"

mkdir -p \
  "$ROOT/photojobs/commands" \
  "$ROOT/photojobs/lib" \
  "$ROOT/presets" \
  "$ROOT/logs"

# -------------------------
# Project metadata
# -------------------------
cat > "$ROOT/pyproject.toml" <<'TOML'
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "photojobs"
version = "0.1.0"
description = "JSP PhotoJobs tools"
requires-python = ">=3.9"

[tool.setuptools]
package-dir = {"" = "."}

[tool.setuptools.packages.find]
where = ["."]
include = ["photojobs*"]
TOML

cat > "$ROOT/.gitignore" <<'GIT'
__pycache__/
*.pyc
*.pyo
*.pyd
.venv/
venv/
.DS_Store
logs/
GIT

# -------------------------
# Python package markers
# -------------------------
cat > "$ROOT/photojobs/__init__.py" <<'PY'
__all__ = []
PY

cat > "$ROOT/photojobs/__main__.py" <<'PY'
from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
PY

# -------------------------
# CLI
# -------------------------
cat > "$ROOT/photojobs/cli.py" <<'PY'
import argparse
from .commands.keywords import run as run_keywords
from .commands.verify import run as run_verify
from .commands.csvgen import run as run_csvgen
from .commands.rename import run as run_rename
from .commands.teams import run as run_teams

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="photojobs", description="JSP PhotoJobs tools")
    sub = p.add_subparsers(dest="cmd", required=True)

    # keywords
    k = sub.add_parser("keywords", help="Apply keywords to images using CSV")
    k.add_argument("--csv", required=True, help="Path to CSV file")
    k.add_argument("--root", required=True, help="Root folder containing original images")
    k.add_argument("--manual", default="", help="Optional manual keyword applied to all images")
    k.add_argument("--preset", default="photoday", help="Preset name in presets/ (no extension)")

    # verify
    v = sub.add_parser("verify", help="Verify output vs source and keyword presence")
    v.add_argument("--root", required=True, help="Source root folder")
    v.add_argument("--out", default="", help="Output folder (defaults to <root>_keywords)")

    # csvgen
    c = sub.add_parser("csvgen", help="Generate derived CSV outputs and rename plan")
    c.add_argument("--csv", required=True, help="Input CSV file")
    c.add_argument("--root", required=True, help="Root folder containing originals (for matching/counts)")
    c.add_argument("--jobname", required=True, help="Job name used in output filenames")
    c.add_argument("--team-field", default="Team", help="Column name for team")
    c.add_argument("--outdir", default="", help="Output directory (defaults to same dir as input csv)")

    # rename
    r = sub.add_parser("rename", help="Rules-based rename using a plan; default mode is copy")
    r.add_argument("--root", required=True, help="Source root folder")
    r.add_argument("--plan", required=True, help="Rename plan file (txt/csv)")
    r.add_argument("--mode", choices=["copy","move"], default="copy", help="Rename mode")

    # teams
    t = sub.add_parser("teams", help="Sort into team folders")
    t.add_argument("--csv", required=True, help="CSV file containing team assignments")
    t.add_argument("--root", required=True, help="Root folder of images to sort (often <job>_keywords)")
    t.add_argument("--team-field", default="Team", help="Team column name")
    t.add_argument("--out", default="", help="Output folder (defaults to <root>_teams)")

    return p

def main(argv=None) -> int:
    p = build_parser()
    args = p.parse_args(argv)

    if args.cmd == "keywords":
        return run_keywords(args)
    if args.cmd == "verify":
        return run_verify(args)
    if args.cmd == "csvgen":
        return run_csvgen(args)
    if args.cmd == "rename":
        return run_rename(args)
    if args.cmd == "teams":
        return run_teams(args)

    p.error("Unknown command")
    return 2
PY

# -------------------------
# Command stubs
# -------------------------
cat > "$ROOT/photojobs/commands/keywords.py" <<'PY'
def run(args) -> int:
    print("keywords stub running")
    print(f"  csv    = {args.csv}")
    print(f"  root   = {args.root}")
    print(f"  manual = {args.manual}")
    print(f"  preset = {args.preset}")
    print("\n=== Summary ===")
    print("This is a stub. Next step: port AddKeywordsOnlly.py logic into this command.")
    return 0
PY

cat > "$ROOT/photojobs/commands/verify.py" <<'PY'
def run(args) -> int:
    print("verify stub running")
    print(f"  root = {args.root}")
    print(f"  out  = {args.out}")
    print("\n=== Summary ===")
    print("This is a stub.")
    return 0
PY

cat > "$ROOT/photojobs/commands/csvgen.py" <<'PY'
def run(args) -> int:
    print("csvgen stub running")
    print(f"  csv       = {args.csv}")
    print(f"  root      = {args.root}")
    print(f"  jobname   = {args.jobname}")
    print(f"  teamfield = {args.team_field}")
    print(f"  outdir    = {args.outdir}")
    print("\n=== Summary ===")
    print("This is a stub.")
    return 0
PY

cat > "$ROOT/photojobs/commands/rename.py" <<'PY'
def run(args) -> int:
    print("rename stub running")
    print(f"  root = {args.root}")
    print(f"  plan = {args.plan}")
    print(f"  mode = {args.mode}")
    print("\n=== Summary ===")
    print("This is a stub.")
    return 0
PY

cat > "$ROOT/photojobs/commands/teams.py" <<'PY'
def run(args) -> int:
    print("teams stub running")
    print(f"  csv       = {args.csv}")
    print(f"  root      = {args.root}")
    print(f"  teamfield = {args.team_field}")
    print(f"  out       = {args.out}")
    print("\n=== Summary ===")
    print("This is a stub.")
    return 0
PY

# -------------------------
# Library placeholders
# -------------------------
cat > "$ROOT/photojobs/lib/__init__.py" <<'PY'
__all__ = []
PY

cat > "$ROOT/photojobs/lib/utils.py" <<'PY'
# shared helpers live here
PY

# -------------------------
# Presets placeholders
# -------------------------
cat > "$ROOT/presets/keywords_photoday.yml" <<'YML'
# placeholder preset for PhotoDay keyword ingestion
csv:
  filenames_column: "Photo Filenames"
  first_name: "First Name"
  last_name: "Last Name"
  fallback_name: "Name"
YML

cat > "$ROOT/presets/keywords_legacy.yml" <<'YML'
# placeholder preset for legacy SPA format
csv:
  filenames_column: "SPA"
  first_name: "First Name"
  last_name: "Last Name"
  fallback_name: "Name"
YML

cat > "$ROOT/README.md" <<'MD'
# PhotoJobsTools

Run from this folder:

- python3 -m photojobs --help
- python3 -m photojobs keywords --csv "/path/file.csv" --root "/path/job"
MD

# -------------------------
# AppleScript launcher template
# -------------------------
cat > "$ROOT/PhotoJobs Launcher.applescript" <<'APPLESCRIPT'
-- PhotoJobs Launcher (template)
-- Runs from the PhotoJobsTools folder and calls: python3 -m photojobs <command>

set toolsFolder to POSIX path of (path to me)
set toolsFolder to do shell script "cd " & quoted form of toolsFolder & " && pwd"

set taskList to {"keywords", "verify", "csvgen", "rename", "teams"}
set chosenTask to choose from list taskList with prompt "Choose PhotoJobs task:" default items {"keywords"}
if chosenTask is false then return
set cmdName to item 1 of chosenTask

-- Common prompts
set csvPath to ""
set rootPath to ""
set outText to ""

if cmdName is "keywords" then
	set csvAlias to choose file with prompt "Select the CSV file:" of type {"public.comma-separated-values-text", "public.text"}
	set csvPath to POSIX path of csvAlias
	set rootFolder to choose folder with prompt "Select the ROOT folder that contains the original images (job folder):"
	set rootPath to POSIX path of rootFolder
	set manualKeywordDialog to display dialog "Enter an extra keyword to add to ALL images (leave blank for none):" default answer ""
	set manualKeyword to text returned of manualKeywordDialog
	set presetChoice to choose from list {"photoday", "legacy"} with prompt "Choose preset:" default items {"photoday"}
	if presetChoice is false then return
	set presetName to item 1 of presetChoice
	if manualKeyword is not "" then
		set shcmd to "cd " & quoted form of toolsFolder & " && /usr/bin/python3 -m photojobs keywords --csv " & quoted form of csvPath & " --root " & quoted form of rootPath & " --manual " & quoted form of manualKeyword & " --preset " & quoted form of presetName
	else
		set shcmd to "cd " & quoted form of toolsFolder & " && /usr/bin/python3 -m photojobs keywords --csv " & quoted form of csvPath & " --root " & quoted form of rootPath & " --preset " & quoted form of presetName
	end if
else if cmdName is "verify" then
	set rootFolder to choose folder with prompt "Select the SOURCE root folder (job folder):"
	set rootPath to POSIX path of rootFolder
	set shcmd to "cd " & quoted form of toolsFolder & " && /usr/bin/python3 -m photojobs verify --root " & quoted form of rootPath
else if cmdName is "csvgen" then
	set csvAlias to choose file with prompt "Select the INPUT CSV file:" of type {"public.comma-separated-values-text", "public.text"}
	set csvPath to POSIX path of csvAlias
	set rootFolder to choose folder with prompt "Select the ROOT folder that contains originals (job folder):"
	set rootPath to POSIX path of rootFolder
	set jobNameDialog to display dialog "Enter job name for output files (e.g., phsdebate25-26):" default answer "job"
	set jobName to text returned of jobNameDialog
	set teamFieldDialog to display dialog "Enter Team field name (default Team):" default answer "Team"
	set teamField to text returned of teamFieldDialog
	set shcmd to "cd " & quoted form of toolsFolder & " && /usr/bin/python3 -m photojobs csvgen --csv " & quoted form of csvPath & " --root " & quoted form of rootPath & " --jobname " & quoted form of jobName & " --team-field " & quoted form of teamField
else if cmdName is "rename" then
	set rootFolder to choose folder with prompt "Select the SOURCE root folder to rename (copy mode by default):"
	set rootPath to POSIX path of rootFolder
	set planAlias to choose file with prompt "Select the rename plan file:" of type {"public.text", "public.comma-separated-values-text"}
	set planPath to POSIX path of planAlias
	set shcmd to "cd " & quoted form of toolsFolder & " && /usr/bin/python3 -m photojobs rename --root " & quoted form of rootPath & " --plan " & quoted form of planPath & " --mode copy"
else if cmdName is "teams" then
	set csvAlias to choose file with prompt "Select the CSV file with teams:" of type {"public.comma-separated-values-text", "public.text"}
	set csvPath to POSIX path of csvAlias
	set rootFolder to choose folder with prompt "Select the ROOT folder of images to sort (often <job>_keywords):"
	set rootPath to POSIX path of rootFolder
	set teamFieldDialog to display dialog "Enter Team field name (default Team):" default answer "Team"
	set teamField to text returned of teamFieldDialog
	set shcmd to "cd " & quoted form of toolsFolder & " && /usr/bin/python3 -m photojobs teams --csv " & quoted form of csvPath & " --root " & quoted form of rootPath & " --team-field " & quoted form of teamField
end if

-- Progress indicator while running
try
	set progress total steps to 1
	set progress completed steps to 0
	set progress description to "Running PhotoJobs: " & cmdName
	set progress additional description to "Working..."
end try

set resultText to do shell script shcmd

try
	set progress completed steps to 1
end try

-- Extract summary
set AppleScript's text item delimiters to "=== Summary ==="
set parts to text items of resultText
if (count of parts) > 1 then
	set summaryText to "=== Summary ===" & item -1 of parts
else
	set summaryText to resultText
end if
set AppleScript's text item delimiters to ""

display dialog summaryText buttons {"OK"} default button 1 with title "PhotoJobs Results"
APPLESCRIPT

echo "✅ Bootstrapped PhotoJobsTools in: $ROOT"
echo "Next: try -> python3 -m photojobs --help"
echo "AppleScript template created: PhotoJobs Launcher.applescript"
echo "Optional (run once): python3 -m pip install -e ."