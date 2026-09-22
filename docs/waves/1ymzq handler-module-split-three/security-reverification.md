# Security Readiness Reverification

Owner: Engineering
Status: active
Last verified: 2026-09-21

Context: `split3-fresh-security-repair-20260921`; fresh independent security-reviewer, with no participation in the plan repair. Readiness review only, not delivered behavior. Bounded sweep: all eleven remaining planned adoption bodies and the indexer removal guard. No full suite, index build, production mutation or public indexing invocation ran.

## Verdict

The repair for `READY-DELTA-CONTAINMENT-ERROR` is verified: requirement 2, AC-2 and the allowlist now preserve `indexer._is_relative_to` and all callers unchanged. Re-executing the exact AST-extracted probe in readiness-review.md produced current `OSError` versus normal return for the known-bad exception-to-False simulation. This clears that finding only.

New blocker `READY-ROOT-RESOLUTION-CONTRACT`: requirement 2's outright adoption of renderer and TechDocs helpers changes their root-resolution error contract. `render_agent_surfaces.py:1663` resolves the root outside its candidate-resolution try; root `OSError` propagates. `techdocs_audit_lib.py:963` catches only `RuntimeError`, so that same root `OSError` propagates through its wrapper. The proposed primitive catches `OSError`; the proposed renderer wrapper raises `RuntimeError` on None and direct TechDocs adoption returns None. This fails required AC-2's unchanged failure contract. No authorization bypass or destructive effect is claimed.

Minimal plan repair: explicitly retain the renderer's existing root resolution before invoking the primitive, and retain an equivalent uncaught root-resolution step for the TechDocs repoint. Pin root-resolution OSError propagation at both sites with a targeted differential test, and inventory every retained resolution/exception boundary before adoption. If exact exception/message preservation cannot coexist with outright adoption, classify these as sub-clause adoptions or allowlist them; do not silently weaken AC-2.

The plan rationale also calls the renderer a "strict form"; actual source uses `candidate.resolve(strict=False)` at line 1666. Preserve acceptance of missing write targets explicitly and pin it; interpreting that phrase as `strict=True` would break first-time carrier creation. The phrase could mean raising behavior, so this is a clarification in the same repair rather than a separately proven regression.

The other nine adopters retain their existing resolution statements and stronger clauses under the plan's sub-clause rule. Their initial resolution failure behavior is therefore preserved as planned. New re-resolution work inside the primitive remains subject to implementation review and injected-error tests; source-text pins alone cannot establish behavioral equivalence. No additional concrete blocker was established in that bounded sweep.

## Executed differential probe

Run from repository root with `python3 -B`; the current renderer body is compiled from source rather than reimplemented. `techdocs` below faithfully represents its observed catch boundary; the proposed side simulates only the plan's error mapping because the primitive does not exist.

```python
import ast
from pathlib import Path
from unittest.mock import patch
p = Path('.wavefoundry/framework/scripts/render_agent_surfaces.py')
tree = ast.parse(p.read_text())
ns = {'Path': Path}
body = [n for n in tree.body if isinstance(n, ast.FunctionDef)
        and n.name == '_contained_review_carrier_path']
exec(compile(ast.Module(body=body, type_ignores=[]), '<exact-renderer>', 'exec'), ns)
old = ns['_contained_review_carrier_path']
def proposed(root, destination):
    try:
        root = root.resolve()
        path = (root / destination).resolve()
        path.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        raise RuntimeError('primitive returned None')
    return path
def techdocs(helper, root, destination):
    try:
        return helper(root, destination)
    except RuntimeError:
        return None
for error in (OSError, RuntimeError):
    with patch.object(Path, 'resolve', side_effect=error('root resolution failure')):
        for label, call in [
            ('renderer current', lambda: old(Path('/repo'), 'docs/a.md')),
            ('renderer proposed', lambda: proposed(Path('/repo'), 'docs/a.md')),
            ('techdocs current', lambda: techdocs(old, Path('/repo'), 'docs/a.md')),
            ('techdocs proposed', lambda: techdocs(proposed, Path('/repo'), 'docs/a.md')),
        ]:
            try:
                print(error.__name__, label, repr(call()))
            except Exception as exc:
                print(error.__name__, label, type(exc).__name__)
```

Expected: each current/planned pair preserves exception class or None outcome. Observed:

```text
OSError renderer current OSError
OSError renderer proposed RuntimeError
OSError techdocs current OSError
OSError techdocs proposed None
RuntimeError renderer current RuntimeError
RuntimeError renderer proposed RuntimeError
RuntimeError techdocs current None
RuntimeError techdocs proposed None
```

| Mutation | Detection | Limitation |
| --- | --- | --- |
| Indexer OSError-to-False | Removal validation changes from OSError to normal return | Existing documented extracted guard; no stored rows changed |
| Root OSError swallowed by planned primitive | Renderer OSError becomes RuntimeError; TechDocs OSError becomes None | Injected root failure, proposed mapping simulation, no shipped primitive exists |

No assertion of a real filesystem failure reproduction or registered public-path execution. Integrity applies to these named faithful boundaries and plan review. Runtime model identity unknown.

## Reviewed fingerprint

`git hash-object` at review: containment plan `4af183634b8b8136fdad9e2b61f985adaa72c80d`; indexer `bfc54b3dfc2bc3785eb3d9fe3fd9fe0d12992b7b`; renderer `8d3d302e78bd3aee3bc61c5574c497c1c15408f8`; TechDocs `717d2860480d3c5e2001058cccc2510b3ce8a464`.

Next action: escalate the remaining focused-round blocker to the coordinator/operator under Prepare Wave. No overall security approval is given.
