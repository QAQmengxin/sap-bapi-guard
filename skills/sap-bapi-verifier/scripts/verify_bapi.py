#!/usr/bin/env python3
"""Verify a SAP BAPI/function module through sap-adt-cli."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree


def candidate_sap_cli_paths() -> list[Path]:
    env_path = os.environ.get("SAP_ADT_CLI")
    paths: list[Path] = []
    if env_path:
        paths.append(Path(env_path).expanduser())
    home = Path.home()
    paths.extend(
        [
            home / ".codex" / "skills" / "sap-adt-cli" / "scripts" / "sap_adt_cli.py",
            home / ".agents" / "skills" / "sap-adt-cli" / "scripts" / "sap_adt_cli.py",
        ]
    )
    return paths


def resolve_sap_cli(explicit: str | None) -> Path:
    if explicit:
        path = Path(explicit).expanduser()
        if path.exists():
            return path
        raise FileNotFoundError(f"sap_adt_cli.py not found: {path}")
    for path in candidate_sap_cli_paths():
        if path.exists():
            return path
    candidates = "\n".join(f"- {p}" for p in candidate_sap_cli_paths())
    raise FileNotFoundError(
        "sap_adt_cli.py not found. Pass --sap-cli or set SAP_ADT_CLI.\n"
        f"Checked:\n{candidates}"
    )


def run_cli(sap_cli: Path, args: list[str]) -> tuple[int, str, str]:
    command = [sys.executable, str(sap_cli), *args]
    proc = subprocess.run(command, text=True, capture_output=True)
    return proc.returncode, proc.stdout, proc.stderr


def strip_ns(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def xml_objects(xml_text: str) -> list[dict[str, str]]:
    objects: list[dict[str, str]] = []
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return objects

    for elem in root.iter():
        attrs = {strip_ns(k): v for k, v in elem.attrib.items()}
        text = (elem.text or "").strip()
        name = attrs.get("name") or attrs.get("title") or text
        uri = attrs.get("uri") or attrs.get("href") or attrs.get("adtcore:uri") or ""
        typ = attrs.get("type") or attrs.get("objectType") or strip_ns(elem.tag)
        if name or uri:
            objects.append({"name": name, "type": typ, "uri": uri})
    return objects


def guess_group_from_text(text: str, function_name: str) -> str | None:
    patterns = [
        r"/groups/([^/\s\"']+)/fmodules/" + re.escape(function_name),
        r"functiongroups/([^/\s\"']+)",
        r"function-groups/([^/\s\"']+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    return None


def extract_interface_hints(source: str) -> dict[str, list[str]]:
    sections = {"exporting": [], "importing": [], "tables": [], "changing": [], "return": []}
    current: str | None = None
    code_starts = {
        "IF",
        "CASE",
        "LOOP",
        "SELECT",
        "CALL",
        "COMMIT",
        "ROLLBACK",
        "DATA",
        "FIELD-SYMBOLS",
        "CLEAR",
        "MOVE",
        "READ",
        "APPEND",
        "ENDFUNCTION",
    }
    has_seen_interface = False
    for raw in source.splitlines():
        line = raw.strip()
        upper = line.upper()
        if not line or upper.startswith("FUNCTION "):
            continue
        first_word = upper.split(None, 1)[0].rstrip(".")
        if has_seen_interface and first_word in code_starts:
            break
        if upper in {"EXPORTING", "IMPORTING", "TABLES", "CHANGING"} or upper.startswith(("* EXPORTING", "* IMPORTING", "* TABLES", "* CHANGING")):
            for key in ("exporting", "importing", "tables", "changing"):
                if key.upper() in upper:
                    current = key
                    has_seen_interface = True
                    break
            continue
        if current:
            if first_word in code_starts:
                break
            match = re.search(r"\b(?:VALUE|REFERENCE)\(([A-Z0-9_]+)\)", upper)
            if not match:
                match = re.match(r"\*?\s*([A-Z0-9_]+)\b", upper)
            if match and match.group(1) not in {"VALUE", "REFERENCE", "TYPE", "LIKE", "OPTIONAL"}:
                token = match.group(1)
                if token not in sections[current]:
                    sections[current].append(token)
                if "RETURN" in token and token not in sections["return"]:
                    sections["return"].append(token)
            if upper.endswith("."):
                current = None
    return sections


def call_mapping(hints: dict[str, list[str]]) -> dict[str, list[str]]:
    return {
        "caller_exporting": hints.get("importing", []),
        "caller_importing": hints.get("exporting", []),
        "caller_tables": hints.get("tables", []),
        "caller_changing": hints.get("changing", []),
    }


def output_markdown(name: str, group: str | None, found: bool, source: str, search_objects: list[dict[str, str]]) -> None:
    print(f"# BAPI Verification: {name}")
    print()
    print(f"- Exists in SAP system: {'yes' if found else 'no'}")
    print(f"- Function group: {group or 'not determined'}")
    if search_objects:
        print("- Search evidence:")
        for obj in search_objects[:10]:
            label = obj.get("name") or "(unnamed)"
            typ = obj.get("type") or "object"
            uri = obj.get("uri") or ""
            print(f"  - {label} [{typ}] {uri}".rstrip())
    if source:
        hints = extract_interface_hints(source)
        mapping = call_mapping(hints)
        print("- Interface hints from retrieved source:")
        for section in ("exporting", "importing", "tables", "changing", "return"):
            values = hints[section]
            print(f"  - {section.upper()}: {', '.join(values) if values else '(not found in source text)'}")
        print("- CALL FUNCTION parameter mapping:")
        print(f"  - EXPORTING in caller: {', '.join(mapping['caller_exporting']) if mapping['caller_exporting'] else '(none found)'}")
        print(f"  - IMPORTING in caller: {', '.join(mapping['caller_importing']) if mapping['caller_importing'] else '(none found)'}")
        print(f"  - TABLES in caller: {', '.join(mapping['caller_tables']) if mapping['caller_tables'] else '(none found)'}")
        print(f"  - CHANGING in caller: {', '.join(mapping['caller_changing']) if mapping['caller_changing'] else '(none found)'}")
        print()
        print("## Retrieved Source Preview")
        print()
        print("```abap")
        preview = "\n".join(source.splitlines()[:160])
        print(preview)
        if len(source.splitlines()) > 160:
            print("* ... truncated; rerun get-function directly for full source ...")
        print("```")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a SAP BAPI/function module with sap-adt-cli.")
    parser.add_argument("name", help="BAPI or function module name, for example BAPI_SALESORDER_CREATEFROMDAT2")
    parser.add_argument("--group", help="Known SAP function group")
    parser.add_argument("--sap-cli", help="Path to sap_adt_cli.py")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args()

    name = args.name.upper()
    group = args.group.upper() if args.group else None
    try:
        sap_cli = resolve_sap_cli(args.sap_cli)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    status_code, status_out, status_err = run_cli(sap_cli, ["status"])
    if status_code != 0:
        print(status_err or status_out, file=sys.stderr)
        return status_code

    search_objects: list[dict[str, str]] = []
    search_code, search_out, search_err = run_cli(sap_cli, ["search-object", name, "--max-results", "20"])
    if search_code == 0:
        search_objects = xml_objects(search_out)
        if not group:
            group = guess_group_from_text(search_out, name)
    elif not group:
        print(search_err or search_out, file=sys.stderr)

    source = ""
    found = False
    get_error = ""
    if group:
        get_code, get_out, get_err = run_cli(sap_cli, ["get-function", name, "--group", group])
        found = get_code == 0 and bool(get_out.strip())
        source = get_out if found else ""
        get_error = get_err or get_out
    else:
        get_error = "Function group was not determined; pass --group after checking search evidence."

    hints = extract_interface_hints(source) if source else {}
    result = {
        "name": name,
        "exists": found,
        "function_group": group,
        "search_objects": search_objects[:20],
        "interface_hints": hints,
        "call_function_mapping": call_mapping(hints) if hints else {},
        "error": "" if found else get_error,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        output_markdown(name, group, found, source, search_objects)
        if not found and get_error:
            print()
            print("## Verification Error")
            print()
            print(get_error.strip())
    return 0 if found else 1


if __name__ == "__main__":
    raise SystemExit(main())
