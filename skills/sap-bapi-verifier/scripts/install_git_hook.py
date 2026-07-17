#!/usr/bin/env python3
"""Install a Git pre-commit hook that checks staged ABAP BAPI calls."""

from __future__ import annotations

import argparse
import stat
import subprocess
import sys
from pathlib import Path


HOOK_TEMPLATE = r'''#!/usr/bin/env python3
# Installed by sap-bapi-guard. Blocks staged BAPI calls without nearby verification evidence.

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SCANNER = Path(r"{scanner}")
VERIFY = Path(r"{verify}")


def main() -> int:
    if not SCANNER.exists():
        print(f"sap-bapi-guard scanner not found: {{SCANNER}}", file=sys.stderr)
        return 1

    proc = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout, file=sys.stderr)
        return proc.returncode

    files = [
        Path(line.strip())
        for line in proc.stdout.splitlines()
        if line.strip().lower().endswith((".abap", ".inc", ".txt"))
    ]
    status = 0
    for file_path in files:
        staged = subprocess.run(
            ["git", "show", f":{{file_path.as_posix()}}"],
            text=True,
            capture_output=True,
        )
        if staged.returncode != 0:
            print(staged.stderr or staged.stdout, file=sys.stderr)
            continue
        check = subprocess.run(
            [
                sys.executable,
                str(SCANNER),
                "--stdin",
                "--label",
                str(file_path),
                "--fail-on-unverified-bapi",
            ],
            input=staged.stdout,
            text=True,
        )
        if check.returncode != 0:
            status = 1

    if status != 0:
        print(
            f"""
sap-bapi-guard blocked this commit.

A staged ABAP file contains a BAPI CALL FUNCTION without nearby verification evidence.
Run:
  python "{{VERIFY}}" BAPI_NAME

Then add a concise verification note near the call or in the changed section, for example:
  "Verified by ADT get-function BAPI_NAME --group FUNCTION_GROUP"
""",
            file=sys.stderr,
        )
    return status


if __name__ == "__main__":
    raise SystemExit(main())
'''


def run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Install SAP BAPI Guard Git pre-commit hook.")
    parser.add_argument("repo", nargs="?", default=".", help="Target Git repository")
    parser.add_argument("--scanner", default=str(Path(__file__).with_name("scan_abap_bapi_calls.py")), help="Path to scan_abap_bapi_calls.py")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    if not (repo / ".git").exists():
        print(f"Not a Git repository: {repo}", file=sys.stderr)
        return 2

    scanner = Path(args.scanner).resolve()
    verify = scanner.with_name("verify_bapi.py")
    if not scanner.exists():
        print(f"Scanner not found: {scanner}", file=sys.stderr)
        return 2
    if not verify.exists():
        print(f"Verifier not found: {verify}", file=sys.stderr)
        return 2

    hooks_dir = repo / ".githooks"
    hooks_dir.mkdir(exist_ok=True)
    hook_path = hooks_dir / "pre-commit"
    hook_path.write_text(HOOK_TEMPLATE.format(scanner=str(scanner), verify=str(verify)), encoding="utf-8")

    current_mode = hook_path.stat().st_mode
    hook_path.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    proc = run(["git", "config", "core.hooksPath", ".githooks"], cwd=repo)
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout, file=sys.stderr)
        return proc.returncode

    print(f"Installed SAP BAPI Guard pre-commit hook: {hook_path}")
    print("Configured git core.hooksPath=.githooks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
