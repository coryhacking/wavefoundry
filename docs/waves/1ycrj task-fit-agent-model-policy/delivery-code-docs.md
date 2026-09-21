# Delivery Code And Docs Contract Review

Owner: Engineering
Status: active
Last verified: 2026-09-21

Verdict: approve code-reviewer and docs-contract-reviewer delivery lanes after the focused editorial recheck. The relocated seed 050 paragraph stands separately before the full wrapper-tools contract, and task 5 has its original cross-reference restored. Both roles share this one fresh independent context (`model-policy-delivery-code-docs-20260921`); these are correlated reviews, not two independent agents. I authored none of the implementation. Requested model and effort: host defaults, appropriate for a bounded, coupled renderer/policy review with executable discrimination. Actual runtime model/effort identity: unknown. No performance, cost, adherence or effective model-selection claim.

Before and after probes, each git blob hash matched evidence/delivery-fingerprint.json, and the computed SHA256 was `f4c777e5e7108bec4e52ba2f5eb03f82349c145d438dfe836b0234776ea74b48` (baseline `ead35718`). Source remained frozen during the initial review. The subsequent editorial-only seed 050 relocation was rechecked at final fingerprint `76014eb765102ad99c642342120c5d34116dcacaacaef9905e0978947d42a890`; all other 15 scoped paths match the initial snapshot. The complete independent probe was rerun successfully against this final tree. The separately requested artifact durably retains my independently written probe and its limitations; it is not a second review authority.

## Verified scope

MCP outline and targeted reads established `_claude_agent_frontmatter`, `_merge_claude_agent`, both reconciliation paths in `render_agent_surfaces`, and the registered `render_platform_surfaces.main` path. Existing header bytes are retained, including quoted unknown model values, effort comments, custom names and restricted `tools: Read`/`permissionMode: plan`; only the generated Guru body refreshes. A registered code-reviewer wrapper with non-scalar effort and absent protocol markers stays byte-identical, warns, is omitted from manifest, and returns zero across two complete renders both with and without canonical Guru. Fresh rendering has no model or effort key.

The five local wrapper diffs against the baseline each delete only `model: sonnet`, preserving allowlists and remaining bytes. Seed 050 removes the Guru example pin and instructs neutral fresh factor defaults. Seed 180 adds primary delegation-time choice and truthful requested/observed/unknown reporting while retaining its task-fit and operator constraints. The three local pointers name the owner and unknown limitation. Seed 160 and the local upgrade prompt match on proven-origin retirement, ambiguous-pin retention, stderr-only warning visibility, no automatic prose-migration claim, and running-host cache limits.

The upgrade probe was independently rerun successfully: `phase_surface_rendering` executes replacement on-disk code in a fresh subprocess. `upgrade_wavefoundry.main` was source-checked for extraction preceding that phase. This is not a complete installed-package upgrade run; no live host, model call or provider behavior was verified. Policy prose checks demonstrate the instruction exists, not that a future worker obeys it. Full suite and docs gate are coordinator-owned and were not duplicated.

## Discriminating controls

| Mechanism | Mutation | Result |
| --- | --- | --- |
| Whole-render malformed wrapper guard | In-memory bypass only for registered code-reviewer wrapper, leaving Guru preservation intact | Probe failed specifically `factor bytes changed` (historical assertion label; actual fixture is code-reviewer.md), proving real reconciliation was reached |
| Truthful unknown runtime policy | Remove the canonical unknown-identity sentence in memory | Policy contract assertion failed on the removed clause |

All five evidence-integrity checks are true for these bounded executed propositions: no unintended skip, real public renderer boundary reached, realistic concrete values, non-vacuous assertions, and known-bad controls detected. Native platform/Python resolution discovery is stubbed to avoid machine changes; renderer behavior itself is real. Temporary roots only. No source mutation, external calls, credentials or paid operations.

The initial candidate factor fixture was not a registered reconciliation carrier and produced no warning; that instrumentation gap was corrected to the registered code-reviewer wrapper before making the executed claim. Factor wrappers remain unchanged by that reconciler; no unexecuted warning claim is made for untouched unregistered files.

## Reproduction

Save the following code in a temporary file and run `PYTHONPATH=.wavefoundry/framework/scripts python3 -B <file>` from repository root. Observed output: baseline two renders each with/without Guru; whole-render mutant killed; fresh defaults neutral; policy propagation asserted; unknown-identity mutant killed.

