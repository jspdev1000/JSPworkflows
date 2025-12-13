"""Teams command - Sort images into team folders.

Usage:
    python3 -m photojobs teams --csv DATA-PNG.csv --root /path/to/images [--team-field TEAMNAME] [--out /path/output]

Behavior:
- Reads CSV (typically the PNG output from csvgen)
- For each person, finds their FIRST image by 4-digit sequence number
- Copies first image for each person to team subfolders
- Prompts for team name if any records have no TEAMNAME
"""

import csv
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Set
from collections import defaultdict

__all__ = ["run"]


def extract_sequence_number(filename: str) -> Optional[str]:
    """Extract the last 4-digit sequence from a filename, ignoring any suffix after it.

    Examples:
        Allen_Brielle_6537_3.png -> 6537
        Smith_John_TeamA_42_1234_5.png -> 1234
        Doe_Jane_9876.png -> 9876

    Returns:
        4-digit string or None if no 4+ digit sequence found
    """
    stem = Path(filename).stem
    # Find all sequences of 4 or more digits
    matches = re.findall(r'\d{4,}', stem)
    if not matches:
        return None
    # Take the last match and get its last 4 digits
    return matches[-1][-4:]


def find_image_file(root: Path, filename: str, debug: bool = False) -> Optional[Path]:
    """Locate an image file in the root directory, matching by stem (ignoring extension).

    Args:
        root: Root directory to search
        filename: Filename to search for (can be with or without extension)
        debug: Enable debug output

    Returns:
        Path to found file or None
    """
    search_stem = Path(filename).stem

    if debug:
        print(f"  DEBUG: Searching for stem '{search_stem}' in {root}")

    # Try exact match first (with common extensions)
    for ext in ['.png', '.PNG', '.jpg', '.JPG', '.jpeg', '.JPEG']:
        candidate = root / f"{search_stem}{ext}"
        if candidate.exists() and candidate.is_file():
            if debug:
                print(f"  DEBUG: Found exact match: {candidate}")
            return candidate

    # Fallback: search recursively
    if debug:
        print(f"  DEBUG: No exact match, searching recursively...")
    for p in root.rglob("*"):
        if p.is_file() and p.stem == search_stem:
            if debug:
                print(f"  DEBUG: Found via rglob: {p}")
            return p

    if debug:
        print(f"  DEBUG: No file found for stem '{search_stem}'")
    return None


def prompt_default_team_name() -> str:
    """Prompt user once for a default team name to apply to all people without one.

    Returns:
        Team name entered by user
    """
    while True:
        team = input("Enter default team name for all people without a team: ").strip()
        if team:
            return team
        print("Team name cannot be empty. Please try again.")


