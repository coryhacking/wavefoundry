"""Profile-portable lifecycle prompt assertions (wave 2134s, change 2134q).

A distribution renames the tiers and the lifecycle prompts through
``vocabulary_profile`` and edits the lifecycle template bodies and rendered
prompts in its own tree. Tests that guard those surfaces derive names through
the profile and check named contract clauses, not our whole wording:

- a clause is written with ``{wave}``, ``{waves}``, ``{change}`` and
  ``{changes}`` placeholders for its tier nouns, ``{doc[<key>]}`` for a
  lifecycle prompt path and ``{shortcut[<key>]}`` for its shortcut phrase;
- against a seed (canonical shared source, never localized) the clause is
  filled with the shipped nouns and compared exactly;
- against a template or a rendered prompt it is filled with the active
  profile's nouns (``vocabulary_profile.tier_noun``) and compared
  case-insensitively.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import vocabulary_profile as vp  # noqa: E402

SHIPPED_NOUNS = {"wave": "wave", "waves": "waves", "change": "change", "changes": "changes"}


def profile_nouns() -> "dict[str, str]":
    """The placeholder values in the active profile's tier nouns."""
    return {
        "wave": vp.tier_noun("container"),
        "waves": vp.tier_noun("container", plural=True),
        "change": vp.tier_noun("item"),
        "changes": vp.tier_noun("item", plural=True),
    }


def tiered(clause: str, *, seed: bool = False) -> str:
    """``clause`` with its placeholders filled: shipped nouns and names for a
    seed, the active profile's otherwise."""
    if seed:
        return clause.format(
            **SHIPPED_NOUNS,
            doc={key: f"docs/prompts/{key}.prompt.md" for key in vp.DEFAULT_PROMPT_NAMES},
            shortcut={key: spec["shortcut"] for key, spec in vp.DEFAULT_PROMPT_NAMES.items()},
        )
    return clause.format(
        **profile_nouns(),
        doc={key: vp.prompt_doc(key) for key in vp.DEFAULT_PROMPT_NAMES},
        shortcut={key: vp.shortcut(key) for key in vp.DEFAULT_PROMPT_NAMES},
    )


def has_clause(clause: str, text: str, *, seed: bool = False) -> bool:
    """Whether ``text`` carries ``clause``: exact in the shipped wording for a
    seed; otherwise case-insensitive in the profile's nouns and names, or in
    the shipped ones. A distribution may reword its templates and rendered
    prompts in its own nouns or keep the shipped wording; either way a clause
    that is missing fails."""
    if seed:
        return tiered(clause, seed=True) in text
    folded = text.casefold()
    return tiered(clause).casefold() in folded or tiered(clause, seed=True).casefold() in folded


def assert_clause(test: unittest.TestCase, clause: str, text: str, *, seed: bool = False) -> None:
    """Fail ``test`` unless ``text`` carries ``clause`` (see ``has_clause``)."""
    if not has_clause(clause, text, seed=seed):
        test.fail(f"contract clause {tiered(clause, seed=seed)!r} not found"
                  f"{'' if seed else ' (case-insensitive)'}")


def shipped_prompt_vocabulary() -> bool:
    """True when the active profile keeps the shipped tier nouns and prompt
    names. Only then is a template or rendered prompt expected to repeat seed
    wording byte for byte: a distribution edits its own template bodies."""
    return profile_nouns() == SHIPPED_NOUNS and all(
        vp.prompt_slug(key) == default["slug"] and vp.shortcut(key) == default["shortcut"]
        and vp.shortcut_aliases(key) == tuple(default["aliases"])
        for key, default in vp.DEFAULT_PROMPT_NAMES.items()
    )


def shipped_prompt_doc(path: str) -> str:
    """The shipped-default path of a profile prompt path (identity for any
    other path), for closed records written before a rename."""
    for key in vp.DEFAULT_PROMPT_NAMES:
        if path == vp.prompt_doc(key):
            return f"docs/prompts/{key}.prompt.md"
        if path == vp.agent_prompt_doc(key):
            return f"docs/prompts/agents/{key}.prompt.md"
    return path


def renames_prompts() -> bool:
    """True when the active profile renames any lifecycle prompt."""
    return any(vp.prompt_slug(key) != default["slug"] for key, default in vp.DEFAULT_PROMPT_NAMES.items())


def prime_profile_render(root: Path) -> None:
    """Under a profile that renames lifecycle prompts, write the prompt-surface
    manifest before a fresh render, as a fresh install does: without that
    record the renderer skips the renamed prompt paths (wave 200xy, change
    200xx). A no-op under the shipped names, so default fixtures are unchanged."""
    if renames_prompts():
        import docs_gardener

        docs_gardener.ensure_manifest(Path(root))


_SHIPPED_PROMPT_PATH_RE = None


def profile_paths(text: str) -> str:
    """``text`` with each shipped lifecycle prompt path
    (``docs/prompts/[agents/]<key>.prompt.md``) replaced by the profile's path;
    template asset paths (``.../lifecycle-prompts/<key>.prompt.md``) and seed
    filenames are kept. The identity under the shipped names."""
    import re

    global _SHIPPED_PROMPT_PATH_RE
    if _SHIPPED_PROMPT_PATH_RE is None:
        keys = "|".join(sorted(map(re.escape, vp.DEFAULT_PROMPT_NAMES), key=len, reverse=True))
        _SHIPPED_PROMPT_PATH_RE = re.compile(rf"docs/prompts/(agents/)?({keys})\.prompt\.md")
    return _SHIPPED_PROMPT_PATH_RE.sub(
        lambda m: vp.agent_prompt_doc(m.group(2)) if m.group(1) else vp.prompt_doc(m.group(2)), text)
