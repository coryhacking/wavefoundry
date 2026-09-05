# Additional smoke tests — wave 1x5tq

Owner: Engineering
Status: active
Last verified: 2026-09-05

Operator-requested smoke pass after implementation. Result: **PASS**.

- Focused regression smoke: **16 tests, zero failures/errors/skips**, 8.475 seconds. Classes: `DryRunIdleMaintenanceTests`, `IdleDocLinkRecoveryTests`, and `LaterCreatedDocTargetTests`.
- Independent process smoke: **12 real CLI invocations**, six each for a Python target and a node-less `.gitignore` target. Every subprocess ran the checked-out `indexer.py --content graph` with the local tool-venv Python, real temporary SQLite/graph persistence and no embeddings or network.
- Both cases start with an absent link target, create it without modifying the referring doc, and inject an interrupted epoch through `begin_build_epoch`. CLI dry-run reports both `graph_recovery` and `dirty_epoch` and preserves persisted rows, artifact bytes and the epoch. A real build restores the exact doc node and EXTRACTED edge, completes the epoch, and matches a separate from-scratch build's node set, edge set and fingerprint. The node-less target remains without a node. Subsequent previews report no pending graph repair and preserve state.

The graph-only fixture leaves the semantic chunk index cold. Its initial standalone assertion that the entire index was idle failed on the correctly reported `chunk_heal`; the fixture was corrected to assert no pending **graph** repair while retaining strict dry-run state checks. Whole-index healthy-idle generation preservation is separately covered by the 16 focused tests with populated semantic tables. This pass found no new defect in the changed behavior.

SQLite transient WAL/SHM reader bookkeeping is excluded from the logical store snapshot; every persisted SQLite row and all other index artifact/Lance bytes are compared. This is smoke evidence, not a delivery-lane approval.

## Reproduction

Focused tests use the repository's existing classes under the local tool-venv Python with `-B`; outputs: `/tmp/1x5tq-smoke-regressions.log`. Standalone runner: `/tmp/1x5tq-cli-smoke.py`; result: `/tmp/1x5tq-cli-smoke-results.json`. Exact standalone fixture follows so the evidence survives temporary-file cleanup.

```python
import gzip, hashlib, json, os, sqlite3, subprocess, sys, tempfile
from pathlib import Path
REPO=Path('/Users/coryhacking/Developer/wavefoundry')
SCRIPT=REPO/'.wavefoundry/framework/scripts/indexer.py'
PYTHON=Path('/Users/coryhacking/.wavefoundry/venv/bin/python')
sys.path.insert(0,str(SCRIPT.parent))
import index_state_store as iss

def payload(index):
    raw=(index/'graph/project-graph.json').read_bytes()
    return json.loads(gzip.decompress(raw) if raw[:2]==b'\x1f\x8b' else raw)

def snapshot(index):
    out={}
    for p in sorted(index.rglob('*')):
        if not p.is_file() or p.name.endswith(('-wal','-shm')): continue
        key=str(p.relative_to(index))
        if p.suffix=='.sqlite':
            c=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True)
            try: out[key]=tuple(c.iterdump())
            finally:c.close()
        else:out[key]=hashlib.sha256(p.read_bytes()).hexdigest()
    return out

def run(root,index,*args):
    cmd=[str(PYTHON),'-B',str(SCRIPT),'--root',str(root),'--index-dir',str(index),'--content','graph',*args]
    p=subprocess.run(cmd,text=True,capture_output=True,timeout=60,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','HF_HUB_OFFLINE':'1'})
    assert p.returncode==0, (cmd,p.stdout,p.stderr)
    return p.stdout+p.stderr

def shape(p):
    return ({n['id'] for n in p['nodes']},{(e['source'],e['target'],e['relation'],e.get('confidence')) for e in p['edges']},p['input_fingerprint'])

results=[]
with tempfile.TemporaryDirectory(prefix='wf-1x5tq-smoke-') as tmp:
    for name,target,body,noded in [('code','src/new.py','def newly_created(): return 7\n',True),('nodeless','assets/.gitignore','cache/\n',False)]:
        work=Path(tmp)/name;root=work/'repo';index=root/'.wavefoundry/index'
        (root/'docs').mkdir(parents=True);(root/'src').mkdir()
        doc=root/'docs/linker.md';doc.write_text(f'[future](/{target})\n')
        (root/'src/base.py').write_text('def baseline(): return 1\n')
        run(root,index,'--full')
        first=payload(index)
        assert not any(e['source']=='docs/linker.md' and e['target']==target for e in first['edges'])
        doc_bytes=doc.read_bytes();dest=root/target;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(body)
        # A real interrupted epoch plus pending graph work, across processes.
        iss.begin_build_epoch(index,'smoke-interrupted')
        epoch=iss.read_build_state(index);before=snapshot(index)
        preview=run(root,index,'--dry-run')
        assert 'graph_recovery' in preview and 'dirty_epoch' in preview,preview
        assert snapshot(index)==before,'dry-run changed persisted state'
        assert iss.read_build_state(index)==epoch,'dry-run completed dirty epoch'
        run(root,index)
        after=payload(index)
        ids,edges,_=shape(after)
        assert ('docs/linker.md',target,'doc_references_doc','EXTRACTED') in edges
        assert 'docs/linker.md' in ids and (target in ids)==noded
        assert doc.read_bytes()==doc_bytes,'referring document was changed'
        assert iss.read_build_state(index)['status']=='complete'
        assert iss.read_build_state(index)['generation']>epoch['generation']
        generation=iss.read_build_state(index)['generation'];stable=shape(after)
        idle_before=snapshot(index)
        idle_epoch=iss.read_build_state(index)
        idle_preview=run(root,index,'--dry-run')
        assert 'graph_recovery' not in idle_preview,idle_preview
        assert snapshot(index)==idle_before
        assert iss.read_build_state(index)==idle_epoch
        run(root,index)
        assert shape(payload(index))==stable
        # Graph-only fixtures can retain a cold semantic chunk index; that
        # independent maintenance may advance an idle epoch. Fully seeded
        # no-op generation preservation is covered by the focused tests.
        oracle=work/'oracle-index';run(root,oracle,'--full')
        assert shape(payload(oracle))==stable,'incremental/full divergence'
        results.append({'case':name,'cli_processes':6,'dry_run_preserved_state':True,'dirty_epoch_reported':True,'graph_recovery_reported':True,'exact_edge_and_doc_node':True,'target_node_present':noded,'doc_unchanged':True,'recovery_completed':True,'resolved_graph_no_longer_pending':True,'full_build_equivalent':True})
print(json.dumps({'status':'passed','cases':results,'limitations':'Graph-only CLI smoke uses real extraction and persistence, with no embedding or network. SQLite transient WAL/SHM reader bookkeeping is excluded from state snapshots; every persisted SQLite row and other artifact bytes are compared.'},indent=2))
```
