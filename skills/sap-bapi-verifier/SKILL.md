---
name: sap-bapi-verifier
description: Verify SAP BAPI and function module existence, function group, interface parameters, DDIC structures, return handling, and commit/rollback requirements before generating or reviewing ABAP code. Use when the user asks to write, modify, review, explain, or troubleshoot ABAP that calls BAPIs, RFC-enabled function modules, CALL FUNCTION, BAPI_TRANSACTION_COMMIT, or BAPI_TRANSACTION_ROLLBACK, and when checking AI-generated ABAP for nonexistent BAPIs or wrong parameters.
---

# SAP BAPI Verifier

Use this skill before writing, changing, or approving any ABAP `CALL FUNCTION` that targets a BAPI or RFC/function module whose signature matters. Treat the live SAP system as the source of truth; do not rely on memory, web snippets, or generic BAPI examples.

## Required Workflow

1. Confirm SAP ADT CLI connectivity.

   ```powershell
   python path\to\sap_adt_cli.py status
   ```

   The bundled scripts locate `sap_adt_cli.py` in this order:

   - `--sap-cli` argument
   - `SAP_ADT_CLI` environment variable
   - `~/.codex/skills/sap-adt-cli/scripts/sap_adt_cli.py`
   - `~/.agents/skills/sap-adt-cli/scripts/sap_adt_cli.py`

2. Verify the BAPI/function module before generating code.

   ```powershell
   python path\to\sap-bapi-verifier\scripts\verify_bapi.py BAPI_NAME
   ```

   If the function group is known:

   ```powershell
   python path\to\sap-bapi-verifier\scripts\verify_bapi.py BAPI_NAME --group FUNCTION_GROUP
   ```

3. If parameters reference DDIC structures, table types, data elements, or domains, query them with SAP ADT CLI before using fields in code.

4. Generate or review ABAP only after verification evidence is available.

5. In the final answer, include a short verification note naming the commands or objects checked.

## Verification Standard

Before using a BAPI/function module in ABAP, confirm:

- The function module exists in the connected SAP system.
- The function group is correct.
- Every used `EXPORTING`, `IMPORTING`, `TABLES`, and `CHANGING` parameter name appears in the system definition.
- Remember the ABAP function module definition perspective: source `IMPORTING` parameters are supplied under caller `EXPORTING`, and source `EXPORTING` parameters are received under caller `IMPORTING`.
- Structure/table fields used to fill BAPI parameters are confirmed through DDIC lookup when they are not already obvious from retrieved source.
- Return handling matches the actual interface, such as `RETURN`, `RETURN[]`, `BAPIRET2`, or a system-specific return parameter.
- Update behavior is explicit: state whether `BAPI_TRANSACTION_COMMIT` or `BAPI_TRANSACTION_ROLLBACK` is required, and why.

If any verification step fails, stop and report that the BAPI has not been verified. Do not invent a signature or patch code by guessing parameter names.

## Reviewing Existing ABAP

For an existing ABAP file or folder, scan for BAPI/function calls:

```powershell
python path\to\sap-bapi-verifier\scripts\scan_abap_bapi_calls.py path\to\file_or_folder
```

Use the scan output as a checklist. For each discovered BAPI or function module, run `verify_bapi.py` before approving or changing the call.

## Installing A Git Safety Hook

To add a repository-local pre-commit hook that blocks staged BAPI calls lacking nearby verification evidence:

```powershell
python path\to\sap-bapi-verifier\scripts\install_git_hook.py path\to\git\repo
```

The installer creates `.githooks/pre-commit` in the target repository and sets `git config core.hooksPath .githooks`. This is a local repository setting; repeat it for each ABAP repository that should enforce the check.

## Safe Output Pattern

When producing ABAP that calls a BAPI, include a compact note like:

```text
Verification:
- Checked BAPI_SALESORDER_CREATEFROMDAT2 in function group BAPI_SD_SALESORDER with ADT get-function.
- Used parameters ORDER_HEADER_IN, ORDER_ITEMS_IN, ORDER_SCHEDULES_IN, RETURN from the retrieved interface.
- Checked DDIC structures BAPISDHD1 and BAPISDITM before filling fields.
- Explicit commit is required only when RETURN contains no E/A/X messages.
```

Keep this evidence concise but specific enough that a reviewer can tell the code was grounded in the connected SAP system.
