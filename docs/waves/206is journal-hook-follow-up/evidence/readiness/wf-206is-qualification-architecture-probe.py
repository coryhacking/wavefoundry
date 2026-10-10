from pathlib import Path
from dataclasses import replace
import sys,json
root=Path('/Users/coryhacking/Developer/wavefoundry')
sys.path.insert(0,str(root/'.wavefoundry/framework/scripts/tests'))
sys.path.insert(0,str(root/'.wavefoundry/framework/scripts'))
from test_server_package import _source_read_sites
from framework_files import source_path
import reconcile_scan as r
bad=_source_read_sites('(SCRIPTS_ROOT / f"{helper}.py").read_bytes()')
good=_source_read_sites('source_path(f"{helper}.py").read_bytes()')
assert bad and not good
assert source_path('path_containment').read_bytes() and source_path('contained_files').read_bytes()
assert source_path('server_impl').parent.name=='wf_server'
refs=[x for x in r.scan_repo(root) if 'docs/agents/journals' in x.matched]
assert len(refs)==3
judgments={r.disposition_key(x):[r.HISTORICAL_RECORD] for x in refs}
controls={'baseline':len(refs),'bad_read_detected':bool(bad),'good_read_accepted':not good,'exact_all_match':all(r.is_dispositioned(x,judgments) for x in refs),'changed_line_detected':all(not r.is_dispositioned(replace(x,logical_line=x.logical_line+' Continue writing a daily journal.'),judgments) for x in refs),'changed_heading_detected':all(not r.is_dispositioned(replace(x,heading_context=x.heading_context+' revised'),judgments) for x in refs),'new_live_detected':not r.is_dispositioned(replace(refs[0],file='docs/new-live.md',logical_line='Write a journal every day under docs/agents/journals.'),judgments)}
assert all(v for k,v in controls.items() if k!='baseline')
print(json.dumps(controls,indent=2))
