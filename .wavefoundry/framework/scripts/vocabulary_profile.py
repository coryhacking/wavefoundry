"""Record vocabulary: what the two lifecycle tiers are called in their records (wave 1z8mm).

A downstream fork edits the constants below at merge time, the same way it
edits the record roots in ``record_paths``. Nothing is read from
configuration. Every production reader and writer of a record marker takes the
marker from here, so a fork with a different vocabulary (for example a
container record ``set.md`` holding a ``## Waves`` member list) runs
unmodified.

A token is vocabulary when its text embeds a tier name or is the container
record filename; everything else in a record is fixed (``events.jsonl``,
``## Progress Log``, ``Status:``, the ``<!-- wave:* -->`` marker fences and so
on). The defaults are today's names, so an unedited profile changes nothing.

The profile also owns the change-kind token of a change id (wave 1zimf): the
fixed ``CORE_CHANGE_KINDS`` plus a distribution's ``EXTRA_CHANGE_KINDS``, so
lint, the server and the lifecycle-id CLI take their kinds from here. It also
names the kinds no creation path mints any more, ``RETIRED_CHANGE_KINDS``
(wave 1zli8), which stay in the grammar so existing ids keep linting.

The module exports strings and regex-escaped fragments, not whole patterns:
each consuming site keeps its own grammar (anchoring, backticks, case, legacy
aliases) around the fragment.

Which labels and headings a profile may use, and how readers must match them,
is stated once in ``docs/architecture/layering-rules.md`` (vocabulary profile
paragraph); ``validation_errors`` enforces the profile half of it.

Stdlib-only and import-cheap; validated at import, failing closed.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Fork-editable constants
# ---------------------------------------------------------------------------

# Tier names, singular and plural.
CONTAINER_NAME = "Wave"
CONTAINER_NAME_PLURAL = "Waves"
ITEM_NAME = "Change"
ITEM_NAME_PLURAL = "Changes"

# Container record.
RECORD_FILENAME = "wave.md"
ID_KEY = "wave-id"  # written as ``wave-id: `<id>` ``
RECORD_TITLE = "# Wave Record"
SUMMARY_HEADING = "## Wave Summary"

# Work items, as listed in the container record and headed in their own docs.
MEMBER_HEADING = "## Changes"
MEMBER_ID_LABEL = "Change ID"
MEMBER_STATUS_LABEL = "Change Status"

# The label a work-item document (and a plan overview) uses to name its container.
BACKREF_LABEL = "Wave"

# The vocabulary of records under ``record_paths.ARCHIVE_ROOT`` (wave 1z8ts):
# ``None`` reads the archive with the constants above; otherwise a mapping of
# exactly the twelve field names above (``FIELD_NAMES``) to the names the
# archived records were written with. Validated at import like the live ones.
ARCHIVE_PROFILE: "dict[str, str] | None" = None

# Change kinds a distribution adds to the core kinds below (wave 1zimf), each
# lowercase ASCII letters and digits, 2 to 16 characters, starting with a
# letter. They apply to live and archived records alike. Kinds are additive:
# removing one that existing records use makes those records fail lint by name.
EXTRA_CHANGE_KINDS: tuple[str, ...] = ()

# Names of the tier-named lifecycle prompts (wave 1zyb4, change 1zxnw): a
# mapping of a ``DEFAULT_PROMPT_NAMES`` key to ``{"slug": ..., "shortcut":
# ..., "aliases": [...]}`` (aliases optional, default none). A key left out
# keeps its default name. The renderer moves already-rendered prompts and
# records the names it applied in the prompt-surface manifest.
PROMPT_NAME_OVERRIDES: "dict[str, dict[str, object]]" = {}

# ---------------------------------------------------------------------------
# Derived forms (not edited)
# ---------------------------------------------------------------------------

PREVIOUS_STATUS_LABEL = f"Previous {MEMBER_STATUS_LABEL}"

# The change-kind token of a change id (``<prefix>-<kind> <slug>``), wave
# 1zimf. The core kinds are fixed, not edited by a distribution; the one source
# of kinds for lint, the server and the lifecycle-id CLI is CHANGE_KINDS.
CORE_CHANGE_KINDS = ("bug", "feat", "enh", "change", "doc", "debt", "ref", "task", "maint", "ops")
# Tokens that already name other lifecycle ids, so never a change kind: the
# lifecycle-id CLI's wave kind, memory ids, scanner finding ids, decision records,
# and the migrated journal files the upgrade writes into wave folders.
RESERVED_KIND_TOKENS = frozenset({"wave", "mem", "sec", "adr", "jrnl"})
_EXTRA_CHANGE_KIND_RE = re.compile(r"[a-z][a-z0-9]{1,15}")
# Derived only from a valid tuple; an invalid declaration is reported by
# validate() below, at import, rather than raised here.
CHANGE_KINDS = CORE_CHANGE_KINDS + (
    tuple(EXTRA_CHANGE_KINDS) if isinstance(EXTRA_CHANGE_KINDS, tuple)
    and all(isinstance(kind, str) for kind in EXTRA_CHANGE_KINDS) else ()
)
CHANGE_KIND_RE = "(?:" + "|".join(re.escape(kind) for kind in CHANGE_KINDS) + ")"
# Kinds no creation path mints any more (wave 1zli8). They stay in
# CHANGE_KINDS, so existing ids keep linting; the MCP tools, the extension
# helper and the lifecycle-id CLI refuse them with ``retired_kind_message``.
# Fixed, not a profile constant: EXTRA_CHANGE_KINDS cannot re-enable one.
RETIRED_CHANGE_KINDS: tuple[str, ...] = ("feat",)
MINTABLE_CHANGE_KINDS = tuple(kind for kind in CHANGE_KINDS if kind not in RETIRED_CHANGE_KINDS)


def retired_kind_message(kind: str) -> str:
    """The one refusal sentence for a retired change kind, on every surface."""
    return (
        f"Change kind {kind!r} is retired for new change docs; existing {kind!r} ids stay valid. "
        "Plan the work as one or more enhancement changes with kind 'enh' (wf_new_enhancement)."
    )


# The tier-named lifecycle prompts (wave 1zyb4, change 1zxnw). Fixed, not
# edited: a distribution renames one through PROMPT_NAME_OVERRIDES above. Each
# key is the prompt's default slug; its public prompt is
# ``docs/prompts/<slug>.prompt.md``, its agent body
# ``docs/prompts/agents/<slug>.prompt.md`` and its skill (where the framework
# registers one) ``wf-<slug>``.
DEFAULT_PROMPT_NAMES: "dict[str, dict[str, object]]" = {
    "plan-change": {"slug": "plan-change", "shortcut": "Plan change", "aliases": ()},
    "create-wave": {"slug": "create-wave", "shortcut": "Create wave", "aliases": ()},
    "add-change-to-wave": {"slug": "add-change-to-wave", "shortcut": "Add change to wave", "aliases": ()},
    "remove-change-from-wave": {
        "slug": "remove-change-from-wave", "shortcut": "Remove change from wave", "aliases": (),
    },
    "prepare-wave": {"slug": "prepare-wave", "shortcut": "Prepare wave", "aliases": ("Ready wave",)},
    "implement-wave": {"slug": "implement-wave", "shortcut": "Implement wave", "aliases": ()},
    "implement-change": {"slug": "implement-change", "shortcut": "Implement change", "aliases": ()},
    "pause-wave": {"slug": "pause-wave", "shortcut": "Pause wave", "aliases": ()},
    "review-wave": {"slug": "review-wave", "shortcut": "Review wave", "aliases": ()},
    "close-wave": {"slug": "close-wave", "shortcut": "Close wave", "aliases": ()},
    "close-change": {"slug": "close-change", "shortcut": "Close change", "aliases": ()},
}
# Framework prompt slugs a renamed prompt may not take: the untiered and
# product-named prompts, the agent bodies without a public twin, the retired
# names and the prompt index.
FIXED_PROMPT_SLUGS: tuple[str, ...] = (
    "review-plan", "memory-review", "council-review", "archetype-council", "red-team-review",
    "evaluate-decision", "refresh-techdocs", "codebase-cleanup-review", "package-wavefoundry",
    "install-wavefoundry", "upgrade-wavefoundry", "framework-config-review",
    "agent-routing-concurrency", "start-dashboard", "stop-dashboard", "restart-dashboard",
    "init-wave-context", "upgrade-wave-context", "performance-reviewer", "security-reviewer",
    "interrogate-plan", "plan-feature", "implement-feature", "finalize-feature", "index",
)
# The renderer's skills that no mapped prompt names (a copy: this module cannot
# import the renderer; a test pins it to the registry), and the retired skill
# folder names the renderer removes on every render.
FIXED_SKILL_NAMES: tuple[str, ...] = (
    "wf-review-plan", "wf-evaluate-decision", "wf-memory-review", "wf-council", "wf-guru",
    "wf-upgrade", "wf-package", "wf-code-cleanup", "wf-techdocs",
)
FIXED_STALE_SKILL_NAMES: tuple[str, ...] = ("auto-guru", "wf-interrogate-plan", "wf-plan-feature")
# The framework's untiered public shortcuts (a test pins them to the manifest).
FIXED_PROMPT_SHORTCUTS: tuple[str, ...] = (
    "Init Wavefoundry", "Start dashboard", "Stop dashboard", "Restart dashboard",
    "Upgrade Wavefoundry", "Package Wavefoundry", "Review memories", "Review plan",
    "Red-team review", "Refresh TechDocs",
)
_PROMPT_SLUG_RE = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*")
_PROMPT_NAME_MAX = 64
_SHORTCUT_FORBIDDEN = ("`", "*", "|", "[", "]")
_PROMPT_SPEC_FIELDS = ("slug", "shortcut", "aliases")


def _prompt_spec(default: "dict[str, object]", spec: object) -> "dict[str, object]":
    """One derived entry: ``spec`` when it is usable, else ``default`` (an
    unusable override is reported by ``prompt_name_errors`` at import)."""
    if not isinstance(spec, dict):
        return dict(default)
    aliases = spec.get("aliases", ())
    if not isinstance(aliases, (list, tuple)):
        aliases = ()
    return {
        "slug": spec.get("slug", default["slug"]),
        "shortcut": spec.get("shortcut", default["shortcut"]),
        "aliases": tuple(aliases),
    }


def derive_prompt_names(overrides: object = None) -> "dict[str, dict[str, object]]":
    """``DEFAULT_PROMPT_NAMES`` overlaid with ``overrides`` (default: the live
    ``PROMPT_NAME_OVERRIDES``); unknown keys are ignored here and reported by
    ``prompt_name_errors``."""
    overrides = PROMPT_NAME_OVERRIDES if overrides is None else overrides
    names = {key: dict(default) for key, default in DEFAULT_PROMPT_NAMES.items()}
    if isinstance(overrides, dict):
        for key, spec in overrides.items():
            if key in names:
                names[key] = _prompt_spec(DEFAULT_PROMPT_NAMES[key], spec)
    return names


def _shortcut_problem(value: object) -> "str | None":
    if not isinstance(value, str):
        return "must be a string"
    if not value or value != value.strip() or "\n" in value or "\r" in value:
        return "must be a non-empty single line without surrounding spaces"
    if len(value) > _PROMPT_NAME_MAX:
        return f"must be at most {_PROMPT_NAME_MAX} characters"
    if any(char in value for char in _SHORTCUT_FORBIDDEN):
        return "must not contain `, *, |, [ or ]"
    return None


def prompt_name_errors(overrides: object = None) -> list[str]:
    """Every problem with ``PROMPT_NAME_OVERRIDES`` (default: the live
    constant); empty when valid. Each message names the constant and the key."""
    overrides = PROMPT_NAME_OVERRIDES if overrides is None else overrides
    label = "PROMPT_NAME_OVERRIDES"
    if not isinstance(overrides, dict):
        return [f"{label} must be a dict of prompt key to name, not {type(overrides).__name__}"]
    errors: list[str] = []
    for key, spec in overrides.items():
        if key not in DEFAULT_PROMPT_NAMES:
            errors.append(f"{label} key {key!r} is not a tier-named lifecycle prompt "
                          f"(known: {', '.join(DEFAULT_PROMPT_NAMES)})")
            continue
        if not isinstance(spec, dict):
            errors.append(f"{label}[{key!r}] must be a dict with 'slug', 'shortcut' and optional 'aliases'")
            continue
        unknown = sorted(str(name) for name in spec if name not in _PROMPT_SPEC_FIELDS)
        if unknown:
            errors.append(f"{label}[{key!r}] has unknown field(s): {', '.join(unknown)}")
        for name in ("slug", "shortcut"):
            if name not in spec:
                errors.append(f"{label}[{key!r}] is missing {name!r}")
        slug = spec.get("slug")
        if "slug" in spec and (not isinstance(slug, str) or not _PROMPT_SLUG_RE.fullmatch(slug)
                               or len(slug) > _PROMPT_NAME_MAX):
            errors.append(f"{label}[{key!r}] slug {slug!r} must match "
                          f"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$ and be at most {_PROMPT_NAME_MAX} characters")
        elif isinstance(slug, str):
            if slug in FIXED_PROMPT_SLUGS:
                errors.append(f"{label}[{key!r}] slug {slug!r} is a fixed framework prompt slug")
            skill = f"wf-{slug}"
            if skill in FIXED_SKILL_NAMES or skill in FIXED_STALE_SKILL_NAMES:
                errors.append(f"{label}[{key!r}] skill name {skill!r} is a fixed or retired framework skill")
        if "shortcut" in spec:
            problem = _shortcut_problem(spec["shortcut"])
            if problem:
                errors.append(f"{label}[{key!r}] shortcut {spec['shortcut']!r} {problem}")
        aliases = spec.get("aliases", ())
        if not isinstance(aliases, (list, tuple)):
            errors.append(f"{label}[{key!r}] aliases must be a list of strings")
        else:
            for alias in aliases:
                problem = _shortcut_problem(alias)
                if problem:
                    errors.append(f"{label}[{key!r}] alias {alias!r} {problem}")
    if errors:
        return errors
    names = derive_prompt_names(overrides)
    overridden = set(overrides)
    by_slug: "dict[str, list[str]]" = {}
    for key, entry in names.items():
        by_slug.setdefault(entry["slug"], []).append(key)
    for slug, keys in by_slug.items():
        if len(keys) > 1:
            named = sorted(set(keys) & overridden) or keys
            errors.append(f"{label} key(s) {', '.join(map(repr, named))}: slug {slug!r} is used by "
                          f"{' and '.join(map(repr, keys))}")
    phrases: "dict[str, list[tuple[str, str]]]" = {}
    for shortcut_text in FIXED_PROMPT_SHORTCUTS:
        phrases.setdefault(shortcut_text.casefold(), []).append(("a fixed framework shortcut", shortcut_text))
    for key, entry in names.items():
        for phrase in (entry["shortcut"], *entry["aliases"]):
            phrases.setdefault(phrase.casefold(), []).append((repr(key), phrase))
    for folded, owners in phrases.items():
        if len(owners) > 1:
            keys = sorted({owner for owner, _ in owners if owner.strip("'") in overridden})
            if not keys:
                keys = sorted({owner for owner, _ in owners if owner.startswith("'")})
            errors.append(f"{label} key(s) {', '.join(keys)}: shortcut or alias {owners[0][1]!r} "
                          f"is used by {' and '.join(owner for owner, _ in owners)} (compared case-insensitively)")
    default_owner = {default["slug"]: key for key, default in DEFAULT_PROMPT_NAMES.items()}
    for start in sorted(overridden):
        seen = [start]
        current = start
        while True:
            nxt = default_owner.get(names[current]["slug"])
            if nxt is None or nxt == current:
                break
            if nxt == start:
                errors.append(f"{label} key {start!r}: rename cycle {' -> '.join(seen + [start])}")
                break
            if nxt in seen:
                break
            seen.append(nxt)
            current = nxt
    return errors


PROMPT_NAMES: "dict[str, dict[str, object]]" = derive_prompt_names()


def prompt_slug(key: str) -> str:
    """The slug of a mapped lifecycle prompt in this profile."""
    return PROMPT_NAMES[key]["slug"]


def prompt_doc(key: str) -> str:
    """The public prompt path, ``docs/prompts/<slug>.prompt.md``."""
    return f"docs/prompts/{prompt_slug(key)}.prompt.md"


def agent_prompt_doc(key: str) -> str:
    """The agent body path, ``docs/prompts/agents/<slug>.prompt.md``."""
    return f"docs/prompts/agents/{prompt_slug(key)}.prompt.md"


def skill_name(key: str) -> str:
    """The skill name, ``wf-<slug>``."""
    return f"wf-{prompt_slug(key)}"


def shortcut(key: str) -> str:
    """The shortcut phrase, for example ``Prepare wave``."""
    return PROMPT_NAMES[key]["shortcut"]


def shortcut_aliases(key: str) -> "tuple[str, ...]":
    """The alias phrases, for example ``("Ready wave",)``."""
    return tuple(PROMPT_NAMES[key]["aliases"])


def title_case(phrase: str) -> str:
    """Each word's first letter upper-cased (``Prepare wave`` -> ``Prepare Wave``)."""
    return " ".join(word[:1].upper() + word[1:] for word in phrase.split(" "))


