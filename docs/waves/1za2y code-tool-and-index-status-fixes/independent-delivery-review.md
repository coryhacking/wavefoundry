# Independent delivery review — 1za2y

Owner: Engineering
Status: active
Last verified: 2026-09-29

Verdict: not ready to close. One blocking finding, DEL-F3.

## DEL-F3 — a refused contender can unlink an active lock carrier

`indexer.py:3177` classifies prior ownership outside the acquisition guard.
The stale branch at line 3188 unlinks the path before the second in-process
hold check at line 3202. If another thread acquires between classification and
unlink, the contender deletes the active holder's carrier and only then raises
`IndexBuildAlreadyRunning`. A second process can create the same pathname and
acquire its new inode while the first build is still inside its lock context.

The stale unlink predates this wave; this finding is an unmet admitted safety
contract, not a claim that the wave introduced the unlink. It defeats 1z9yb's
AC-3 promise that refusing a second in-process acquisition preserves the first
hold. The acquisition guard repair did not cover the earlier unlink.

A separate code/security reviewer reproduced this, and the coordinator reran
it independently with a before/after negative control. Observed:

```json
{"external_before_contender":"BLOCKED","refused":"IndexBuildAlreadyRunning","path_exists_during_first_hold":false,"external_process":"ACQUIRED","exit":0}
```

The smallest repair to investigate is to keep the carrier inode, acquire it,
and replace stale metadata through the acquired descriptor. Merely moving
unlink under the process-local guard does not resolve the equivalent
cross-process race. Add an interleaving regression checking external exclusion
throughout contender refusal. Do not repair this by weakening the assertion or
changing the status report.

## Other verification

- Canonical runner: `test_navigation_walker_runtime.py` 10 tests pass;
  `test_navigation_glob.py` five pass; `test_graph_quality_eval.py` 102 tests
  run successfully with seven skips.
- Separate lock reviewer: eight lock-hold tests pass; removing the process
  guard is killed by the external-lock observation test. These tests do not
  cover the stale-classification interleaving reproduced here.
- The reviewer's liveness suite could not establish its assertions because
  this host sandbox denied `ps`; those failures are not classified as product
  findings.
- Independently recomputed the framework receipt hash: current, green,
  10,035 tests, timestamp 2026-09-29T19:16:18.816500+00:00. This was receipt
  verification, not a new full-suite run.
- Compared both graph reports recursively with HEAD. Only evaluator identity,
  timestamps, repository commit, digest, baseline source-root path, and the two
  explicitly documented post-production hashes changed. All measured fields
  remain equal; both evaluator hashes match current source.
- Navigation never reinstates the unfiltered fallback. Public-tool tests
  exercise stale and missing indexer responses; graph-only callers are covered
  by the generic wrapper mechanism test rather than a complete public graph
  tool matrix. That is a verification limitation, not another reproduced bug.
- Existing specialist/council approvals and docs lint were current at review
  entry. The new finding requires repair and fresh affected-lane review before
  operator closure.

## Reproduction

Run the following Python from the repository root with its existing framework
test environment. It uses only a temporary index directory, two local threads
and short-lived local lock-probe processes; it does not open the real index.
The scheduling patch pauses after the real classifier result and otherwise
uses production lock acquisition. The source under review was not edited.

```python
import sys,pathlib,tempfile,threading,json,os,subprocess
from unittest.mock import patch
s=pathlib.Path('.wavefoundry/framework/scripts').resolve();sys.path[:0]=[str(s),str(s/'tests')]
import run_tests
from server_tools_support import load_server
load_server();from wf_server import server_impl
idx=server_impl._indexer_module()
with tempfile.TemporaryDirectory() as d:
 p=pathlib.Path(d); lockpath=p/idx.INDEX_BUILD_LOCK_NAME
 lockpath.write_text(json.dumps({'pid':99999999,'started_at':0}))
 ready=threading.Event(); resume=threading.Event(); results={}
 real=idx.classify_index_build_lock_owner
 def classify(meta):
  result=real(meta)
  if threading.current_thread().name=='contender':
   ready.set(); assert resume.wait(10)
  return result
 def contender():
  try:
   with idx._index_build_lock(p): results['entered']=True
  except Exception as e: results['refused']=type(e).__name__
 with patch.object(idx,'classify_index_build_lock_owner',classify):
  t=threading.Thread(target=contender,name='contender');t.start();assert ready.wait(10)
  with idx._index_build_lock(p):
   probe='import os,fcntl,sys;f=os.open(sys.argv[1],os.O_RDWR|os.O_CREAT);fcntl.lockf(f,fcntl.LOCK_EX|fcntl.LOCK_NB,1,int(sys.argv[2]));print("ACQUIRED")'
   before=subprocess.run([sys.executable,'-B','-c',probe,str(lockpath),str(idx.INDEX_BUILD_LOCK_SENTINEL)],capture_output=True,text=True)
   assert before.returncode != 0, before.stdout
   results['external_before_contender']='BLOCKED'
   resume.set();t.join(10)
   results['path_exists_during_first_hold']=lockpath.exists()
   probe='import os,fcntl,sys;f=os.open(sys.argv[1],os.O_RDWR|os.O_CREAT);fcntl.lockf(f,fcntl.LOCK_EX|fcntl.LOCK_NB,1,int(sys.argv[2]));print("ACQUIRED")'
   r=subprocess.run([sys.executable,'-B','-c',probe,str(lockpath),str(idx.INDEX_BUILD_LOCK_SENTINEL)],capture_output=True,text=True)
   results['external_process']=r.stdout.strip();results['exit']=r.returncode
 assert results['refused']=='IndexBuildAlreadyRunning'
 assert results['path_exists_during_first_hold'] is False
 assert results['external_process']=='ACQUIRED' and results['exit']==0
 print(json.dumps(results))
```
