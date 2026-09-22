import sys,unittest,io,json,ast,subprocess,hashlib
from pathlib import Path
from unittest.mock import patch
root=Path('/Users/coryhacking/Developer/wavefoundry'); scripts=root/'.wavefoundry/framework/scripts'
sys.path[:0]=[str(scripts/'tests'),str(scripts)]
import test_path_containment as tests
import path_containment as subject
import render_agent_surfaces as renderer
import techdocs_audit_lib as td
rows=[]
def run(label, case, patcher):
 with patcher:
  r=unittest.TextTestRunner(stream=io.StringIO()).run(unittest.defaultTestLoader.loadTestsFromName(case,tests))
 rows.append({'mutation':label,'test':case,'detected':not r.wasSuccessful(),'failures':len(r.failures),'errors':len(r.errors)})
original=subject.contained_resolved_path
run('accept escaped candidate','ContainedPathTests.test_directory_link_escape_with_missing_tail',patch.object(subject,'contained_resolved_path',lambda r,c:c))
run('extra resolve in pure comparator','WrapperContractTests.test_renderer_and_techdocs_resolution_matrix',patch.object(subject,'contained_resolved_path',lambda r,c:original(r.resolve(),c.resolve())))
orig=renderer._contained_review_carrier_path
def swallow(r,c):
 try:return orig(r,c)
 except OSError:return None
run('swallow renderer root OSError','WrapperContractTests.test_renderer_and_techdocs_resolution_matrix',patch.object(renderer,'_contained_review_carrier_path',swallow))
origtd=td._contained
def swallowtd(r,c):
 try:return origtd(r,c)
 except OSError:return None
run('swallow indirect TechDocs root OSError','WrapperContractTests.test_renderer_and_techdocs_resolution_matrix',patch.object(td,'_contained',swallowtd))
# Test's direct import uses the patched callable identity to choose expected handling.
print(json.dumps(rows,indent=2))
Path('/private/tmp/1ymzq-security-mutants.json').write_text(json.dumps(rows,indent=2))
# Verify protected helper/file untouched versus HEAD.
old=subprocess.check_output(['git','show','HEAD:.wavefoundry/framework/scripts/indexer.py'],cwd=root,text=True)
current=(scripts/'indexer.py').read_text()
print('indexer_whole_file_unchanged',old==current)
fp=json.loads(Path('/private/tmp/1ymzq-delivery-fingerprint.json').read_text())
bad=[p for p,h in fp.items() if subprocess.check_output(['git','hash-object',p],cwd=root,text=True).strip()!=h]
print('fingerprint_changed',bad)
