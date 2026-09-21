# Independent delivery QA

Owner: Engineering
Status: active
Last verified: 2026-09-21

## Verdict and scope

Renderer behavior passes the bounded independent QA review. No executable behavior blocker found. The seed 050 editorial insertion was corrected and independently rechecked: Task 5 cross-reference is restored, and the unchanged defaults paragraph now stands before the unique tools-contract section. Full framework suite was coordinator-run and its green result and current receipt were independently verified; AC-5 has verification evidence.

Fresh independent qa-reviewer context `model-policy-delivery-qa-20260921`; did not author implementation or plan. Requested host-default model/effort for bounded adversarial configuration checks; observed runtime identity unknown. Budget: ten minutes, risk-selected probes; source edits forbidden. Before and after the initial probe, the 16-path hashes both matched `f4c777e5e7108bec4e52ba2f5eb03f82349c145d438dfe836b0234776ea74b48`, baseline `ead35718`. If the coordinator edits seed 050, only that documentation delta needs additional inspection; executable source evidence remains scoped to unchanged hashes.

## Executed evidence and AC mapping

- AC-1: fresh complete render emits no model/effort header, retains retrieval tool list and explicit read-only body; checked seed default removal. Existing renderer suite includes the fixed-default negative control. Factor generation is seed-guided; no live agent generation was claimed.
- AC-2: independent matrix runs 48 malformed scenarios (six header defects × two newline styles × missing/stale protocol × Guru available/unavailable), each twice. Exact bytes preserved, warning emitted, wrapper omitted from written list. Twelve valid scenarios preserve CRLF header bytes, deliberate Sonnet/high, quoted inherit/low, opus/max, custom name, sequence tool list and unrelated custom keys; stale policy refreshes. Existing suite adds missing delimiter and future-value cases.
- AC-3: all valid cases and one fresh case compare full bytes after repeat and require wrapper absent from repeat written list. Independently invoked unmocked `render_platform_surfaces.py --repo-root <temporary-root> --platform claude --manifest <temporary-manifest>` twice for valid and malformed wrappers: each exit 0, expected bytes retained, second manifest exactly `{"written": []}`. This reaches actual CLI subprocess without mocking Python resolution.
- AC-4: inspected canonical task-selection and requested/observed/unknown clauses and local pointers. No new runtime identity verification or cost claim. Seed 050 placement correction was independently verified.
- AC-5: independently ran `PYTHONPATH=.wavefoundry/framework/scripts python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_render_*surfaces.py'`: 236 tests passed in 11.879 seconds, no skips reported. Guided `wf_review_wave(phase='delivery')` reported lint_passed=true. Coordinator final suite ran 9452 tests across 117 files in 311.586 seconds, green with 12 suite-reported skips; QA independently read the log and recomputed its receipt hash.

## Mutation table

| Mutant | Faithful boundary and failed oracle | Outcome |
| --- | --- | --- |
| Replace `_merge_claude_agent` with unconditional generated template | Complete `render_agent_surfaces` with explicit Sonnet/high and tools Read; exact original header no longer prefixes output | Killed |
| Replace `_claude_agent_frontmatter` with unconditional acceptance | Complete `render_agent_surfaces`, Guru unavailable, duplicate model and missing protocol; byte-equality oracle detects initial reconciler mutation | Killed |
| Reinsert fixed template model | Existing suite self-mutant test executed in 236-test run | Killed by suite; not independently reimplemented |

No surviving mutant; no broader sweep needed. Positive and negative controls use real temporary trees and whole-render calls. Runtime monkeypatches are confined to the probe process; repository source unchanged. Permissions and runtime model configuration were not modified; no external, credential-bearing or paid calls.

## Limitations

Configuration behavior only. No observed effective host model, reviewer adherence or cost savings; no full packaged upgrade. Public CLI and renderer tests cover the called render boundary, while the separate coordinator upgrade evidence owns extraction ordering. The finite matrix is not a general YAML parser certification. No new deferrals or `[~]` rows requested. AC-5 now has passing scoped tests, full-suite receipt and guided documentation validation evidence; coordinator owns final checkbox/bookkeeping updates.

## Reproducible independent matrix

Run the following as a temporary script using `python3 -B` from the repository root. It is reproduced here to keep evidence durable without adding source/test files.

