
"""Wavefoundry session-end capture hook. Capture/nudge only; never blocks."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


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
        out = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain"],
            capture_output=True, text=True, timeout=5,
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
