import ast, contextlib, io, json, sys, tempfile, types, zipfile
from pathlib import Path
from unittest.mock import patch
S=Path('/Users/coryhacking/Developer/wavefoundry/.wavefoundry/framework/scripts')
sys.path.insert(0,str(S))
SOURCE=(S/'upgrade_extensions.py').read_text()
MEMBER='.wavefoundry/framework/scripts/upgrade_extensions.py'
results=[]

def module(source=SOURCE):
    m=types.ModuleType('reality_incoming_upgrade_extensions')
    m.__file__=MEMBER
    exec(compile(source,MEMBER,'exec'),m.__dict__)
    return m

def fixture(trigger='journals_present', hook_body='pass', source_kind='regular'):
    tmp=tempfile.TemporaryDirectory(prefix='wf-c6-reality-')
    root=Path(tmp.name)
    scripts=root/'.wavefoundry/framework/scripts'
    scripts.mkdir(parents=True)
    journals=root/'docs/agents/journals'
    journals.mkdir(parents=True)
    (root/'docs/waves').mkdir(parents=True)
    (root/'.wavefoundry/upgrade-in-progress.json').write_text('{"review_sidecar_cleanup":{}}')
    if source_kind=='regular':(journals/'live.md').write_text('operator content\n')
    marker=root/'declaration-called'
    decl="from pathlib import Path\nEXTENSION_JOURNAL_TEMPLATES=()\nEXTENSION_JOURNAL_PRE_MIGRATION_HOOK='reality_hooks:prepare'\nEXTENSION_HELPER_MODULES=('reality_dep','reality_hooks')\ndef journal_declaration_problems(): return []\n"
    if trigger is not None:decl+=f'EXTENSION_JOURNAL_PRE_MIGRATION_TRIGGER={trigger!r}\n'
    decl+=f'Path({str(marker)!r}).write_text("declaration")\n'
    (scripts/'mcp_tool_extensions.py').write_text(decl)
    hook="from pathlib import Path\ndef prepare(root):\n    with open(Path(root)/'calls','a') as out:out.write('call\\n')\n    "+hook_body+'\n'
    (scripts/'reality_hooks.py').write_text(hook)
    return tmp,root,scripts,journals

def gate(m,root,version):
    out=io.StringIO()
    with patch.object(m,'repair_declaring_scaffold'),patch.object(m,'_reconcile_graph_builder_doc_claim'),patch.object(m,'_migrate_memory_naming'),patch.object(m,'_migrate_journals') as builtin,contextlib.redirect_stdout(out):
        m.pre_docs_gate(types.SimpleNamespace(root=root,from_version=version))
    return builtin.call_count,out.getvalue()

# Probe 1: version/default baseline through the incoming pre-docs callable.
for trigger in (None,'journals_present'):
    for version in ('1.14.9','1.15.0','1.29.0'):
        tmp,root,scripts,journals=fixture(trigger)
        try:
            m=module(); builtin,warning=gate(m,root,version)
            calls=len((root/'calls').read_text().splitlines()) if (root/'calls').exists() else 0
            expected_legacy=1 if version=='1.14.9' else 0
            assert calls==expected_legacy and builtin==expected_legacy
            results.append({'probe':'version_default_baseline','trigger':trigger,'version':version,'hook_calls':calls,'builtin_calls':builtin,'declaration_executed':(root/'declaration-called').exists(),'expected_current':expected_legacy})
        finally:tmp.cleanup()

# Probe 2: broadened-gate known-bad control reveals unauthorized builtin call.
tmp,root,scripts,journals=fixture()
try:
    bad=SOURCE.replace('if _from_version_predates(from_version, "1.15.0"):', 'if True: # deliberate bad broad gate',1)
    assert bad!=SOURCE
    m=module(bad); builtin,_=gate(m,root,'1.29.0')
    calls=(root/'calls').read_text().count('call')
    assert calls==1 and builtin==1
    try:assert builtin==0
    except AssertionError:detected=True
    else:detected=False
    assert detected
    results.append({'probe':'broadened_gate_known_bad','version':'1.29.0','hook_calls':calls,'builtin_calls':builtin,'AC2_oracle_expected_builtin_calls':0,'known_bad_detected':detected})
finally:tmp.cleanup()

