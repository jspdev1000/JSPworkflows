"""Rename command - Apply systematic file renaming using a CSV plan.

Usage:
    python3 -m photojobs rename --root /path/to/source --plan /path/to/DATA-JPG.csv [--mode copy|move]

Behavior:
- Reads CSV with PHOTO (source) and NEWFILENAME (destination) columns
- Finds source files in root directory (matches by stem, ignores extension)
- Supports one-to-many: one source file can be copied to multiple destinations
- Copies or moves files to output directory with new names
- Default mode is copy (safer than move)
- Output directory: <root>_renamed
"""

import csv
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict

__all__ = ["run"]


def find_source_file(root: Path, filename: str, debug: bool = False) -> Optional[Path]:
    """Locate a source file by stem (ignoring extension).

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
    for ext in ['.jpg', '.JPG', '.jpeg', '.JPEG', '.png', '.PNG']:
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


def run(args) -> int:
    """PhotoJobs CLI entrypoint for the rename command."""
    root_folder = Path(args.root).expanduser().resolve()
    plan_file = Path(args.plan).expanduser().resolve()
    mode = args.mode or "copy"

    # Default output: <root>_renamed
    output_root = root_folder.parent / f"{root_folder.name}_renamed"

    # Validate inputs
    if not root_folder.exists():
        print(f"ERROR: Root folder not found: {root_folder}")
        return 1

    if not plan_file.exists():
        print(f"ERROR: Plan file not found: {plan_file}")
        return 1

    print(f"DEBUG: Source root: {root_folder}")
    print(f"DEBUG: Rename plan CSV: {plan_file}")
    print(f"DEBUG: Output folder: {output_root}")
    print(f"DEBUG: Mode: {mode}")
    print()

    # Read CSV and build rename map (one source -> multiple destinations)
    # Key: PHOTO (source filename), Value: list of NEWFILENAME (destination filenames)
    rename_map: Dict[str, List[str]] = defaultdict(list)

    with plan_file.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []

        # Verify required columns
        if "PHOTO" not in fieldnames or "NEWFILENAME" not in fieldnames:
            print(f"ERROR: CSV must contain 'PHOTO' and 'NEWFILENAME' columns")
            print(f"Available columns: {', '.join(fieldnames)}")
            return 1

        for row in reader:
            photo = (row.get("PHOTO") or "").strip()
            newfilename = (row.get("NEWFILENAME") or "").strip()

            if photo and newfilename:
                rename_map[photo].append(newfilename)

    if not rename_map:
        print("ERROR: No valid rename entries found in CSV")
        return 1

    # Count total operations (sum of all destination files)
    total_dest_files = sum(len(destinations) for destinations in rename_map.values())
    unique_sources = len(rename_map)

    print(f"Loaded rename plan:")
    print(f"  Unique source files: {unique_sources}")
    print(f"  Total destination files: {total_dest_files}")
    print(f"  One-to-many mappings: {sum(1 for dests in rename_map.values() if len(dests) > 1)}")
    print()

    # Create output directory
    output_root.mkdir(parents=True, exist_ok=True)
    print(f"Created output directory: {output_root}")
    print()

    # Process renames
    total_operations = 0
    successful = 0
    missing_sources = 0
    errors = 0
    missing_list: List[str] = []
    error_list: List[str] = []

    # Cache for found source files (to avoid repeated searches)
    source_file_cache: Dict[str, Optional[Path]] = {}

    for source_idx, (source_name, dest_names) in enumerate(rename_map.items(), start=1):
        debug_mode = (source_idx <= 3)  # Debug first 3 sources

        if debug_mode:
            print(f"DEBUG: Source {source_idx}: {source_name} -> {len(dest_names)} destination(s)")

        # Find source file (use cache if already found)
        if source_name not in source_file_cache:
            source_file_cache[source_name] = find_source_file(root_folder, source_name, debug=debug_mode)

        source_file = source_file_cache[source_name]

        if not source_file:
            missing_sources += 1
            missing_list.append(source_name)
            print(f"WARNING: Source file not found: {source_name}")
            # Skip all destinations for this source
            total_operations += len(dest_names)
            continue

        # Process each destination for this source
        for dest_idx, dest_name in enumerate(dest_names, start=1):
            total_operations += 1

            # Preserve the extension from the source file
            dest_name_path = Path(dest_name)
            dest_name_with_ext = dest_name_path.stem + source_file.suffix
            dest_file = output_root / dest_name_with_ext

            # Perform operation
            try:
                # Always copy (even in move mode) for one-to-many
                # Only the last destination in move mode should actually move
                if mode == "move" and dest_idx == len(dest_names):
                    shutil.move(str(source_file), str(dest_file))
                    action = "Moved"
                else:
                    shutil.copy2(source_file, dest_file)
                    action = "Copied"

                successful += 1
                if source_idx <= 5 or (total_operations % 100 == 0):  # Show first 5 sources, then every 100th
                    if len(dest_names) > 1:
                        print(f"{action}: {source_file.name} -> {dest_name_with_ext} ({dest_idx}/{len(dest_names)})")
                    else:
                        print(f"{action}: {source_file.name} -> {dest_name_with_ext}")

            except Exception as e:
                errors += 1
                error_msg = f"{source_name} -> {dest_name}: {e}"
                error_list.append(error_msg)
                print(f"ERROR: Failed to {mode} {source_name} to {dest_name}: {e}")

    # Summary
    print()
    print("=== Summary ===")
    print(f"Total source files:         {unique_sources}")
    print(f"Total destination files:    {total_dest_files}")
    print(f"Successfully processed:     {successful}")
    print()

    if missing_sources > 0:
        print(f"Missing source files: {missing_sources}")
        for filename in missing_list[:10]:  # Show first 10
            print(f"  - {filename}")
        if len(missing_list) > 10:
            print(f"  ... and {len(missing_list) - 10} more")
        print()

    if errors > 0:
        print(f"Errors encountered: {errors}")
        for error_msg in error_list[:10]:  # Show first 10
            print(f"  - {error_msg}")
        if len(error_list) > 10:
            print(f"  ... and {len(error_list) - 10} more")
        print()

    print(f"Output folder: {output_root}")

    return 0