def shortcut_title(key: str) -> str:
    """The shortcut in title case, as prompt headings write it."""
    return title_case(shortcut(key))


_PROMPT_HEADING_RE = re.compile(r"\A# [^\r\n]*")
_PROMPT_SHORTCUT_LINE_RE = re.compile(r"(?m)^Shortcut: [^\r\n]*")


def shortcut_line(key: str) -> str:
    """The ``Shortcut:`` line of a lifecycle prompt in this profile, with the
    singular ``| Alias:`` form for one alias and ``| Aliases:`` for several."""
    line = f"Shortcut: **`{shortcut(key)}`**"
    aliases = shortcut_aliases(key)
    if aliases:
        label = "Alias" if len(aliases) == 1 else "Aliases"
        line += f" | {label}: " + ", ".join(f"**`{alias}`**" for alias in aliases)
    return line


def localize_prompt_template(key: str, text: str) -> str:
    """A shipped lifecycle prompt template in this profile's names: only its
    line-1 ``# `` heading (the shortcut in title case) and its first
    ``Shortcut:`` line are rewritten; other text is kept. The identity under the
    default names. Apply it to a shipped template only."""
    text = _PROMPT_HEADING_RE.sub(lambda _m: f"# {shortcut_title(key)}", text, count=1)
    return _PROMPT_SHORTCUT_LINE_RE.sub(lambda _m: shortcut_line(key), text, count=1)


