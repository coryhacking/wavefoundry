import sys,unittest,io,json
from pathlib import Path
from unittest.mock import patch
s=Path('/Users/coryhacking/Developer/wavefoundry/.wavefoundry/framework/scripts'); sys.path[:0]=[str(s/'tests'),str(s)]
import test_handler_modules as t
orig=Path.read_text
rows=[]
for module in t.SPLIT_THREE_ROSTERS:
 for kind,tail,test in [('local sibling import','\ndef _bad_boundary():\n    import memory_handlers\n','test_split_three_complete_partitions_and_identity'),('eager root import','\nimport server_impl\n','test_locations_import_boundaries_and_name_resolution')]:
  def read(path,*a,**kw):
   text=orig(path,*a,**kw)
   return text+tail if path==s/(module+'.py') else text
  with patch.object(Path,'read_text',read):
   r=unittest.TextTestRunner(stream=io.StringIO()).run(t.HandlerStructureTests(test))
  rows.append({'module':module,'mutation':kind,'detected':not r.wasSuccessful(),'failures':len(r.failures),'errors':len(r.errors)})
oldload=t.load_server
for name in ['_BACKGROUND_BUILD_PIDS','_FRESHNESS_CACHE','_DASHBOARD_CHILD_PIDS']:
 def load():
  server=oldload(); setattr(server,name,getattr(server,name).copy()); return server
 with patch.object(t,'load_server',load):
  r=unittest.TextTestRunner(stream=io.StringIO()).run(t.HandlerStructureTests('test_split_three_complete_partitions_and_identity'))
 rows.append({'object':name,'mutation':'copy instead of shared alias','detected':not r.wasSuccessful(),'failures':len(r.failures),'errors':len(r.errors)})
print(json.dumps(rows,indent=2));Path('/private/tmp/1ymzq-architecture-mutants.json').write_text(json.dumps(rows,indent=2))
