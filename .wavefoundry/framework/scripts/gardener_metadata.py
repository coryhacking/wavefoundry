"""Canonical recognition and normalization of docs-gardener metadata."""

from __future__ import annotations

import re

from change_doc_checklist import comment_visible_lines

# Wave 1z8mm: the member labels, id key and back-reference are vocabulary.
import vocabulary_profile as _vocab


GARDENER_DATE_SENTINEL = "Last verified: <gardener-owned-date>"
PROGRESS_LOG_SENTINEL = "<progress-log narration excluded from the review-policy digest>"
SESSION_HANDOFF_SENTINEL = "<session-handoff boilerplate excluded from the review-policy digest>"
# The exact template body. Two producers ship this sentence -- docs/plans/plan-template.md
# and the wf_new_* literal in server_impl.py -- and they are byte-identical today. They
# must stay in step: a drift between them silently narrows the exclusion, because a body
# that no longer matches is treated as substantive and stays digested.
SESSION_HANDOFF_TEMPLATE_BODY = (
    "See `docs/agents/session-handoff.md` for current session state."
)
_GARDENER_DATE_LINE_RE = re.compile(r"^Last verified:\s+\d{4}-\d{2}-\d{2}\s*$")
# Wave 1z8mm: the member-status label comes from the profile, so a second
# profile's status advance is excluded from the digest too (otherwise every
# advance would move the digest and lapse approvals).
_REVIEW_TRACKING_STATUS_LINE_RE = re.compile(
    rf"^(?:{_vocab.MEMBER_STATUS_LABEL_RE}|Status):\s+.+?\s*$"
)
_FRONTMATTER_METADATA_RE = re.compile(r"^[A-Za-z][\w .()/-]*:\s")
_FRONTMATTER_KEY_RE = re.compile(r"^(?P<key>[A-Za-z][\w .()/-]*):\s")
# The keys a real leading metadata carrier uses, curated from a census of every
# markdown document in this repository. Membership is what separates metadata
# from prose that merely looks like it: `Owner: Eng` is a carrier line and
# `Problem: the gate fails.` is not, and no line SHAPE can tell them apart.
# `Role` and `Category` are load-bearing rather than decorative — without them
# `docs/agents/memory-archive.md` closes its carrier above a genuine `Status:`
# line and starts churning on every status advance.
_CARRIER_METADATA_KEYS = frozenset({
    _vocab.MEMBER_ID_LABEL, _vocab.MEMBER_STATUS_LABEL, "Status", "Owner",
    _vocab.BACKREF_LABEL, "Last verified", "Title", _vocab.ID_KEY,
    "review-evidence-source",
    "review-policy-reprepare-required", "Completed At", "Closed At",
    _vocab.PREVIOUS_STATUS_LABEL, "Role", "Category", "Memory ID", "Kind",
    "Confidence", "Created", "Updated", "Source event", "Validation",
    "Validated by", "Action delta", "Validation rationale",
    "Evidence verified", "Current target verified", "Canonical overlap",
    "Source exploration cost", "Shortcut", "Superseded by", "Schema version",
    "Actor", "Last distilled", "Archived", "Archive reason", "Archive path",
    "Supersedes", "Alias", "Verification method", "Amended", "Depends on",
    "Release target", "Measured", "Decision",
})
# `\s*$` rather than `[ \t]*$` so a CRLF checkout's `## Progress Log\r` still
# matches, exactly as `_GARDENER_DATE_LINE_RE` above already tolerates it. The
# splitter below splits on "\n", so the trailing "\r" reaches this pattern.
_PROGRESS_LOG_HEADING_RE = re.compile(r"^##[ \t]+Progress Log\s*$")
_SESSION_HANDOFF_HEADING_RE = re.compile(r"^##[ \t]+Session Handoff\s*$")
_SECTION_HEADING_PREFIX = "## "
_SECTION_HEADING_RE = re.compile(r"^##[ \t]+(?P<name>[^\r\n]+?)\s*$")
_CHECKBOX_LINE_RE = re.compile(r"^(?P<prefix>\s*-\s*\[)(?P<mark>[ x~X])(?P<suffix>\]\s+.*)$")
# Change 23q1h: an Acceptance Criteria item may also sit in a blockquote, as
# the mark tools allow; Tasks keep the unquoted form above.
_AC_CHECKBOX_LINE_RE = re.compile(
    r"^(?P<prefix>\s*(?:>[ \t]*)*-\s*\[)(?P<mark>[ x~X])(?P<suffix>\]\s+.*)$"
)
# Change 23q1h: a criterion's canonical status note. The one pattern serves
# both forms: searched at the end of an item's first line (after a space and
# some item text) and matched against a whole continuation line once its
# blockquote prefix and indentation are set aside. The reason holds no `*`
# and no line break, so the note is recognised exactly where it was written.
_STATUS_NOTE_RE = re.compile(r"\*Status:(?P<reason>[^*\r\n]*)\*$")
# A checklist item at any marker: it ends the previous criterion's block.
_CHECKLIST_ITEM_START_RE = re.compile(
    r"^[ \t]*(?:[-*+]|\d{1,9}[.)])[ \t]+\[[^\]\r\n]\][ \t]+\S"
)


