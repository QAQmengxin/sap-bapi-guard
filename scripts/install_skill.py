#!/usr/bin/env python3
"""Install SAP BAPI Guard skills into a Codex skills directory."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "skills" / "sap-bapi-verifier"


def default_target_root() -> Path:
    return Path.home() / ".codex" / "skills"


def copy_skill(source: Path, target_root: Path, force: bool) -> Path:
    if not source.exists() or not (source / "SKILL.md").exists():
        raise FileNotFoundError(f"Skill source is invalid: {source}")

    target_root.mkdir(parents=True, exist_ok=True)
    target = target_root / source.name
    if target.exists():
        if not force:
            raise FileExistsError(f"Target skill already exists: {target}. Use --force to replace it.")
        shutil.rmtree(target)

    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", ".mypy_cache", ".ruff_cache")
    shutil.copytree(source, target, ignore=ignore)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Install SAP BAPI Guard's sap-bapi-verifier skill.")
    parser.add_argument("--target", default=str(default_target_root()), help="Target skills root, default: ~/.codex/skills")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE), help="Source skill directory")
    parser.add_argument("--force", action="store_true", help="Replace an existing installed skill")
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    target_root = Path(args.target).expanduser().resolve()

    try:
        target = copy_skill(source, target_root, args.force)
    except (FileNotFoundError, FileExistsError, OSError) as exc:
        print(f"Install failed: {exc}", file=sys.stderr)
        return 1

    print(f"Installed skill: {target}")
    print()
    print("Next steps:")
    print("1. Restart or refresh Codex so the new skill is discovered.")
    print("2. Ensure sap-adt-cli is configured, or set SAP_ADT_CLI to your sap_adt_cli.py path.")
    print("3. Try: Use $sap-bapi-verifier to verify BAPI_TRANSACTION_COMMIT.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
