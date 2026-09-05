# Readiness Review — Later-Created Doc Link Targets

Owner: Engineering
Status: active
Last verified: 2026-09-05

This report records plan review, not delivery verification. The original plan
received COUNCIL-READY-1; the coordinator revised it in readiness repair cycle 1.
Final independent reverification and council approval are recorded below when complete.

## Initial council synthesis

# Wave Council readiness review — 1x8e1 / wave 1x5tq

Verdict: changes requested. Deduplicated finding COUNCIL-READY-1 blocks readiness until bounded plan corrections are independently reverified by QA and reality-checker. No proposed implementation or delivery approval is claimed.

## Scope and protocol

Full primer depth selected because the change affects persisted graph data flow. Red-team primer ran first in isolation with all five stances and three questions. Independent fixed seats: architecture-reviewer, security-reviewer, qa-reviewer, reality-checker. Performance-reviewer ran afterward as rotating best-alternative seat. Fixed seats were isolated from one another's outputs and received the shared primer intentionally. A pre-primer initial-read isolation claim is unavailable for seats that read the primer with the packet; this is recorded honestly, not retroactively manufactured. The local preparation prompt directs seats to receive briefing plus primer.

Frozen scope: admitted change doc, graph_indexer.py, test_graph_incremental_merge.py, graph-index-system.md, CHANGELOG.md. Initial per-file Git object hashes are in packet.json and were rechecked by all seats with no changes. wave.md coordinator metadata was excluded. Initial frozen review ended after the rotating seat returned. Later coordinator repairs are a new review packet.

A randomized Seat 1..4 first synthesis is in anonymized-fixed.md and merit-pass.md, with identity reattached afterward. Required blockers retain their authority. Initial aggregate: seat_agreement=split; max_severity=high. QA/reality explicitly withhold approval; architecture/security phrase approval with notes but request the same corrections. One targeted challenge round combines explicit alternative weighing and reconciliation of this timing distinction; it does not waive the blockers or re-review repaired text.

## Primer outcome and council judgment

The primer's strongest challenge was confirmed by every fixed seat: “newly current” is underspecified as a consumed global transition. Current graph paths include legitimate targets with no store rows. A referring doc may miss its target-creation build while unreadable; its repair obligation must survive. finalize also returns zero-change before reading merge summaries, so an otherwise idle relevant path change must defeat that return. Current code validates these seams; this is not a claim that unimplemented work has failed delivery.

All seats endorse the existing narrow approach once clarified: retain normalized unresolved targets per referring doc; intersect with current paths; rescan only the affected readable docs; clear/replace obligations only after successful extraction. Preserve them on skip/read failure. Copy metadata through extraction artifacts AND the summary allowlist so it survives sessions even when a zero-edge served doc node is pruned.

Existing path normalization, markdown/backtick eligibility and exclusions remain authoritative. No referenced-target content reads, exclusion bypass or new trust boundary is warranted. No security exploit chain was found. GraphIndexSession retains ownership; no ADR or new storage service is required.

## Required corrections (one deduplicated finding)

1. Define the retained per-doc unresolved-current condition before zero-change, with retry on later readable builds and no consumption on skipped/failed extraction.
2. Require artifact and persisted fragment coverage, preserving unresolved-only doc fragments and existing normalized local candidate rules. Keep the planned builder bump.
3. Make AC-1 evidence non-vacuous: exact source/target/relation edge and referring-doc node, plus full-oracle equality, immediately after target-only creation and on unchanged/unrelated followups, for noded and node-less targets. Verify retained metadata across sessions.
4. Pin never-appearing target zero-rescan behavior, successful-resolution no-repeat behavior, and unreadable/failed-read recovery. Validate target-only and unchanged-recovery reachability through the actual index-build caller before delivery; if a caller change proves necessary, disclose the evidence and route scope explicitly.
5. Preserve no row hydration/writes and no payload/blob writes on a genuine idle build; a single reused existing merge-state blob read is permitted by existing tests. Acknowledge its whole-graph decoding cost instead of claiming O(unresolved) total I/O or measured latency.

These clarify and provide evidence for the already required next-merge equality and selective-rescan obligations. Do not broaden deletion/symbol-mention semantics or adopt a global path snapshot in this repair.

## Strongest alternative