def is_gardener_date_line(line: str) -> bool:
    """Return whether ``line`` is the one canonical gardener date shape."""

    return _GARDENER_DATE_LINE_RE.fullmatch(line) is not None


def normalize_gardener_date(text: str, *, replacement: str | None) -> str:
    """Replace or remove one canonical leading-frontmatter gardener date.

    Zero matches and ambiguous multiple matches are returned byte-for-byte. The
    leading frontmatter ends at the first line that is neither blank, a level-1
    title, nor a ``Key: value`` metadata line, so body and fenced lookalikes stay
    load-bearing.
    """

    lines = text.split("\n")
    matches: list[int] = []
    in_frontmatter = True
    for index, line in enumerate(lines):
        if not in_frontmatter:
            break
        if is_gardener_date_line(line):
            matches.append(index)
        if line.strip() and not line.startswith("# ") and not _FRONTMATTER_METADATA_RE.match(line):
            in_frontmatter = False
    if len(matches) != 1:
        return text
    index = matches[0]
    if replacement is None:
        del lines[index]
    else:
        lines[index] = replacement
    return "\n".join(lines)


def normalize_review_tracking_status(text: str, *, replacement: str | None) -> str:
    """Stabilize leading change-status metadata for review-policy comparison.

    ``Status`` and ``Change Status`` describe workflow progress, not the
    approved change contract.  Limit this normalization to the leading metadata
    carrier so a similarly named prose line remains reviewable.

    The carrier is bounded by a KNOWN-KEY allowlist rather than by line shape.
    A shape test cannot separate ``Owner: Eng`` from ``Problem: the gate
    fails.``; both match ``Word: text``, so prose kept the region open and a
    later body ``Status:`` line was rewritten.  That is the inverse of this
    function's purpose: it makes a real contract edit digest-invisible, so an
    operator can change a document's meaning and the receipt will not move.

    Bounding at the first ``## `` heading was considered and does not work.  A
    ``## `` heading already closes the scan (non-blank, not a ``# `` title, and
    no ``Key: `` prefix), so every capture necessarily lies BEFORE one and
    heading-bounding removes none of them while widening the carrier over all
    preceding prose.

    Blockquote tolerance is a measured repair, not a convenience: the previous
    scan truncated at a ``> **REFRAMED...**`` line and left genuine frontmatter
    status lines digest-significant, so advancing that document's status
    lapsed its approvals.

    Failure direction is chosen deliberately.  An unrecognized key closes the
    carrier early, so a genuine status line below it stays significant and its
    document churns visibly on a status advance.  That is recoverable; silent
    capture of contract prose is not.

    NOTE: ``normalize_gardener_date`` above deliberately keeps the older
    shape-based scan, so the two functions can disagree about where the leading
    region ends.  That divergence is intentional and unpinned by any test;
    whether the date normalizer should follow is a separate change.
    """

    lines = text.split("\n")
    matches: list[int] = []
    for index, line in enumerate(lines):
        if _REVIEW_TRACKING_STATUS_LINE_RE.fullmatch(line):
            matches.append(index)
            continue
        if not line.strip():
            continue
        if line.startswith("# "):
            continue
        if line.lstrip().startswith(">"):
            continue
        key_match = _FRONTMATTER_KEY_RE.match(line)
        if key_match and key_match.group("key") in _CARRIER_METADATA_KEYS:
            continue
        break
    # One or two matches are both legitimate: a spec carries
    # `Change Status:` and `Status:`, and 794 of 1457 documents in this
    # repository have exactly that pair.  The siblings above degrade on
    # `len(matches) != 1` because they normalize a SINGLE line; copying that
    # contract here would stop normalizing every paired document, moving the
    # digest on each status advance and lapsing the approvals already
    # recorded.  Any other count is a shape this corpus cannot produce, so it
    # degrades to a byte-for-byte return rather than a guess.
    if len(matches) not in (1, 2):
        return text
    for index in matches:
        if replacement is None:
            lines[index] = ""
        else:
            label = lines[index].split(":", 1)[0]
            lines[index] = f"{label}: {replacement}"
    return "\n".join(lines)


