# Production memory policy baseline

Owner: Engineering
Status: active
Last verified: 2026-09-16

Independent QA execution by `/root/memory_holdout`. Result: **14/14 controls passed**, including the existing 11/11 hermetic invariants. This is a preserved-production baseline, not finalist qualification or holdout scoring.

Command from repository root: `/Users/coryhacking/.wavefoundry/venv/bin/python -B /private/tmp/wf_policy_probe.py`. macOS ARM64, Python 3.13.5; no embeddings or reranking, deterministic semantic hit stubs. All corpus and database writes occurred inside auto-cleaned `TemporaryDirectory` roots. No live memory/index writes or source edits occurred. Source hashes and exact environment follow.

The controls cover absent/broken semantic index equivalence and an empty query match, default exclusions despite adversarial semantic hits, explicit status and history inclusion, two simultaneous compact archive entries versus historical archive bodies, target/symbol restriction before semantic ranking, and contrary active claims. Production puts the higher-confidence old claim before a lower-confidence newer semantic hit and leaves both active: order is not contradiction resolution.

## Pre-scoring fixture erratum

The frozen `qualification-queries.json` policy-only case `policy-archive-02` records `required_record_types` as `memory` for an archived body. This is a label-schema error: the canonical loader/public response labels it **`archive_body`**. The executed two-archive control below proves the distinction. Apply that explicit correction when executing the policy control; retain the frozen file/hash and cite this erratum. The 24 relevance holdout cases and their judgments are unaffected. No holdout scoring had occurred when this was found.

Two scratch-harness authoring errors preceded the successful execution: the first expected nonexistent `overall.passed/total` fields instead of `invariants_passed/invariants_total`; the second attempted to archive protected decision fixtures without the required authorization. The harness was corrected to read the actual metrics and use unprotected successful-pattern archive fixtures. Neither failure required changing production behavior or bypassing protection.

## Executed report

```json
{
  "environment": {
    "python": "3.13.5 (main, Jun 11 2025, 15:36:57) [Clang 17.0.0 (clang-1700.0.13.3)]",
    "executable": "/Users/coryhacking/.wavefoundry/venv/bin/python",
    "platform": "macOS-27.0-arm64-arm-64bit-Mach-O",
    "machine": "arm64",
    "root": "/Users/coryhacking/Developer/wavefoundry",
    "native_acceleration": "none; deterministic semantic stubs, no embedding/reranking"
  },
  "sources": {
    "server_impl.py": "ce4aef8264e1cdd246b7808a5d8d3e71948768d3140afc9be8cb2b81d283bbb3",
    "memory_eval.py": "960be3a3cf4203539c8d7c2b887284986f92632cb4fec3055dc59e5fa48966ba",
    "memory_records.py": "0b7c5024f82a21468f383bb5a53cd85c49115c8f1d32239dd4988e1c558e8ace"
  },
  "checks": [
    {
      "name": "existing_hermetic_golden",
      "passed": true,
      "detail": {
        "recall_at_k": 1.0,
        "mrr": 1.0,
        "invariants_passed": 11,
        "invariants_total": 11,
        "candidate_invariants_passed": 11
      }
    },
    {
      "name": "unavailable_fallback:known lexical",
      "passed": true,
      "detail": {
        "records": [
          "mem-policy-active",
          "mem-policy-candidate"
        ],
        "diagnostics": []
      }
    },
    {
      "name": "unavailable_fallback:alpha",
      "passed": true,
      "detail": {
        "records": [
          "mem-policy-active"
        ],
        "diagnostics": []
      }
    },
    {
      "name": "unavailable_fallback:there_is_no_such_policy",
      "passed": true,
      "detail": {
        "records": [],
        "diagnostics": [
          "no_memory_matches"
        ]
      }
    },
    {
      "name": "default_statuses_exclude_even_semantic_hits",
      "passed": true,
      "detail": [
        "mem-policy-active",
        "mem-policy-candidate"
      ]
    },
    {
      "name": "history_admits_retired",
      "passed": true,
      "detail": [
        "mem-policy-active",
        "mem-policy-candidate",
        "mem-policy-stale",
        "mem-policy-super",
        "mem-policy-rejected"
      ]
    },
    {
      "name": "explicit_status_only",
      "passed": true,
      "detail": [
        "mem-policy-rejected"
      ]
    },
    {
      "name": "multiple_archive_entries_are_compact",
      "passed": true,
      "detail": {
        "types": [
          [
            "mem-archive-live",
            "memory"
          ],
          [
            "mem-archive-one",
            "archive_register_entry"
          ],
          [
            "mem-archive-two",
            "archive_register_entry"
          ]
        ],
        "count": 2
      }
    },
    {
      "name": "history_archive_bodies",
      "passed": true,
      "detail": {
        "types": [
          [
            "mem-archive-one",
            "archive_body"
          ],
          [
            "mem-archive-two",
            "archive_body"
          ]
        ],
        "count": 2
      }
    },
    {
      "name": "target_symbol:{'target': 'src/one.py'}",
      "passed": true,
      "detail": [
        "mem-target-one"
      ]
    },
    {
      "name": "target_symbol:{'symbol': 'Widget.run'}",
      "passed": true,
      "detail": [
        "mem-target-one"
      ]
    },
    {
      "name": "target_symbol:{'target': 'src/one.py', 'symbol': 'Widget.run'}",
      "passed": true,
      "detail": [
        "mem-target-one"
      ]
    },
    {
      "name": "confidence_precedes_relevance_and_recency",
      "passed": true,
      "detail": [
        "mem-claim-old",
        "mem-claim-new"
      ]
    },
    {
      "name": "conflicting_claims_not_auto_superseded",
      "passed": true,
      "detail": null
    }
  ],
  "pass_count": 14,
  "check_count": 14
}
```

