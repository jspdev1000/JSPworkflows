# PhotoJobsTools Project

## Project Overview

PhotoJobsTools is a Python CLI application designed to manage photo metadata and organization for PhotoDay jobs. The tool helps photographers and photo coordinators batch-process images by applying keywords, verifying metadata, generating reports, renaming files, and organizing photos into team folders.

## Architecture

- **Entry point**: `photojobs/__main__.py` (runs via `python3 -m photojobs`)
- **CLI interface**: `photojobs/cli.py` - argparse-based command router
- **Commands**: Individual command modules in `photojobs/commands/`
- **Utilities**: Shared helper functions in `photojobs/lib/utils.py`

## Implementation Status

| Command | Status | Notes |
|---------|--------|-------|
| keywords | ✅ Fully implemented | Production-ready, complex file matching logic |
| verify | ⚠️ Stub only | Placeholder implementation |
| csvgen | ⚠️ Standalone only | Implemented but not integrated into CLI (no run() function) |
| rename | ⚠️ Stub only | Placeholder implementation |
| teams | ✅ Fully implemented | Sorts first image per person into team subfolders |

## Commands

### 1. keywords
**Purpose**: Apply IPTC/XMP keywords to images based on CSV data

**Usage**:
```bash
python3 -m photojobs keywords --csv "/path/file.csv" --root "/path/job" [--manual "keyword"] [--preset "photoday"]
```

**Behavior**:
- Reads CSV with person/image mappings (supports multiple CSV formats)
- Locates image files under root folder (flexible matching, ignores extensions)
- Copies files to temp directory: `/Users/jerry/Pictures/PhotoJobs/scripts/_Files/TempAddKeyword`
- Writes keywords using exiftool to IPTC:Keywords, XMP-dc:Subject, XMP-lr:HierarchicalSubject
- Outputs processed images to `<root>_keywords/` preserving directory structure
- Generates `_keyword_failures.txt` log with detailed summary

**CSV Format Support**:
- Legacy: Uses "Name" or "First Name"+"Last Name", image path in "SPA"
- Alternate: Uses "First Name"+"Last Name", filenames in "Photo Filenames" (supports multiple per row)

**File Matching Rules** (in `locate_matches()`):
- Ignores file extensions (matches by stem)
- Handles PhotoDay camera filenames (e.g., JS106537.jpg)
- Supports suffix variants (e.g., JS106537_3.jpg)
- Falls back to numeric tail matching (e.g., 6537 from JS106537)
- Handles renamed files (Last_First_6537_3.jpg format)
- Uses first name/last name validation when available

**Implementation**: `photojobs/commands/keywords.py:246`

### 2. verify
**Purpose**: Verify output files against source and check keyword presence

**Usage**:
```bash
python3 -m photojobs verify --root "/path/source" [--out "/path/output"]
```

**Default output**: `<root>_keywords` if not specified

**Status**: STUB - Not yet implemented

**Implementation**: `photojobs/commands/verify.py`

### 3. csvgen
**Purpose**: Generate derived CSV outputs and rename plan from PhotoDay subject data

**Usage**:
```bash
python3 -m photojobs csvgen --csv "/path/file.csv" --root "/path/originals" --jobname "JobName" [--team-field "Team"] [--outdir "/path/output"]
```

**Behavior**:
- Reads PhotoDay-format CSV with subject information
- Renames columns: "Last Name" → "LASTNAME", "First Name" → "FIRSTNAME", "Team" → "TEAMNAME"
- Removes columns: "Check-In Date", "Added With", "Photo Filenames", "Featured Photo"
- Adds new columns: "NAME" (First + Last), "Team File" (e.g., "TeamName.psb")
- Parses "Photo Filenames" field (supports multiple filenames per subject)
- Expands each subject into multiple rows (one per photo)
- Generates new filenames: `Last_First_Team_Number_Grade_FileNumber.ext`
- Extracts 4-digit file numbers from original filenames

**Outputs**:
- `<jobname> DATA-JPG.csv` - All subjects with .jpg extension
- `<jobname> DATA-PNG.csv` - All subjects with .png extension
- `<jobname> DATA-ALL.csv` - Combined JPG + PNG rows
- `<jobname> DATA-RENAME.txt` - Tab-delimited rename plan (original → new filename)

**Status**: Implemented but not integrated - csvgen.py has a standalone main() but no run() function for CLI integration

**Notes**:
- Currently has hardcoded job name "phsdebate25-26" in output filenames (csvgen.py:130-133)
- Can be run standalone: `python3 photojobs/commands/csvgen.py <csv> <outdir>`
- Not callable via `python3 -m photojobs csvgen` (cli.py:58 will fail - no run() function)

**Implementation**: `photojobs/commands/csvgen.py`

### 4. rename
**Purpose**: Rules-based file renaming using a plan file

**Usage**:
```bash
python3 -m photojobs rename --root "/path/source" --plan "/path/plan.txt" [--mode copy|move]
```

**Default mode**: copy (safer than move)

**Status**: STUB - Not yet implemented

**Implementation**: `photojobs/commands/rename.py`

### 5. teams
**Purpose**: Sort images into team folders based on CSV

**Usage**:
```bash
python3 -m photojobs teams --csv "/path/file.csv" --root "/path/images" [--team-field "TEAMNAME"] [--out "/path/output"]
```

**Behavior**:
- Reads CSV (typically the PNG output from csvgen)
- Groups images by person (LASTNAME + FIRSTNAME)
- For each person, identifies their FIRST image by 4-digit sequence number
- Extracts sequence from filename (last 4-digit block, ignoring any suffix after it)
- Copies first image for each person to team subfolders
- If any people have no TEAMNAME, prompts ONCE for a default team name to apply to all
- Creates team subfolders automatically in output directory

