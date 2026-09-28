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

The module exports strings and regex-escaped fragments, not whole patterns:
each consuming site keeps its own grammar (anchoring, backticks, case, legacy
aliases) around the fragment.

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

# ---------------------------------------------------------------------------
# Derived forms (not edited)
# ---------------------------------------------------------------------------

PREVIOUS_STATUS_LABEL = f"Previous {MEMBER_STATUS_LABEL}"

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


def validation_errors(fields: "dict[str, str] | None" = None) -> list[str]:
    """Every problem with a profile; empty when valid.

    With no argument, the live constants above (including the derived
    ``PREVIOUS_STATUS_LABEL``). With a mapping (``ARCHIVE_PROFILE``), exactly
    the ``FIELD_NAMES`` keys, and the previous-status label derived from it."""
    errors: list[str] = []
    if fields is None:
        fields = {name: globals()[name] for name in FIELD_NAMES}
        previous = PREVIOUS_STATUS_LABEL
    else:
        if not isinstance(fields, dict):
            return ["the profile must be a dict of the field names"]
        missing = sorted(set(FIELD_NAMES) - set(fields))
        extra = sorted(set(fields) - set(FIELD_NAMES), key=str)
        if missing:
            errors.append("missing field(s): " + ", ".join(missing))
        if extra:
            errors.append("unknown field(s): " + ", ".join(map(str, extra)))
        if errors:
            return errors
        fields = dict(fields)
        status = fields["MEMBER_STATUS_LABEL"]
        previous = f"Previous {status}" if isinstance(status, str) else status
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
    items = sorted(labels.items())
    for i, (name_a, a) in enumerate(items):
        for name_b, b in items[i + 1:]:
            if a == b:
                errors.append(f"{name_a} and {name_b} must differ ({a!r})")
            elif a.startswith(b) or b.startswith(a):
                errors.append(f"{name_a} and {name_b} must not be a prefix of one another ({a!r}, {b!r})")
    # Some readers test for a heading or label by substring, so a token that
    # is a prefix of another (``## Set`` and ``## Set Summary``) would match
    # the wrong line. Fixed tokens are compared too (``## Progress``).
    for group, fixed in ((headings, FIXED_HEADINGS), (labels, FIXED_LABELS)):
        for name, value in sorted(group.items()):
            for other in sorted(fixed):
                if value != other and (value.startswith(other) or other.startswith(value)):
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
    errors = validation_errors()
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