def prompt_names_record_problems(record: object) -> list[str]:
    """Problems with a manifest ``prompt_names`` object (key to applied slug)."""
    if not isinstance(record, dict):
        return ["prompt_names must be an object of prompt key to applied slug"]
    problems: list[str] = []
    for key, slug in record.items():
        if key not in DEFAULT_PROMPT_NAMES:
            problems.append(f"prompt_names key {key!r} is not a tier-named lifecycle prompt")
        elif not isinstance(slug, str) or not _PROMPT_SLUG_RE.fullmatch(slug) or len(slug) > _PROMPT_NAME_MAX:
            problems.append(f"prompt_names[{key!r}] slug {slug!r} is not a valid prompt slug")
    return problems


def applied_prompt_slugs(record: object) -> "dict[str, str]":
    """Every key's applied slug from a manifest ``prompt_names`` object
    (``None`` when absent: every key at its default). Raises ``ValueError``
    naming the problems when the object is invalid."""
    applied = {key: default["slug"] for key, default in DEFAULT_PROMPT_NAMES.items()}
    if record is None:
        return applied
    problems = prompt_names_record_problems(record)
    if problems:
        raise ValueError("; ".join(problems))
    applied.update(record)
    return applied


def pending_prompt_name_keys(record: object) -> "list[str]":
    """The keys whose applied slug (from a manifest ``prompt_names`` object,
    ``None`` meaning defaults) differs from the slug in this profile."""
    applied = applied_prompt_slugs(record)
    return [key for key in DEFAULT_PROMPT_NAMES if applied[key] != prompt_slug(key)]


