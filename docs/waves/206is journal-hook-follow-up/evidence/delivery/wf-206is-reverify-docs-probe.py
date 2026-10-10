import dataclasses, hashlib, json, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path
ROOT=Path('/Users/coryhacking/Developer/wavefoundry')
sys.path[:0]=[str(ROOT/'.wavefoundry/framework/scripts')]
import reconcile_scan as rs
PACK=json.load(open('/tmp/wf-206is-final-delivery-packet.json'))
STORE=json.loads((ROOT/rs.DISPOSITIONS_REL).read_text())
FILES={r['file'] for r in STORE}

def snapshot():
 return [{'path':row['path'],'sha256':hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest(),'git_blob':subprocess.check_output(['git','hash-object',str(ROOT/row['path'])],text=True).strip()} for row in PACK['paths']]
BEFORE=snapshot(); assert BEFORE==PACK['paths']
def select(refs): return [r for r in refs if r.retired_surface=='docs/agents/journals' and r.file in FILES]
def channels(root): return select(sum((list(x) for x in rs.scan_repo_channels(root)),[]))
RAW=select(rs.scan_repo(ROOT)); CURRENT=channels(ROOT)
assert len(RAW)==3 and not CURRENT
assert {rs.disposition_key(r) for r in RAW}=={x['key'] for x in STORE}
for ref in RAW:
 entry=next(x for x in STORE if x['key']==rs.disposition_key(ref))
 for field in ('file','matched','logical_line','heading_context'): assert entry[field]==getattr(ref,field)
 assert entry['status']=='historical-record'
OBS={'repository_raw':len(RAW),'repository_reported':len(CURRENT),'rows':[dataclasses.asdict(r)|{'actual_key':rs.disposition_key(r)} for r in RAW]}
class ExactJudgmentReverification(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='wf-c6-docs-reverify-');self.root=Path(self.tmp.name)
  for file in FILES:
   path=self.root/file;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/file,path)
  self.store=self.root/rs.DISPOSITIONS_REL;self.store.write_text(json.dumps(STORE))
 def tearDown(self): self.tmp.cleanup()
 def test_exact_current_judgments_suppress_only_reported_channel(self):
  self.assertEqual(3,len(select(rs.scan_repo(self.root))));self.assertEqual([],channels(self.root));OBS['exact']=0;OBS['raw']=3
 def test_omitted_judgment_is_reported(self):
  self.store.write_text(json.dumps(STORE[1:]));found=channels(self.root);self.assertEqual(1,len(found));self.assertEqual(STORE[0]['file'],found[0].file);OBS['omitted']=1
 def test_modified_logical_line_is_reported(self):
  entry=next(x for x in STORE if x['file']=='docs/specs/mcp-tool-surface.md');p=self.root/entry['file'];p.write_text(p.read_text().replace(entry['logical_line'],entry['logical_line']+' Additional ongoing journal text.',1));found=channels(self.root);self.assertEqual(1,len(found));self.assertNotEqual(entry['key'],rs.disposition_key(found[0]));OBS['modified_line']=1
 def test_modified_heading_is_reported(self):
  entry=next(x for x in STORE if x['file']=='docs/architecture/data-and-control-flow.md');p=self.root/entry['file'];p.write_text(p.read_text().replace(entry['heading_context'],entry['heading_context']+' revised',1));found=channels(self.root);self.assertEqual(1,len(found));self.assertNotEqual(entry['key'],rs.disposition_key(found[0]));OBS['modified_heading']=1
 def test_new_ongoing_journal_directive_is_reported(self):
  p=self.root/'docs/specs/mcp-tool-surface.md';p.write_text(p.read_text()+'\n## New ongoing authoring directive\nWrite all future engineering session notes into docs/agents/journals/new.md.\n');found=channels(self.root);self.assertEqual(1,len(found));self.assertIn('Write all future',found[0].logical_line);OBS['new_directive']=1
 def test_same_line_ongoing_directive_invalidates_exact_judgment(self):
  entry=next(x for x in STORE if x['file']=='docs/specs/mcp-tool-surface.md');p=self.root/entry['file'];p.write_text(p.read_text().replace(entry['logical_line'],entry['logical_line']+' Write all future notes into docs/agents/journals/new.md.',1));found=channels(self.root);self.assertGreaterEqual(len(found),1);self.assertTrue(any('Write all future' in r.logical_line for r in found));OBS['same_line_directive']=len(found)
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ExactJudgmentReverification))
 AFTER=snapshot();assert BEFORE==AFTER
 OBS.update(source_hashes_before=BEFORE,source_hashes_after=AFTER,hashes_unchanged=True,tree_fingerprint=PACK['tree_fingerprint'],tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped))
 Path('/tmp/wf-206is-reverify-docs-probe.json').write_text(json.dumps(OBS,indent=2)+'\n');print(json.dumps({k:v for k,v in OBS.items() if k not in ('rows','source_hashes_before','source_hashes_after')},indent=2));sys.exit(not result.wasSuccessful())
