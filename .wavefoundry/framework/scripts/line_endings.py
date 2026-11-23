"""Line-ending rule shared by every framework writer that edits a file in place.

Standard library only: ``upgrade_extensions.py`` loads this module from an
incoming pack through ``_incoming_framework_module``, so it must not import
any other framework module.

The rule:

* Existing lines keep their own ending, byte for byte.
* Inserted or replaced lines take the file's majority ending; a tie goes to
  CRLF; a file with no terminated line gives LF.

A writer reads the file once (``original``, endings intact), computes its
result on ``to_lf(original)``, and publishes ``encode(merge(original, new))``
through its own write primitive.  Fully generated files never pass through
``merge``: they are LF bytes on every platform.
"""

from __future__ import annotations

import difflib
from pathlib import Path

CRLF = "\r\n"
LF = "\n"


def to_lf(text: str) -> str:
    """Replace each CRLF pair with LF.  A lone ``\\r`` is content and is kept."""
    return text.replace(CRLF, LF)


def _split(text: str, *, crlf: bool = True) -> list[tuple[str, str]]:
    """Split ``text`` into ``(body, ending)`` pairs on LF.

    ``ending`` is ``"\\r\\n"``, ``"\\n"`` or ``""`` (the final unterminated
    line).  With ``crlf=False`` (LF text) every ``\\r`` stays in the body.
    """
    pairs: list[tuple[str, str]] = []
    start = 0
    length = len(text)
    while start < length:
        idx = text.find(LF, start)
        if idx < 0:
            pairs.append((text[start:], ""))
            break
        if crlf and idx > start and text[idx - 1] == "\r":
            pairs.append((text[start : idx - 1], CRLF))
        else:
            pairs.append((text[start:idx], LF))
        start = idx + 1
    return pairs


def majority(text: str) -> str:
    """Return the file's majority line ending; ties go to CRLF; none gives LF."""
    crlf = text.count(CRLF)
    lf = text.count(LF) - crlf
    if crlf and crlf >= lf:
        return CRLF
    return LF


def merge(original: str, new_lf: str) -> str:
    """Apply ``original``'s line endings to ``new_lf``.

    ``new_lf`` is the writer's result computed on ``to_lf(original)``.  Lines
    the alignment finds equal keep their original ending; inserted or replaced
    lines take ``majority(original)``.  An equal line that had no ending in
    the original but now has a following line takes the majority ending.
    """
    old_pairs = _split(original)
    old_bodies = [body for body, _ in old_pairs]
    new_pairs = _split(new_lf, crlf=False)
    new_bodies = [body for body, _ in new_pairs]
    default = majority(original)
    out: list[str] = []
    matcher = difflib.SequenceMatcher(None, old_bodies, new_bodies, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        for offset, j in enumerate(range(j1, j2)):
            body, new_ending = new_pairs[j]
            if not new_ending:
                out.append(body)
                continue
            ending = default
            if tag == "equal":
                old_ending = old_pairs[i1 + offset][1]
                if old_ending:
                    ending = old_ending
            out.append(body + ending)
    return "".join(out)


def encode(text: str) -> bytes:
    """Return UTF-8 bytes with no newline translation."""
    return text.encode("utf-8")


def read(path: Path) -> str:
    """Read ``path`` as UTF-8 with its line endings intact."""
    return Path(path).read_bytes().decode("utf-8")
