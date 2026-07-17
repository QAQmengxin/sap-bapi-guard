# SAP BAPI Guard

SAP BAPI Guard is a Codex plugin that prevents AI-generated ABAP from guessing BAPI names or parameters. It gives Codex a reusable skill for live SAP ADT verification and a Git pre-commit hook that blocks unverified `BAPI_*` calls.

## What It Does

- Verifies that a BAPI or function module exists in the connected SAP system.
- Resolves the function group through ADT object search when possible.
- Reads the function module source and extracts interface hints.
- Maps function module definition direction to `CALL FUNCTION` direction.
- Scans ABAP files for `CALL FUNCTION 'BAPI_*'`.
- Installs a repository-local Git hook that checks staged ABAP content before commit.

## Repository Layout

```text
sap-bapi-guard/
  .codex-plugin/plugin.json
  skills/sap-bapi-verifier/
    SKILL.md
    agents/openai.yaml
    scripts/
      verify_bapi.py
      scan_abap_bapi_calls.py
      install_git_hook.py
```

## Prerequisites

- Python 3.10 or newer.
- Git.
- The companion `sap-adt-cli` skill or equivalent `sap_adt_cli.py`.
- SAP ADT services enabled on the target SAP system.
- SAP credentials configured in `sap-adt-cli`; credentials are not stored by this plugin.

`verify_bapi.py` finds `sap_adt_cli.py` in this order:

1. `--sap-cli path/to/sap_adt_cli.py`
2. `SAP_ADT_CLI` environment variable
3. `~/.codex/skills/sap-adt-cli/scripts/sap_adt_cli.py`
4. `~/.agents/skills/sap-adt-cli/scripts/sap_adt_cli.py`

## Install As A Codex Plugin

Clone or copy this repository into a local plugins folder, then add it through your Codex plugin marketplace flow. The plugin manifest is:

```text
.codex-plugin/plugin.json
```

If you use a personal marketplace file, add an entry like:

```json
{
  "name": "sap-bapi-guard",
  "source": {
    "source": "local",
    "path": "./plugins/sap-bapi-guard"
  },
  "policy": {
    "installation": "AVAILABLE",
    "authentication": "ON_INSTALL"
  },
  "category": "Productivity"
}
```

## Install Only The Skill

If you do not want to install the whole plugin, install only the reusable skill:

```powershell
python scripts\install_skill.py
```

Install to a custom skills directory:

```powershell
python scripts\install_skill.py --target path\to\skills
```

Replace an existing installed copy:

```powershell
python scripts\install_skill.py --force
```

## Configure SAP Access

Configure the companion SAP ADT CLI first:

```powershell
python path\to\sap_adt_cli.py configure
python path\to\sap_adt_cli.py status
```

The plugin only performs read operations. It does not require SAP write or transport permissions.

## Verify A BAPI

```powershell
python skills\sap-bapi-verifier\scripts\verify_bapi.py BAPI_TRANSACTION_COMMIT
```

With a known function group:

```powershell
python skills\sap-bapi-verifier\scripts\verify_bapi.py BAPI_TRANSACTION_COMMIT --group BAPT
```

Machine-readable output:

```powershell
python skills\sap-bapi-verifier\scripts\verify_bapi.py BAPI_TRANSACTION_COMMIT --json
```

## Scan ABAP Files

```powershell
python skills\sap-bapi-verifier\scripts\scan_abap_bapi_calls.py path\to\repo
```

Fail on unverified BAPI calls:

```powershell
python skills\sap-bapi-verifier\scripts\scan_abap_bapi_calls.py path\to\file.abap --fail-on-unverified-bapi
```

The scanner treats a nearby note like this as verification evidence:

```abap
" Verified by ADT get-function BAPI_TRANSACTION_COMMIT --group BAPT.
CALL FUNCTION 'BAPI_TRANSACTION_COMMIT'
  EXPORTING
    wait = abap_true.
```

## Install The Git Hook

From this repository:

```powershell
python skills\sap-bapi-verifier\scripts\install_git_hook.py path\to\abap-repo
```

The installer creates:

```text
path/to/abap-repo/.githooks/pre-commit
```

and runs:

```powershell
git config core.hooksPath .githooks
```

The generated hook checks the staged version of each changed `.abap`, `.inc`, and `.txt` file. This matters because a pre-commit hook must validate exactly what Git is about to commit, not whatever happens to be in the working tree.

## Codex Usage

Ask Codex:

```text
Use $sap-bapi-verifier to verify BAPI_ACC_DOCUMENT_POST before writing ABAP.
```

or:

```text
Use $sap-bapi-verifier to scan this ABAP repository and install the safety hook.
```

Codex should include verification evidence in its final answer, for example:

```text
Verification:
- Checked BAPI_TRANSACTION_COMMIT in function group BAPT with ADT get-function.
- Caller EXPORTING parameter WAIT and caller IMPORTING parameter RETURN were confirmed.
```

## Local Tests

Run:

```powershell
python tests\run_tests.py
```

The tests cover scanner behavior and the generated Git hook's staged-content enforcement.

## Security Notes

- Do not commit SAP credentials.
- Do not include SAP hostnames, client numbers, usernames, passwords, or internal object details in public test fixtures.
- The hook does not connect to SAP; it only checks for local verification evidence.
- Live SAP verification is done explicitly through `verify_bapi.py`.

## License

MIT