```python
import sys,tempfile,pathlib,contextlib,io,json
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path('.wavefoundry/framework/scripts').resolve()))
import render_agent_surfaces as r
REL='.claude/agents/guru.md'
def fixture(root,header=None,guru=True,protocol='missing'):
 (root/'.claude/agents').mkdir(parents=True)
 if guru:
  (root/'docs/agents').mkdir(parents=True); (root/'docs/agents/guru.md').write_text('# Guru\n')
 if header is not None:
  body='\n# Operator old body\n'
  if protocol=='stale': body+='\n'+r.REVIEW_PROTOCOL_MARKER_BEGIN+'\nold policy\n'+r.REVIEW_PROTOCOL_MARKER_END+'\n'
  (root/REL).write_bytes(header+body.encode())
def invoke(root):
 stderr=io.StringIO()
 with contextlib.redirect_stderr(stderr): written=r.render_agent_surfaces(root)
 return written,stderr.getvalue()
count=0
# Matrix deliberately built independently of implementation's test helpers.
for guru in (True,False):
 for protocol in ('missing','stale'):
  for field in (b'model: sonnet\nmodel: opus\n',b'effort: [high]\n',b'model: |\n  sonnet\n',b'model: "unterminated\n',b'effort:\n',b' model: sonnet\n'):
   for nl in (b'\n',b'\r\n'):
    with tempfile.TemporaryDirectory() as d:
     root=pathlib.Path(d); header=(b'---\nname: guru\n'+field+b'---\n').replace(b'\n',nl); fixture(root,header,guru,protocol); before=(root/REL).read_bytes()
     for repeat in range(2):
      written,err=invoke(root); assert (root/REL).read_bytes()==before; assert REL not in written; assert 'malformed or ambiguous Claude agent frontmatter' in err
     count+=1
for guru in (True,False):
 for protocol in ('missing','stale'):
  for pref in ('model: sonnet\neffort: high\n','"model": "inherit" # explicit\n\'effort\': low\n','model: opus\neffort: max\n'):
   with tempfile.TemporaryDirectory() as d:
    root=pathlib.Path(d); header=('---\nname: custom-guru\n'+pref+'tools:\n  - Read\n  - mcp__wavefoundry__code_read\ncustom: [a, b]\n---\n').replace('\n','\r\n').encode(); fixture(root,header,guru,protocol)
    invoke(root); first=(root/REL).read_bytes(); assert first.startswith(header),first[:len(header)]; assert b'old policy' not in first; assert r.REVIEW_PROTOCOL_MARKER_BEGIN.encode() in first
    written,_=invoke(root); assert (root/REL).read_bytes()==first; assert REL not in written
    count+=1
with tempfile.TemporaryDirectory() as d:
 root=pathlib.Path(d); fixture(root); invoke(root); first=(root/REL).read_bytes(); front=first.decode().split('---')[1]; assert 'model:' not in front and 'effort:' not in front; assert 'tools: Read, Grep, Glob, Bash, ToolSearch' in front; assert 'Read-only in this subagent' in first.decode(); written,_=invoke(root); assert first==(root/REL).read_bytes() and REL not in written; count+=1
print('PASS independent scenarios',count)
# Inject known-bad old overwrite on the real complete render route.
with tempfile.TemporaryDirectory() as d:
 root=pathlib.Path(d); header=b'---\nname: guru\nmodel: sonnet\neffort: high\ntools: Read\n---\n'; fixture(root,header)
 with patch.object(r,'_merge_claude_agent',lambda text,generated,path:generated): invoke(root)
 assert not (root/REL).read_bytes().startswith(header)
print('KILLED unconditional-template-overwrite: explicit header assertion detects loss')
# Bypass all frontmatter guards: no-Guru first reconciliation alone must mutate.
with tempfile.TemporaryDirectory() as d:
 root=pathlib.Path(d); fixture(root,b'---\nmodel: sonnet\nmodel: opus\n---\n',False); before=(root/REL).read_bytes()
 with patch.object(r,'_claude_agent_frontmatter',lambda text,path:''): invoke(root)
 assert (root/REL).read_bytes()!=before
print('KILLED validation-bypass: byte-equality assertion detects no-Guru reconciliation mutation')

```

## Editorial delta verification

Rechecked final fingerprint `76014eb765102ad99c642342120c5d34116dcacaacaef9905e0978947d42a890` against all 16 current git blob hashes. Compared final and archived initial fingerprint maps: only seed 050 changed; renderer and test source hashes are unchanged. Targeted MCP reads verify restored Task 5 sentence and standalone default policy before the tools contract. Final suite completed green: 9452 tests across 117 files, 12 reported skips, 311.586 seconds. QA read `/tmp/1ycrj-final-suite.log` and `.wavefoundry/framework/test-cache.json`, then independently executed `run_tests._hash_inputs()` and matched receipt `bccb13c717c88225f91743b96af31951603588d51d9fe9ab5790a8947837a4e0` (result `ok`, ran_at `2026-09-21T16:45:37.920997+00:00`). Scope-specific 236-test run had no skips. All 16 final delivery hashes were rechecked and match `76014eb765102ad99c642342120c5d34116dcacaacaef9905e0978947d42a890`. No remaining QA blocker.
