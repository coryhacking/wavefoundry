#!/usr/bin/env python3
"""Canonical gate launcher implementation — .wavefoundry/framework/scripts/wave_gate.py

Manages the ``seed_edit_allowed`` and ``framework_edit_allowed`` guards in
``<repo-root>/.wavefoundry/guard-overrides.json``. Invoked via the cross-OS
``wf gate`` operator CLI (``.wavefoundry/bin/wf gate …``, dispatched by
``wf_cli.py``) and usable standalone with ``python3 -m`` or direct invocation.

Repo root resolves from this script's location by default (three levels up,
i.e. ``parents[3]``). Pass ``--root <path>`` to override — useful when
invoking outside the framework's directory layout (e.g. in tests).

Usage:
    wf gate open <gate-name>     Enable a guard (error if already open)
    wf gate close <gate-name>    Disable a guard (advisory if already closed)
    wf gate status               Show the current state of all gates
    wf gate --root <path> ...    Override the repo-root resolution

Valid gate names: seed_edit_allowed, framework_edit_allowed
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import venv_bootstrap  # the single venv resolver (wave 1p7pl)

# Re-exec into the shared tool venv before any heavy work (wave 1p7pl). No-op when
# already in the venv or when it does not exist yet (fresh bootstrap).
venv_bootstrap.reexec_into_tool_venv()

VALID_GATES = {"seed_edit_allowed", "framework_edit_allowed"}


def _default_repo_root() -> Path:
    """Repo root by walking up from this script's location.

    Layout: ``<repo-root>/.wavefoundry/framework/scripts/wave_gate.py`` →
    ``parents[3]`` is the repo root.
    """
    return Path(__file__).resolve().parents[3]


def _overrides_path(repo_root: Path) -> Path:
    return repo_root / ".wavefoundry" / "guard-overrides.json"


def _read(repo_root: Path) -> dict:
    path = _overrides_path(repo_root)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"error: could not read {path}: {exc}", file=sys.stderr)
        sys.exit(1)


def _write(repo_root: Path, data: dict) -> None:
    path = _overrides_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _status(data: dict) -> None:
    for gate in sorted(VALID_GATES):
        state = "open" if data.get(gate, {}).get("enabled", False) else "closed"
        print(f"  {gate}: {state}")


def cmd_open(repo_root: Path, gate: str) -> int:
    if gate not in VALID_GATES:
        print(f"error: unknown gate '{gate}'. Valid: {', '.join(sorted(VALID_GATES))}", file=sys.stderr)
        return 1
    data = _read(repo_root)
    if data.get(gate, {}).get("enabled", False):
        print(f"error: gate '{gate}' is already open. Close it first with: gate close {gate}", file=sys.stderr)
        return 1
    data.setdefault(gate, {})["enabled"] = True
    _write(repo_root, data)
    print(f"ok: gate '{gate}' opened.")
    _status(data)
    return 0


def cmd_close(repo_root: Path, gate: str) -> int:
    if gate not in VALID_GATES:
        print(f"error: unknown gate '{gate}'. Valid: {', '.join(sorted(VALID_GATES))}", file=sys.stderr)
        return 1
    data = _read(repo_root)
    already_closed = not data.get(gate, {}).get("enabled", False)
    data.setdefault(gate, {})["enabled"] = False
    _write(repo_root, data)
    if already_closed:
        print(f"advisory: gate '{gate}' was already closed — no change made.")
    else:
        print(f"ok: gate '{gate}' closed.")
    _status(data)
    return 0


def cmd_status(repo_root: Path) -> int:
    data = _read(repo_root)
    print("Gate states:")
    _status(data)
    return 0


def _parse_root(argv: list[str]) -> tuple[Path, list[str]]:
    """Extract optional ``--root <path>`` and return (repo_root, remaining argv)."""
    if "--root" in argv:
        i = argv.index("--root")
        if i + 1 >= len(argv):
            print("error: --root requires a path argument", file=sys.stderr)
            sys.exit(1)
        return Path(argv[i + 1]).resolve(), argv[:i] + argv[i + 2:]
    return _default_repo_root(), argv


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    repo_root, args = _parse_root(args)
    if not args:
        print(__doc__)
        return 0
    cmd = args[0]
    if cmd == "status":
        return cmd_status(repo_root)
    if cmd in ("open", "close") and len(args) == 2:
        return cmd_open(repo_root, args[1]) if cmd == "open" else cmd_close(repo_root, args[1])
    print(f"usage: wave-gate open|close <gate-name>  or  wave-gate status", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