RECORD_FILENAME_RE = re.escape(RECORD_FILENAME)
ID_KEY_RE = re.escape(ID_KEY)
RECORD_TITLE_RE = re.escape(RECORD_TITLE)
SUMMARY_HEADING_RE = re.escape(SUMMARY_HEADING)
MEMBER_HEADING_RE = re.escape(MEMBER_HEADING)
MEMBER_ID_LABEL_RE = re.escape(MEMBER_ID_LABEL)
MEMBER_STATUS_LABEL_RE = re.escape(MEMBER_STATUS_LABEL)
PREVIOUS_STATUS_LABEL_RE = re.escape(PREVIOUS_STATUS_LABEL)
BACKREF_LABEL_RE = re.escape(BACKREF_LABEL)

# Tokens that are fixed in every profile; a vocabulary token may not reuse one.
FIXED_HEADINGS = frozenset({
    "## Participants", "## Objective", "## Dependencies", "## Watchpoints",
    "## Journal Watchpoints", "## Finding Synthesis", "## Review Evidence",
    "## Review Checkpoints", "## Context Efficiency", "## Progress Log",
    "## Items",
})
FIXED_LABELS = frozenset({
    "Depends On", "Title", "Status", "Completed At", "Closed At", "Owner",
    "Last verified", "Item ID", "Item Status", "Previous Item Status",
    "review-evidence-source",
})
RESERVED_RECORD_FILENAMES = frozenset({"readme.md", "plan-template.md", "events.jsonl"})

