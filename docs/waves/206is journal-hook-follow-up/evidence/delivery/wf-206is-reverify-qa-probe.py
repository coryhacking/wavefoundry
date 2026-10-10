import ast, hashlib, json, os, shutil, subprocess, tempfile
from pathlib import Path
ROOT=Path('/Users/coryhacking/Developer/wavefoundry'); PY='/Users/coryhacking/.wavefoundry/venv/bin/python'
PACK=json.loads(Path('/tmp/wf-206is-final-delivery-packet.json').read_text())
rows=PACK['paths']
assert isinstance(rows,list),PACK.keys()
def snap():
 out=[]
 for row in rows:
  path=row['path']; b=(ROOT/path).read_bytes(); sha=hashlib.sha256(b).hexdigest(); blob=subprocess.check_output(['git','hash-object','--',str(ROOT/path)],text=True,cwd=ROOT).strip()
  assert sha==row['sha256'] and blob==row['git_blob'],path
  out.append(dict(path=path,sha256=sha,git_blob=blob))
 return out
before=snap()
TESTS=['test_extension_tool_modules.DeclarationConstantCensusTests.test_the_refusal_driver_resets_every_declaration_constant','test_extension_tool_modules.DeclarationConstantCensusTests.test_every_declaration_constant_is_classified','test_server_package.TestCensusTests.test_no_source_read_of_a_moved_flat_path','test_upgrade_wavefoundry.JournalTriggerPolicyTests','test_upgrade_protocol.JournalIncomingRunnerTests']
runs=[]
def run(label,scripts,tests,expect):
 env=os.environ.copy();env['PYTHONPATH']=str(scripts)+os.pathsep+str(scripts/'tests');env['PYTHONDONTWRITEBYTECODE']='1'
 cmd=[PY,'-B','-m','unittest','-v',*tests];p=subprocess.run(cmd,cwd=ROOT,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=160)
 log=Path('/tmp/wf-206is-reverify-qa-'+label+'.log');log.write_text(p.stdout)
 print(label,p.returncode,p.stdout[-700:],flush=True)
 assert p.returncode==expect,(label,p.stdout[-1000:])
 assert 'skipped' not in p.stdout.lower(),label
 runs.append(dict(label=label,command=cmd,pythonpath=env['PYTHONPATH'],exit_code=p.returncode,log=str(log),summary=p.stdout[-1000:]))
 return p.stdout
S=ROOT/'.wavefoundry/framework/scripts';run('current',S,TESTS,0)
work=Path(tempfile.mkdtemp(prefix='wf-206is-qa-reverify-'));ss=work/'.wavefoundry/framework/scripts';shutil.copytree(S,ss,ignore=shutil.ignore_patterns('__pycache__','.pytest_cache','test-cache.json','test-run.lock'))
EXT=ss/'tests/test_extension_tool_modules.py';UP=ss/'tests/test_upgrade_wavefoundry.py';e=EXT.read_text();u=UP.read_text()
needle='                     EXTENSION_JOURNAL_PRE_MIGRATION_TRIGGER="legacy_cutover",\n';assert e.count(needle)==1
EXT.write_text(e.replace(needle,''));bad=run('missing-trigger',ss,TESTS[:1],1);assert 'EXTENSION_JOURNAL_PRE_MIGRATION_TRIGGER=' in bad and 'AssertionError' in bad
EXT.write_text(e);run('trigger-restored',ss,TESTS[:2],0)
needle='source_path(f"{helper}.py").read_bytes()';assert u.count(needle)==1
UP.write_text(u.replace(needle,'(SCRIPTS_ROOT / f"{helper}.py").read_bytes()'));bad=run('computed-source',ss,TESTS[2:3],1);assert 'test_upgrade_wavefoundry.py' in bad and 'SCRIPTS_ROOT /' in bad and 'AssertionError' in bad
UP.write_text(u);run('source-restored',ss,TESTS[2:3],0)
# Adjacent defect-class sweep over actual refusal-driver declaration set and C6 archive reads.
for p in [S/'tests/test_upgrade_wavefoundry.py',S/'tests/test_upgrade_protocol.py']:
 tree=ast.parse(p.read_text());nodes=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name in ['JournalTriggerPolicyTests','JournalIncomingRunnerTests']]
 for node in nodes:
  print('AC_METHODS',node.name,[n.name for n in node.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')],flush=True)
after=snap();assert before==after
result=dict(packet_fingerprint=PACK['tree_fingerprint'],before=before,after=after,tree_unchanged=True,runs=runs,scratch=str(work))
Path('/tmp/wf-206is-reverify-qa-probe.json').write_text(json.dumps(result,indent=2)+'\n')
