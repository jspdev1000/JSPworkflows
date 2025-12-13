"""Rename command - Apply systematic file renaming using a plan file.

Usage:
    python3 -m photojobs rename --root /path/to/source --plan /path/to/plan.txt [--mode copy|move]

Behavior:
- Reads tab-delimited rename plan (old_name -> new_name)
- Finds source files in root directory (matches by stem, ignores extension)
- Copies or moves files to output directory with new names
- Default mode is copy (safer than move)
- Output directory: <root>_renamed
"""

import csv
import shutil
from pathlib import Path
from typing import Dict, List, Optional

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
    print(f"DEBUG: Rename plan: {plan_file}")
    print(f"DEBUG: Output folder: {output_root}")
    print(f"DEBUG: Mode: {mode}")
    print()

    # Read rename plan
    rename_plan: List[tuple[str, str]] = []
    with plan_file.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if len(row) >= 2:
                old_name = row[0].strip()
                new_name = row[1].strip()
                if old_name and new_name:
                    rename_plan.append((old_name, new_name))

    if not rename_plan:
        print("ERROR: No valid rename entries found in plan file")
        return 1

    print(f"Loaded {len(rename_plan)} rename operations from plan")
    print()

    # Create output directory
    output_root.mkdir(parents=True, exist_ok=True)
    print(f"Created output directory: {output_root}")
    print()

    # Process renames
    total_operations = 0
    successful = 0
    missing_files = 0
    errors = 0
    missing_list: List[str] = []
    error_list: List[str] = []

    for idx, (old_name, new_name) in enumerate(rename_plan, start=1):
        total_operations += 1
        debug_mode = (idx <= 3)  # Debug first 3

        if debug_mode:
            print(f"DEBUG: Operation {idx}: {old_name} -> {new_name}")

        # Find source file
        source_file = find_source_file(root_folder, old_name, debug=debug_mode)

        if not source_file:
            missing_files += 1
            missing_list.append(old_name)
            print(f"WARNING: Source file not found: {old_name}")
            continue

        # Determine destination
        # Preserve the extension from the source file
        new_name_path = Path(new_name)
        new_name_with_ext = new_name_path.stem + source_file.suffix
        dest_file = output_root / new_name_with_ext

        # Perform operation
        try:
            if mode == "move":
                shutil.move(str(source_file), str(dest_file))
                action = "Moved"
            else:  # copy
                shutil.copy2(source_file, dest_file)
                action = "Copied"

            successful += 1
            if idx <= 10 or (idx % 100 == 0):  # Show first 10, then every 100th
                print(f"{action}: {source_file.name} -> {new_name_with_ext}")

        except Exception as e:
            errors += 1
            error_msg = f"{old_name}: {e}"
            error_list.append(error_msg)
            print(f"ERROR: Failed to {mode} {old_name}: {e}")

    # Summary
    print()
    print("=== Summary ===")
    print(f"Total operations in plan:   {total_operations}")
    print(f"Successfully {mode}d:        {successful}")
    print()

    if missing_files > 0:
        print(f"Missing source files: {missing_files}")
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
