# Summary5 independent delivery review — frozen first pass

Owner: Engineering
Status: active
Last verified: 2026-09-17

## Verdict and identity

**Needs revision. No delivery approval.** Code, architecture and docs-contract identify two repairable contract gaps below. Security has no evidenced attacker-boundary finding from this bounded pass; performance approval remains pending real CPU public-path timing and provider evidence. All five specialist lenses share reviewer `/root/summary5_delivery`, context `summary5-delivery-frozen-20260917`; this is one fresh independent review context, not five isolated reviews. This reviewer authored no production repair. QA separately reproduced the stale-source issue according to the coordinator; that is attributed evidence, not this reviewer's execution.

## Frozen scope and executed checks

All 12 reviewed file Git blob hashes matched `/private/tmp/wf-summary5-freeze.json` before and after the sweep. The packet is reproduced below. MCP code_outline/code_read inspected implementation, tests and contracts; direct targeted reads/diff supplemented them. No holdout queries or private precision packets were opened. No model inference, live index write, whole-suite run, lifecycle mutation or source edit occurred.

Python 3.13.5 on macOS ARM64 executed nine `MemoryQueryQualificationTests` successfully, then nine selected baseline checks and five in-memory function mutants. Every selected baseline passed. All five mutants were detected by their targeted test: widening summary checks to six, weakening cutoff to -5, restoring confidence order, ignoring incomplete coverage, accepting nonfinite qualification. No survivors required whole-file testing. The selected checks also exercised brief/queryless ordering, SQL grouping/read-only hash invariance, the GPU-discovering factory trap, and preservation of the shared commit-time global. These are mocked provider tests, not real CPU/provider or platform qualification.

An initial command accidentally selected Apple's Python 3.9 after PATH adjustment and failed importing `tomllib`; it is an environment setup failure, not test evidence. All reported results above used explicit `/opt/homebrew/bin/python3` and `/Library/Developer/CommandLineTools/usr/bin` for Git.

## Finding S5-STALE-SOURCE

- Disposition: `do_now`; category `required_ac`; AC-4; required lanes code-reviewer, architecture-reviewer, docs-contract-reviewer. High confidence; correctness/contract gap, not an attacker escalation.
- Locations at this freeze: `server_impl.py:11768` and `:11788`; `sqlite_vector_store.py:250`; required promise `docs/specs/mcp-tool-surface.md:880`, `docs/architecture/search-architecture.md:554`, admitted plan Production integration decision.
- Proposition: completed build generation plus matching path coverage does not prove the eligible memory vectors correspond to current memory text.
- Public probe: actual `memory_search_response`, actual `WaveIndex._ensure_loaded`, actual `dense_path_scores` SQL over a read-only temporary database. Stable completed token, embedding distance and reranker are deterministic seams. First call has matching fixture source/vector; then change source summary without changing path or completed epoch and call again.
- Expected: stale source produces lexical-policy/unavailable with explicit recovery; unchanged adjacent control remains hybrid/model_relevance.
- Observed: both calls returned `method=hybrid_rrf`, `qualification=model_relevance`, `fallback_reason=null`; second returned the revised summary. SQL made only SELECTs and database SHA-256 was unchanged. Source hash changed while path coverage stayed complete.
- Root cause: freshness check only observes build epoch and coverage only counts paths. Neither verifies current eligible bytes against published indexed provenance. This can change dense candidate coverage/ranking while claiming the contracted healthy path.
- Repair: compare eligible memory source hashes against canonical published docs provenance within the read snapshot, without scanning unrelated files or auto-repair. Missing/mismatched provenance must recover explicitly. Add real producer-shaped positive/mismatch tests. Re-run focused review and CPU timing after repair.
- Limitation: the completed token and distance kernel are controlled; this did not mutate the actual live index or establish concurrent publication behavior.

## Finding S5-MODEL-RECOVERY-GUIDANCE

