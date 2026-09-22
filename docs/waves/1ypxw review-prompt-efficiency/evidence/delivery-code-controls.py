import sys,pathlib,unittest,io,inspect
from unittest.mock import patch
sys.path[:0]=['.wavefoundry/framework/scripts','.wavefoundry/framework/scripts/tests']
import review_evidence as re,server_impl as srv

def run(name,test,target,mutant):
 stream=io.StringIO()
 with patch.object(target[0],target[1],mutant):
  result=unittest.TextTestRunner(stream=stream,verbosity=0).run(unittest.defaultTestLoader.loadTestsFromName(test))
 print(name,'KILLED' if not result.wasSuccessful() else 'SURVIVED','tests',result.testsRun,'fail',len(result.failures),'errors',len(result.errors),'skips',len(result.skipped));print(stream.getvalue()[-1600:])
 assert result.failures and not result.errors

def historical(rows):
 rows=tuple(rows);cur=re.current_policy_receipt(rows)
 return tuple(dict.fromkeys(r['policy_receipt_id'] for r in rows if r.get('claim_kind')=='approval' and r.get('policy_receipt_id') and r['policy_receipt_id']!=cur['receipt_id']))
def globally_latest(rows):
 rows=tuple(rows);cur=re.current_policy_receipt(rows);ap=list(re._approval_rows(rows,approval_phase='readiness').values())
 if not ap:return ()
 r=max(ap)[1];return (r['policy_receipt_id'],) if r.get('policy_receipt_id')!=cur['receipt_id'] else ()
name='test_server_tools_lifecycle.WaveCouncilPolicyTests.test_repeated_receipt_advice_tracks_latest_approval_per_lane'
run('scan historical approvals',name,(srv,'stale_readiness_receipt_ids'),historical)
run('use globally latest approval',name,(srv,'stale_readiness_receipt_ids'),globally_latest)
source=inspect.getsource(re.ephemeral_artifact_tokens).replace('if "scratchpad" in path.casefold().split("/"):','if False:')
namespace=dict(vars(re));exec(source,namespace)
run('drop scratchpad classification','test_server_tools_lifecycle.WaveCouncilPolicyTests.test_ephemeral_evidence_advises_on_preview_and_write',(srv,'ephemeral_artifact_tokens'),namespace['ephemeral_artifact_tokens'])
