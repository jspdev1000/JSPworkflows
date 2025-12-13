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
| csvgen | ✅ Fully implemented | Generates derived CSV outputs and rename plans |
| rename | ✅ Fully implemented | CSV-based file renaming with one-to-many support |
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
python3 -m photojobs csvgen --csv "/path/file.csv" --jobname "JobName" [--team-field "Team"] [--outdir "/path/output"]
```

**Behavior**:
- Reads PhotoDay-format CSV with subject information (pure data processing - no image files needed)
- Renames columns: "Last Name" → "LASTNAME", "First Name" → "FIRSTNAME", team field → "TEAMNAME"
- Removes columns: "Check-In Date", "Added With", "Photo Filenames", "Featured Photo"
- Adds new columns: "NAME" (First + Last), "Team File" (e.g., "TeamName.psb")
- Parses "Photo Filenames" field (supports multiple filenames per subject)
- Expands each subject into multiple rows (one per photo)
- Generates new filenames: `Last_First_Team_Number_Grade_FileNumber.ext`
- Extracts 4-digit file numbers from original filenames

**Outputs**:
- `<jobname> DATA-JPG.csv` - All subjects with .jpg extension (includes PHOTO and NEWFILENAME columns for rename command)
- `<jobname> DATA-PNG.csv` - All subjects with .png extension (includes TEAMNAME column for teams command)
- `<jobname> DATA-ALL.csv` - Combined JPG + PNG rows
- `<jobname> DATA-RENAME.txt` - Tab-delimited rename plan (original → new filename) - legacy format

**Default output**: Same directory as input CSV (unless `--outdir` specified)

**Notes**:
- Can still be run standalone: `python3 photojobs/commands/csvgen.py <csv> <outdir>`
- Team field name is configurable via `--team-field` (defaults to "Team")

**Implementation**: `photojobs/commands/csvgen.py`

### 4. rename
**Purpose**: Apply systematic file renaming using a CSV plan

**Usage**:
```bash
python3 -m photojobs rename --root "/path/source" --plan "/path/DATA-JPG.csv" [--mode copy|move]
```

**Behavior**:
- Reads CSV with PHOTO (source filename) and NEWFILENAME (destination filename) columns
- Finds source files in root directory (matches by stem, ignores extension)
- Supports one-to-many mapping: one source file can be copied to multiple destinations
- Copies or moves files to output directory with new names
- Preserves file extension from source file
- Default mode is copy (safer than move)
- Output directory: `<root>_renamed`

**File Matching**:
- Matches files by stem (ignoring extension)
- Tries exact match first with common extensions (.jpg, .JPG, .jpeg, .JPEG, .png, .PNG)
- Falls back to recursive search if exact match not found
- Uses cache to avoid repeated searches for same source file

**One-to-Many Support**:
- A single source file can map to multiple destination filenames in the CSV
- All destinations are copied from the same source
- In move mode, only the last destination actually moves the file (others are copied)
- Shows progress with "(1/3)", "(2/3)", etc. for multiple destinations

**Summary Output**:
- Total unique source files
- Total destination files (may exceed source count due to one-to-many)
- Successfully processed files
- Missing source files (with list)
- Errors encountered (with details)

**Default mode**: copy (safer than move)

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
- **For each person, checks which files actually exist in the source folder**
- **Identifies FIRST image from existing files by 4-digit sequence number**
- Extracts sequence from filename (last 4-digit block, ignoring any suffix after it)
- Copies first image for each person to team subfolders
- If any people have no TEAMNAME, prompts ONCE for a default team name to apply to all
- Creates team subfolders automatically in output directory
- **Key: Determines first photo based on actual folder contents, not CSV order**

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

### Standard PhotoDay Workflow (Manual)
```bash
# 1. Apply keywords from CSV
python3 -m photojobs keywords --csv job.csv --root ./originals --manual "Spring2024"

# 2. Verify keywords were applied (NOT YET IMPLEMENTED)
# python3 -m photojobs verify --root ./originals

# 3. Generate team assignments and rename plan
python3 -m photojobs csvgen --csv job.csv --jobname "MyJob2025"

# 4. Rename files using the JPG CSV
python3 -m photojobs rename --root ./originals_keywords --plan "MyJob2025 DATA-JPG.csv" --mode copy

# 5. Sort into team folders using the PNG CSV
python3 -m photojobs teams --csv "MyJob2025 DATA-PNG.csv" --root ./originals_keywords_renamed
```

### "Run All" Automated Workflow (AppleScript Launcher)

The AppleScript launcher includes a "Run All" option that automates the complete workflow:

**Sequence**:
1. **Keywords**: Apply keywords to originals → `<root>_keywords/`
2. **Csvgen**: Generate JPG/PNG CSVs and rename plan
3. **Rename**: Use JPG CSV to rename `<root>_keywords/` → `<root>_keywords_renamed/`
4. **Teams**: Use PNG CSV to sort `<root>_keywords_renamed/` → `_TeamIndSorted/`

**Features**:
- Single initial prompt for CSV, root folder, and manual keyword
- Automatically derives all intermediate paths and filenames
- Progress indicator shows 4 steps with current step
- Detects preset from CSV headers (photoday vs legacy)
- Handles team assignment prompts if needed
- Final summary shows all output locations

**Output locations**:
- Keywords output: `<root>_keywords/`
- Renamed files: `<root>_keywords_renamed/`
- CSV files: Same directory as input CSV
- Team folders: `_TeamIndSorted/` (in parent of root folder)

## Known Issues & TODOs

1. **Stub implementation**: verify command needs full implementation
2. **Hardcoded temp path**: Keywords command uses macOS-specific temp directory `/Users/jerry/Pictures/PhotoJobs/scripts/_Files/TempAddKeyword`
3. **lib/utils.py empty**: No shared utilities implemented yet
4. **Preset system not implemented**: The --preset flag is accepted but YAML preset files in `presets/` are not loaded or used. CSV format detection is hardcoded in keywords.py

## Important Notes

- Success is defined as a keyword actually being written and verified in the file
- Files are copied (not moved) by default for safety
- Output folders preserve the original directory structure
- Detailed failure logs are generated for troubleshooting
- The tool handles multiple CSV formats for backward compatibility
- Production-ready commands: `keywords`, `csvgen`, `rename`, `teams`
- The `teams` command prompts once per execution for a default team name if any people lack TEAMNAME values
- The `csvgen` command is pure data processing - no image files needed
- The AppleScript launcher provides both individual command access and a "Run All" automated workflow
