import csv
import re
from pathlib import Path

def sanitize(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "", value.strip().replace(" ", "_"))

def extract_number(stem: str) -> str:
    match = re.search(r"(\d{4,})", stem)
    if match:
        return match.group(1)[-4:]  # Get last 4 digits
    return "0000"

def extract_batch_prefix(filename: str) -> str:
    """Extract batch prefix from PhotoDay camera filename.

    Examples:
        JS101234.jpg -> JS10
        JS201234.jpg -> JS20
        ABC101234.jpg -> ABC10
        renamed_file.jpg -> UNKNOWN

    Returns:
        Batch prefix string or "UNKNOWN" if pattern not found
    """
    stem = Path(filename).stem
    # Look for pattern: letters followed by digits
    # Extract everything up to and including first 2 digits after letters
    match = re.match(r"^([A-Za-z]+)(\d{2})", stem)
    if match:
        return match.group(1) + match.group(2)  # e.g., "JS10"
    return "UNKNOWN"

def construct_filename(row: dict, file_number: str, ext: str, batch_suffix: str = "") -> str:
    last = sanitize(row.get("LASTNAME", ""))
    first = sanitize(row.get("FIRSTNAME", ""))
    team = sanitize(row.get("TEAMNAME", ""))
    grade = sanitize(row.get("GRADE", ""))
    number = sanitize(row.get("NUMBER", ""))

    parts = [last, first]
    if team:
        parts.append(team)
    if number:
        parts.append(number)
    if grade:
        parts.append(grade)
    parts.append(file_number)

    basename = "_".join(parts)
    if batch_suffix:
        return basename + batch_suffix + ext
    return basename + ext

def expand_rows(row: dict, photo_filenames: list[str], batch_suffix_map: dict = None) -> list[dict]:
    output_jpg = []
    output_png = []
    batch_suffix_map = batch_suffix_map or {}

    for fname in photo_filenames:
        ext = Path(fname).suffix.lower()
        file_number = extract_number(Path(fname).stem)
        batch_prefix = extract_batch_prefix(fname)

        # Get suffix for this batch (if any)
        batch_suffix = batch_suffix_map.get(batch_prefix, "")

        # Create JPG version
        newname_jpg = construct_filename(row, file_number, ".jpg", batch_suffix)
        row_jpg = row.copy()
        row_jpg["FILENUMBER"] = file_number
        row_jpg["BATCH"] = batch_prefix
        row_jpg["PHOTO"] = fname
        row_jpg["NEWFILENAME"] = newname_jpg
        row_jpg["SPA"] = newname_jpg
        output_jpg.append(row_jpg)

        # Create PNG version
        newname_png = construct_filename(row, file_number, ".png", batch_suffix)
        row_png = row.copy()
        row_png["FILENUMBER"] = file_number
        row_png["BATCH"] = batch_prefix
        row_png["PHOTO"] = fname
        row_png["NEWFILENAME"] = newname_png
        row_png["SPA"] = newname_png
        output_png.append(row_png)

    return output_jpg, output_png

def parse_filenames(raw: str) -> list[str]:
    raw = raw or ""
    cleaned = re.sub(r"[\r\n;|]+", ",", raw)
    return [f.strip() for chunk in cleaned.split(",") for f in chunk.split() if f.strip()]

