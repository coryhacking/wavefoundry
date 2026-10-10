import sys,json
from pathlib import Path
sys.path[:0]=[str(Path.cwd()/'.wavefoundry/framework/scripts'),str(Path.cwd()/'.wavefoundry/framework/scripts/tests')]
from test_upgrade_wavefoundry import CouncilRoleLinkRepairUpgradeTests as T
t=T('runTest');t.setUp()
try:
 old,new=next((a,b) for a,b in t.ras.COUNCIL_ROLE_RENAMES if a.endswith('/SKILL.md'))
 q=t.root/old;q.parent.mkdir(parents=True,exist_ok=True);q.write_text('# Native\nSee '+t.old_rel+'\n')
 a,b='../../../'+old,'../../../'+new
 source=f'[native]({a}#scope)\r\n[live]({t.old.name})\r\n';expected=f'[native]({b}#scope)\r\n[live]({t.new.name})\r\n';t.peer.write_bytes(source.encode())
 p=t.scripts/'render_agent_surfaces.py';s=p.read_text();oldguard='if old_name == new_name:';assert s.count(oldguard)==1;p.write_text(s.replace(oldguard,'if old_name == new_name or not old_name.endswith(".md"):'))
 snap=t._tree();t._preview_incoming_role_links();assert t._tree()==snap;t._surface();actual=t.peer.read_bytes().decode();t._surface();row={'mutant':'skip-native-directory-component','passed':actual==expected,'detected':actual!=expected and not q.exists() and (t.root/new).exists(),'observed':actual,'expected':expected,'no_errors':True};assert row['detected'];Path('/tmp/wf-204mp-autolink-final-arch-docs-native-mutant.json').write_text(json.dumps(row,indent=2));print(row)
finally:t.doCleanups()
