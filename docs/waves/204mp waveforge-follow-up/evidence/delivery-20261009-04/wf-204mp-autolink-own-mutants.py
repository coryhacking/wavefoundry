import sys,io,json,time,unittest
from pathlib import Path
sys.path[:0]=[str(Path.cwd()/'.wavefoundry/framework/scripts'),str(Path.cwd()/'.wavefoundry/framework/scripts/tests')]
import test_upgrade_wavefoundry as o
T=o.CouncilRoleLinkRepairUpgradeTests
base=T.setUp
M=[
 ('M03-container-def-offset','test_installing_upgrade_repairs_container_reference_definitions','reference_starts.add(absolute)','reference_starts.add(-1)'),
 ('M04-ignore-html-blocks','test_installing_upgrade_preserves_html_literal_blocks','masked = bool(mark or html_open)','html_open = None\n            masked = bool(mark or html_open)'),
 ('M05-invalid-backtick-info','test_installing_upgrade_distinguishes_backtick_and_tilde_info','if fence is None and mark and mark[1][0] == "`" and "`" in mark[2]:','if False:'),
 ('M06-ignore-escaped-opener','test_installing_upgrade_respects_link_and_image_escape_parity','if escaped(m.start()):','if False:'),
 ('M07-no-native-directory','test_installing_upgrade_repairs_native_skill_directory_destinations','if old_name == new_name:','if old_name == new_name or index != len(old_parts) - 1:'),
 ('M09-ignore-inline-html','test_installing_upgrade_preserves_inline_html_and_code_precedence','tag = inline_html.match(masked, at, last)','tag = None'),
 ('M10-paragraph-definitions','test_installing_upgrade_respects_reference_definition_context','if not masked and (not paragraph or new_container or closed_container):','if not masked:'),
 ('M11-ignore-metadata','test_installing_upgrade_consumes_link_metadata_before_code_ticks','if chars[pos] not in "\\r\\n":\n                        chars[pos] = " "','if False:\n                        chars[pos] = " "'),
 ('M14-ignore-URI','test_installing_upgrade_preserves_autolink_atoms_and_code_precedence','+ r"|<[A-Za-z][A-Za-z0-9+.-]{1,31}:[^\\x00-\\x20<>]*>"','+ r"|(?!)"'),
 ('M14-ignore-email','test_installing_upgrade_preserves_autolink_atoms_and_code_precedence','+ r"|<[A-Za-z0-9.!#$%&\'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*>"','+ r"|(?!)"'),
]
rows=[]
for name,method,a,b in M:
 def setup(self):
  base(self);p=self.scripts/'render_agent_surfaces.py';s=p.read_text();assert a in s,(name,'needle missing');p.write_text(s.replace(a,b,1))
 T.setUp=setup
 stream=io.StringIO();start=time.monotonic();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('test_upgrade_wavefoundry.CouncilRoleLinkRepairUpgradeTests.'+method))
 rows.append(dict(name=name,method=method,ran=r.testsRun,failures=len(r.failures),errors=len(r.errors),skips=len(r.skipped),seconds=time.monotonic()-start,detected=bool(r.failures) and not r.errors and not r.skipped,log=stream.getvalue()));print(name,rows[-1]['failures'],rows[-1]['errors'],flush=True)
T.setUp=base
Path('/tmp/wf-204mp-autolink-own-mutants.json').write_text(json.dumps(rows,indent=2))