Performance's strongest distinct alternative retains all normalized explicit-link candidates and derives available edges at payload assembly, avoiding source rereads and repeated symbol matching for path arrivals. It is attractive if measured source I/O becomes a bottleneck. It also changes edge-production, prior-availability detection, deletion and outage contracts, beyond this rescan repair. The council favors the minimal retained per-doc obligation now. A global path-delta sidecar still needs per-doc acknowledgement/retry state and adds consistency complexity; blanket rescans violate AC-2. No speculative backlog is created.

## Executable evidence and limitations

Moderator executed four bounded readiness cells through the real update_graph_index merge boundary in temporary repositories with bytecode disabled. Both later-created src/later.py and node-less assets/.gitignore had zero incremental versus one oracle target edge; assert_equivalent rejected both known-bad baselines. Explicit source-doc rescan restored equality. A target that never appears yielded zero doc extraction calls and full-oracle equality. Creating a target while its referring doc was walk-shadowed, then recovering without changes, still yielded zero incremental versus one oracle edge.

Evidence: probe.py, probe-output.json, recovery_probe.py, recovery-output.json. This validates the current defect and positive/negative controls, not future implementation. The oracle shares extraction code; absolute expected-edge controls mitigate common-mode vacuity only for these selected cases. The outage fixture models unreadable_dirs and does not change real permissions. Upstream idle index-build reachability remains unexecuted. No broad suite, delivery mutation or measured latency claim is made.

Exact executable integrity and caller fields are in evidence.json and finding.json. Initial recording actor wave-council, context codex-1x8e1-readiness-council-20260905, fresh_context=true and independent=true for this first current-tree review; the moderator did not implement the plan/code repair. Subsequent alternative discussion retains review context and is not claimed fresh. Repaired-plan lane confirmation and final council approval need fresh independent contexts.

## Artifacts

packet.json; primer.md; architecture.md; security.md; qa.md; reality.md; performance.md; four *-alternative.md notes; anonymized-fixed.md; merit-pass.md; finding.json; evidence.json; probe scripts and outputs. Root coordinator owns typed finding/repair/reverification/approval authoring and final prepare.

## Targeted challenge outcome

All four fixed seats explicitly weighed performance's raw-candidate assembly alternative in their *-alternative.md reports. Each prefers retained per-doc unresolved-current retries with a reused existing blob read for this repair and preserves the QA/reality readiness blocker. They agree the specified text corrections are sufficient in principle, but none approves unseen amended text. The apparent verdict disagreement was resolved as a difference in lane emphasis and approval timing, not a disagreement about the remedy: architecture/security accept the narrow design; QA/reality require its precise retry and evidence commitments before readiness. Highest recorded severity remains high; the initial independent seat_agreement remains split rather than being retroactively relabeled unanimous. No second challenge round or expanded sweep occurred.

Coordinator reports the plan was patched after freeze release and typed finding/repair_start recording. This moderator has not re-reviewed that edited packet and asserts no fresh repaired-plan conclusion. Proceed to fresh independent QA/reality same-phase reverification, then fresh council synthesis/approval and prepare.

## Original frozen packet

```json
{
  "wave_id": "1x5tq",
  "phase": "readiness",
  "change_ids": [
    "1x8e1"
  ],
  "trust_boundaries_touched": [],
  "files_in_scope": [
    "docs/waves/1x5tq later-created-doc-link-targets/1x8e1-bug doc-link-into-later-created-target-never-gains-edge.md",
    ".wavefoundry/framework/scripts/graph_indexer.py",
    ".wavefoundry/framework/scripts/tests/test_graph_incremental_merge.py",
    "docs/architecture/graph-index-system.md",
    "CHANGELOG.md"
  ],
  "tree_fingerprint": {
    "docs/waves/1x5tq later-created-doc-link-targets/1x8e1-bug doc-link-into-later-created-target-never-gains-edge.md": "8976db622280c6eb72d6740790c12b3049afceca",
    ".wavefoundry/framework/scripts/graph_indexer.py": "da952e74b12d8a428a5399456b586f7c1079c066",
    ".wavefoundry/framework/scripts/tests/test_graph_incremental_merge.py": "84e1593d89720d62d6cee3a20abf83fe9c8a7520",
    "docs/architecture/graph-index-system.md": "4d67a26e3a9d3023430cce2d2f935b61d64472ca",
    "CHANGELOG.md": "a058e60570e866df18f9f7d9d8bc08558247d04e"
  },
  "time_budget": "180 seconds per seat",
  "sweep_rule": "readiness current-tree feasibility; no delivery implementation claims",
  "primer_depth": "full",
  "architecture_refs": [
    "docs/architecture/graph-index-system.md"
  ],
  "explicit_non_goals": [
    "implementation edits",
    "delivery approval",
    "symbol mentions",
    "delete side redesign"
  ]
}
```