# The editable fields, in declaration order.
FIELD_NAMES = (
    "CONTAINER_NAME", "CONTAINER_NAME_PLURAL", "ITEM_NAME", "ITEM_NAME_PLURAL",
    "RECORD_FILENAME", "ID_KEY", "RECORD_TITLE", "SUMMARY_HEADING",
    "MEMBER_HEADING", "MEMBER_ID_LABEL", "MEMBER_STATUS_LABEL", "BACKREF_LABEL",
)
_RE_FIELD_NAMES = (
    "RECORD_FILENAME", "ID_KEY", "RECORD_TITLE", "SUMMARY_HEADING", "MEMBER_HEADING",
    "MEMBER_ID_LABEL", "MEMBER_STATUS_LABEL", "PREVIOUS_STATUS_LABEL", "BACKREF_LABEL",
)


class VocabularyProfileInvalid(ValueError):
    """The vocabulary constants are unusable; the message names the field."""


def change_kind_errors(extra: object = None) -> list[str]:
    """Every problem with ``EXTRA_CHANGE_KINDS`` (default: the live constant);
    empty when valid. Each message names the constant."""
    extra = EXTRA_CHANGE_KINDS if extra is None else extra
    if not isinstance(extra, tuple):
        return [f"EXTRA_CHANGE_KINDS must be a tuple of strings, not {type(extra).__name__}"]
    errors: list[str] = []
    seen: set[str] = set()
    for kind in extra:
        if not isinstance(kind, str):
            errors.append(f"EXTRA_CHANGE_KINDS entry {kind!r} must be a string")
            continue
        # fullmatch, not match: '$' also matches before a trailing newline.
        if not _EXTRA_CHANGE_KIND_RE.fullmatch(kind):
            errors.append(
                f"EXTRA_CHANGE_KINDS entry {kind!r} must match ^[a-z][a-z0-9]{{1,15}}$ "
                "(lowercase ASCII letters and digits, 2 to 16 characters, no '-' or space)"
            )
        if kind in CORE_CHANGE_KINDS:
            errors.append(f"EXTRA_CHANGE_KINDS entry {kind!r} is a core change kind")
        if kind in RESERVED_KIND_TOKENS:
            errors.append(
                f"EXTRA_CHANGE_KINDS entry {kind!r} is reserved (it names another lifecycle id: "
                f"{', '.join(sorted(RESERVED_KIND_TOKENS))})"
            )
        if kind in seen:
            errors.append(f"EXTRA_CHANGE_KINDS entry {kind!r} is declared twice")
        seen.add(kind)
    return errors


