"""Container fixture arguments: the extra served-tool arguments test fixtures pass (wave 22r99).

Fork-editable, like ``vocabulary_profile.py``: a downstream distribution whose
served ``wf_create_wave`` or ``wf_close_wave`` requires more arguments than
Wavefoundry's edits only this module at merge time. Upstream never changes it
beyond its defaults, which add nothing.

``container_fixture_args`` runs at each fixture call, so a distribution may
also create, in the fixture repository at ``root``, anything its arguments
name (for example a parent record) before returning them. The helpers in
``server_tools_support`` merge the returned arguments into the served call and
raise when a key collides with one the test passes itself.

Test-only: production code never imports this module.
"""
from __future__ import annotations

from pathlib import Path


def container_fixture_args(tool_name: str, root: Path) -> dict:
    """Return extra keyword arguments for ``tool_name`` ("wf_create_wave" or "wf_close_wave")."""
    return {}