## Baseline probe source

```python
import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path('/Users/coryhacking/Developer/wavefoundry')
sys.path.insert(0,str(ROOT/'.wavefoundry/framework/scripts/tests'))
import test_graph_incremental_merge as t
rows=[]
for target,body in [('src/later.py','def later():\n    return 1\n'),('assets/.gitignore','cache/\n')]:
 with tempfile.TemporaryDirectory() as tmp:
  mod=t.load_graph_indexer(); d=t._RepoDriver(mod,Path(tmp))
  d.write('docs/linker.md',f'See [later](../{target}).\n')
  first=d.build_incremental(set(d.files))
  assert not t._find_edges(first,target=target)
  d.write(target,body)
  added=d.build_incremental({target})
  d.write('unrelated.py','X = 2\n')
  inc=d.build_incremental({'unrelated.py'}); full=d.build_oracle()
  assert not t._find_edges(inc,target=target)
  assert t._find_edges(full,target=target)
  rejected=False
  try: t._IncrementalMergeBase().assert_equivalent(inc,full,'known-bad pre-fix')
  except AssertionError: rejected=True
  assert rejected
  repaired=d.build_incremental({'docs/linker.md'})
  t._IncrementalMergeBase().assert_equivalent(repaired,d.build_oracle(),'explicit doc scan positive control')
  rows.append({'target':target,'incremental_edges':len(t._find_edges(inc,target=target)),'full_edges':len(t._find_edges(full,target=target)),'known_bad_rejected':rejected,'explicit_rescan_equivalent':True})
with tempfile.TemporaryDirectory() as tmp:
 mod=t.load_graph_indexer(); d=t._RepoDriver(mod,Path(tmp));d.write('docs/linker.md','See [later](../assets/.gitignore).\n')
 first=d.build_incremental(set(d.files));d.write('unrelated.py','X = 2\n')
 from unittest.mock import patch
 with patch.object(mod.GraphIndexSession,'_extract_doc_artifact',autospec=True,side_effect=mod.GraphIndexSession._extract_doc_artifact) as spy:
  inc=d.build_incremental({'unrelated.py'})
  assert spy.call_count==0,spy.call_count
 t._IncrementalMergeBase().assert_equivalent(inc,d.build_oracle(),'unresolved negative control')
 rows.append({'target_still_absent':True,'doc_rescans':spy.call_count,'oracle_equivalent':True})
print(json.dumps(rows,indent=2))
```

## Baseline probe output

```json
[
  {
    "target": "src/later.py",
    "incremental_edges": 0,
    "full_edges": 1,
    "known_bad_rejected": true,
    "explicit_rescan_equivalent": true
  },
  {
    "target": "assets/.gitignore",
    "incremental_edges": 0,
    "full_edges": 1,
    "known_bad_rejected": true,
    "explicit_rescan_equivalent": true
  },
  {
    "target_still_absent": true,
    "doc_rescans": 0,
    "oracle_equivalent": true
  }
]
```

## Deferred-read recovery probe source

```python
import json,sys,tempfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path('/Users/coryhacking/Developer/wavefoundry')
sys.path.insert(0,str(ROOT/'.wavefoundry/framework/scripts/tests'))
import test_graph_incremental_merge as t
rows=[]
with tempfile.TemporaryDirectory() as tmp:
 mod=t.load_graph_indexer();d=t._RepoDriver(mod,Path(tmp))
 d.write('docs/linker.md','See [later](/assets/.gitignore).\n')
 d.build_incremental(set(d.files));d.write('assets/.gitignore','cache/\n')
 outage=d.build_incremental({'assets/.gitignore'},unreadable_dirs={'docs'})
 recovered=d.build_incremental(set());full=d.build_oracle()
 assert not t._find_edges(recovered,target='assets/.gitignore')
 assert t._find_edges(full,target='assets/.gitignore')
 rejected=False
 try:t._IncrementalMergeBase().assert_equivalent(recovered,full)
 except AssertionError:rejected=True
 assert rejected
 rows.append({'case':'target added while referring doc unreadable; no-change recovery','incremental_edges':0,'full_edges':1,'known_bad_rejected':True})
print(json.dumps(rows,indent=2))
```

