#!/usr/bin/env python3
"""Self-contained tests for SAP BAPI Guard."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "sap-bapi-verifier" / "scripts"
SCANNER = SCRIPTS / "scan_abap_bapi_calls.py"
INSTALLER = SCRIPTS / "install_git_hook.py"
SKILL_INSTALLER = ROOT / "scripts" / "install_skill.py"


def run(args: list[str], cwd: Path | None = None, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, input=input_text, text=True, capture_output=True)


def assert_ok(proc: subprocess.CompletedProcess[str], label: str) -> None:
    if proc.returncode != 0:
        raise AssertionError(f"{label} failed with {proc.returncode}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")


def assert_fail(proc: subprocess.CompletedProcess[str], label: str) -> None:
    if proc.returncode == 0:
        raise AssertionError(f"{label} unexpectedly passed\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")


def test_scanner_blocks_unverified_bapi() -> None:
    source = """REPORT ztest.

CALL FUNCTION 'BAPI_TRANSACTION_COMMIT'
  EXPORTING
    wait = abap_true.
"""
    proc = run(
        [
            sys.executable,
            str(SCANNER),
            "--stdin",
            "--label",
            "ztest.abap",
            "--fail-on-unverified-bapi",
        ],
        input_text=source,
    )
    assert_fail(proc, "scanner should block unverified BAPI")
    if "needs-verification" not in proc.stdout:
        raise AssertionError(proc.stdout)


def test_scanner_allows_verified_bapi() -> None:
    source = """REPORT ztest.

" Verified by ADT get-function BAPI_TRANSACTION_COMMIT --group BAPT.
CALL FUNCTION 'BAPI_TRANSACTION_COMMIT'
  EXPORTING
    wait = abap_true.
"""
    proc = run(
        [
            sys.executable,
            str(SCANNER),
            "--stdin",
            "--label",
            "ztest.abap",
            "--fail-on-unverified-bapi",
        ],
        input_text=source,
    )
    assert_ok(proc, "scanner should allow verified BAPI")
    if "verified-note-nearby" not in proc.stdout:
        raise AssertionError(proc.stdout)


def test_hook_checks_staged_content_not_worktree() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        assert_ok(run(["git", "init"], cwd=repo), "git init")
        assert_ok(run(["git", "config", "user.email", "test@example.invalid"], cwd=repo), "git config email")
        assert_ok(run(["git", "config", "user.name", "Test User"], cwd=repo), "git config name")

        source_path = repo / "ztest.abap"
        source_path.write_text(
            """REPORT ztest.

CALL FUNCTION 'BAPI_TRANSACTION_COMMIT'
  EXPORTING
    wait = abap_true.
""",
            encoding="utf-8",
        )
        assert_ok(run(["git", "add", "ztest.abap"], cwd=repo), "git add unverified")

        source_path.write_text(
            """REPORT ztest.

" Verified by ADT get-function BAPI_TRANSACTION_COMMIT --group BAPT.
CALL FUNCTION 'BAPI_TRANSACTION_COMMIT'
  EXPORTING
    wait = abap_true.
""",
            encoding="utf-8",
        )

        assert_ok(run([sys.executable, str(INSTALLER), str(repo)]), "install hook")
        proc = run([sys.executable, str(repo / ".githooks" / "pre-commit")], cwd=repo)
        assert_fail(proc, "hook should block staged unverified content")
        if "blocked this commit" not in proc.stderr:
            raise AssertionError(proc.stderr)

        assert_ok(run(["git", "add", "ztest.abap"], cwd=repo), "git add verified")
        proc = run([sys.executable, str(repo / ".githooks" / "pre-commit")], cwd=repo)
        assert_ok(proc, "hook should allow staged verified content")


def test_skill_installer_copy_and_force() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target_root = Path(tmp) / "skills"
        proc = run([sys.executable, str(SKILL_INSTALLER), "--target", str(target_root)])
        assert_ok(proc, "install skill")
        installed = target_root / "sap-bapi-verifier"
        if not (installed / "SKILL.md").exists():
            raise AssertionError(f"Skill was not installed: {installed}")
        if not (installed / "scripts" / "verify_bapi.py").exists():
            raise AssertionError("verify_bapi.py was not installed")

        proc = run([sys.executable, str(SKILL_INSTALLER), "--target", str(target_root)])
        assert_fail(proc, "installer should refuse overwrite without --force")
        if "--force" not in proc.stderr:
            raise AssertionError(proc.stderr)

        proc = run([sys.executable, str(SKILL_INSTALLER), "--target", str(target_root), "--force"])
        assert_ok(proc, "installer should overwrite with --force")


def main() -> int:
    tests = [
        test_scanner_blocks_unverified_bapi,
        test_scanner_allows_verified_bapi,
        test_hook_checks_staged_content_not_worktree,
        test_skill_installer_copy_and_force,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
