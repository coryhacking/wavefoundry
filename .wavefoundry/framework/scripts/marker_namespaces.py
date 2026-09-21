"""Author-facing marker namespaces; edit MARKER_NAMESPACES once at merge time.

This module depends only on the standard library so every marker consumer can
share its patterns without importing framework runtime state.
"""
import re

MARKER_NAMESPACES: tuple[str, ...] = ("wave", "waveframework", "wavefoundry", "waveforge")


def compile_marker_patterns(namespaces: tuple[str, ...]) -> tuple[re.Pattern[str], re.Pattern[str], str]:
    """Build begin/name and named-or-bare end patterns for the supplied names."""
    alternation = "(?:" + "|".join(re.escape(name) for name in namespaces) + ")"
    begin = re.compile(r"<!--\s*" + alternation + r":([\w:-]+)\s+begin\b")
    end = re.compile(r"<!--\s*(?:" + alternation + r":([\w:-]+)\s+)?end\s*-->")
    return begin, end, alternation


MARKER_BEGIN_RE, MARKER_END_RE, MARKER_NAMESPACE_ALTERNATION = compile_marker_patterns(MARKER_NAMESPACES)