def _fenced_line_flags(lines: list[str]) -> list[bool]:
    """Flag each line that is a fence marker or sits inside a fenced block.

    Mirrors ``commit_provenance._without_fenced_code``: the fence toggles only
    when the marker matches the currently open fence, so a ``~~~`` inside a
    ``` block does not close it.
    """

    flags: list[bool] = []
    fence = ""
    for line in lines:
        stripped = line.lstrip()
        marker = "```" if stripped.startswith("```") else (
            "~~~" if stripped.startswith("~~~") else ""
        )
        if marker:
            flags.append(True)
            fence = "" if fence == marker else marker if not fence else fence
            continue
        flags.append(bool(fence))
    return flags


def normalize_progress_log(text: str, *, replacement: str | None) -> str:
    """Replace or remove the body of the one canonical ``## Progress Log`` section.

    The Progress Log narrates what happened; it states no reviewable claim, so
    the review-policy digest must not move when a repairer records a repair.
    Zero matches and ambiguous multiple matches are returned byte-for-byte, the
    same degrade contract ``normalize_gardener_date`` uses. The heading is
    anchored at line start, the region ends at the next ``## `` heading or end of
    file, and fenced code is skipped so a heading lookalike inside a fence
    neither opens nor closes a region.
    """

    lines = text.split("\n")
    visible = comment_visible_lines(lines, tracking_fences=True)
    fenced = _fenced_line_flags(visible)
    matches = [
        index
        for index, line in enumerate(visible)
        if not fenced[index] and _PROGRESS_LOG_HEADING_RE.fullmatch(line)
    ]
    if len(matches) != 1:
        return text
    start = matches[0] + 1
    end = len(lines)
    for index in range(start, len(lines)):
        if not fenced[index] and visible[index].startswith(_SECTION_HEADING_PREFIX):
            end = index
            break
    body = [] if replacement is None else [replacement]
    return "\n".join([*lines[:start], *body, *lines[end:]])


def _split_quote(line: str) -> tuple[int, str]:
    """``(depth, rest)``: the blockquote ``>`` markers prefixing ``line`` and the
    text after them (one optional space or tab after each marker belongs to it)."""

    depth = 0
    index = 0
    length = len(line)
    while True:
        probe = index
        while probe < length and line[probe] in " \t":
            probe += 1
        if probe < length and line[probe] == ">":
            depth += 1
            index = probe + 1
            if index < length and line[index] in " \t":
                index += 1
            continue
        return depth, line[index:] if depth else line