## Deferred-read recovery output

```json
[
  {
    "case": "target added while referring doc unreadable; no-change recovery",
    "incremental_edges": 0,
    "full_edges": 1,
    "known_bad_rejected": true
  }
]
```

## Fresh QA reverification

# QA readiness reverification — COUNCIL-READY-1, cycle 1

Verdict: QA readiness blocker resolved by the plan repair. Clear only qa-reviewer; reality-checker remains blocking. This is not delivery approval.

Reviewer: qa-reviewer, fresh context codex-qa-reverify-1x8e1-20260905-fresh-independent. I did not author or implement the repair. I independently read the final requirements, ACs, tasks and risks and inspected/executed their current-tree fixture boundary. Prior finding and coordinator summaries served as scope orientation, not verdict evidence.

Final plan hash verified: f4ad1340568aa704aa0641c7bc4246d72b66fcd8. All four packet source hashes remain unchanged.

| Requirement | Independent plan assessment |
| --- | --- |
| AC-1 | Requirements 1-3 bind eligibility to each document's retained unresolved intersection with current paths, before the zero-change return, including node-less targets. They require retention across unreadable skips and failed reads until successful extraction, both artifact and summary persistence, closed/reopened session inspection, exact doc node and edge source/target/relation assertions plus assert_equivalent, target-only/unchanged/unrelated builds, and unchanged recovery. These address the original deficient contract without claiming implementation completion. |
| AC-2 | Intersection-based selection, never-appearing negative controls, resolved-target cessation, no unaffected text reads, no duplicate merge-state reads, and existing zero-change row/write cost assertions are explicit. Whole-blob decode cost is honestly acknowledged. |
| AC-3 | Relevant suites, version pins and edited-document validation remain required and unchecked. This review neither executes nor approves future delivery suites. |

Executed commands: python3 -B /tmp/1x8e1-readiness/probe.py and python3 -B /tmp/1x8e1-readiness/recovery_probe.py, both exit 0 with no skips. Source validation through MCP code_outline and targeted code_read confirmed _RepoDriver._build dispatches update_graph_index using real temporary files and faithful walk-shadowed metadata; assert_equivalent compares node sets, edge keys and input fingerprint. GraphIndexSession.finalize directly confirms the existing zero-change return is before merge-state acquisition.

| Selected control | Observed |
| --- | --- |
| noded src/later.py created after referring doc | Incremental 0 target edges; oracle 1; equivalence assertion rejects known bad. Explicit referring-doc scan restores equivalence. |
| node-less assets/.gitignore created after referring doc | Incremental 0 target edges; oracle 1; equivalence assertion rejects known bad. Explicit referring-doc scan restores equivalence. |
| target never created | Unrelated merge performs zero doc extraction calls and equals oracle. |
| target appears while referring doc is walk-shadowed, then unchanged recovery | Recovery still has 0 target edges versus oracle 1 and is rejected. This proves the baseline failure, not a repaired product. |

Independent reference: directly read AC-1/AC-2 and the original defect reproduction. The differential oracle shares the extractor; it is not a materially independent implementation. Presence/absence assertions and the positive rescan control mitigate that common mode for the selected cases. Future exact graph assertions, persisted-state checks and cost spies in the plan strengthen delivery evidence.

Mutation table: no implementation landed, so no delivered mechanism was mutated. The finite readiness budget used existing pre-fix behavior as its known-bad control. No broad scan or suite was run. Failed-read retry, persisted unresolved-state round trips, exact source/relation assertions, resolved-rescan cessation and cost assertions are mandatory planned delivery checks, not executed product evidence. Actual index-build entry reachability is explicitly required before delivery; any necessary caller expansion must update scope and re-Prepare.

The focused plan repair introduces no replacement QA blocker observed in this review. Submitted judgment preserves real/admitted/required_ac and records repair_execution_state completed for documentation only. No approval event or ledger write performed. Exact caller input is qa-reverification.json with mode dry_run for coordinator validation.

