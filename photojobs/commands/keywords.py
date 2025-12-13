"""AddKeywordsOnlly.py

Usage:
    python3 AddKeywordsOnlly.py /path/to/data.csv /path/to/root_folder [manual_keyword]

Behavior:
- Reads CSV.
- Supports TWO CSV formats:

  1) Legacy format:
     - Keyword is taken from:
         a) Name
         b) If missing/empty, "First Name"/"FIRSTNMAE" + "Last Name"/"LASTNAME" (space between)
     - Image path/filename is in SPA (extension may be wrong).

  2) Alternate format:
     - Keyword is always "First Name" + "Last Name" (space between).
     - Image filenames are in "Photo Filenames" column and may contain multiple filenames.

- The script:
    - Locates matching file(s) under root_folder (ignores extension, supports suffix variants).
    - Copies files to: /Users/jerry/Pictures/PhotoJobs/scripts/_Files/TempAddKeyword
    - Adds keywords using exiftool to IPTC and XMP (XMP-dc:Subject and XMP:Subject). (EXIF:Keywords is intentionally not used because many files report it as non-writable.)
    - Writes final keyworded files into:
        <root_folder>_keywords/<same relative path as original>

Notes:
- Success is defined as a keyword actually being written to a file.
"""

import csv
import subprocess
from pathlib import Path
from typing import Optional, List
import shutil
import re

__all__ = ["run"]

TEMP_DIR = Path("/Users/jerry/Pictures/PhotoJobs/scripts/_Files/TempAddKeyword")