def validation_errors(fields: "dict[str, str] | None" = None) -> list[str]:
    """Every problem with a profile; empty when valid.

    With no argument, the live constants above (including the derived
    ``PREVIOUS_STATUS_LABEL``) and ``EXTRA_CHANGE_KINDS`` (wave 1zimf). With a
    mapping (``ARCHIVE_PROFILE``), exactly the ``FIELD_NAMES`` keys, and the
    previous-status label derived from it; change kinds are not part of it."""
    if fields is None:
        live = {name: globals()[name] for name in FIELD_NAMES}
        return change_kind_errors() + _field_errors(live, PREVIOUS_STATUS_LABEL)
    if not isinstance(fields, dict):
        return ["the profile must be a dict of the field names"]
    errors: list[str] = []
    missing = sorted(set(FIELD_NAMES) - set(fields))
    extra = sorted(set(fields) - set(FIELD_NAMES), key=str)
    if missing:
        errors.append("missing field(s): " + ", ".join(missing))
    if extra:
        errors.append("unknown field(s): " + ", ".join(map(str, extra)))
    if errors:
        return errors
    status = fields["MEMBER_STATUS_LABEL"]
    previous = f"Previous {status}" if isinstance(status, str) else status
    return _field_errors(dict(fields), previous)


def _field_errors(fields: "dict[str, str]", previous: object) -> list[str]:
    """The field rules shared by the live profile and ``ARCHIVE_PROFILE``."""
    errors: list[str] = []
    for name, value in fields.items():
        if not isinstance(value, str) or not value.strip() or value != value.strip() or "\n" in value:
            errors.append(f"{name} must be a non-empty single-line string without surrounding spaces")
    if errors:
        return errors
    for name in ("RECORD_TITLE",):
        if not fields[name].startswith("# ") or fields[name].startswith("## "):
            errors.append(f"{name} must be a level-1 heading (`# ...`)")
    for name in ("SUMMARY_HEADING", "MEMBER_HEADING"):
        if not fields[name].startswith("## ") or fields[name].startswith("### "):
            errors.append(f"{name} must be a level-2 heading (`## ...`)")
    for name in ("ID_KEY", "MEMBER_ID_LABEL", "MEMBER_STATUS_LABEL", "BACKREF_LABEL"):
        if ":" in fields[name] or "`" in fields[name]:
            errors.append(f"{name} must not contain ':' or '`' (the colon is added where it is written)")
    record = fields["RECORD_FILENAME"]
    if "/" in record or "\\" in record or not record.lower().endswith(".md"):
        errors.append("RECORD_FILENAME must be a bare .md file name")
    if record.lower() in RESERVED_RECORD_FILENAMES:
        errors.append(f"RECORD_FILENAME must not be {record!r} (a reserved file name)")
    headings = {name: fields[name] for name in ("RECORD_TITLE", "SUMMARY_HEADING", "MEMBER_HEADING")}
    if len({v for v in headings.values()}) != len(headings):
        errors.append("RECORD_TITLE, SUMMARY_HEADING and MEMBER_HEADING must all differ")
    for name, value in headings.items():
        if value in FIXED_HEADINGS:
            errors.append(f"{name} {value!r} collides with a fixed heading")
    labels = {name: fields[name] for name in ("ID_KEY", "MEMBER_ID_LABEL", "MEMBER_STATUS_LABEL", "BACKREF_LABEL")}
    labels["PREVIOUS_STATUS_LABEL"] = previous
    for name, value in labels.items():
        if value in FIXED_LABELS:
            errors.append(f"{name} {value!r} collides with a fixed label")
    # The rule for labels and headings is stated once, in
    # docs/architecture/layering-rules.md (vocabulary profile paragraph).
    items = sorted(labels.items())
    for i, (name_a, a) in enumerate(items):
        for name_b, b in items[i + 1:]:
            if a.casefold() == b.casefold():
                errors.append(f"{name_a} and {name_b} must differ ({a!r}, {b!r})")
    for name, value in sorted(headings.items()):
        for other in sorted(FIXED_HEADINGS):
            if value != other and (value.startswith(other) or other.startswith(value)):
                errors.append(f"{name} {value!r} must not be a prefix of the fixed {other!r}, or it of {name}")
    for name, value in sorted(labels.items()):
        folded = value.casefold()
        for other in sorted(FIXED_LABELS):
            other_folded = other.casefold()
            if value != other and (folded.startswith(other_folded) or other_folded.startswith(folded)):
                errors.append(f"{name} {value!r} must not be a prefix of the fixed {other!r}, or it of {name}")
    heading_items = sorted(headings.items())
    for i, (name_a, a) in enumerate(heading_items):
        for name_b, b in heading_items[i + 1:]:
            if a != b and (a.startswith(b) or b.startswith(a)):
                errors.append(f"{name_a} and {name_b} must not be a prefix of one another ({a!r}, {b!r})")
    return errors


