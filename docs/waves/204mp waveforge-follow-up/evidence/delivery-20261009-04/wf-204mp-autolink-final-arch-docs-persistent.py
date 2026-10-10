import sys,json,io,unittest
from pathlib import Path
sys.path[:0]=[str(Path.cwd()/'.wavefoundry/framework/scripts'),str(Path.cwd()/'.wavefoundry/framework/scripts/tests')]
from test_upgrade_wavefoundry import CouncilRoleLinkRepairUpgradeTests as T
original=T.setUp
rows=[]
for mut,name in [(False,'baseline'),(True,'omit-metadata-blank')]:
 def setup(self):
  original(self)
  if mut:
   p=self.scripts/'render_agent_surfaces.py';s=p.read_text();old='for pos in range(metadata_start, metadata_end - 1):';assert s.count(old)==1;p.write_text(s.replace(old,'for pos in range(0):'))
 T.setUp=setup
 r=unittest.TextTestRunner(stream=io.StringIO()).run(unittest.TestSuite([T('test_installing_upgrade_consumes_link_metadata_before_code_ticks')]))
 rows.append(dict(name=name,tests=r.testsRun,failures=[text for _,text in r.failures],errors=[text for _,text in r.errors],skips=r.skipped,passed=r.wasSuccessful()))
T.setUp=original
Path('/tmp/wf-204mp-autolink-final-arch-docs-persistent.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
