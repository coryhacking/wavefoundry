"""Pre-change baseline driver for the 1whup prose measurement (wave 1wik9).

The golden set changed after the first freeze (the trio-anchored fence queries
violated Requirement 5's anchor-uniqueness constraint and were replaced by
unique-anchor queries over three new fence fixture files), so the standing
watchpoint forces a baseline re-run. The chunker on disk already carries the
doc-code change and git HEAD predates the whole uncommitted 1wfsl footprint
(HEAD chunker is v32, not the pre-1whup v34), so no pre-change chunker file
exists to load. The driver instead reconstructs the pre-change MEASUREMENT
SURFACE: over the 16-row markdown differential fixture, the classified
regeneration diff (regen_differentials_1whup.json) showed the only v34 -> v35
output change is the fence row itself (kind code -> doc-code plus the ordinal
id; every prose row byte-identical), and code reading plus executed
adjacent-content probes extend that equivalence to the rst/adoc and prompt
paths (their kind/ordinal/breadcrumb changes are confined to the emitted
code-chunk list, which the pre-change docs mirror excluded as kind "code"
anyway; an independent cross-check against the committed 1wfsl v33-era prose
eval reproduced all 91 docs-mirror rows). Running the current chunker with
the harness's docs mirror restricted to the pre-change kind set therefore
yields the pre-change corpus. [Precision note per the delivery review: the
byte-diffed evidence covers the markdown fixture; the rst/adoc leg rests on
the confinement argument plus those probes, not a v34 byte-diff — no v34
chunker exists on disk (git HEAD is v32).]

Run under the tool venv from the repository root:
    ~/.wavefoundry/venv/bin/python \
      "docs/waves/1wik9 fenced-diagram-and-spec-retrieval/evidence/baseline_prechange_driver.py" \
      --out <results.json> --label "<label>"
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = REPO_ROOT / ".wavefoundry" / "framework" / "scripts"
HARNESS = SCRIPTS / "tests" / "fixtures" / "retrieval_golden" / "run_retrieval_eval.py"

PRECHANGE_DOCS_KINDS = frozenset({"doc", "doc-summary", "seed", "prompt"})


def main() -> int:
    spec = importlib.util.spec_from_file_location("run_retrieval_eval", HARNESS)
    harness = importlib.util.module_from_spec(spec)
    sys.modules["run_retrieval_eval"] = harness
    spec.loader.exec_module(harness)
    assert harness.chunker.CHUNKER_VERSION == "35", (
        "the surface-equivalence argument above is stated against v35; "
        f"found {harness.chunker.CHUNKER_VERSION} — re-verify before reuse")
    harness._DOCS_KINDS = PRECHANGE_DOCS_KINDS
    sys.argv = [str(HARNESS), "--set", "prose", *sys.argv[1:]]
    return harness.main()


if __name__ == "__main__":
    raise SystemExit(main())