# Probe 3: cached sibling imported at load and during call; real incoming loader.
tmp,root,scripts,journals=fixture()
try:
    (scripts/'reality_dep.py').write_text("VALUE='INCOMING'\n")
    (scripts/'reality_hooks.py').write_text("from pathlib import Path\nfrom reality_dep import VALUE\ndef prepare(root):\n    import reality_dep\n    (Path(root)/'dependency-seen').write_text(VALUE+' / '+reality_dep.VALUE)\n")
    old=types.ModuleType('reality_dep');old.VALUE='OLD'
    saved=sys.modules.get('reality_dep')
    try:
        sys.modules['reality_dep']=old
        m=module();gate(m,root,'1.14.9')
        cached=(root/'dependency-seen').read_text()
        assert cached=='OLD / OLD' and sys.modules['reality_dep'] is old
        del sys.modules['reality_dep']
        gate(m,root,'1.14.9')
        clean=(root/'dependency-seen').read_text()
        assert clean=='INCOMING / INCOMING'
        results.append({'probe':'cached_sibling_import_and_call','cached':cached,'uncached_control':clean,'AC4_expected':'INCOMING / INCOMING','known_bad_detected':cached!=clean})
    finally:
        sys.modules.pop('reality_dep',None)
        if saved is not None:sys.modules['reality_dep']=saved
finally:tmp.cleanup()

# Probe 4: existing failure repeated invocation, then public preview non-execution.
tmp,root,scripts,journals=fixture(hook_body='raise RuntimeError("private detail")')
try:
    m=module();before_path=list(sys.path)
    one,w1=gate(m,root,'1.14.9');two,w2=gate(m,root,'1.14.9')
    count=(root/'calls').read_text().count('call')
    assert count==2 and one==two==0 and list(sys.path)==before_path
    assert 'private detail' not in w1 and 'later upgrades do not retry' in w1
    (root/'declaration-called').unlink();(root/'calls').unlink()
    pack=root/'incoming.zip'
    with zipfile.ZipFile(pack,'w') as z:
        for filename in ('upgrade_extensions.py','contained_files.py'):
            z.write(S/filename,'.wavefoundry/framework/scripts/'+filename)
    journal_before=(journals/'live.md').read_bytes()
    preview=m.migrate_journals(root,apply=False,zip_path=pack)
    assert not (root/'declaration-called').exists() and not (root/'calls').exists()
    assert (journals/'live.md').read_bytes()==journal_before
    results.append({'probe':'failure_retry_preview','two_legacy_invocations_hook_calls':count,'builtin_calls':[one,two],'path_restored':list(sys.path)==before_path,'existing_warning':w1.strip(),'preview':preview,'preview_declaration_executed':False,'preview_hook_called':False,'journal_bytes_unchanged':True})
finally:tmp.cleanup()

Path('/tmp/wf-206is-reality-probe-results.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
# Probe 5: public enumeration provides topology evidence, not trigger eligibility.
source_rows=[]
for kind in ('regular','README_only','nested_only','symlink','hardlink'):
    tmp,root,scripts,journals=fixture(source_kind='empty')
    try:
        m=module()
        pack=root/'incoming.zip'
        with zipfile.ZipFile(pack,'w') as z:
            z.write(S/'contained_files.py','.wavefoundry/framework/scripts/contained_files.py')
        if kind=='regular':(journals/'live.md').write_text('operator content')
        elif kind=='README_only':(journals/'README.md').write_text('keep guide')
        elif kind=='nested_only':
            (journals/'nested').mkdir();(journals/'nested/live.md').write_text('operator content')
        elif kind=='symlink':
            (root/'other.md').write_text('linked data');(journals/'live.md').symlink_to(root/'other.md')
        elif kind=='hardlink':
            import os
            (root/'other.md').write_text('linked data');os.link(root/'other.md',journals/'live.md')
        qualified=[]
        for p in journals.iterdir():
            if p.name.endswith('.md') and p.name!='README.md' and m._journal_source_ok(p.lstat()):qualified.append(p.name)
        preview=m.migrate_journals(root,apply=False,zip_path=pack)
        assert bool(qualified)==(kind=='regular')
        if kind in ('README_only','nested_only'):assert preview['left']==[]
        if kind in ('symlink','hardlink'):assert preview['left']==['docs/agents/journals/live.md']
        source_rows.append({'source':kind,'qualified':qualified,'preview_left':preview['left'],'nonempty_left_is_valid_presence_predicate':bool(preview['left'])==bool(qualified)})
    finally:tmp.cleanup()
results.append({'probe':'source_presence_feasibility','rows':source_rows,'known_bad_control':'Using nonempty preview left as trigger incorrectly admits symlink and hardlink-only sources.'})
Path('/tmp/wf-206is-reality-probe-results.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results[-1],indent=2))