## Fresh reality-checker reverification

# Reality-checker cycle-1 readiness reverification

Verdict: COUNCIL-READY-1 plan omission resolved; clear the reality-checker lane after QA. Product behavior remains unimplemented and known-bad. No implementation AC/task is completed by this review.

Fresh independent context: codex-1x8e1-reality-reverification-independent-20260905-1554. I performed no repair, repository edit, or ledger write; inspected final text, verified fingerprints, inspected GraphIndexSession.finalize through MCP outline/targeted reads, and reran both probes myself.

Plan hash verified: `f4ad1340568aa704aa0641c7bc4246d72b66fcd8`. All four implementation/test/architecture/changelog fingerprints match packet.json.

| Assumption | Verification and disposition |
| --- | --- |
| A creation transition is enough | Refuted by baseline/recovery probes; Requirements 1 and 2 explicitly require per-doc unresolved-current intersection before fast return, retained until successful extraction. Resolved as a plan omission. |
| Artifact-only metadata persists | Current finalize copies a fixed summary allowlist. Requirement 2 and implementation task explicitly cover both extraction artifacts and fragment summaries, including zero-edge documents. Resolved as a plan omission; persistence tests still required. |
| Oracle equality alone proves repair | Requirement 3 and AC-1 require exact doc node, edge source/target/relation, node-less target absence, oracle equality, reopened persistent state and target-only/unchanged/unrelated/recovery sequences. Resolved as a plan omission. |
| Selective repair is cost-free | Requirement 2 explicitly acknowledges whole-blob decode cost and requires reuse/no unaffected text reads; AC-2 requires absent-target/no-repeat controls and existing row/write assertions. No measured latency claim made. |
| Full upstream build always reaches merge on recovery | Unknown: fixtures reach update_graph_index through _RepoDriver only. Task 3 explicitly requires actual entry-path verification before delivery and scope update/re-Prepare for any additional caller edit. Accepted for readiness with this mandatory delivery obligation. |

Executed: `python3 -B /tmp/1x8e1-readiness/probe.py` and `python3 -B /tmp/1x8e1-readiness/recovery_probe.py`, both exit 0 with no skipped steps. For both src/later.py and assets/.gitignore, incremental graph has 0 matching edges versus oracle 1; assert_equivalent rejects the known-bad result, and explicit doc rescan restores oracle equality. Never-created target yields zero doc rescans and oracle equality. Walk-shadowed doc followed by unchanged recovery again yields 0 versus 1 and a rejected differential.

These are readiness-safe known-bad controls, not green repair tests. Direct plan inspection establishes contract presence only. Exact graph identity, failed-read recovery, persistence/reopen and cost tests prescribed by the revised plan have not run against a proposed implementation. No upstream dispatch, network or broad suite was executed. The shared oracle extractor remains a limitation; selected edge-presence and explicit rescan controls reduce common-mode error only for these cases.

No new concrete readiness blocker found in the focused repair scope. Preserve real/admitted/required_ac judgment and do_now classification; repair_execution_state=completed refers solely to plan clarification. Caller JSON is reality-reverification.json; blocking_required_lanes=[] assumes QA has already independently cleared its lane and must not be submitted before that transition.

## Final independent council decision

# Final focused readiness synthesis — wave 1x5tq / change 1x8e1

Verdict: approve wave-council-readiness. COUNCIL-READY-1's plan omission is resolved. Record only after the coordinator has sequentially submitted fresh QA and reality reverification. No repository or ledger writes were made by this reviewer.

## Scope and independence

Fresh context codex-1x8e1-final-council-fresh-20260905; I did not implement the plan or product repair. I directly read the current admitted plan through MCP, inspected GraphIndexSession.finalize's fast return, skip/read failure and summary allowlist, inspected the real _RepoDriver._build dispatch, reran both bounded probes, and recomputed the frozen hashes. Prior council history framed the correction scope, not evidence of its completion. I then assessed fresh QA/reality reports against my current-tree evidence.

Final plan hash: f4ad1340568aa704aa0641c7bc4246d72b66fcd8, rechecked at conclusion. Four source hashes remain identical to packet.json: graph_indexer da952e74b12d8a428a5399456b586f7c1079c066; merge tests 84e1593d89720d62d6cee3a20abf83fe9c8a7520; graph architecture 4d67a26e3a9d3023430cce2d2f935b61d64472ca; CHANGELOG a058e60570e866df18f9f7d9d8bc08558247d04e.