# The vocabulary the shipped ``install/plan-template.md`` is written with.
# Fixed text describing that file, not profile values: a fork edits the
# constants above, and ``localize_template`` rewrites these to them.
_SHIPPED_TEMPLATE_LABELS = ("Change ID", "Change Status", "Wave")
_SHIPPED_TEMPLATE_LABEL_RE = re.compile(
    r"(?m)^(" + "|".join(re.escape(label) for label in _SHIPPED_TEMPLATE_LABELS) + r"):"
)
# The record filename as the last segment of the template's example path.
_SHIPPED_TEMPLATE_RECORD_RE = re.compile(r"(?<=/)wave\.md(?=`)")


def localize_template(text: str) -> str:
    """The shipped change template in this profile's vocabulary: its
    line-leading header labels (``Change ID:``, ``Change Status:``, ``Wave:``)
    rewritten in one pass, and the record filename in its example path. The
    identity under the default profile. Apply it to the shipped template only,
    never to a project copy it already produced."""
    current = dict(zip(_SHIPPED_TEMPLATE_LABELS, (MEMBER_ID_LABEL, MEMBER_STATUS_LABEL, BACKREF_LABEL)))
    text = _SHIPPED_TEMPLATE_LABEL_RE.sub(lambda m: current[m.group(1)] + ":", text)
    return _SHIPPED_TEMPLATE_RECORD_RE.sub(lambda _m: RECORD_FILENAME, text)