def _first_line_notes(line: str, match: re.Match[str]) -> tuple[re.Match[str], ...]:
    """The canonical notes ending an item's first line, in document order.

    Each note follows a space, and some item text precedes the first. A run
    of canonical notes (``... *Status: A* *Status: B*``, as a hand edit that
    defers again leaves) is read whole, so no earlier note of the run stays
    digested; any other text between two notes ends the run.
    """

    notes: list[re.Match[str]] = []
    end = len(line)
    while True:
        note = _STATUS_NOTE_RE.search(line, 0, end)
        if note is None or line[note.start() - 1: note.start()] != " ":
            break
        notes.append(note)
        end = note.start() - 1
    # The earliest note of the run is item text when nothing precedes it.
    if notes and not line[match.start("suffix") + 1: notes[-1].start()].strip():
        notes.pop()
    return tuple(reversed(notes))


def _criterion_blocks(
    lines: list[str], fenced: list[bool], raw_lines: list[str]
) -> list[tuple[int, re.Match[str], tuple[re.Match[str], ...], tuple[int, ...], int]]:
    """Every Acceptance Criteria item: ``(index, match, first-line notes,
    continuation note line indexes, block end)``.

    The one reading of criteria and their status notes (change 23q1h): the
    review-policy normalizer below, the criterion status recorded on delivery
    approvals and the delivery gate all use it, so a note cannot be out of the
    digest and out of the recorded status at once.  An item's block is its
    line and the following lines at its blockquote depth that are not blank,
    not fenced, not a heading and not another checklist item, and that are
    indented or are a note line; a note line that follows no item is not a
    note.
    """

    blocks = []
    section = ""
    for index, line in enumerate(lines):
        if fenced[index]:
            continue
        heading = _SECTION_HEADING_RE.fullmatch(line)
        if heading:
            section = heading.group("name").strip().lower()
            continue
        if section != "acceptance criteria":
            continue
        match = _AC_CHECKBOX_LINE_RE.match(line)
        if match is None:
            continue
        depth = _split_quote(line)[0]
        notes: list[int] = []
        end = index + 1
        for probe in range(index + 1, len(lines)):
            if fenced[probe]:
                break
            probe_depth, rest = _split_quote(lines[probe])
            if probe_depth != depth or not rest.strip():
                break
            if rest.lstrip().startswith("#") or _CHECKLIST_ITEM_START_RE.match(rest):
                break
            if lines[probe] == raw_lines[probe] and _STATUS_NOTE_RE.fullmatch(rest.strip()):
                notes.append(probe)
            elif not rest.startswith((" ", "\t")):
                break
            end = probe + 1
        firsts = _first_line_notes(line, match)
        # Keep inline comments in the digest and in source on a note rewrite.
        # Only a literal trailing note can be discarded from the original line.
        if firsts and raw_lines[index][firsts[0].start():] != line[firsts[0].start():]:
            firsts = ()
        blocks.append((index, match, firsts, tuple(notes), end))
    return blocks


def criterion_note_positions(lines: list[str]) -> dict[int, tuple[int | None, tuple[int, ...]]]:
    """Per Acceptance Criteria item line index: where its canonical notes are.

    ``(first-line note start, continuation note line indexes)``, the start
    being the column where the item's first-line run of notes begins (None
    without one). ``lines`` may keep a ``\\r`` or trailing spaces; they are
    set aside, as ``normalize_carriers`` does, before the shared reading, so a
    writer replacing a note finds exactly the notes the digest removes.
    """

    raw_lines = [line.rstrip() for line in lines]
    stripped = comment_visible_lines(raw_lines, tracking_fences=True)
    fenced = _fenced_line_flags(stripped)
    return {
        index: (firsts[0].start() if firsts else None, note_lines)
        for index, _match, firsts, note_lines, _end in _criterion_blocks(stripped, fenced, raw_lines)
    }