## Reusable scratch probe

Save this block outside the repository and run it from the repository root with the dependency-equipped interpreter and `-B`. It writes only temporary fixtures and emits the report to stdout.

```python
import json,sys,tempfile,platform,hashlib
from pathlib import Path
root=Path.cwd();sys.path.insert(0,str(root/'.wavefoundry/framework/scripts'))
import memory_eval as e,server_impl as s
m=s._memory_mod();checks=[]
def check(name,value,detail=None):checks.append({'name':name,'passed':bool(value),'detail':detail})
def ids(response):return [x['memory_id'] for x in response['data']['records']]
def rec(mid,summary,status='active',**kw):return dict(memory_id=mid,kind=('successful_pattern' if kw.get('archive') else 'decision'),confidence=.9,status=status,summary=summary,evidence=['fixture-policy-evidence'],targets=['src/policy.py'],created='2026-09-16',**kw)
with tempfile.TemporaryDirectory(prefix='wf-policy-only-') as temp:
 p=Path(temp)/'golden';p.mkdir();gold=e.run(p);check('existing_hermetic_golden',gold['overall']['invariants_passed']==gold['overall']['invariants_total'],gold['overall'])
 p=Path(temp)/'faults';p.mkdir();e.build_corpus(p,[rec('mem-policy-active','Known lexical policy alpha'),rec('mem-policy-candidate','Known lexical candidate beta','candidate'),rec('mem-policy-stale','Known lexical stale guidance','stale'),rec('mem-policy-rejected','Known lexical rejected guidance','rejected'),rec('mem-policy-super','Known lexical superseded guidance','superseded',superseded_by='mem-policy-active')],m)
 class Broken:
  def search_docs(self,*a,**k):raise RuntimeError('intentional unavailable index')
 for query in ['known lexical','alpha','there_is_no_such_policy']:
  a=s.memory_search_response(p,query=query,index=None);b=s.memory_search_response(p,query=query,index=Broken());check('unavailable_fallback:'+query,ids(a)==ids(b) and not b['data']['semantic_assist'],{'records':ids(b),'diagnostics':[x['code'] for x in b['diagnostics']]})
 injected=e._StubIndex(['mem-policy-stale','mem-policy-rejected','mem-policy-super','mem-policy-active','mem-policy-candidate'])
 a=s.memory_search_response(p,query='unknown words',index=injected)
 check('default_statuses_exclude_even_semantic_hits',set(ids(a))=={'mem-policy-active','mem-policy-candidate'},ids(a))
 a=s.memory_search_response(p,query='known lexical',include_history=True,index=injected);check('history_admits_retired',len(ids(a))==5,ids(a))
 a=s.memory_search_response(p,query='known lexical',status='rejected',index=injected);check('explicit_status_only',ids(a)==['mem-policy-rejected'],ids(a))
 # Archive all records in one creation pass so both compact register entries coexist.
 p=Path(temp)/'archives';p.mkdir();e.build_corpus(p,[rec('mem-archive-one','Archived needle one','stale',archive=True),rec('mem-archive-two','Archived needle two','stale',archive=True),rec('mem-archive-live','Current needle advice')],m)
 a=s.memory_search_response(p,target='src/policy.py',limit=20)
 views=a['data']['records'];arch=[x for x in views if x['status']=='archived']
 check('multiple_archive_entries_are_compact',len(arch)==2 and all(x['record_type']=='archive_register_entry' and not x['summary'] for x in arch),{'types':[(x['memory_id'],x['record_type']) for x in views],'count':a['data']['archive_register_entry_count']})
 a=s.memory_search_response(p,query='archived needle',include_history=True);arch=a['data']['records'];check('history_archive_bodies',len(arch)==2 and all(x['record_type']=='archive_body' and x['summary'].startswith('Archived needle') for x in arch),{'types':[(x['memory_id'],x['record_type']) for x in arch],'count':a['data']['archived_body_count']})
 p=Path(temp)/'targets';p.mkdir();r1=rec('mem-target-one','Specific target alpha');r1['targets']=['src/one.py','symbol:Widget.run'];r2=rec('mem-target-two','Specific target beta');r2['targets']=['src/two.py','symbol:Other.run'];e.build_corpus(p,[r1,r2],m)
 idx=e._StubIndex(['mem-target-two','mem-target-one'])
 for selector in [{'target':'src/one.py'},{'symbol':'Widget.run'},{'target':'src/one.py','symbol':'Widget.run'}]:
  a=s.memory_search_response(p,query='specific target',index=idx,**selector);check('target_symbol:'+str(selector),ids(a)==['mem-target-one'],ids(a))
 p=Path(temp)/'conflict';p.mkdir();old=rec('mem-claim-old','Timeout is 30 seconds');old.update(confidence=.95,created='2024-01-01');new=rec('mem-claim-new','Timeout is now 60 seconds');new.update(confidence=.7);e.build_corpus(p,[old,new],m)
 a=s.memory_search_response(p,query='timeout',index=e._StubIndex(['mem-claim-new','mem-claim-old']));check('confidence_precedes_relevance_and_recency',ids(a)==['mem-claim-old','mem-claim-new'],ids(a));check('conflicting_claims_not_auto_superseded',all(x['status']=='active' and not x.get('superseded_by') for x in a['data']['records']))
report={'environment':{'python':sys.version,'executable':sys.executable,'platform':platform.platform(),'machine':platform.machine(),'root':str(root),'native_acceleration':'none; deterministic semantic stubs, no embedding/reranking'},'sources':{f:hashlib.sha256((root/'.wavefoundry/framework/scripts'/f).read_bytes()).hexdigest() for f in ['server_impl.py','memory_eval.py','memory_records.py']},'checks':checks,'pass_count':sum(x['passed'] for x in checks),'check_count':len(checks)}
print(json.dumps(report,indent=2));sys.exit(0 if all(x['passed'] for x in checks) else 1)
```