class _Profile:
    """A profile's field values, derived previous-status label and escaped
    fragments, under the same attribute names as this module's constants."""

    def __init__(self, fields: "dict[str, str]") -> None:
        for name in FIELD_NAMES:
            setattr(self, name, fields[name])
        self.PREVIOUS_STATUS_LABEL = f"Previous {self.MEMBER_STATUS_LABEL}"
        for name in _RE_FIELD_NAMES:
            setattr(self, name + "_RE", re.escape(getattr(self, name)))

    def id_line(self, wave_id: str) -> str:
        return f"{self.ID_KEY}: `{wave_id}`"


def archive_profile() -> _Profile:
    """The vocabulary archived records are read with (wave 1z8ts): the
    ``ARCHIVE_PROFILE`` mapping when set, else the live constants, read at
    call time."""
    if ARCHIVE_PROFILE is None:
        return _Profile({name: globals()[name] for name in FIELD_NAMES})
    return _Profile(dict(ARCHIVE_PROFILE))


def validate() -> None:
    """Raise :class:`VocabularyProfileInvalid` when the constants are unusable."""
    errors = validation_errors() + prompt_name_errors()
    if ARCHIVE_PROFILE is not None:
        errors += [f"ARCHIVE_PROFILE: {e}" for e in validation_errors(ARCHIVE_PROFILE)]
    if errors:
        raise VocabularyProfileInvalid("vocabulary_profile_invalid: " + "; ".join(errors))


def record_file(directory):
    """The container record path inside ``directory`` (a ``pathlib.Path``)."""
    return directory / RECORD_FILENAME


def id_line(wave_id: str) -> str:
    """The container id line as written into a record."""
    return f"{ID_KEY}: `{wave_id}`"


validate()
