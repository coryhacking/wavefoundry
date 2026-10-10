import ast,hashlib,json,pathlib,sys
root=pathlib.Path('/Users/coryhacking/Developer/wavefoundry');scripts=root/'.wavefoundry/framework/scripts';sys.path[:0]=[str(scripts),str(scripts/'tests')]
import test_extension_tool_modules as ext_test
import mcp_tool_extensions
from declaration_support import DECLARATION_CONSTANTS
import reconcile_scan
# Independently inspect values, not only the census's spelling assertion.
driver=ast.parse(ext_test._DRIVER)
empty=[n for n in ast.walk(driver) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='empty' for t in n.targets)]
assert len(empty)==1
kw={x.arg:ast.literal_eval(x.value) for x in empty[0].value.keywords}
assert set(kw)==set(DECLARATION_CONSTANTS)
assert kw['EXTENSION_JOURNAL_PRE_MIGRATION_TRIGGER']==mcp_tool_extensions.EXTENSION_JOURNAL_PRE_MIGRATION_TRIGGER=='legacy_cutover'
# Exact historical store must cover only its three independently enumerated references.
raw=[f for f in reconcile_scan.scan_repo(root) if f.retired_surface=='docs/agents/journals']
store=json.load(open(root/'docs/reconcile-dispositions.json'))
assert len(raw)==len(store)==3
assert {reconcile_scan.disposition_key(f) for f in raw}=={d['key'] for d in store}
assert all(d['key'].startswith('v2:') and d['status']=='historical-record' for d in store)
assert all((root/d['evidence']).is_file() for d in store)
result={'declaration_reset_values_match':True,'complete_reset_count':len(kw),'trigger_shipped_default':'legacy_cutover','historical_judgment_count':3,'all_raw_keys_retained_and_exact':True,'durable_store_evidence_exists':True,'raw_refs':[f.as_dict() for f in raw]}
json.dump(result,open('/tmp/wf-206is-reverify-code-work/sibling-results.json','w'),indent=2)
print(json.dumps(result,indent=2))