```python
import contextlib,io,json,tempfile
from pathlib import Path
from unittest.mock import patch
import render_agent_surfaces as ras
import render_platform_surfaces as rps
import venv_bootstrap

def exercise(mutant=False, guru=True):
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp); wrappers=root/'.claude/agents'; wrappers.mkdir(parents=True)
        if guru:
            role=root/'docs/agents/guru.md'; role.parent.mkdir(parents=True); role.write_text('# Guru\n')
        factor=wrappers/'code-reviewer.md'
        malformed=b'---\r\nname: code-reviewer\r\neffort: [high]\r\ntools: Read\r\n---\r\nBody with absent protocol\r\n'
        factor.write_bytes(malformed)
        wrapper=wrappers/'guru.md'
        header=b'---\r\nname: custom\r\n"model": "future/vendor"\r\neffort: high # explicit\r\ntools: Read\r\npermissionMode: plan\r\n---\r\n'
        wrapper.write_bytes(header+b'Old body\r\n')
        original=ras._claude_agent_frontmatter
        def bypass(text,path):
            return '' if path.name=='code-reviewer.md' else original(text,path)
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(venv_bootstrap,'ensure_python_resolves',return_value='ok'))
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            stderr=stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
            if mutant: stack.enter_context(patch.object(ras,'_claude_agent_frontmatter',side_effect=bypass))
            for i in range(2):
                manifest=root/f'm{i}.json'
                assert rps.main(['--repo-root',str(root),'--platform','claude','--manifest',str(manifest)])==0
                changed=json.loads(manifest.read_text())['written']
                assert factor.read_bytes()==malformed, 'factor bytes changed'
                assert '.claude/agents/code-reviewer.md' not in changed
                assert wrapper.read_bytes().startswith(header), 'operator header changed'
                if guru: assert b'## Your job' in wrapper.read_bytes()
                if i: assert wrapper.read_bytes()==first, 'repeat changed wrapper'
                first=wrapper.read_bytes()
            assert 'render_agent_surfaces: WARNING' in stderr.getvalue()
for guru in (True,False): exercise(guru=guru)
try: exercise(mutant=True)
except AssertionError as exc:
    assert str(exc)=='factor bytes changed'; print('baseline: 2 complete renders each with/without Guru; mutant killed: '+str(exc))
else: raise AssertionError('whole-render factor guard mutant survived')
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp); (root/'.claude').mkdir(); (root/'docs/agents').mkdir(parents=True)
    (root/'docs/agents/guru.md').write_text('# Guru\n')
    with contextlib.redirect_stdout(io.StringIO()),patch.object(venv_bootstrap,'ensure_python_resolves',return_value='ok'):
        assert rps.main(['--repo-root',str(root),'--platform','claude'])==0
    header=(root/'.claude/agents/guru.md').read_text().split('---',2)[1]
    assert '\nmodel:' not in header and '\neffort:' not in header
repo=Path.cwd()
policy=(repo/'.wavefoundry/framework/seeds/180-implement-feature.prompt.md').read_text()
required=['Delegation-time selection is primary','inheritance alone is not a task-fit decision','When the host does not expose the actual model or effort, record unknown','This adds no telemetry store','Optimize total verified effort','Respect operator choices']
def policy_contract(text):
    for clause in required: assert clause in text,clause
policy_contract(policy)
try: policy_contract(policy.replace(required[2],''))
except AssertionError as exc: assert str(exc)==required[2]
else: raise AssertionError('unknown-identity policy mutant survived')
for name in ('docs/agents/platform-mapping.md','docs/contributing/agent-team-workflow.md','docs/prompts/implement-feature.prompt.md'):
    text=(repo/name).read_text(); assert '180-implement-feature.prompt.md' in text and 'unknown when unavailable' in text
for name in ('.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md','docs/prompts/upgrade-wavefoundry.prompt.md'):
    text=(repo/name).read_text()
    for clause in ('Never add a framework pin or infer ownership from a model name','not an automatic prose migration claim','fresh subprocess after extraction','does not reload agent definitions','stderr warning is not added to the upgrade summary'):
        assert clause in text,(name,clause)
print('fresh defaults neutral; policy propagation asserted; missing unknown-identity clause mutant killed')
```