- Disposition: `do_now`; category `required_ac`; AC-4/AC-7; required lanes code-reviewer, docs-contract-reviewer. High confidence; recovery guidance defect, not a security boundary defect.
- Locations: `server_impl.py:1573`, `:1578`, `:11892`, `:30394`; public recovery wording in the named tool/reference/architecture docs.
- Proposition: a transient CPU constructor failure is latched for the same model until runtime teardown, but the public diagnostic only directs the caller to `index_health()` and docs omit the required restart.
- Public probe: use actual `memory_search_response` and actual `_get_memory_reranker`, a controlled dense source and factory sequence transient failure then valid CPU model. Both calls return `memory_relevance_model_unavailable`; factory called once despite provider recovery. Separate direct control resets the failure marker and the next construction succeeds. Teardown clearing the marker is source-verified, not an executed host restart.
- Expected: explicit model recovery guidance explaining that after remedying the load/provider condition the MCP runtime must restart (unless a separately implemented reset path exists).
- Observed: both fallback responses say only `recovery_tools=[index_health]`, `recovery_usage=index_health()`. No model-specific restart remedy is provided.
- Repair: retain failure caching and safe lexical fallback, document/reset guidance explicitly in diagnostic and public docs. Do not add an automatic per-query retry loop merely to satisfy this review.

## Remaining lane assessment

Code and architecture: first-five/threshold/order, malformed output recovery, eligibility, compact archive identity and historical lexical recovery have passing finite public-path controls. The stale-source contract remains unmet. Diff preserves queryless policy/brief/advisory implementation and ordinary code/docs rankers; targeted controls corroborate the relevant boundaries, not every unrelated path.

Security: current trusted local operator/repository threat assumptions remain. Path resolution is confined to root; SQL binds paths through JSON parameters, including the quote-bearing test case, and opens read-only. SQL trace/hash controls passed. Exceptions do not expose private query/error text in response. The CPU factory trap and global sentinel tests pass; actual native provider construction is still pending. No new credible attacker-controlled privilege delta was established, so these correctness findings are not severity-inflated security claims.

Performance: caps are output/materialization bounds, not scan bounds. Docs correctly disclose full eligible SQL/BM25 scaling, 100-call p95 <=500 ms and baseline/material-gain gates, prototype-only 200/694 ms measurements, and single-machine limits. Actual production timing, cold initialization and extra resident model memory are pending; no performance approval from mocked tests.

Docs-contract: frozen parameters, support-unverified semantics, calling-agent judgment and the explicitly revised empty-result acceptance rule align. Public stale-index and model recovery promises need the repairs above. Prototype evidence is correctly separated from production delivery evidence; no host-agent search service is claimed.

## Typed evidence facts

For both findings: phase `delivery`, claim_kind `finding`, required_for_approval true, execution_status `executed`, probe_class `local_safe`, authorization_status `authorized`, safe_boundary false, universal_claim false. The public path is `memory_search_response`. Use distinct finding IDs above and matching lane actors with this shared context. `fresh_context=true`, `independent=true`; reviewer made no repair.

Integrity: test_ran_without_unintended_skip=true; public_path_reached=true; boundary_values_realistic=true; assertions_non_vacuous=true; known_bad_detected=true; known_bad_detection_method=controlled stale-source/cached-failure reproduction with adjacent unchanged/reset controls and five safe in-memory mutants. The desired rejection/remedy assertions are currently violated; do not mark findings as resolved. Counterexample to repair: changed current source still reports model_relevance, or a latched provider failure still lacks actionable restart guidance.

Safety: fixture writes confined to temporary directories; SQLite fixture read-only during probes; fault mutants affect only the subprocess module object and are restored; production 12-file hashes unchanged. Timing and live model probes were intentionally held at coordinator request, so they provide no approval evidence.

## Frozen packet

```json
{
  ".wavefoundry/framework/scripts/server_impl.py": "7c1f58f3d4fdc22a46baa1b41e7422f40c4d3cd6",
  ".wavefoundry/framework/scripts/memory_eval.py": "d3fb6eab2085d6a9a2c30dd0b5769faab2eb6587",
  ".wavefoundry/framework/scripts/sqlite_vector_store.py": "4c25b4503c12ae94448f27813b66d05ca354eca1",
  ".wavefoundry/framework/scripts/tests/test_memory_records.py": "b06dd2aca670292c92c8f867dfac7375c979853d",
  ".wavefoundry/framework/scripts/tests/test_memory_eval.py": "81c15292e8b2ef2e749d9c5c28ecd363d001bd5d",
  ".wavefoundry/framework/scripts/tests/eval/memory_golden.json": "3376a0ddfe241216c8f049632bc171233b0d4251",
  "docs/specs/mcp-tool-surface.md": "fa842d94294a4f1e4e5e89fff88a8927d963427d",
  "docs/architecture/search-architecture.md": "b91414e2898d49d9396824d391bafad86fe19302",
  "docs/architecture/performance-budget.md": "e1985d7adafb1540398522f43add84c646ce6907",
  "docs/architecture/testing-architecture.md": "0f85ffabe521338460f7a721c02a9d1631e83e1b",
  "docs/references/memory-retrieval-eval.md": "a9cc2420b1abe495a1ed0902687431f6e7d6ea3e",
  "CHANGELOG.md": "5dae3b6f20602db9bc716c422573171def3add1a"
}
```

