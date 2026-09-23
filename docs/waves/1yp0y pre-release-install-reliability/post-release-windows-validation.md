# Post-release Windows Validation

Owner: Engineering
Status: planned
Last verified: 2026-09-22

## Authority and limitation

On 2026-09-22 the operator requested final review for wave 1yp0y and said external testers will be obtained after the next release. This defers native qualification; it does not claim Windows execution succeeded. The operator coordinates testers and Engineering triages results. No tester has been contacted by this agent, and no release or outreach is authorized by this record.

## Tester protocol

Use a standard-user Windows workstation and record Windows/Python/agent-host versions, installer or approved Python source, and the exact package version/build. Use a repository path containing spaces. Cover both a fresh install and an already-seeded checkout on a new workstation. Preserve repository configuration and existing index bytes while diagnosing.

1. Run `powershell -NoProfile -File ".\.wavefoundry\framework\scripts\diagnose_python.ps1" -Json`. Exercise missing python3 with a working python, both absent, old python3, failed/Store-placeholder launch, timeout and valid canonical python3. Retain attempted/resolved commands, actual spawned interpreter identity, output and exit status; do not infer causes from path alone. Verify JSON numeric types parsed by Windows PowerShell satisfy the version check and that reported resolution matches the spawned command.
2. Exercise `wf.cmd setup` with python3 unavailable; confirm actionable diagnostics and no setup provisioning, surface writes or fallback success. Test Python-level strict setup with the legacy skip variable set: it must still fail.
3. Use only a permitted existing python3 entry/user PATH correction. If policy blocks the script or repair, follow manual diagnosis/IT guidance without bypass, elevation or machine-wide changes. Record the remaining unready state.
4. After repair, verify interpreter identity in a new terminal. On first install allow setup to provision dependencies before server dry-run; on an already-provisioned checkout verify `python3 .wavefoundry/framework/scripts/server.py --dry-run` directly. Do not reseed or rebuild solely for command repair.
5. Fully restart the agent host, verify actual MCP initialization and a representative generated hook. Record before/after identity, restart requirements, error output and any changes made. Remove private paths/usernames from shared evidence as appropriate.

## Result disposition

Attach durable tester results to this wave or a linked follow-up change. File defects against the observed behavior. Only successful real-host evidence can establish native qualification; until then, AC-3/AC-6 remain intentionally unmet, and the one Darwin-skipped native regression is not proof.
