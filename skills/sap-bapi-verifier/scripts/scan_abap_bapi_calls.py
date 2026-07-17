#!/usr/bin/env python3
"""Scan ABAP files for CALL FUNCTION usage that should be verified."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


CALL_RE = re.compile(r"CALL\s+FUNCTION\s+['`]([^'`]+)['`]", re.IGNORECASE)
VERIFY_RE = re.compile(r"(verified\s+by\s+adt|get-function|sap-bapi-verifier)", re.IGNORECASE)


def iter_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(p for p in path.rglob("*") if p.is_file() and p.suffix.lower() in {".abap", ".txt", ".inc"})


def scan_text(text: str, label: str) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    lines = text.splitlines()
    for idx, line in enumerate(lines, start=1):
        for match in CALL_RE.finditer(line):
            name = match.group(1).upper()
            window = "\n".join(lines[max(0, idx - 8): min(len(lines), idx + 8)])
            findings.append(
                {
                    "file": label,
                    "line": idx,
                    "function": name,
                    "is_bapi": name.startswith("BAPI_") or name in {"BAPI_TRANSACTION_COMMIT", "BAPI_TRANSACTION_ROLLBACK"},
                    "has_nearby_verification_note": bool(VERIFY_RE.search(window)),
                }
            )
    return findings


def scan_file(path: Path) -> list[dict[str, object]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return scan_text(text, str(path))


def input_text() -> str:
    data = sys.stdin.buffer.read()
    return data.decode("utf-8", errors="ignore")


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan ABAP files for function calls requiring SAP system verification.")
    parser.add_argument("path", nargs="?", help="ABAP file or folder to scan")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    parser.add_argument("--stdin", action="store_true", help="Read ABAP source from stdin instead of a file")
    parser.add_argument("--label", default="<stdin>", help="Display label when scanning stdin")
    parser.add_argument("--fail-on-unverified-bapi", action="store_true", help="Exit 1 when a BAPI call lacks nearby verification evidence")
    args = parser.parse_args()

    findings: list[dict[str, object]] = []
    if args.stdin:
        findings.extend(scan_text(input_text(), args.label))
    else:
        if not args.path:
            parser.error("path is required unless --stdin is used")
        root = Path(args.path)
        for file_path in iter_files(root):
            findings.extend(scan_file(file_path))

    if args.json:
        print(json.dumps(findings, ensure_ascii=False, indent=2))
    else:
        if not findings:
            print("No CALL FUNCTION usage found.")
        for item in findings:
            marker = "BAPI" if item["is_bapi"] else "FM"
            status = "verified-note-nearby" if item["has_nearby_verification_note"] else "needs-verification"
            print(f"{item['file']}:{item['line']} [{marker}] {item['function']} - {status}")

    has_unverified = any(item["is_bapi"] and not item["has_nearby_verification_note"] for item in findings)
    return 1 if args.fail_on_unverified_bapi and has_unverified else 0


if __name__ == "__main__":
    raise SystemExit(main())
