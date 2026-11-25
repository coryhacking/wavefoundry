# Security delivery review

Owner: Engineering
Status: active
Last verified: 2026-11-24

The security seat approves the reviewed boundary at fingerprint `7cb3a3714a6e996278cc3a097c32c522ba830d215d1d530f219ee09532e503df`. CR-D1 affects the interrupted prompt replacement and its checkpoint. Its reported missing policy guidance warrants code-lane repair. I did not verify that repair or identify a runtime permission change in the reported failure.

Four fresh stdio sessions listed tools and called `memory_brief(context="review")` on a private copy of the installed q5tt fixture. Moving the checkout and user home invalidated its old receipts and withheld all five new tools. Running the shipped permission render made all five visible. A user deny for the retired get tool withheld only its successor on two consecutive restarts, even with a repository grant and existing verification receipt. No retired route appeared. The four sessions returned one active record and preserved all memory, wave and ledger file bytes. The user setting stayed byte-identical across both restricted sessions. Run `~/.wavefoundry/venv/bin/python -B .wavefoundry/work/24buu/delivery/security-probe.py`. Primary output is in `security-probe-final.log`.

Fourteen focused tests passed with zero skips on the frozen tree. `security-positive.log` names each test. From the framework tests directory, run its named test IDs with `PYTHONPATH=.. ~/.wavefoundry/venv/bin/python -B -m unittest -v`. Positive coverage includes six outside-policy fixtures, idempotence, symlink and FIFO refusal, late prompt edits, global memory counts on an empty brief, unavailable churn, required and malformed cleanup guards, and the ordinary extracted cleanup child.

| Mutation | Target and observation |
| --- | --- |
| Return a hold for all five routes whenever one outside restriction exists | The normal migration entry failed five exact held-set comparisons. A wildcard already covering all five still passed. No skips or execution errors. From the framework tests directory run `PYTHONPATH=..:. ~/.wavefoundry/venv/bin/python -B ../../../work/24buu/delivery/security-control.py`. |

Requiring manual migration everywhere would give operators a place to review opaque launch or enterprise policy at the cost of hand-copying every exact repository rule. Updating user files automatically would cross the checkout owner's write boundary. Exact copies within their original repository files and read-only assessment of user files preserve tested restrictions while reserving ambiguous policy for the operator. Files in OS-managed locations, host arguments, native client prompts and Windows were outside the execution evidence. The security seat does not attest to a final successor archive or full-tree filesystem immutability. Guard assertions exercised fixture state, and separate telemetry and SQLite coordination writes fall outside the memory-record check.

No actionable entries in scan-findings.json. Its 281 entries have false-positive status.

## Final rehearsal and manual cleanup

The security seat favors conditional CLI cleanup. Publication, guard validation and a checkpoint whose next action is cleanup give the runner sufficient evidence to proceed. The focused tests showed that malformed guards, outstanding stops and retained continuations preserve the checkpoint. Requiring a person to inspect every clean checkpoint adds no demonstrated protection in those cases and made the earlier successor regression harder to see.

I checked all six final primary checkpoints, terminal summaries and inspection reports. The two direct archive runs and successor installed CLI cleared the checkpoint themselves. The legacy installed CLI and both MCP primary calls retained it at `index_complete` for explicit cleanup. Every hop recorded one cleanup-complete marker and passed all 18 checks, including lock removal. These are coordinator-run Apple Silicon rehearsals. I independently inspected their records.