def run(args) -> int:
    """PhotoJobs CLI entrypoint for the teams command."""
    csv_path = Path(args.csv).expanduser().resolve()
    root_folder = Path(args.root).expanduser().resolve()
    team_field = args.team_field or "TEAMNAME"

    # Default output: _TeamIndSorted in the same directory as root_folder
    if args.out:
        output_root = Path(args.out).expanduser().resolve()
    else:
        output_root = root_folder.parent / "_TeamIndSorted"

    if not csv_path.exists():
        print(f"ERROR: CSV not found: {csv_path}")
        return 1

    if not root_folder.exists():
        print(f"ERROR: Root folder not found: {root_folder}")
        return 1

    print(f"DEBUG: Reading CSV: {csv_path}")
    print(f"DEBUG: Source images: {root_folder}")
    print(f"DEBUG: Output folder: {output_root}")
    print(f"DEBUG: Team field: {team_field}")
    print()

    # Read CSV and group by person (identified by LASTNAME + FIRSTNAME)
    # Track all images per person, then sort to find first by sequence number
    person_images: Dict[str, List[Dict]] = defaultdict(list)
    rows_without_team: List[Dict] = []

    with csv_path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []

        # Verify required fields
        if team_field not in fieldnames:
            print(f"ERROR: Team field '{team_field}' not found in CSV.")
            print(f"Available fields: {', '.join(fieldnames)}")
            return 1

        required_fields = ["LASTNAME", "FIRSTNAME", "SPA"]
        missing = [f for f in required_fields if f not in fieldnames]
        if missing:
            print(f"ERROR: Missing required fields: {', '.join(missing)}")
            print(f"Available fields: {', '.join(fieldnames)}")
            return 1

        row_index = 0
        rows_read = 0
        for row in reader:
            row_index += 1
            rows_read += 1
            lastname = (row.get("LASTNAME") or "").strip()
            firstname = (row.get("FIRSTNAME") or "").strip()
            spa = (row.get("SPA") or "").strip()
            teamname = (row.get(team_field) or "").strip()

            # Debug first few rows
            if row_index <= 3:
                print(f"DEBUG: Row {row_index}: {lastname=}, {firstname=}, {spa=}, {teamname=}")

            if not lastname or not firstname:
                print(f"WARNING: Row {row_index} missing name, skipping")
                continue

            if not spa:
                print(f"WARNING: Row {row_index} missing SPA filename, skipping")
                continue

            # Extract sequence number
            seq_num = extract_sequence_number(spa)
            if not seq_num:
                print(f"WARNING: Row {row_index} - could not extract sequence number from '{spa}', skipping")
                continue

            person_key = f"{lastname}|{firstname}"

            # Store row data with sequence number
            row_data = {
                "lastname": lastname,
                "firstname": firstname,
                "spa": spa,
                "teamname": teamname,
                "sequence": seq_num,
                "row_index": row_index,
                "original_row": row
            }

            person_images[person_key].append(row_data)

            # Track rows without team
            if not teamname:
                rows_without_team.append(row_data)

        print(f"DEBUG: Total rows read from CSV: {rows_read}")
        print(f"DEBUG: CSV fieldnames: {fieldnames}")
        print()

    if not person_images:
        print("ERROR: No valid person records found in CSV")
        return 1

    print(f"Found {len(person_images)} unique people")
    print()

    # Handle missing team names
    persons_needing_team: Set[str] = set()
    if rows_without_team:
        print(f"WARNING: Found {len(rows_without_team)} records without a team name")
        print()

        # Group by person to show who needs a team
        for row_data in rows_without_team:
            person_key = f"{row_data['lastname']}|{row_data['firstname']}"
            persons_needing_team.add(person_key)

        print(f"The following {len(persons_needing_team)} people do not have a team assigned:")
        for person_key in sorted(persons_needing_team):
            lastname, firstname = person_key.split("|")
            print(f"  - {firstname} {lastname}")
        print()

        # Prompt ONCE for a default team name to apply to all
        default_team_name = prompt_default_team_name()
        print(f"DEBUG: User entered team name: '{default_team_name}'")
        print(f"Assigning '{default_team_name}' to all people without a team.")
        print()

        # Apply default team name to all people without one
        for person_key, images in person_images.items():
            for img_data in images:
                if not img_data['teamname']:
                    img_data['teamname'] = default_team_name
                    print(f"DEBUG: Assigned '{default_team_name}' to {person_key}")

    # Create output directory
    output_root.mkdir(parents=True, exist_ok=True)
    print(f"DEBUG: Created output directory: {output_root}")
    print()

    # Process each person: find first image and copy to team folder
    total_people = 0
    total_copied = 0
    missing_files = 0
    errors = 0
    team_stats: Dict[str, int] = defaultdict(int)
    people_without_photos: List[str] = []
    error_details: List[str] = []
    people_without_team_count = len(persons_needing_team)

    for person_key, images in person_images.items():
        total_people += 1
        lastname, firstname = person_key.split("|")
        person_name = f"{firstname} {lastname}"

        # Debug first 3 people
        debug_mode = (total_people <= 3)
        if debug_mode:
            print(f"DEBUG: Processing person {total_people}: {person_name}")
            print(f"  Total CSV records for this person: {len(images)}")

        # Find which files actually exist in the folder
        existing_files = []
        for img_data in images:
            spa_filename = img_data['spa']
            source_file = find_image_file(root_folder, spa_filename, debug=debug_mode)
            if source_file:
                existing_files.append({
                    'path': source_file,
                    'sequence': img_data['sequence'],
                    'teamname': img_data['teamname'],
                    'spa': spa_filename
                })
                if debug_mode:
                    print(f"  Found existing file: {spa_filename} (seq: {img_data['sequence']})")
            else:
                if debug_mode:
                    print(f"  File not found: {spa_filename}")

        # If no files exist for this person, skip
        if not existing_files:
            missing_files += 1
            expected_list = ', '.join([img['spa'] for img in images[:3]])  # Show first 3
            if len(images) > 3:
                expected_list += f" ... ({len(images)} total)"
            people_without_photos.append(f"{person_name} (expected: {expected_list})")
            print(f"WARNING: No files found for {person_name} (checked {len(images)} CSV records)")
            continue

        # Sort existing files by sequence number and pick the first
        existing_files_sorted = sorted(existing_files, key=lambda x: x['sequence'])
        first_file = existing_files_sorted[0]

        source_file = first_file['path']
        teamname = first_file['teamname']

        if debug_mode:
            print(f"  Selected first file: {first_file['spa']} (seq: {first_file['sequence']})")
            print(f"  Team: {teamname}")

        # Create team subfolder
        team_folder = output_root / teamname
        team_folder.mkdir(parents=True, exist_ok=True)

        # Copy file
        dest_file = team_folder / source_file.name

        try:
            shutil.copy2(source_file, dest_file)
            total_copied += 1
            team_stats[teamname] += 1
            print(f"Copied: {person_name} ({first_file['sequence']}) -> {teamname}/{source_file.name}")
        except Exception as e:
            errors += 1
            error_msg = f"{person_name}: {e}"
            error_details.append(error_msg)
            print(f"ERROR: Failed to copy {source_file} for {person_name}: {e}")

    # Summary
    print()
    print("=== Summary ===")
    print(f"Total people in CSV:        {total_people}")
    print(f"Files successfully copied:  {total_copied}")
    print()

    # Teams breakdown
    print(f"Teams found: {len(team_stats)}")
    for team in sorted(team_stats.keys()):
        print(f"  {team}: {team_stats[team]} player(s)")
    print()

    # People without team assignment
    if people_without_team_count > 0:
        print(f"People without team assignment: {people_without_team_count}")
        print("  (assigned to default team during execution)")
        print()

    # Missing photos
    if missing_files > 0:
        print(f"People without photos: {missing_files}")
        for person_info in people_without_photos:
            print(f"  - {person_info}")
        print()

    # Errors
    if errors > 0:
        print(f"Errors encountered: {errors}")
        for error_msg in error_details:
            print(f"  - {error_msg}")
        print()

    print(f"Output folder: {output_root}")

    return 0
