import sys,json,stat,hashlib,subprocess
from pathlib import Path
from markdown_it import MarkdownIt
ROOT=Path('/Users/coryhacking/Developer/wavefoundry')
sys.path[:0]=[str(ROOT/'.wavefoundry/framework/scripts'),str(ROOT/'.wavefoundry/framework/scripts/tests')]
import test_upgrade_wavefoundry as o
md=MarkdownIt('commonmark')
C={
'uri_literal':('Paragraph <https://example.invalid/[CODE](OLD)> [LIVE](OLD)\n','Paragraph <https://example.invalid/[CODE](OLD)> [LIVE](NEW)\n'),
'custom_uri_literal':('Paragraph <custom+protocol://example.invalid/?x=[CODE](OLD)> [LIVE](OLD)\n','Paragraph <custom+protocol://example.invalid/?x=[CODE](OLD)> [LIVE](NEW)\n'),
'uri_tick':('Paragraph <https://example.invalid/?x=`> [LIVE](OLD) tail `\n','Paragraph <https://example.invalid/?x=`> [LIVE](NEW) tail `\n'),
'email_tick':('Paragraph <a`@example.invalid> [LIVE](OLD) tail `\n','Paragraph <a`@example.invalid> [LIVE](NEW) tail `\n'),
'earlier_code_uri':('Paragraph ` <https://example.invalid/[CODE](OLD)?x=`> [LIVE](OLD)\n','Paragraph ` <https://example.invalid/[CODE](OLD)?x=`> [LIVE](NEW)\n'),
'earlier_code_email':('Paragraph ` <a`@example.invalid> [LIVE](OLD)\n','Paragraph ` <a`@example.invalid> [LIVE](NEW)\n'),
'escaped_angle':(r'Paragraph \<https://example.invalid/[LIVE](OLD)> [LIVE](OLD)'+'\n',r'Paragraph \<https://example.invalid/[LIVE](NEW)> [LIVE](NEW)'+'\n'),
'even_escape_angle':(r'Paragraph \\<https://example.invalid/[CODE](OLD)> [LIVE](OLD)'+'\n',r'Paragraph \\<https://example.invalid/[CODE](OLD)> [LIVE](NEW)'+'\n'),
'short_scheme_not_autolink':('Paragraph <a:[LIVE](OLD)> [LIVE](OLD)\n','Paragraph <a:[LIVE](NEW)> [LIVE](NEW)\n'),
'valid_two_scheme':('Paragraph <aa:[CODE](OLD)> [LIVE](OLD)\n','Paragraph <aa:[CODE](OLD)> [LIVE](NEW)\n'),
'valid_long_scheme':('Paragraph <'+'a'*32+':[CODE](OLD)> [LIVE](OLD)\n','Paragraph <'+'a'*32+':[CODE](OLD)> [LIVE](NEW)\n'),
'invalid_long_scheme':('Paragraph <'+'a'*33+':[LIVE](OLD)> [LIVE](OLD)\n','Paragraph <'+'a'*33+':[LIVE](NEW)> [LIVE](NEW)\n'),
'uri_has_space':('Paragraph <aa:prefix [LIVE](OLD)> [LIVE](OLD)\n','Paragraph <aa:prefix [LIVE](NEW)> [LIVE](NEW)\n'),
'email_domain_boundary':('Paragraph <a`@a> [LIVE](OLD) tail `\n','Paragraph <a`@a> [LIVE](NEW) tail `\n'),
'email_subdomain_boundary':('Paragraph <a`@a-b.c> [LIVE](OLD) tail `\n','Paragraph <a`@a-b.c> [LIVE](NEW) tail `\n'),
'html_tick':('Paragraph <span title="`"> [LIVE](OLD) </span> tail `\n','Paragraph <span title="`"> [LIVE](NEW) </span> tail `\n'),
'metadata_image':('[A](elsewhere "![icon][ref]")\n\n[ref]: OLD\n\n[LIVE](OLD)\n','[A](elsewhere "![icon][ref]")\n\n[ref]: NEW\n\n[LIVE](NEW)\n'),
'query_nested':('[A](OLD?x=[CODE](OLD)) [LIVE](OLD)\n','[A](NEW?x=[CODE](OLD)) [LIVE](NEW)\n'),
'paragraph_reference':('Paragraph\n[ref]: OLD\n\n[LIVE](OLD)\n','Paragraph\n[ref]: OLD\n\n[LIVE](NEW)\n'),
'quote_reference':('> [ref]: OLD "`"\n> [LIVE](OLD)\n> Other `\n','> [ref]: NEW "`"\n> [LIVE](NEW)\n> Other `\n'),
'recursive_fence':('- > - > ~~~md\n  >   > [CODE](OLD)\n  >   > ~~~\n  >   > [LIVE](OLD)\n','- > - > ~~~md\n  >   > [CODE](OLD)\n  >   > ~~~\n  >   > [LIVE](NEW)\n'),
'setext':('heading\n===\n    [CODE](OLD)\n\n[LIVE](OLD)\n','heading\n===\n    [CODE](OLD)\n\n[LIVE](NEW)\n'),
'escaped_tick':('\\` [LIVE](OLD) \\`\n','\\` [LIVE](NEW) \\`\n'),
'escaped_link':('\\[CODE](OLD) [LIVE](OLD)\n','\\[CODE](OLD) [LIVE](NEW)\n'),
'image_reference':('![icon][ref]\n\n[ref]: OLD\n\n[LIVE](OLD)\n','![icon][ref]\n\n[ref]: OLD\n\n[LIVE](NEW)\n'),
}
rows=[]
def run(name,a,b,prior=False):
 t=o.CouncilRoleLinkRepairUpgradeTests('runTest');t.setUp()
 try:
  if prior:(t.scripts/'render_agent_surfaces.py').write_bytes(Path('/tmp/wf-204mp-pre-autolink-renderer.py').read_bytes())
  def content(s):return s.replace('OLD',t.old.name).replace('NEW',t.new.name).replace('\n','\r\n').encode()
  orig,expect=content(a),content(b);t.peer.write_bytes(orig);t.peer.chmod(0o640)
  before=t._tree();preview=t._preview_incoming_role_links();readonly=t._tree()==before
  t._surface();actual=t.peer.read_bytes();mode=stat.S_IMODE(t.peer.stat().st_mode);moved=not t.old.exists() and t.new.is_file()
  t._surface();repeat=t.peer.read_bytes();stablemode=stat.S_IMODE(t.peer.stat().st_mode)==mode==0o640
  html=md.render(a.replace('OLD',t.old.name));html_expected=md.render(b.replace('OLD',t.old.name).replace('NEW',t.new.name))
  rows.append(dict(name=name,pre_autolink=prior,passed=actual==expect and repeat==expect and readonly and moved and stablemode,exact_bytes=actual==expect,reinstall=repeat==expect,preview_read_only=readonly,role_moved=moved,mode_preserved=stablemode,original=orig.decode(),expected=expect.decode(),observed=actual.decode(),oracle_html=html,expected_oracle_html=html_expected,preview=preview))
 finally:t.doCleanups()
for name,(a,b) in C.items():run(name,a,b)
for name in list(C)[:6]:run(name,*C[name],prior=True)
Path('/tmp/wf-204mp-autolink-own-matrix.json').write_text(json.dumps(rows,indent=2))
print(json.dumps([dict(name=r['name'],old=r['pre_autolink'],passed=r['passed'],observed=r['observed'] if not r['passed'] else 'exact') for r in rows],indent=2))
