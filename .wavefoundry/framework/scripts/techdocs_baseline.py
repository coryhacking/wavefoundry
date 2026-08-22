#!/usr/bin/env python3
"""``wf techdocs-baseline`` — generate the missing-only Backstage catalog and TechDocs baseline (wave 1vj4e).

A thin CLI entry (the ``gpu_doctor.py`` pattern) over
``render_agent_surfaces.render_techdocs_baseline``: it parses ``--root``/``--json``, calls the module
function, and formats the typed result. All behavior (the navigation-target precondition, the
containment classification of the three destinations, the missing-only ``O_EXCL`` writes, the
generated-by marker, and the marker-derived partial record) lives in the module function so a later
flag-gated setup/upgrade caller inherits it; nothing is re-implemented here.

Exit codes: 0 (generated, preserved, or a mixed trio with its warning), 1 (precondition unmet: one
stderr line names the missing navigation targets, nothing written), 2 (refused or failed). Exit 2
covers two shapes the ERROR line distinguishes: a preflight refusal (containment escape or a
non-regular destination), where nothing was written, and a post-preflight write failure, where the
envelope's ``written_paths`` names what this run wrote before failing and
``preserved_paths``/``generated_paths`` report the members on disk now. Text mode prints
``techdocs-baseline: generated <path>`` /
``techdocs-baseline: preserved <path>`` on stdout and ``techdocs-baseline: WARNING ...`` /
``techdocs-baseline: ERROR ...`` on stderr; ``--json`` prints one envelope on stdout on every exit
(``written_paths``, ``preserved_paths``, ``generated_paths``, ``missing_targets``, ``partial``,
``refusal``) and keeps the WARNING/ERROR line on stderr.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import venv_bootstrap  # the single venv resolver (wave 1p7pl)
import cli_stdio  # shared UTF-8 stdio reconfigure (wave 1p8gv)

# Activate the shared tool venv IN-PROCESS like every other ``wf`` subcommand (no-op when already
# in the venv or when it does not exist yet). CLI entry: UTF-8 stdout/stderr (wave 1p8gv).
venv_bootstrap.activate_tool_venv()
cli_stdio.configure_utf8_stdio()

_PREFIX = "techdocs-baseline"


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="wf techdocs-baseline",
        description=(
            "Generate the missing-only Backstage catalog and TechDocs baseline (catalog-info.yaml, "
            "mkdocs.yml, docs/index.md) for this repository. Runs only when docs/references/"
            "project-overview.md, docs/ARCHITECTURE.md, and docs/prompts/index.md exist; existing "
            "files are preserved byte-for-byte; a mixed trio (some generated, some project-owned) "
            "prints one WARNING. Invoked by the Refresh TechDocs workflow."
        ),
    )
    parser.add_argument(
        "--root",
        default=None,
        help="Repository root (default: discovered by walking up from the current directory).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print one JSON envelope on stdout (written_paths, preserved_paths, generated_paths, "
        "missing_targets, partial, refusal) instead of the text summary.",
    )
    return parser.parse_args(argv)


def _emit(
    *,
    as_json: bool,
    written: list[str],
    preserved: list[str],
    generated: list[str],
    missing_targets: list[str],
    partial: dict | None,
    refusal: str | None,
) -> None:
    if missing_targets:
        print(
            f"{_PREFIX}: ERROR precondition unmet; missing navigation targets: "
            + ", ".join(missing_targets)
            + " (nothing written)",
            file=sys.stderr,
        )
    if refusal:
        suffix = "" if written else " (nothing written)"
        print(f"{_PREFIX}: ERROR {refusal}{suffix}", file=sys.stderr)
    if partial:
        print(f"{_PREFIX}: WARNING {partial['detail']}", file=sys.stderr)
    if as_json:
        print(
            json.dumps(
                {
                    "written_paths": list(written),
                    "preserved_paths": list(preserved),
                    "generated_paths": list(generated),
                    "missing_targets": list(missing_targets),
                    "partial": partial,
                    "refusal": refusal,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return
    for path in written:
        print(f"{_PREFIX}: generated {path}")
    for path in preserved:
        print(f"{_PREFIX}: preserved {path}")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(list(sys.argv[1:] if argv is None else argv))
    if args.root:
        repo_root = Path(args.root).expanduser().resolve()
    else:
        from render_platform_surfaces import discover_repo_root

        repo_root = discover_repo_root()

    from render_agent_surfaces import (
        TechdocsDestinationRefused,
        TechdocsWriteFailed,
        classify_techdocs_baseline,
        render_techdocs_baseline,
        techdocs_member_states,
    )

    try:
        result = render_techdocs_baseline(repo_root)
    except TechdocsDestinationRefused as exc:
        # Preflight: refused before the first write, so the tree is untouched.
        _emit(
            as_json=args.json,
            written=[],
            preserved=[],
            generated=[],
            missing_targets=[],
            partial=None,
            refusal=str(exc),
        )
        return 2
    except TechdocsWriteFailed as exc:
        # After preflight (an unreadable packaged template, an O_EXCL collision,
        # a write error): earlier members may be on disk, so report the tree.
        written = list(exc.written_paths)
        generated, preserved, _absent = techdocs_member_states(repo_root)
        detail = "" if not written else f"; wrote {', '.join(written)} before failing"
        _emit(
            as_json=args.json,
            written=written,
            preserved=list(preserved),
            generated=list(generated),
            missing_targets=[],
            partial=classify_techdocs_baseline(repo_root),
            refusal=f"{exc}{detail}; a rerun writes only what is still absent",
        )
        return 2
    except (RuntimeError, OSError) as exc:
        # Defense in depth: the module normalizes every failure inside its write
        # loop into TechdocsWriteFailed, so this covers only something raised
        # outside it (template resolution, for instance). What this run wrote is
        # not knowable here, but the tree still is, and the MCP entry reports it,
        # so report the same thing rather than empty lists (delivery finding DEL-2).
        generated, preserved, _absent = techdocs_member_states(repo_root)
        _emit(
            as_json=args.json,
            written=[],
            preserved=list(preserved),
            generated=list(generated),
            missing_targets=[],
            partial=classify_techdocs_baseline(repo_root),
            refusal=str(exc),
        )
        return 2
    _emit(
        as_json=args.json,
        written=list(result.written_paths),
        preserved=list(result.preserved_paths),
        generated=list(result.generated_paths),
        missing_targets=list(result.missing_targets),
        partial=result.partial,
        refusal=None,
    )
    return 1 if result.missing_targets else 0


if __name__ == "__main__":
    raise SystemExit(main())
