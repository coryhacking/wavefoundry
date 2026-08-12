"""Wave 1v454 / AC-6 acceptance validation: the int8 re-embed happens EXACTLY ONCE.

NOT part of the standard suite, by design. ``run_tests.py`` discovers ``test_*.py`` only
(see its ``_TESTS_DIR.glob("test_*.py")``), so this filename is deliberately outside that
pattern: it is never collected, never reported as a skip, and does not move the suite count.
A skipped test inside the suite would be indistinguishable from an UNINTENDED skip, which is
exactly the failure mode the review evidence contract's ``test_ran_without_unintended_skip``
field exists to catch. An operator-run file avoids that ambiguity entirely.

Run it deliberately, from the repository root:

    ~/.wavefoundry/venv/bin/python .wavefoundry/framework/scripts/tests/acceptance_ac6_int8_reembed.py

Exit code 0 means AC-6 holds. Any other exit code prints what failed.

WHAT IT PROVES, and why the second half is the one that matters:

  1. An index carrying the PRE-change int8 identity re-embeds when this change lands.
  2. The very next build, with no content change, re-embeds NOTHING.

Half 2 is the load-bearing half. ``_identity_fingerprint_for_class`` is consulted by both the
compare sites and the write site; if those two ever disagree, every incremental build would
re-embed the whole corpus forever, because the compare would keep seeing a mismatch it had
just written. The unit tests assert that agreement at the identity level. This file asserts it
end to end, through a real ``build_index``.

The int8 class is obtained by forcing provider selection to CPU rather than by patching
``_predicted_precision_class``. Patching the predicate under test would make the run vacuous:
we want the REAL classification path to produce ``int8``, and the precondition below fails
loudly if it does not.

Embedders are mocked (as the standard suite does) because AC-6 is about the re-embed DECISION
and the chunk accounting, not about vector values. Vector-level behaviour is covered by the
real-graph evidence in the change doc's Progress Log.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

SCRIPTS = Path(__file__).resolve().parent.parent

# Force CPU classification BEFORE indexer/accel_embedder are imported, so the real
# provider-selection path resolves to a CPU-bound machine and the recorded class is `int8`.
os.environ["WAVEFOUNDRY_EMBED_PROVIDER_SELECTED"] = "CPUExecutionProvider"

sys.path.insert(0, str(SCRIPTS))
import venv_bootstrap  # noqa: E402

venv_bootstrap.activate_tool_venv()

import numpy as np  # noqa: E402


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _embedder_mock(calls: list[list[str]], dim: int = 4):
    def fake_embed(texts, batch_size=256):
        text_list = list(texts)
        calls.append(text_list)
        for _ in text_list:
            yield np.zeros(dim, dtype=np.float32)

    mock = MagicMock()
    mock.embed.side_effect = fake_embed
    return mock


def _make_repo(root: Path) -> None:
    """Mirror the standard suite's repo fixture, including the workflow config it writes."""
    import json

    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "workflow-config.json").write_text(
        json.dumps(
            {"lifecycle_id_policy": {"epoch_utc": "2020-02-02T02:02:00Z", "hour_offset": 0}}
        ),
        encoding="utf-8",
    )
    (root / "docs" / "guide.md").write_text(
        "## Intro\n\nWave lifecycle documentation body.\n", encoding="utf-8"
    )
    (root / "src" / "handler.py").write_text(
        "def handle(req):\n    return process(req)\n", encoding="utf-8"
    )


def main() -> int:
    bi = _load("indexer")
    iss = _load("index_state_store")
    failures: list[str] = []

    def check(label: str, ok: bool, detail: str = "") -> None:
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f" -- {detail}" if detail else ""))
        if not ok:
            failures.append(label)

    print("AC-6: int8 re-embed happens exactly once\n")

    # --- Precondition. If this fails the whole run is vacuous, so it is a hard stop. ---
    predicted = bi._predicted_precision_class(bi.DOCS_MODEL, bi._onnx_providers())
    print(f"precondition: predicted precision class = {predicted!r}")
    if predicted != "int8":
        print(
            "  ABORT: could not obtain an int8-class machine. This run would have proved "
            "nothing, so it refuses rather than reporting a green result.\n"
            "  A GPU provider is still being selected despite "
            "WAVEFOUNDRY_EMBED_PROVIDER_SELECTED=CPUExecutionProvider."
        )
        return 2

    bare = bi.EMBEDDING_MODEL_SET_FINGERPRINT
    revised = bi._identity_fingerprint_for_class("int8")
    check(
        "int8 identity differs from the bare fingerprint",
        revised != bare,
        f"{revised!r} != {bare!r}",
    )

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_repo(root)
        index_dir = root / ".wavefoundry" / "index"

        def build(full: bool = False) -> tuple[dict, list[str]]:
            docs_calls: list[list[str]] = []
            code_calls: list[list[str]] = []
            with patch.object(
                bi,
                "_get_embedder",
                side_effect=[_embedder_mock(docs_calls), _embedder_mock(code_calls)],
            ):
                res = bi.build_index(root, full=full, content="all", verbose=False)
            embedded = [t for batch in docs_calls + code_calls for t in batch]
            return res, embedded

        # --- Establish an index on the current code. ---
        _, first_embedded = build(full=True)
        check("initial full build embedded content", len(first_embedded) > 0,
              f"{len(first_embedded)} chunk(s)")

        meta = iss.read_build_summary(index_dir) or {}
        recorded = (meta.get("model_versions") or {}).get("docs", "")
        check(
            "a fresh int8 build records the encoding revision",
            bi._model_set_fingerprint_from_version(recorded) == revised,
            recorded,
        )

        # --- Simulate an index built BEFORE this change: int8 class, bare fingerprint. ---
        meta.setdefault("model_versions", {})
        for layer, model in (("docs", bi.DOCS_MODEL), ("code", bi.CODE_MODEL)):
            meta["model_versions"][layer] = f"{model}@int8@{bare}"
        # Seeded through the canonical producer the standard suite uses, so the fixture is
        # written exactly the way production records it rather than hand-shaped.
        iss.write_build_bookkeeping(index_dir, meta)

        # --- Half 1: the one-time re-embed. ---
        result_a, embedded_a = build(full=False)
        check(
            "a pre-revision int8 index re-embeds when this change lands",
            len(embedded_a) > 0 and not result_a.get("up_to_date", False),
            f"{len(embedded_a)} chunk(s) re-embedded",
        )

        # --- Half 2: it must then STOP. This is the perpetual-loop guard. ---
        result_b, embedded_b = build(full=False)
        check(
            "the very next build with no content change re-embeds NOTHING",
            len(embedded_b) == 0,
            f"{len(embedded_b)} chunk(s) re-embedded (expected 0)",
        )
        check(
            "the settled identity is the revised one",
            bi._model_set_fingerprint_from_version(
                ((iss.read_build_summary(index_dir) or {}).get("model_versions") or {}).get("docs", "")
            )
            == revised,
        )

    print()
    if failures:
        print(f"AC-6 NOT satisfied. Failing checks: {', '.join(failures)}")
        return 1
    print("AC-6 satisfied: re-embed occurred once and then stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