## Reproduction scripts

Run each with `PATH=/Library/Developer/CommandLineTools/usr/bin:$PATH /opt/homebrew/bin/python3 -B <script>`. The second script imports the first script preamble; retain the shown scratch filenames when reproducing. Paths are local review artifacts, not production requirements.

### wf-summary5-review-controls.py

```python
import sys,json,threading,sqlite3,struct,hashlib,io,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
S=Path('/Users/coryhacking/Developer/wavefoundry/.wavefoundry/framework/scripts')
sys.path[:0]=[str(S),str(S/'tests')]
import test_memory_records as t
import sqlite_vector_store as store
import accel_embedder
case=t.MemoryQueryQualificationTests();case.setUp();srv=case.srv
try:
 p=case._add('mem-a','decision');before=hashlib.sha256(p.read_bytes()).hexdigest()
 db=case.root/'fixture.sqlite';c=sqlite3.connect(db);c.executescript('CREATE TABLE chunks_docs(id INTEGER PRIMARY KEY,path TEXT); CREATE TABLE vectors_docs(chunk_id INTEGER PRIMARY KEY,embedding BLOB);')
 rel=p.relative_to(case.root).as_posix();c.execute('INSERT INTO chunks_docs VALUES(1,?)',(rel,));c.execute('INSERT INTO vectors_docs VALUES(1,?)',(struct.pack('<f',0.1),));c.commit();c.close()
 traces=[]
 def readonly(_):
  c=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True);c.set_trace_callback(traces.append);c.create_function('vec_distance_cosine',2,lambda a,b:struct.unpack('<f',a)[0]);return c
 idx=object.__new__(srv.WaveIndex);idx.index_dir=case.index_dir;idx._loaded=True;idx._loaded_meta_signature={'project':('completed',1)};idx._docs_vector_layer='docs';idx._index_meta_signature=lambda d:('completed',1)
 idx._memory_candidate_scores=lambda q,paths:store.dense_path_scores(case.index_dir,'docs',[1.0]*store.DIMENSIONS,paths)
 idx._get_memory_reranker=lambda:SimpleNamespace(rerank=lambda q,texts:[0.0]*len(texts))
 original=hashlib.sha256(db.read_bytes()).hexdigest()
 with patch.object(store,'_open',side_effect=readonly):
  fresh=srv.memory_search_response(case.root,query='lesson',index=idx)
  p.write_text(p.read_text().replace('Lesson from mem-a.','Completely revised current lesson.'))
  stale=srv.memory_search_response(case.root,query='lesson',index=idx)
 print(json.dumps({'fresh':fresh['data']['retrieval'],'source_changed':before!=hashlib.sha256(p.read_bytes()).hexdigest(),'stale':stale['data']['retrieval'],'stale_return_summary':stale['data']['records'][0]['summary'],'database_unchanged':original==hashlib.sha256(db.read_bytes()).hexdigest(),'sql_statements':traces},indent=2))
 idx=object.__new__(srv.WaveIndex);idx._reranker_lock=threading.Lock();idx._indexer_constant=lambda n:'same-model';idx._reranker=None
 cpu=SimpleNamespace(provider='CPUExecutionProvider',model_name='same-model')
 with patch.object(accel_embedder,'_reranker_disabled',return_value=False),patch.object(accel_embedder,'StaticShapeReranker',side_effect=[RuntimeError('transient'),cpu]) as construct:
  first=idx._get_memory_reranker();second=idx._get_memory_reranker();idx._memory_reranker_failed_model=None;third=idx._get_memory_reranker()
 print(json.dumps({'transient_first_none':first is None,'second_still_none':second is None,'after_reset_recovers':third is cpu,'constructor_calls':construct.call_count}))
finally:case.doCleanups()
```

