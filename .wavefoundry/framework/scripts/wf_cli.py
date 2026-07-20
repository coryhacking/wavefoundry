#!/usr/bin/env python3
"""``wf`` — the single cross-OS Wavefoundry operator CLI dispatcher (wave 1p7tz).

Replaces the nine POSIX-only ``.wavefoundry/bin/*`` bash wrappers with one self-bootstrapping
argparse dispatcher exposed through a thin ``wf`` (bash) + ``wf.cmd`` (Windows) shim pair. Each
subcommand routes to an existing entry script, forwarding the remaining ``argv`` through to that
target's own argument parsing — ``wf_cli`` only dispatches, it re-homes no logic.

Three-tier bootstrap (1p7pb-adr / 1p802): every subcommand activates the shared tool venv in-process
first — **except** ``setup``, which must stay on the system interpreter pre-symlink so a fresh
bootstrap is never blocked (``setup_wavefoundry`` owns venv + ``python`` symlink creation; its own
import-time ``activate_tool_venv`` no-ops when the venv does not exist yet).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import venv_bootstrap  # the single venv resolver (wave 1p7pl)
import cli_stdio  # shared UTF-8 stdio reconfigure (wave 1p8gv)

# Wave 1p8gv: the dispatcher is a CLI entry — reconfigure stdout/stderr to UTF-8 so non-ASCII output
# from any in-process-dispatched subcommand never raises on a cp1252 Windows console.
cli_stdio.configure_utf8_stdio()


# Subcommand -> (target module, target script basename for sys.argv[0], optional fixed prefix args).
# The script basename keeps the target's own ``parse_args`` / ``--help`` / prog name accurate, and the
# fixed prefix supplies the args the retired bash wrapper used to hardcode (e.g. update-indexes).
# ``setup`` is intentionally NOT in this map's bootstrap loop — see _SETUP_SUBCOMMAND below.
_SUBCOMMANDS: dict[str, dict] = {
    "docs-lint": {"module": "docs_lint", "script": "docs_lint.py"},
    "docs-gardener": {"module": "docs_gardener", "script": "docs_gardener.py"},
    "gate": {"module": "wave_gate", "script": "wave_gate.py"},
    "dashboard": {
        "module": "dashboard_server",
        "script": "dashboard_server.py",
        # The retired ``wave-dashboard`` wrapper self-detached + opened the browser; keep that default.
        "prefix": ["--daemon", "--open"],
    },
    "update-indexes": {
        "module": "setup_index",
        "script": "setup_index.py",
        # The retired ``update-indexes`` wrapper ran the incremental docs/code refresh.
        "prefix": ["--background-code", "--verbose"],
    },
    "lifecycle-id": {"module": "lifecycle_id", "script": "lifecycle_id.py"},
    "upgrade": {"module": "upgrade_wavefoundry", "script": "upgrade_wavefoundry.py"},
    "setup": {"module": "setup_wavefoundry", "script": "setup_wavefoundry.py"},
    "codebase-map": {"module": "gen_codebase_map", "script": "gen_codebase_map.py"},
    "render-surfaces": {"module": "render_platform_surfaces", "script": "render_platform_surfaces.py"},
    "secrets-scan": {"module": "run_secrets_scan", "script": "run_secrets_scan.py"},
    "gpu-doctor": {"module": "gpu_doctor", "script": "gpu_doctor.py"},
    "memory-backfill": {
        "module": "memory_cli",
        "script": "memory_cli.py",
        "prefix": ["backfill"],
    },
    "memory-validate": {
        "module": "memory_cli",
        "script": "memory_cli.py",
        "prefix": ["validate"],
    },
    # NOTE: `prune_framework.py` is intentionally NOT a wf subcommand. It is a manual,
    # source-host/upgrade-cleanup fallback run directly (it needs the pre-upgrade MANIFEST,
    # which only the operator running the upgrade has); routing it through `wf` added no value
    # and its `main() -> None` made the dispatcher's int() coercion crash. Run it directly:
    #   python3 .wavefoundry/framework/scripts/prune_framework.py --old-manifest <path>
}

# ``setup`` must NOT trigger the dispatcher's up-front venv activation: it runs on a fresh box BEFORE
# the ``python`` symlink / venv exists, so it stays on the system interpreter (``setup_wavefoundry``
# owns venv creation, and its import-time ``activate_tool_venv`` no-ops pre-venv). Every other
# subcommand activates the venv in-process first.
_SETUP_SUBCOMMAND = "setup"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wf",
        description="Wavefoundry operator CLI — cross-OS dispatcher to the framework entry scripts. "
        "Each subcommand forwards its remaining arguments to the target's own CLI. Prefer the "
        "Wavefoundry MCP tools when an MCP host is attached; `wf` is the no-MCP terminal/CI fallback.",
    )
    sub = parser.add_subparsers(dest="subcommand", metavar="<subcommand>")
    descriptions = {
        "docs-lint": "Run the docs lint gate (docs_lint.py).",
        "docs-gardener": "Run the docs metadata gardener (docs_gardener.py).",
        "gate": "Open/close/inspect framework edit gates (wave_gate.py: open|close|status).",
        "dashboard": "Start the local repository dashboard, self-detached (dashboard_server.py --daemon).",
        "update-indexes": "Run the incremental docs/code index refresh (setup_index.py).",
        "lifecycle-id": "Mint lifecycle prefixes for waves/changes (lifecycle_id.py).",
        "upgrade": "Upgrade the Wavefoundry framework in this repo (upgrade_wavefoundry.py).",
        "setup": "Bootstrap the harness: venv + deps + indexes + configs (setup_wavefoundry.py).",
        "codebase-map": "Generate the codebase map orientation doc (gen_codebase_map.py).",
        "render-surfaces": "Regenerate host configs, hooks, bin shims, and agent surfaces (render_platform_surfaces.py).",
        "secrets-scan": "Run the secrets scanner fallback CLI (run_secrets_scan.py).",
        "gpu-doctor": "Embedding-provider / GPU capability diagnostic — same report as wave_gpu_doctor (gpu_doctor.py).",
        "memory-backfill": "Inventory historical waves and draft one bounded memory batch.",
        "memory-validate": "Record focused agent judgment for one historical candidate.",
    }
    for name in _SUBCOMMANDS:
        sub.add_parser(
            name,
            help=descriptions.get(name, ""),
            add_help=False,  # the target owns --help; we pass argv straight through
        )
    return parser


def _dispatch(subcommand: str, rest: list[str]) -> int:
    """Route ``subcommand`` to its target module's ``main()``, forwarding ``rest`` as the target argv.

    Sets ``sys.argv`` to the target's own argv (script basename + forwarded args) so targets that read
    ``sys.argv`` directly (e.g. docs_lint via wave_lint_lib.cli) parse correctly, and also passes the
    forwarded argv explicitly to ``main(argv=...)`` for targets whose ``main`` accepts it.
    """
    spec = _SUBCOMMANDS[subcommand]
    prefix = [] if subcommand == "dashboard" and rest else spec.get("prefix", [])
    forwarded = [*prefix, *rest]

    import importlib

    module = importlib.import_module(spec["module"])

    # Make the target see its own argv (covers sys.argv-reading targets like docs_lint).
    sys.argv = [spec["script"], *forwarded]

    main = getattr(module, "main", None)
    if main is None:
        # No callable main() (a pure __main__ script) — re-exec the script as a subprocess so its
        # `if __name__ == "__main__"` block runs with the forwarded argv on the current interpreter.
        import subprocess_util  # shared subprocess isolation (wave 1p8gu)

        target = _SCRIPTS_DIR / spec["script"]
        result = subprocess_util.isolated_run([sys.executable, str(target), *forwarded], check=False)
        return result.returncode

    # Targets whose main() accepts an argv parameter: pass it explicitly. Targets whose main() takes
    # no args (e.g. docs_lint -> wave_lint_lib.cli.main) read the sys.argv we set above. Decide by the
    # signature, NOT by catching TypeError (which would swallow a real TypeError from main's body).
    import inspect

    accepts_argv = False
    try:
        sig = inspect.signature(main)
        accepts_argv = len(sig.parameters) >= 1
    except (TypeError, ValueError):
        accepts_argv = False
    # A target's main() may return an int exit code or None (a convention for "exit 0").
    # Coerce None -> 0 so a None-returning main() can never crash the dispatcher on int(None).
    rc = main(forwarded) if accepts_argv else main()
    return 0 if rc is None else int(rc)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    parser = _build_parser()

    # Parse ONLY the subcommand; everything after it is forwarded verbatim to the target.
    if not args or args[0] in ("-h", "--help"):
        parser.print_help()
        return 0
    subcommand = args[0]
    if subcommand not in _SUBCOMMANDS:
        parser.error(f"unknown subcommand: {subcommand!r} (choose from {', '.join(_SUBCOMMANDS)})")
    rest = args[1:]

    # Three-tier bootstrap: activate the tool venv in-process up-front for every subcommand EXCEPT
    # setup (which must stay on the system interpreter pre-symlink — see _SETUP_SUBCOMMAND).
    if subcommand != _SETUP_SUBCOMMAND:
        venv_bootstrap.activate_tool_venv()

    return _dispatch(subcommand, rest)


if __name__ == "__main__":
    raise SystemExit(main())