**Sequence Number Extraction**:
- Finds all 4+ digit sequences in filename
- Takes the last match and uses its last 4 digits
- Examples:
  - `Allen_Brielle_6537_3.png` → 6537
  - `Smith_John_TeamA_42_1234_5.png` → 1234
  - `Doe_Jane_9876.png` → 9876

**Default output**: `_TeamIndSorted` in the same directory as the root source folder

**Summary Output**:
- Total people in CSV
- Files successfully copied
- Teams found with player count per team
- People without team assignment (if any)
- People without photos (with expected filename)
- Errors encountered (with details)

**Implementation**: `photojobs/commands/teams.py`

## Key Technical Details

### ExifTool Integration
- **Location detection**: `find_exiftool()` checks common paths (Homebrew, system)
- **Metadata fields written**: IPTC:Keywords, XMP-dc:Subject, XMP-lr:HierarchicalSubject
- **Verification**: Reads back metadata to confirm keywords were written
- **Deduplication**: Removes duplicate keywords from XMP-dc:Subject arrays

### File Matching Algorithm
The `locate_matches()` function in `keywords.py:63` implements sophisticated file matching:

1. PhotoDay camera files (JS106537.jpg):
   - Matches full stem with suffix variants (JS106537_3.jpg)
   - Falls back to last 4 digits (6537) for renamed files

2. Renamed files (Last_First_6537_3.jpg):
   - Validates against first/last name when available
   - Matches by numeric tail embedded in stem

3. Search strategy:
   - Searches in intended directory first (from SPA path parent)
   - Falls back to recursive glob across entire root
   - Returns ALL matches (not just first)

### CSV Header Normalization
- `norm_header()` removes spaces and lowercases for flexible matching
- Supports common typos (e.g., "FIRSTNMAE" for "FIRSTNAME")

### csvgen Filename Construction
The `construct_filename()` function in `csvgen.py:14` builds output filenames:

**Format**: `Last_First_Team_Number_Grade_FileNumber.ext`

**Components** (in order):
1. LASTNAME (sanitized - alphanumeric, underscores, hyphens only)
2. FIRSTNAME (sanitized)
3. TEAMNAME (if present, sanitized)
4. NUMBER (if present, sanitized)
5. GRADE (if present, sanitized)
6. FileNumber (4-digit number extracted from original filename)

**Sanitization** (`sanitize()` in csvgen.py:5):
- Strips whitespace
- Replaces spaces with underscores
- Removes all characters except A-Z, a-z, 0-9, underscore, hyphen

**File Number Extraction** (`extract_number()` in csvgen.py:8):
- Searches for sequences of 4+ digits in original filename stem
- Takes last 4 digits from the match
- Defaults to "0000" if no number found

## Development Environment

- **Python**: Python 3.9+ (specified in pyproject.toml)
- **Dependencies**: exiftool (required external tool)
- **Platform**: macOS (hardcoded paths for temp directory)
- **Build system**: setuptools with pyproject.toml

## Project Setup

The project includes a bootstrap script for initializing the project structure:
- `bootstrap_photojobs.sh` - Creates directory structure, pyproject.toml, .gitignore, and stub files

## Presets

The `presets/` directory contains YAML configuration files for different CSV formats:

- `keywords_photoday.yml` - PhotoDay format (Photo Filenames column)
- `keywords_legacy.yml` - Legacy SPA format (SPA column)

**Note**: These preset files are currently placeholders and not actually loaded/used by the keywords command. The CSV format detection is hardcoded in `keywords.py`.

## Temp Directory
`/Users/jerry/Pictures/PhotoJobs/scripts/_Files/TempAddKeyword`

## Common Workflows

### Standard PhotoDay Workflow
```bash
# 1. Apply keywords from CSV
python3 -m photojobs keywords --csv job.csv --root ./originals --manual "Spring2024"

# 2. Verify keywords were applied (NOT YET IMPLEMENTED)
# python3 -m photojobs verify --root ./originals

# 3. Generate team assignments and rename plan (USE STANDALONE)
python3 photojobs/commands/csvgen.py job.csv ./output

# 4. Sort into team folders
python3 -m photojobs teams --csv "./output/jobname DATA-PNG.csv" --root ./images_folder
```

## Known Issues & TODOs

1. **csvgen CLI integration**: csvgen.py needs a `run(args)` function to work with the CLI router (cli.py:58)
2. **Hardcoded job names**: csvgen.py has hardcoded output filenames "phsdebate25-26" instead of using --jobname argument
3. **Stub implementations**: verify and rename commands need full implementation
4. **Hardcoded temp path**: Keywords command uses macOS-specific temp directory `/Users/jerry/Pictures/PhotoJobs/scripts/_Files/TempAddKeyword`
5. **lib/utils.py empty**: No shared utilities implemented yet
6. **Preset system not implemented**: The --preset flag is accepted but YAML preset files in `presets/` are not loaded or used. CSV format detection is hardcoded in keywords.py

## Important Notes

- Success is defined as a keyword actually being written and verified in the file
- Files are copied (not moved) by default for safety
- Output folders preserve the original directory structure
- Detailed failure logs are generated for troubleshooting
- The tool handles multiple CSV formats for backward compatibility
- Production-ready commands: `keywords`, `teams`
- The `teams` command prompts once per execution for a default team name if any people lack TEAMNAME values
