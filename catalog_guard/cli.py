"""Command line interface and safe standalone HTML report."""
import argparse
import csv
import html
import json
import sys
from datetime import date
from pathlib import Path
from . import __version__
from .core import InputError, analyze, load_rows, read_json


def render_html(report):
    payload = html.escape(json.dumps(report, ensure_ascii=False, indent=2))
    return ('<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Catalog Guard report</title><style>'
            'body{font:16px system-ui;background:#f4f7fb;color:#192739;max-width:960px;margin:40px auto;padding:24px}'
            'h1{font-size:36px}pre{background:white;padding:24px;border-radius:12px;white-space:pre-wrap;overflow-wrap:anywhere}'
            '</style><h1>Catalog Guard</h1>'
            f'<p>{report["records"]} records · {report["errors"]} errors · {report["warnings"]} warnings</p>'
            '<p>Offline structural checks. A passing report does not prove real-world accuracy.</p>'
            f'<pre>{payload}</pre></html>')


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline CSV/JSON catalog quality gate")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--today", type=date.fromisoformat, help="Reproducible check date (YYYY-MM-DD)")
    parser.add_argument("--format", choices=("text", "json", "html"), default="text")
    parser.add_argument("--output", type=Path, help="Create a new report file; existing files are never overwritten")
    parser.add_argument("--strict", action="store_true", help="Fail on warnings as well as errors")
    args = parser.parse_args(argv)
    try:
        rows = load_rows(args.input)
        baseline = load_rows(args.baseline) if args.baseline else None
        report = analyze(rows, read_json(args.config), baseline, args.today)
        if args.format == "json":
            content = json.dumps(report, ensure_ascii=False, indent=2)
        elif args.format == "html":
            content = render_html(report)
        else:
            content = f'Catalog Guard: {report["records"]} records, {report["errors"]} errors, {report["warnings"]} warnings'
            for item in report["findings"]:
                content += f'\n{item["severity"].upper()} {item["code"]} record={item["row"]} field={item["field"]}: {item["message"]}'
            if report["diff"] is not None:
                diff = report["diff"]
                content += f'\nChanges: +{len(diff["added"])} -{len(diff["removed"])} ~{len(diff["changed"])}'
        if args.output:
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(content + "\n")
        else:
            print(content)
        return 1 if report["errors"] or (args.strict and report["warnings"]) else 0
    except (OSError, ValueError, csv.Error) as exc:
        print(f"catalog-guard: {exc}", file=sys.stderr)
        return 2