def criterion_statuses(text: str) -> tuple[dict[str, object], ...]:
    """Each Acceptance Criteria item with its mark and canonical status notes.

    Change 23q1h: the carriers are stabilized first, exactly as
    ``canonical_review_policy_body`` does, so a CRLF line or a trailing space
    reads as it does for the digest.  ``text`` is the item's first-line text
    after the mark, ``notes`` the reason of each canonical note in document
    order (stripped), and ``quote`` the item as written, one line.
    """

    raw_lines = normalize_carriers(text).split("\n")
    lines = comment_visible_lines(raw_lines, tracking_fences=True)
    fenced = _fenced_line_flags(lines)
    statuses = []
    for index, match, firsts, note_lines, end in _criterion_blocks(lines, fenced, raw_lines):
        reasons = [first.group("reason").strip() for first in firsts]
        for note_index in note_lines:
            note = _STATUS_NOTE_RE.fullmatch(_split_quote(lines[note_index])[1].strip())
            reasons.append(note.group("reason").strip())
        quote = " ".join(
            _split_quote(line)[1].strip() for line in lines[index:end]
        )
        statuses.append({
            "mark": match.group("mark"),
            "deferred": match.group("mark") == "~",
            "text": match.group("suffix")[1:].strip(),
            "notes": tuple(reasons),
            "quote": quote,
        })
    return tuple(statuses)


def normalize_checkbox_tracking(text: str) -> str:
    """Stabilize completion and deferral tracking in Acceptance Criteria and Tasks.

    Only list items in the canonical Acceptance Criteria and Tasks sections are
    considered, and fenced lines are excluded.  Every completion, deferral and
    task marker canonicalizes to ``[ ]``.  In Acceptance Criteria a criterion's
    canonical status note is removed too, whatever its mark: a trailing
    `` *Status: <reason>*`` on its first line (a run of them, read whole) and
    a continuation line that is
    exactly ``*Status: <reason>*`` (change 23q1h), so deferring, reopening or
    re-ticking a criterion moves no digest.  Every other byte of a criterion,
    including a note in any other form, stays digested.
    """

    lines = text.split("\n")
    visible = comment_visible_lines(lines, tracking_fences=True)
    fenced = _fenced_line_flags(visible)
    dropped: set[int] = set()
    for index, match, firsts, note_lines, _end in _criterion_blocks(visible, fenced, lines):
        line = lines[index]
        if firsts:
            line = line[: firsts[0].start()].rstrip()
        lines[index] = line[:match.start("mark")] + " " + line[match.end("mark"):]
        dropped.update(note_lines)
    section = ""
    for index, line in enumerate(visible):
        if fenced[index]:
            continue
        heading = _SECTION_HEADING_RE.fullmatch(line)
        if heading:
            section = heading.group("name").strip().lower()
            continue
        if section != "tasks":
            continue
        match = _CHECKBOX_LINE_RE.match(line)
        if match is None:
            continue
        lines[index] = lines[index][:match.start("mark")] + " " + lines[index][match.end("mark"):]
    return "\n".join(line for index, line in enumerate(lines) if index not in dropped)


