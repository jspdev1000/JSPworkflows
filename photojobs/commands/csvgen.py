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

def construct_filename(row: dict, file_number: str, ext: str) -> str:
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
    return "_".join(parts) + ext

def expand_rows(row: dict, photo_filenames: list[str]) -> list[dict]:
    output_jpg = []
    output_png = []
    for fname in photo_filenames:
        ext = Path(fname).suffix.lower()
        file_number = extract_number(Path(fname).stem)
        
        # Create JPG version
        newname_jpg = construct_filename(row, file_number, ".jpg")
        row_jpg = row.copy()
        row_jpg["FILENUMBER"] = file_number
        row_jpg["PHOTO"] = fname
        row_jpg["NEWFILENAME"] = newname_jpg
        row_jpg["SPA"] = newname_jpg
        output_jpg.append(row_jpg)
        
        # Create PNG version
        newname_png = construct_filename(row, file_number, ".png")
        row_png = row.copy()
        row_png["FILENUMBER"] = file_number
        row_png["PHOTO"] = fname
        row_png["NEWFILENAME"] = newname_png
        row_png["SPA"] = newname_png
        output_png.append(row_png)
    
    return output_jpg, output_png

def parse_filenames(raw: str) -> list[str]:
    raw = raw or ""
    cleaned = re.sub(r"[\r\n;|]+", ",", raw)
    return [f.strip() for chunk in cleaned.split(",") for f in chunk.split() if f.strip()]

def process_csv(input_csv: Path, output_dir: Path):
    all_rows = []
    jpg_rows = []
    png_rows = []

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
                elif key == "Team":
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
            expanded_jpg, expanded_png = expand_rows(renamed_row, photos)
            jpg_rows.extend(expanded_jpg)
            png_rows.extend(expanded_png)

    # Build output fieldnames
    output_fieldnames = ["SPA"]
    for fn in input_fieldnames:
        if fn == "Last Name":
            output_fieldnames.append("LASTNAME")
        elif fn == "First Name":
            output_fieldnames.append("FIRSTNAME")
        elif fn == "Team":
            output_fieldnames.append("TEAMNAME")
        elif fn not in columns_to_remove and fn not in output_fieldnames:
            output_fieldnames.append(fn)
    
    # Add new columns and processing columns
    output_fieldnames.extend(["NAME", "Team File", "FILENUMBER", "PHOTO", "NEWFILENAME"])

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

    write_csv("phsdebate25-26 DATA-JPG.csv", jpg_rows)
    write_csv("phsdebate25-26 DATA-PNG.csv", png_rows)
    write_csv("phsdebate25-26 DATA-ALL.csv", jpg_rows + png_rows)
    write_rename_txt("phsdebate25-26 DATA-RENAME.txt", jpg_rows)
    print("✅ Generated JPG, PNG, ALL CSVs and RENAME.txt with proper SPA filenames.")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate compositing CSVs from PhotoDay subject data")
    parser.add_argument("csv", help="Path to PhotoDay-format subject CSV")
    parser.add_argument("outdir", help="Output directory")
    args = parser.parse_args()

    process_csv(Path(args.csv).resolve(), Path(args.outdir).resolve())