### wf-summary5-recovery-public.py

```python
exec(open('/private/tmp/wf-summary5-review-controls.py').read().split('case=t.MemoryQueryQualificationTests()')[0])
case=t.MemoryQueryQualificationTests();case.setUp();srv=case.srv
try:
 case._add('mem-a','decision');idx=case._semantic_index('mem-a');idx._reranker_lock=threading.Lock();idx._indexer_constant=lambda n:'same-model';idx._reranker=None;idx._memory_reranker=None;idx._memory_reranker_failed_model=None
 idx._get_memory_reranker=lambda:srv.WaveIndex._get_memory_reranker(idx)
 cpu=SimpleNamespace(provider='CPUExecutionProvider',model_name='same-model',rerank=lambda q,texts:[0.0]*len(texts))
 with patch.object(accel_embedder,'_reranker_disabled',return_value=False),patch.object(accel_embedder,'StaticShapeReranker',side_effect=[RuntimeError('transient'),cpu]) as construct:
  responses=[srv.memory_search_response(case.root,query='lesson',index=idx) for _ in range(2)]
  print(json.dumps({'responses':[{'retrieval':r['data']['retrieval'],'diagnostics':r['diagnostics']} for r in responses],'constructor_calls':construct.call_count},indent=2))
finally:case.doCleanups()
```

### wf-summary5-review-mutants.py

```python
import sys,unittest,io,ast,inspect,json
from pathlib import Path
from unittest.mock import patch
S=Path('/Users/coryhacking/Developer/wavefoundry/.wavefoundry/framework/scripts');sys.path[:0]=[str(S),str(S/'tests')]
import test_memory_records as t
import test_memory_eval as e
srv=t.load_server()
checks=[(t.MemoryQueryQualificationTests,'test_five_summary_checks_no_refill_and_rrf_order_is_preserved'),(t.MemoryQueryQualificationTests,'test_relevance_failure_never_returns_unchecked_semantic_hits'),(t.MemoryQueryQualificationTests,'test_missing_stale_code_only_incomplete_and_model_disabled_recover_lexically'),(t.MemoryQueryQualificationTests,'test_cpu_reranker_is_isolated_cached_and_respects_disable'),(t.MemorySearchOrderingTests,'test_query_relevance_can_precede_confidence_without_claiming_authority'),(t.MemorySearchOrderingTests,'test_query_relevance_can_cross_kind_without_changing_queryless_policy'),(t.MemorySearchOrderingTests,'test_brief_remains_queryless_and_exact_target_promoted'),(e.QualificationTests,'test_scoped_sql_groups_before_limit_and_preserves_database'),(e.MemoryEvalTests,'test_curated_pass_never_rebinds_the_shared_commit_times_global')]
def run(cls,name):
 out=io.StringIO();r=unittest.TextTestRunner(stream=out).run(unittest.TestSuite([cls(name)]));return r.wasSuccessful(),out.getvalue()
print('BASELINE',[(n,run(c,n)[0])for c,n in checks])
mutants=[('cap6','_memory_query_records','[:MEMORY_QUERY_CHECK_CAP]','[:6]',checks[0]),('threshold-5','_memory_query_records','score >= MEMORY_QUERY_MIN_LOGIT','score >= -5',checks[0]),('trust-sort','memory_search_response','ranked.sort(key=lambda pair: query_order[pair[0]["memory_id"]])','ranked.sort(key=lambda pair: -pair[0].get("confidence",0))',checks[4]),('unchecked-incomplete','_memory_query_records','if not dense["complete"]:','if False:',checks[2]),('unchecked-inf','_memory_query_records','if not all(math.isfinite(value) for value in values):','if False:',checks[1])]
for label,fn,old,new,(cls,test) in mutants:
 src=inspect.getsource(getattr(srv,fn));assert old in src
 ns={};exec(compile(src.replace(old,new),'<safe-memory-mutant>','exec'),srv.__dict__,ns)
 with patch.object(srv,fn,ns[fn]): good,out=run(cls,test)
 print('MUTANT',label,'DETECTED' if not good else 'SURVIVED',out.strip().splitlines()[-1])
```
