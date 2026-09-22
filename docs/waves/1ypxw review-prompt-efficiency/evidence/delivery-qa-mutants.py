import sys,unittest,io
from unittest.mock import patch
sys.path[:0]=['.wavefoundry/framework/scripts','.wavefoundry/framework/scripts/tests']
from test_server_tools_lifecycle import WaveCouncilPolicyTests as C
import review_evidence as re
C.setUpClass()
def check(label,target,replacement,test):
 with patch.object(C.srv,target,replacement):
  r=unittest.TextTestRunner(stream=io.StringIO()).run(C(test))
  print(label,'KILLED' if r.failures and not r.errors else 'SURVIVED/ERROR', 'runs',r.testsRun,'failures',len(r.failures),'errors',len(r.errors),'skips',len(r.skipped))
  if r.failures: print(r.failures[0][1].splitlines()[-1][:220])
  assert r.failures and not r.errors and not r.skipped

def historical(rows):
 current=re.current_policy_receipt(rows)
 return tuple(r['policy_receipt_id'] for r in rows if r.get('claim_kind')=='approval' and r.get('approval_phase')=='readiness' and r.get('policy_receipt_id') and r['policy_receipt_id']!=current['receipt_id'])
def latestglobally(rows):
 approvals=list(re._approval_rows(rows,approval_phase='readiness').values())
 if not approvals:return ()
 a=max(approvals,key=lambda x:x[0])[1]
 current=re.current_policy_receipt(rows)
 return (a['policy_receipt_id'],) if a.get('policy_receipt_id')!=current['receipt_id'] else ()
check('suppress ephemeral approval','ephemeral_artifact_tokens',lambda x:(), 'test_ephemeral_evidence_advises_on_preview_and_write')
check('suppress ephemeral finding','ephemeral_artifact_tokens',lambda x:(), 'test_ephemeral_finding_is_recorded_with_advisory')
check('scan historical approvals','stale_readiness_receipt_ids',historical,'test_repeated_receipt_advice_tracks_latest_approval_per_lane')
check('latest approval globally','stale_readiness_receipt_ids',latestglobally,'test_repeated_receipt_advice_tracks_latest_approval_per_lane')
original=C.srv.ephemeral_artifact_tokens
check('remove scratchpad branch','ephemeral_artifact_tokens',lambda x:tuple(t for t in original(x) if 'scratchpad' not in t.lower().replace('\\','/').split('/')),'test_ephemeral_evidence_advises_on_preview_and_write')
