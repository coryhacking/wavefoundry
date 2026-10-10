import io,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
root=Path('/Users/coryhacking/Developer/wavefoundry'); scripts=root/'.wavefoundry/framework/scripts'; sys.path[:0]=[str(scripts/'tests'),str(scripts)]
import graph_fixture_support as gfs,test_server_tools_retrieval as t
actual=gfs.publish_evidence_fixture; roots=[]
def observe(p):
 roots.append(str(p)); return actual(p)
r=unittest.TestResult()
with patch.object(gfs,'publish_evidence_fixture',side_effect=observe):
 t.EvidencePartitionResponseTests('test_the_limit_applies_independently_to_each_half').run(r)
assert r.testsRun==1 and not r.failures and not r.errors and not r.skipped
assert len(roots)==1 and Path(roots[0])!=root and 'wf-evidence-response-' in roots[0]
observed='scratch-hermetic-source'
class DocContract(unittest.TestCase):
 def __init__(self,claimed): super().__init__('runTest');self.claimed=claimed
 def runTest(self): self.assertEqual(self.claimed,observed,'Claimed coverage provenance contradicts observed real public-response fixture root')
def run(claimed):
 z=unittest.TestResult();DocContract(claimed).run(z); return dict(tests=z.testsRun,failures=len(z.failures),errors=len(z.errors),skips=len(z.skipped),failure_details=[v for _,v in z.failures])
out={'actual_response':dict(tests=r.testsRun,failures=len(r.failures),errors=len(r.errors),skips=len(r.skipped)),'observed_public_response_roots':roots,'current_doc_provenance_assertion':run('scratch-hermetic-source'),'injected_original_live_qualification_claim':run('checkout-live-after-canonical-setup'),'method':'Specification-derived provenance invariant: observed real fixture producer root must agree with hand-authored coverage claim; old prose interpreted as checkout-live qualification disagrees. This detects false claim, not presence of a phrase.'}
assert out['current_doc_provenance_assertion']['failures']==0 and out['injected_original_live_qualification_claim']['failures']==1
Path('/private/tmp/wf-2071n-reverify-doc-control.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
