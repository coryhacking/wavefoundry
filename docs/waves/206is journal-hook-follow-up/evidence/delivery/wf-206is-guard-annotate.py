import ast,collections,datetime,difflib,hashlib,json,pathlib
p=pathlib.Path('/tmp/wf-206is-guard-pins.json');r=json.loads(p.read_text())
for row in r['records']:
 source=pathlib.Path(row['source']);text=source.read_text();n=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name==row['symbol']); row['source_anchor']={'symbol':n.name,'lines':[n.lineno,n.end_lineno],'sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
 lines=text.splitlines(keepends=True);before=''.join(lines[n.lineno-1:n.end_lineno]);after=before
 if row['id']=='ancestor_refusal_complete':after=after.replace('refuse_symlink_components=True','refuse_symlink_components=False').replace('if _journal_dir_fd_supported():','if False:')
 elif row['id']=='ancestor_refusal_partial':after=after.replace('folder = containment.contained_path(root, _JOURNALS_REL, refuse_symlink_components=True)','folder = root / _JOURNALS_REL').replace('if _journal_dir_fd_supported():','if False:')
 else:after=after.replace(row['old'],row['new'])
 row['exact_diff']=''.join(difflib.unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),fromfile=row['source']+'::'+n.name,tofile='scratch-mutant::'+n.name))
 log=pathlib.Path(row['mutant']['log']).read_text();proof=[]
 for line in log.splitlines():
  if line.startswith(('PROPERTY_EXCEPTION ','AssertionError:','AttributeError:','SystemExit:')) and line not in proof:proof.append(line[:1600])
 row['failure_assertions']=proof
 row['no_unintended_skips']=row['baseline']['skips']==row['mutant']['skips']==0
 row['baseline_valid']=row['baseline']['exit']==0 and row['baseline']['errors']==row['baseline']['failures']==0 and row['baseline']['run']>0
 row['right_property_review']='Named test failed at expected assertion or patched forbidden action; no missing test/import dependency/fixture syntax error.' if row['classification']=='detected' else 'Mutant remains green; no detection claim.'
 if row['id'] in ('cached_name_eviction','path_precedence'):
  row['right_property_review']='Real incoming declaration assertion: declaration got old dependency, with trace proving c6_dependency.__file__ lies in old-scripts; production older runner correctly exits3. Not a missing dependency or fixture error.'
 if row['id']=='descendant_shadowing':
  row['right_property_review']='Cached c6_package.child survives while incoming parent reloads, so Python import leaves the incoming parent without a child attribute. Trace proves stale child.__file__ lies in old-scripts while fresh parent.__file__ lies in target incoming tree; production refusal exits3. This is the intended cached-descendant incoherence, not a missing file or fixture error.'
 if row['id']=='ancestor_refusal_partial':row['survivor_assessment']='Not missing pin: per-candidate containment still refuses ancestor. Complete family mutant detected by same test.'
 elif row['classification']=='survived':row['survivor_assessment']='Missing named guard pin: deletion survives all twelve new policy tests. Runtime correctness is not inferred from mutation survival; return to root/test owner.'
r['summary']=dict(collections.Counter(row['classification'] for row in r['records']));r['recorded_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();r['unresolved_named_guard_pins']=[row['id'] for row in r['records'] if row['classification']=='survived' and row['id']!='ancestor_refusal_partial'];r['all_baselines_green_zero_skips']=all(row['baseline_valid'] and row['no_unintended_skips'] for row in r['records']);r['replay_scripts']=['/tmp/wf-206is-guard-replay.py','/tmp/wf-206is-extra-guard-check.py','/tmp/wf-206is-guard-annotate.py'];p.write_text(json.dumps(r,indent=2));print(json.dumps({k:r[k] for k in ('summary','unchanged','all_baselines_green_zero_skips','unresolved_named_guard_pins')},indent=2))