def normalize_carriers(text: str) -> str:
    """Stabilize bytes that carry no markdown meaning and no reviewable claim.

    A BOM, CRLF line endings, the presence or absence of a trailing newline,
    and a LONE trailing space are all invisible to a reader and to every
    consumer of this document, yet each moves the digest and lapses every
    approval in a wave with zero human intent. A Windows checkout or an editor
    that strips whitespace on save would otherwise supersede a receipt.

    ALL trailing whitespace outside a fence is normalized, including a markdown
    hard line break. An earlier revision preserved runs of two or more spaces on
    the grounds that a hard break changes rendering, but the digest exists to
    detect changes to the approved CLAIM contract, and a hard break changes
    layout rather than words. The split was also unpredictable for an author,
    who can see neither form, and it fixed the smaller population: measured on
    this corpus, 2 lines carry a lone trailing space while 24 carry a run of two
    or more, so the rule normalized 2 lines and left 24 churning.

    Trailing whitespace INSIDE a fence is preserved, because there it can be the
    subject rather than the formatting: a spec that demonstrates
    one-space versus two-space behaviour in a fenced example would otherwise
    become indistinguishable from itself. Interior whitespace is untouched
    everywhere.

    This runs FIRST, before every section normalizer, because the section
    matchers compare bodies against fixed text. If a carrier ran after them, a
    CRLF checkout would make a boilerplate body fail its match and the churn
    would return for exactly the population this function protects -- silently,
    because a body that differs from the template is indistinguishable from an
    author who wrote something substantive.
    """

    text = text.lstrip("﻿")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    visible = comment_visible_lines(lines, tracking_fences=True)
    fenced = _fenced_line_flags(visible)
    lines = [
        line if fenced[index] else line.rstrip()
        for index, line in enumerate(lines)
    ]
    return "\n".join(lines).rstrip("\n") + "\n"


def normalize_session_handoff(text: str, *, replacement: str | None) -> str:
    """Replace the body of ``## Session Handoff`` only when it is boilerplate.

    Measured across the corpus, 39 of 732 sections carry substantive text, some
    of it load-bearing for admission ("this change is planning-only until it is
    admitted, prepared..."). Deleting that after a council approved on the basis
    of it must not be invisible, so the exclusion is conditional: the stripped
    body must equal the template sentence EXACTLY. A prefix match would swallow
    five real documents that open with the template sentence and then continue
    with substantive text.

    Degrade contract, matching the sibling normalizers: zero matches is the
    NORMAL absent case -- 89 of 825 documents carry no such section -- and two
    or more is ambiguity. Both return the text byte for byte rather than
    raising, because this function is a pure helper on the digest hot path
    whose callers have no handler; loudness for the ambiguous case belongs in
    the diagnostic channel, not in an exception out of lane selection.
    """

    lines = text.split("\n")
    visible = comment_visible_lines(lines, tracking_fences=True)
    fenced = _fenced_line_flags(visible)
    matches = [
        index
        for index, line in enumerate(visible)
        if not fenced[index] and _SESSION_HANDOFF_HEADING_RE.fullmatch(line)
    ]
    if len(matches) != 1:
        return text
    start = matches[0] + 1
    end = len(lines)
    for index in range(start, len(lines)):
        if not fenced[index] and visible[index].startswith(_SECTION_HEADING_PREFIX):
            end = index
            break
    if "\n".join(lines[start:end]).strip() != SESSION_HANDOFF_TEMPLATE_BODY:
        return text
    body = [] if replacement is None else [replacement]
    return "\n".join([*lines[:start], *body, *lines[end:]])