def process_csv(input_csv: Path, output_dir: Path, jobname: str = "phsdebate25-26", team_field: str = "Team", batch_suffix_map: dict = None):
    all_rows = []
    jpg_rows = []
    png_rows = []
    batch_suffix_map = batch_suffix_map or {}

    with input_csv.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        input_fieldnames = reader.fieldnames or []

        # Columns to remove
        columns_to_remove = {"Check-In Date", "Added With", "Photo Filenames", "Featured Photo"}

        for row in reader:
            # Rename headers by creating new keys
            renamed_row = {}
            for key, value in row.items():
                if key == "Last Name":
                    renamed_row["LASTNAME"] = value
                elif key == "First Name":
                    renamed_row["FIRSTNAME"] = value
                elif key == team_field:
                    renamed_row["TEAMNAME"] = value
                elif key not in columns_to_remove:
                    renamed_row[key] = value

            # Add new columns
            firstname = renamed_row.get("FIRSTNAME", "")
            lastname = renamed_row.get("LASTNAME", "")
            renamed_row["NAME"] = f"{firstname} {lastname}".strip()

            teamname = renamed_row.get("TEAMNAME", "")
            renamed_row["Team File"] = f"{teamname}.psb" if teamname else ""

            photos = parse_filenames(row.get("Photo Filenames", ""))
            expanded_jpg, expanded_png = expand_rows(renamed_row, photos, batch_suffix_map)
            jpg_rows.extend(expanded_jpg)
            png_rows.extend(expanded_png)

    # Build output fieldnames
    output_fieldnames = ["SPA"]
    for fn in input_fieldnames:
        if fn == "Last Name":
            output_fieldnames.append("LASTNAME")
        elif fn == "First Name":
            output_fieldnames.append("FIRSTNAME")
        elif fn == team_field:
            output_fieldnames.append("TEAMNAME")
        elif fn not in columns_to_remove and fn not in output_fieldnames:
            output_fieldnames.append(fn)

    # Add new columns and processing columns
    output_fieldnames.extend(["NAME", "Team File", "FILENUMBER", "BATCH", "PHOTO", "NEWFILENAME"])

    def write_csv(name: str, rows: list):
        rows.sort(key=lambda r: r.get("SPA", ""))
        with (output_dir / name).open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=output_fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def write_rename_txt(name: str, rows: list):
        rows.sort(key=lambda r: r.get("SPA", ""))
        with (output_dir / name).open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter="\t")
            for row in rows:
                writer.writerow([row.get("PHOTO", ""), row.get("SPA", "")])

    write_csv(f"{jobname} DATA-JPG.csv", jpg_rows)
    write_csv(f"{jobname} DATA-PNG.csv", png_rows)
    write_csv(f"{jobname} DATA-ALL.csv", jpg_rows + png_rows)
    write_rename_txt(f"{jobname} DATA-RENAME.txt", jpg_rows)
    print(f"✅ Generated {jobname} DATA-JPG.csv, DATA-PNG.csv, DATA-ALL.csv and DATA-RENAME.txt with proper SPA filenames.")
    print(f"   Output directory: {output_dir}")

    # Report batch detection
    batches_found = set(row.get("BATCH", "UNKNOWN") for row in jpg_rows)
    if len(batches_found) > 1:
        print(f"\n📸 Multiple image batches detected: {', '.join(sorted(batches_found))}")
        for batch in sorted(batches_found):
            count = sum(1 for row in jpg_rows if row.get("BATCH") == batch)
            suffix_info = f" (suffix: {batch_suffix_map[batch]})" if batch in batch_suffix_map and batch_suffix_map[batch] else ""
            print(f"   {batch}: {count} images{suffix_info}")
        if batch_suffix_map:
            print(f"   Batch suffixes applied to filenames")
    elif len(batches_found) == 1:
        batch = list(batches_found)[0]
        if batch != "UNKNOWN":
            suffix_info = f" (suffix: {batch_suffix_map[batch]})" if batch in batch_suffix_map and batch_suffix_map[batch] else ""
            print(f"\n📸 Single image batch detected: {batch}{suffix_info}")


def run(args) -> int:
    """PhotoJobs CLI entrypoint for the csvgen command."""
    csv_path = Path(args.csv).expanduser().resolve()
    jobname = args.jobname
    team_field = args.team_field or "Team"
    batch_suffixes_str = args.batch_suffixes or ""

    # Parse batch suffixes (format: "BATCH1:_suffix1,BATCH2:_suffix2")
    batch_suffix_map = {}
    if batch_suffixes_str:
        for pair in batch_suffixes_str.split(","):
            pair = pair.strip()
            if ":" in pair:
                batch, suffix = pair.split(":", 1)
                batch_suffix_map[batch.strip()] = suffix.strip()

    # Determine output directory
    if args.outdir:
        output_dir = Path(args.outdir).expanduser().resolve()
    else:
        output_dir = csv_path.parent

    # Validate inputs
    if not csv_path.exists():
        print(f"ERROR: CSV file not found: {csv_path}")
        return 1

    # Create output directory if needed
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Processing CSV: {csv_path}")
    print(f"Job name: {jobname}")
    print(f"Team field: {team_field}")
    if batch_suffix_map:
        print(f"Batch suffixes: {batch_suffix_map}")
    print(f"Output directory: {output_dir}")
    print()

    # Process the CSV
    process_csv(csv_path, output_dir, jobname, team_field, batch_suffix_map)

    return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate compositing CSVs from PhotoDay subject data")
    parser.add_argument("csv", help="Path to PhotoDay-format subject CSV")
    parser.add_argument("outdir", help="Output directory")
    args = parser.parse_args()

    process_csv(Path(args.csv).resolve(), Path(args.outdir).resolve())