def find_exiftool() -> str:
    """Try a few common locations, otherwise fall back to 'exiftool' in PATH."""
    candidates = [
        "/opt/homebrew/bin/exiftool",  # Apple Silicon Homebrew
        "/usr/local/bin/exiftool",     # Intel Homebrew
        "/usr/bin/exiftool",           # system-wide
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return "exiftool"


def norm_header(s: str) -> str:
    """Normalize header names for flexible matching."""
    return "".join(s.lower().split()) if s else ""


from typing import Optional

def locate_matches(spa_value: str, root: Path, first_name: Optional[str] = None, last_name: Optional[str] = None) -> List[Path]:
    """Locate one or more files under root based on an input path/filename whose extension may be wrong.

    Matching rules (returns ALL matches, not just the first):
    - Ignore extension; match by stem.
    - First, look for exact stem matches, and stems that start with "<stem>_".
    - If none, strip trailing "_<number>" from the stem (person prefix) and look for stems that start with "<prefix>_".
      Example: SPA stem "Allen_Brielle_6537" -> prefix "Allen_Brielle" will match:
        Allen_Brielle_6537_3.jpg, Allen_Brielle_6538_3.jpg, ...
    - Search first in the intended directory (SPA parent if exists), then fallback to rglob across root.

    Returns:
      A list of matching file Paths (may be empty).
    """
    spa_value = (spa_value or "").strip()
    if not spa_value:
        return []

    spa_path = Path(spa_value)
    if not spa_path.is_absolute():
        spa_path = root / spa_path

    stem = spa_path.stem
    search_root = spa_path.parent if spa_path.parent.exists() else root

    def _norm_token(s: Optional[str]) -> str:
        s = (s or "").strip()
        return s.lower().replace(" ", "_")

    fn = _norm_token(first_name)
    ln = _norm_token(last_name)
    # Common filename formats we may need to match
    #   Last_First_####_x
    #   First_Last_####_x (rare)
    name_prefixes = []
    if fn and ln:
        name_prefixes.append(f"{ln}_{fn}_")
        name_prefixes.append(f"{fn}_{ln}_")

    def _name_ok(file_stem: str) -> bool:
        if not name_prefixes:
            return True  # if we don't have names, don't block matching
        s = (file_stem or "").lower()
        return any(s.startswith(p) for p in name_prefixes)

    def matches_for_stem_in_dir(directory: Path, target: str) -> List[Path]:
        if not directory.exists():
            return []
        found: List[Path] = []
        for f in directory.iterdir():
            if not f.is_file():
                continue
            if f.stem == target or f.stem.startswith(target + "_"):
                found.append(f)
        return sorted(found)

    def matches_for_stem_rglob(root_dir: Path, target: str) -> List[Path]:
        found: List[Path] = []
        for p in root_dir.rglob("*"):
            if not p.is_file():
                continue
            if p.stem == target or p.stem.startswith(target + "_"):
                found.append(p)
        return sorted(found)

    # ---------------------------------------------------------------------
    # PhotoDay camera filenames (e.g., JS106537.jpg)
    # We support 2 cases:
    #   A) The source folder actually contains JS106537_*.jpg variants.
    #   B) The source folder was already renamed to Last_First_6537_*.jpg.
    #      In that case we fall back to matching by the trailing numeric block
    #      (e.g., JS106537 -> 6537) and match stems containing _6537 or ending
    #      with _6537.
    # ---------------------------------------------------------------------
    m_js = re.match(r"^([A-Za-z]+)(\d+)$", stem)
    js_tail = None
    if m_js:
        # A) match files starting with the full JS stem (including suffix variants)
        found = matches_for_stem_in_dir(search_root, stem)
        if found:
            return found
        found = matches_for_stem_rglob(root, stem)
        if found:
            return found

        # B) fallback by last 4 digits of the numeric part (common mapping)
        num = m_js.group(2)
        if len(num) >= 4:
            js_tail = num[-4:]

    if js_tail:
        def matches_for_tail_in_dir(directory: Path, tail: str) -> List[Path]:
            if not directory.exists():
                return []
            hits: List[Path] = []
            for f in directory.iterdir():
                if not f.is_file():
                    continue
                # match stems like Allen_Brielle_6537_6 or Allen_Brielle_6537
                if (f.stem == tail or f.stem.endswith("_" + tail) or ("_" + tail + "_") in (f.stem + "_")) and _name_ok(f.stem):
                    hits.append(f)
            return sorted(hits)

        def matches_for_tail_rglob(root_dir: Path, tail: str) -> List[Path]:
            hits: List[Path] = []
            for p in root_dir.rglob("*"):
                if not p.is_file():
                    continue
                if (p.stem == tail or p.stem.endswith("_" + tail) or ("_" + tail + "_") in (p.stem + "_")) and _name_ok(p.stem):
                    hits.append(p)
            return sorted(hits)

        found = matches_for_tail_in_dir(search_root, js_tail)
        if found:
            return found
        found = matches_for_tail_rglob(root, js_tail)
        if found:
            return found

    def matches_for_prefix_in_dir(directory: Path, prefix: str) -> List[Path]:
        if not directory.exists():
            return []
        found: List[Path] = []
        for f in directory.iterdir():
            if not f.is_file():
                continue
            if f.stem.startswith(prefix + "_"):
                found.append(f)
        return sorted(found)

    def matches_for_prefix_rglob(root_dir: Path, prefix: str) -> List[Path]:
        found: List[Path] = []
        for p in root_dir.rglob("*"):
            if not p.is_file():
                continue
            if p.stem.startswith(prefix + "_"):
                found.append(p)
        return sorted(found)

    # 1) Exact/prefix match using the full stem in the intended directory
    found = matches_for_stem_in_dir(search_root, stem)
    if found:
        return found

    # 2) If the stem ends with _<number>, broaden to the person prefix (strip that numeric)
    prefix = None
    m = re.match(r"^(.*)_\d+$", stem)
    if m:
        prefix = m.group(1)
        found = matches_for_prefix_in_dir(search_root, prefix)
        if found:
            return found

    # 3) Fallback: rglob exact/prefix by full stem
    found = matches_for_stem_rglob(root, stem)
    if found:
        return found

    # 4) Fallback: rglob by person prefix
    if prefix:
        found = matches_for_prefix_rglob(root, prefix)
        if found:
            return found

    return []


# Helper to extract setup/camera prefix from filename stem (e.g., JS1_Allen_Brielle_6537_3 -> 'JS1')
def extract_setup_prefix(stem: str) -> Optional[str]:
    """
    Extract a leading camera/setup prefix from a filename stem.
    Example matches: JS1_Allen_Brielle_6537_3 -> 'JS1'
    Rule: leading letters + digits followed by underscore.
    """
    if not stem:
        return None
    m = re.match(r"^([A-Za-z]+\d+)_", stem)
    if m:
        return m.group(1)
    return None


# PhotoJobs CLI entrypoint for the `keywords` command.
def run(args) -> int:
    """
    PhotoJobs CLI entrypoint for the `keywords` command.
    """
    csv_path = Path(args.csv).expanduser().resolve()
    root_folder = Path(args.root).expanduser().resolve()
    manual_keyword = args.manual.strip() if getattr(args, "manual", None) else None

    preset_name = getattr(args, "preset", "photoday")
    print(f"DEBUG: Using preset     = {preset_name}")

    if not csv_path.exists():
        print(f"CSV not found: {csv_path}")
        return 1
    if not root_folder.exists():
        print(f"Root folder not found: {root_folder}")
        return 1

    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    print(f"DEBUG: Script path     = {Path(__file__).resolve()}")
    print(f"DEBUG: CSV path        = {csv_path}")
    print(f"DEBUG: Root folder     = {root_folder}")
    if manual_keyword:
        print(f"DEBUG: Manual keyword  = {manual_keyword}")

    exiftool = find_exiftool()
    print(f"DEBUG: Using exiftool  = {exiftool}")

    # Output root: "<root_folder>_keywords"
    output_root = root_folder.with_name(root_folder.name + "_keywords")
    output_root.mkdir(parents=True, exist_ok=True)

    total_rows = 0
    rows_with_success = 0
    files_attempted = 0
    files_success = 0
    missing_files = 0
    errors = 0
    skipped_no_name = 0
    failed_entries = []
    updated_files = set()

    with csv_path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []

        norm_map = {norm_header(h): h for h in fieldnames}

        has_spa = "spa" in norm_map
        has_photo_filenames = "photofilenames" in norm_map

        print(f"DEBUG: Detected headers (normalized): {sorted(list(norm_map.keys()))}")
        print(f"DEBUG: has_spa={has_spa}, has_photo_filenames={has_photo_filenames}")

        if not (has_spa or has_photo_filenames):
            print("ERROR: CSV must contain either 'SPA' or 'Photo Filenames' column.")
            print(f"Found columns: {fieldnames}")
            return 1

        def get_value(row, norm_keys):
            for nk in norm_keys:
                original = norm_map.get(nk)
                if original:
                    val = row.get(original)
                    if val is not None and str(val).strip():
                        return str(val).strip()
            return ""

        def split_filenames(value: str):
            # Supports comma/semicolon/newline/pipe-separated lists, and also whitespace-separated lists.
            if not value:
                return []
            cleaned = re.sub(r"[\r\n;|]+", ",", value)
            parts = []
            for chunk in cleaned.split(","):
                chunk = chunk.strip()
                if not chunk:
                    continue
                for token in chunk.split():
                    token = token.strip()
                    if token:
                        parts.append(token)
            return parts

        for row in reader:
            total_rows += 1

            # Get filename(s)
            photo_filenames_raw = get_value(row, ["photofilenames"]) if has_photo_filenames else ""
            spa = get_value(row, ["spa"]) if has_spa else ""

            filenames = []
            if photo_filenames_raw:
                filenames = split_filenames(photo_filenames_raw)
                if not filenames:
                    msg = f"[Row {total_rows}] Photo Filenames present but empty after parsing, skipping."
                    print(msg)
                    failed_entries.append(msg)
                    continue
            else:
                if not spa:
                    msg = f"[Row {total_rows}] No SPA/Photo Filenames value, skipping."
                    print(msg)
                    failed_entries.append(msg)
                    continue
                filenames = [spa]

            # Build the name keyword
            first = get_value(row, ["firstname", "firstnmae"])
            last = get_value(row, ["lastname"])
            name = (first + " " + last).strip() if (first or last) else ""

            if not name:
                name = get_value(row, ["name"])

            if not name:
                first2 = get_value(row, ["firstname", "firstnmae"])
                last2 = get_value(row, ["lastname"])
                name = (first2 + " " + last2).strip()

            if not name:
                skipped_no_name += 1
                msg = f"[Row {total_rows}] No Name / First+Last available for row, skipping."
                print(msg)
                failed_entries.append(msg)
                continue

            row_had_success = False

            for idx, fname in enumerate(filenames, start=1):
                matches = locate_matches(fname, root_folder, first_name=first, last_name=last)
                if not matches:
                    missing_files += 1
                    msg = f"[Row {total_rows}] Could not find any files for filename='{fname}'"
                    print(msg)
                    failed_entries.append(msg)
                    continue

                for m_idx, orig in enumerate(matches, start=1):
                    files_attempted += 1
                    try:
                        # Unique temp filename to avoid collisions across multiple matches
                        temp_file = TEMP_DIR / f"{orig.stem}__r{total_rows}_f{idx}_m{m_idx}{orig.suffix}"
                        shutil.copy2(orig, temp_file)

                        # Build the full keyword list (name keyword + optional manual keyword)
                        keywords = [name]
                        if manual_keyword:
                            keywords.append(manual_keyword)

                        cmd = [
                            exiftool,
                            "-overwrite_original",
                            "-m",      # ignore minor warnings
                            "-q", "-q", # quiet output; we rely on our own logging
                        ]

                        # IMPORTANT:
                        # PhotoDay appears to read XMP-dc:Subject reliably when it is a clean, de-duplicated array.
                        # We therefore write IPTC:Keywords and XMP-dc:Subject explicitly (and LR HierarchicalSubject for compatibility).

                        # Clear then append IPTC Keywords
                        cmd.append("-IPTC:Keywords=")
                        for kw in keywords:
                            cmd.append(f"-IPTC:Keywords+={kw}")

                        # Clear then append XMP dc:Subject (primary XMP keyword field)
                        cmd.append("-XMP-dc:Subject=")
                        for kw in keywords:
                            cmd.append(f"-XMP-dc:Subject+={kw}")

                        # Clear then append Lightroom hierarchical subject (extra compatibility)
                        cmd.append("-XMP-lr:HierarchicalSubject=")
                        for kw in keywords:
                            cmd.append(f"-XMP-lr:HierarchicalSubject+={kw}")

                        cmd.append(str(temp_file))

                        subprocess.run(cmd, check=True)

                        # Verify the keyword actually landed (success = keyword present in file)
                        verify_cmd = [
                            exiftool,
                            "-s",
                            "-s",
                            "-s",
                            "-IPTC:Keywords",
                            "-XMP-dc:Subject",
                            "-MWG:Keywords",
                            str(temp_file),
                        ]
                        v = subprocess.run(verify_cmd, capture_output=True, text=True)
                        verify_text = (v.stdout or "") + "\n" + (v.stderr or "")
                        # Normalize for a simple contains check
                        verify_text_l = verify_text.lower()
                        if name.lower() not in verify_text_l:
                            raise RuntimeError("Keyword verification failed (name not found after write).")

                        # De-duplicate XMP-dc:Subject if ExifTool shows repeated values (e.g., "Name, Name").
                        # Some files end up with duplicate list values depending on existing metadata state.
                        try:
                            jcmd = [
                                exiftool,
                                "-j",
                                "-XMP-dc:Subject",
                                str(temp_file),
                            ]
                            jr = subprocess.run(jcmd, capture_output=True, text=True)
                            import json
                            data = json.loads(jr.stdout) if jr.stdout else []
                            subj = []
                            if data and isinstance(data, list) and isinstance(data[0], dict):
                                subj = data[0].get("Subject", []) or []
                            # Normalize to list
                            if isinstance(subj, str):
                                subj_list = [subj]
                            else:
                                subj_list = list(subj)
                            # Build unique list preserving order
                            seen = set()
                            uniq = []
                            for v_ in subj_list:
                                v_ = str(v_)
                                key = v_.strip().lower()
                                if not key:
                                    continue
                                if key in seen:
                                    continue
                                seen.add(key)
                                uniq.append(v_)

                            # If duplicates detected, rewrite the list cleanly
                            if len(uniq) != len(subj_list) and uniq:
                                fix_cmd = [
                                    exiftool,
                                    "-overwrite_original",
                                    "-m",
                                    "-q", "-q",
                                    "-XMP-dc:Subject=",
                                ]
                                for v_ in uniq:
                                    fix_cmd.append(f"-XMP-dc:Subject+={v_}")
                                fix_cmd.append(str(temp_file))
                                subprocess.run(fix_cmd, check=True)
                        except Exception:
                            # Don't fail the whole run if de-dup logic has an issue
                            pass

                        rel_path = orig.relative_to(root_folder)
                        dest_path = output_root / rel_path
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(temp_file, dest_path)

                        if getattr(args, "debug", False):
                            print(f"DEBUG: Wrote metadata to temp file then copied to output. Output mtime={dest_path.stat().st_mtime}")

                        updated_files.add(str(dest_path))
                        files_success += 1
                        row_had_success = True

                        if manual_keyword:
                            print(f"[Row {total_rows}] Added keywords '{name}', '{manual_keyword}' to {dest_path}")
                        else:
                            print(f"[Row {total_rows}] Added keyword '{name}' to {dest_path}")

                    except Exception as e:
                        errors += 1
                        msg = f"[Row {total_rows}] ERROR processing {orig}: {e}"
                        print(msg)
                        failed_entries.append(msg)

            if row_had_success:
                rows_with_success += 1

    total_output_files = 0
    if output_root.exists():
        for p in output_root.rglob("*"):
            if p.is_file():
                total_output_files += 1

    files_updated = len(updated_files)

    failures_log_path = output_root / "_keyword_failures.txt"
    try:
        with failures_log_path.open("w", encoding="utf-8") as log_f:
            total_failed = len(failed_entries)
            summary_header = (
                "Summary:\n"
                f"  Total CSV rows:                 {total_rows}\n"
                f"  Rows with at least 1 file tagged:{rows_with_success}\n"
                f"  Files attempted:                {files_attempted}\n"
                f"  Files successfully keyworded:   {files_success}\n"
                f"  Distinct files keyworded:       {files_updated}\n"
                f"  Total failed entries:           {total_failed}\n"
                "\n"
            )
            log_f.write(summary_header)

            if failed_entries:
                log_f.write("Details of rows/files that did NOT get a keyword successfully:\n")
                for entry in failed_entries:
                    log_f.write(entry + "\n")
            else:
                log_f.write("All rows that were processed either added a keyword or were skipped intentionally.\n")
    except Exception as e:
        print(f"DEBUG: Could not write failures log: {e}")

    print("\n=== Summary ===")
    print(f"Total CSV rows:                        {total_rows}")
    print(f"Rows with at least 1 file tagged:       {rows_with_success}")
    print(f"Files attempted:                        {files_attempted}")
    print(f"Files successfully keyworded:           {files_success}")
    print(f"Distinct files keyworded:               {files_updated}")
    print(f"Total files in output folder:           {total_output_files}")
    print(f"Missing files (not found):              {missing_files}")
    print(f"Rows skipped (no name):                 {skipped_no_name}")
    print(f"Errors during processing:               {errors}")
    print(f"Output root:                            {output_root}")
    print(f"Failures log (with summary details):    {failures_log_path}")

    return 0