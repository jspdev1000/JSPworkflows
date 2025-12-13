import argparse
from .commands import keywords as keywords_cmd
from .commands import verify as verify_cmd
from .commands import csvgen as csvgen_cmd
from .commands import rename as rename_cmd
from .commands import teams as teams_cmd


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
    c.add_argument("--jobname", required=True, help="Job name used in output filenames")
    c.add_argument("--team-field", default="Team", help="Column name for team")
    c.add_argument("--outdir", default="", help="Output directory (defaults to same dir as input csv)")
    c.add_argument("--batch-suffixes", default="", help="Batch suffix mappings (format: BATCH1:_suffix1,BATCH2:_suffix2)")

    # rename
    r = sub.add_parser("rename", help="Rules-based rename using a plan; default mode is copy")
    r.add_argument("--root", required=True, help="Source root folder")
    r.add_argument("--plan", required=True, help="Rename plan file (txt/csv)")
    r.add_argument("--mode", choices=["copy", "move"], default="copy", help="Rename mode")

    # teams
    t = sub.add_parser("teams", help="Sort into team folders")
    t.add_argument("--csv", required=True, help="CSV file containing team assignments")
    t.add_argument("--root", required=True, help="Root folder of images to sort (often <job>_keywords)")
    t.add_argument("--team-field", default="TEAMNAME", help="Team column name")
    t.add_argument("--out", default="", help="Output folder (defaults to _TeamIndSorted in parent dir)")

    return p


def main(argv=None) -> int:
    p = build_parser()
    args = p.parse_args(argv)

    if args.cmd == "keywords":
        return keywords_cmd.run(args)
    elif args.cmd == "verify":
        return verify_cmd.run(args)
    elif args.cmd == "csvgen":
        return csvgen_cmd.run(args)
    elif args.cmd == "rename":
        return rename_cmd.run(args)
    elif args.cmd == "teams":
        return teams_cmd.run(args)

    p.error("Unknown command")
    return 2