This is focused repair replay and final synthesis, not a new full council. The prior full red-team primer, four isolated fixed seats (architecture, security, QA, reality), rotating performance alternative and one challenge remain the initial council record. Original independent seat aggregate remains split / high; do not relabel historical votes unanimous. The single challenge established agreement on the remedy while preserving QA/reality blocks until actual repaired-text verification. Both fresh required rechecks now clear those plan blocks. This final approval is moderator judgment grounded in current evidence, not invented new fixed-seat votes.

## Resolution

- Requirements 1-2 now bind eligibility to retained per-doc unresolved targets intersecting current paths before zero-change, including node-less targets. Successful extraction alone replaces the obligation; skipped and failed reads retain it.
- Artifact and fragment-summary persistence, including zero-edge pruned documents, is explicit, with a builder bump.
- Requirement 3 and AC-1 require exact referring node and edge source/target/relation, node-less target absence, oracle equality, persistent state round trips, immediate target-only and unchanged/unrelated/recovery checks.
- AC-2 binds selectivity through never-appearing and already-resolved controls and retains existing zero-change row/write guarantees. One reused whole-state blob decode is allowed and its cost acknowledged.
- Task 3 requires real index-build entry-path recovery reachability before delivery; any necessary caller expansion must update scope and re-Prepare.

The red-team challenge about globally consumed creation transitions is therefore addressed. QA and reality independently verified these commitments and replayed the same baseline controls. No required specialist blocker is waived.

## Alternative and improvements

The strongest distinct alternative remains retaining raw explicit-link candidates and resolving availability at assembly, avoiding source rereads and parsing on target arrival. All initial fixed seats weighed it in the one challenge. It changes edge ownership, candidate metadata and outage/deletion contracts beyond this narrow repair. Retained per-doc unresolved-current retries remain the smaller supported choice; a global path snapshot still needs per-doc acknowledgment and blanket rescans violate selectivity. No speculative backlog is created.

Concrete improvements from review are now binding plan requirements: durable retries, dual persistence, absolute graph assertions, recovery and cost controls. Implementation must fulfill them before delivery approval; no further readiness text change is warranted.

## Personally executed evidence

Both python3 -B /tmp/1x8e1-readiness/probe.py and recovery_probe.py exited 0, with no selected checks skipped.

| Cell | Observed |
| --- | --- |
| Later-created src/later.py | 0 incremental target edges versus oracle 1; differential rejects; explicit doc rescan restores equality |
| Later-created node-less assets/.gitignore | 0 incremental target edges versus oracle 1; differential rejects; explicit doc rescan restores equality |
| Never-created target | 0 doc rescans on unrelated merge; oracle equality |
| Target appears while doc walk-shadowed, then unchanged recovery | 0 incremental target edges versus oracle 1; differential rejects |

These are readiness-safe known-bad and legitimate controls, not passing repair tests. The corrected plan makes the missing implementation evidence explicit.

## Limitations and recording

Focused final synthesis, not a newly run full fixed-seat council. Original full primer/isolated seats/rotating alternative and one challenge are historical inputs; original pre-primer ordering was not independently sealed. This reviewer inspected current plan/code and executed its own probes; supplied history oriented scope, not proof. Plan only: product remains defective and all implementation ACs/tasks remain unchecked. Real upstream index-build dispatch, failed-read injection, exact source/relation/node assertions, persisted unresolved-state round trips, resolved-rescan cessation and cost verification remain mandatory future delivery checks. Oracle shares extraction implementation. Temporary unreadable_dirs models walk outage, not actual permissions. No broad suite or latency measurement. Initial bulk orientation output was truncated; load-bearing plan, protocol, targeted code, probe and recheck reads were complete. One code_outline call rejected unsupported options; corrected path-only call succeeded.

Root should preserve original and focused reports, both probe sources/results and this synthesis in docs/waves/1x5tq later-created-doc-link-targets/readiness-review.md before recording final-approval.json. That JSON contains exact typed approval caller facts and five honest integrity booleans. The coordinator owns sequential ledger recording, validation and final Prepare. This review approves readiness only; implementation ACs/tasks remain unchecked.