def ambiguous_excluded_headings(text: str) -> tuple[str, ...]:
    """Name each excluded-region heading this document makes ambiguous.

    The exclusion normalizers degrade silently by returning the text unchanged,
    which is the only safe behavior for a pure helper on the digest hot path:
    its three call sites have no handler, so raising would take down lane
    selection, digest computation and prepare on ordinary author input. But a
    silent degrade means the churn returns with no explanation, so the LOUD
    half lives here and is surfaced by the caller as a diagnostic.

    Ambiguity is two or more exact headings. Zero is the NORMAL absent case --
    89 of 825 specs carry no ``## Session Handoff`` at all -- and is
    never reported, because conflating absent with duplicated is exactly the
    defect the shipped ``len(matches) != 1`` predicate has.
    """

    lines = text.split("\n")
    visible = comment_visible_lines(lines, tracking_fences=True)
    fenced = _fenced_line_flags(visible)
    ambiguous: list[str] = []
    for label, pattern, name in (
        ("## Progress Log", _PROGRESS_LOG_HEADING_RE, "progress log"),
        ("## Session Handoff", _SESSION_HANDOFF_HEADING_RE, "session handoff"),
    ):
        exact = [
            index
            for index, line in enumerate(visible)
            if not fenced[index] and pattern.fullmatch(line)
        ]
        if len(exact) > 1:
            ambiguous.append(
                f"`{label}` appears {len(exact)} times outside a fence, so its "
                "review-policy exclusion is ambiguous and was NOT applied; "
                "every edit to that section will supersede the receipt until "
                "there is exactly one heading"
            )
            continue
        if exact:
            continue
        # A VARIANT heading in a document carrying no exact one. This is the
        # other half of the hazard and it is the quieter one: `## Progress Log
        # (delivery)`, `### Progress Log` and `## progress log` each disable
        # the exclusion silently, and the author sees only that their narration
        # started superseding the receipt. Reported only when no exact heading
        # exists, so a document that legitimately has none stays silent -- 89
        # of 825 carry no Session Handoff at all.
        for index, line in enumerate(visible):
            if fenced[index]:
                continue
            stripped = line.strip()
            if not stripped.startswith("#"):
                continue
            heading = stripped.lstrip("#").strip().lower()
            if heading.startswith(name) and stripped != label:
                ambiguous.append(
                    f"`{stripped}` looks like `{label}` but does not match it, "
                    "so the review-policy exclusion for that section was NOT "
                    "applied and every edit to it supersedes the receipt; use "
                    f"exactly `{label}`"
                )
                break
    return tuple(ambiguous)


def canonical_review_policy_body(body: bytes) -> bytes:
    """Return review-policy bytes with the non-substantive carriers stabilized.

    Carrier stabilization (BOM, line endings, trailing newline, lone trailing
    space) followed by five narrow section normalizations: leading workflow-status metadata,
    the gardener-owned date line, the body of the one canonical ``## Progress
    Log`` section, a boilerplate ``## Session Handoff`` body, and completion and
    deferral checkbox markers in Acceptance Criteria and Tasks, with a
    criterion's canonical ``*Status: <reason>*`` note (change 23q1h). A
    deferral therefore supersedes no receipt and lapses no readiness approval;
    the delivery approvals judge it instead, through the criterion status they
    record and the shared delivery gate. Every other section, and every
    checkbox LABEL, stays digested byte for byte, so a plan edit, including a
    reworded criterion or a note in any other form, still supersedes the
    receipt.
    """

    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        return body
    # Carriers FIRST. The section matchers below compare against fixed text, so
    # a CRLF checkout would otherwise defeat them silently. See normalize_carriers.
    text = normalize_carriers(text)
    text = normalize_review_tracking_status(text, replacement="<workflow-status>")
    text = normalize_gardener_date(text, replacement=GARDENER_DATE_SENTINEL)
    text = normalize_progress_log(text, replacement=PROGRESS_LOG_SENTINEL)
    text = normalize_session_handoff(text, replacement=SESSION_HANDOFF_SENTINEL)
    text = normalize_checkbox_tracking(text)
    return text.encode("utf-8")


__all__ = [
    "GARDENER_DATE_SENTINEL",
    "PROGRESS_LOG_SENTINEL",
    "SESSION_HANDOFF_SENTINEL",
    "SESSION_HANDOFF_TEMPLATE_BODY",
    "ambiguous_excluded_headings",
    "canonical_review_policy_body",
    "criterion_statuses",
    "is_gardener_date_line",
    "normalize_gardener_date",
    "normalize_review_tracking_status",
    "normalize_checkbox_tracking",
    "normalize_carriers",
    "normalize_progress_log",
    "normalize_session_handoff",
]
