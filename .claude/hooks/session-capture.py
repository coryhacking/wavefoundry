#!/usr/bin/env python3
from __future__ import annotations

import sys as _wf_sys
from pathlib import Path as _WfPath

_WF_SCRIPTS = _WfPath(__file__).resolve().parents[2] / ".wavefoundry" / "framework" / "scripts"
if _WF_SCRIPTS.is_dir() and str(_WF_SCRIPTS) not in _wf_sys.path:
    _wf_sys.path.insert(0, str(_WF_SCRIPTS))
try:
    import venv_bootstrap as _wf_venv_bootstrap

    _wf_venv_bootstrap.activate_tool_venv()
except Exception:
    pass
try:
    import cli_stdio as _wf_cli_stdio

    _wf_cli_stdio.configure_utf8_stdio()
except Exception:
    pass

import os
import subprocess
import sys
from pathlib import Path

# Wave 1p8gu: shared subprocess isolation (HOOK_BOOTSTRAP already put the scripts dir on
# sys.path); guarded so the session-capture hook still loads against a transient tree.
try:
    import subprocess_util as _wf_subprocess_util
except Exception:
    _wf_subprocess_util = None


def _find_repo_root(start: Path) -> Path | None:
    cur = start.resolve()
    for cand in [cur, *cur.parents]:
        if (cand / "docs" / "waves").is_dir() or (cand / ".wavefoundry").is_dir():
            return cand
    return None


def _active_wave(root: Path):
    waves = root / "docs" / "waves"
    if not waves.is_dir():
        return None
    for wave_dir in sorted(waves.iterdir()):
        wave_md = wave_dir / "wave.md"
        if not wave_md.is_file():
            continue
        try:
            text = wave_md.read_text(encoding="utf-8")
        except Exception:
            continue
        status = ""
        wave_id = wave_dir.name
        for line in text.splitlines():
            s = line.strip()
            if s.lower().startswith("status:"):
                status = s.split(":", 1)[1].strip().lower()
            elif s.startswith("wave-id:"):
                wave_id = s.split(":", 1)[1].strip().strip("`")
        if status in ("active", "implementing"):
            return (wave_id, wave_dir)
    return None


def _ac_progress(wave_dir: Path):
    done = total = 0
    for md in sorted(wave_dir.glob("*.md")):
        if md.name == "wave.md":
            continue
        try:
            for line in md.read_text(encoding="utf-8").splitlines():
                st = line.strip()
                if st.startswith("- [ ] AC") or st.startswith("- [] AC"):
                    total += 1
                elif st.startswith("- [x] AC") or st.startswith("- [X] AC"):
                    total += 1
                    done += 1
        except Exception:
            continue
    return done, total


def _git_dirty_count(root: Path) -> int | None:
    try:
        if _wf_subprocess_util is not None:
            out = _wf_subprocess_util.isolated_run(
                ["git", "-C", str(root), "status", "--porcelain"],
                capture_output=True, text=True, timeout=5,
            )
        else:
            out = subprocess.run(
                ["git", "-C", str(root), "status", "--porcelain"],
                capture_output=True, text=True, timeout=5,
                stdin=subprocess.DEVNULL,
                creationflags=(getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0),
            )
        if out.returncode != 0:
            return None
        return len([ln for ln in out.stdout.splitlines() if ln.strip()])
    except Exception:
        return None


def _handoff_stale(root: Path, wave_dir: Path | None) -> bool | None:
    handoff = root / "docs" / "agents" / "session-handoff.md"
    if not handoff.is_file() or wave_dir is None:
        return None
    try:
        hf = handoff.stat().st_mtime
        newest = max(
            (p.stat().st_mtime for p in wave_dir.glob("*.md")), default=0.0
        )
        return newest > hf
    except Exception:
        return None


def _flush_reindex_if_pending(root: Path) -> None:
    # Wave 1p9am: turn-end coalesced reindex. The post-edit hook now MARKS a reindex-pending
    # sentinel per edit instead of spawning a reindex; this Stop hook flushes it ONCE per turn.
    # If an index-worthy edit is pending and no build is live, consume the marker and spawn one
    # detached incremental reindex. Fully fail-safe — never blocks or fails session end.
    try:
        import importlib.util
        index_dir = root / ".wavefoundry" / "index"
        indexer_path = root / ".wavefoundry" / "framework" / "scripts" / "indexer.py"
        if not indexer_path.exists():
            return
        spec = importlib.util.spec_from_file_location("wavefoundry_indexer_stop", indexer_path)
        if spec is None or spec.loader is None:
            return
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        held, _pid = mod._index_build_lock_held(index_dir)
        if held:
            return  # a build is running; leave the marker for the next opportunity
        if not mod.consume_reindex_pending(index_dir):
            return  # nothing pending this turn
        try:
            mod.record_hook_reindex_spawn(index_dir)
        except Exception:
            pass
        # Console-free spawn: prefer pythonw.exe on Windows (detached all-DEVNULL flasher).
        py = sys.executable
        if os.name == "nt":
            cand = Path(sys.executable).with_name("pythonw.exe")
            if cand.exists():
                py = str(cand)
        _detach = {}
        if os.name == "nt":
            _detach["creationflags"] = (
                subprocess.DETACHED_PROCESS
                | subprocess.CREATE_NEW_PROCESS_GROUP
                | getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
        else:
            _detach["start_new_session"] = True
        subprocess.Popen(
            [py, str(indexer_path), "--root", str(root), "--content", "all"],  # 1sek8: all-content flush
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(root),
            close_fds=os.name != "nt",
            **_detach,
        )
    except Exception:
        pass


def main() -> int:
    try:
        # Drain stdin so the host never blocks on the pipe; payload unused.
        try:
            sys.stdin.read()
        except Exception:
            pass
        root = _find_repo_root(Path(os.getcwd()))
        if root is None:
            return 0
        # Wave 1p9am: flush the turn's coalesced reindex before capture (fail-safe, non-blocking).
        _flush_reindex_if_pending(root)
        wave = _active_wave(root)
        lines = ["# Session capture", ""]
        if wave:
            wave_id, wave_dir = wave
            done, total = _ac_progress(wave_dir)
            lines.append(f"- Open wave: {wave_id}")
            if total:
                lines.append(f"- AC progress: {done}/{total} checked")
            stale = _handoff_stale(root, wave_dir)
            if stale is True:
                lines.append("- Session handoff looks STALE vs the wave — update it before stopping.")
        else:
            lines.append("- No active wave.")
        dirty = _git_dirty_count(root)
        if dirty:
            lines.append(f"- Uncommitted changes: {dirty} path(s).")
        lines.append("")
        lines.append("Learnings: record any new build/test quirk or decision discovered this")
        lines.append("session as a memory candidate (confirm before writing — never auto-saved).")
        lines.append("")
        try:
            cache_dir = root / ".wavefoundry" / "logs"
            cache_dir.mkdir(parents=True, exist_ok=True)
            (cache_dir / "last-session-capture.md").write_text(
                "\n".join(lines) + "\n", encoding="utf-8"
            )
        except Exception:
            pass
        summary = wave[0] if wave else "no active wave"
        print(f"[wavefoundry] session capture saved ({summary}); review learnings before next session.")
        return 0
    except Exception:
        # Never let a capture error block the session from ending.
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
