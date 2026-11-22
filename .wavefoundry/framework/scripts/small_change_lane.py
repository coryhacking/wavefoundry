"""Operator-selected small changes: immutable admission and local Git evidence."""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import stat
import subprocess
import tempfile
import time
import unicodedata
from pathlib import Path, PureWindowsPath

import contained_files
import review_evidence
import review_policy

MARKER = "small-change-selection:"
DECLINED = "small-change-request-declined:"
EXPANDED = "small-change-membership-expanded: true"
_FIELDS = {"operator_direction", "intended_diff", "paths"}
_LIMIT = contained_files.DEFAULT_MAX_BYTES
_SHA = re.compile(r"(?:[a-f0-9]{40}|[a-f0-9]{64})")
_CODE = frozenset("py js ts jsx tsx mjs cjs mts cts go rs java kt kts swift c cc cpp cxx h hh hpp cs fs vb rb php sh bash zsh fish html css scss sass sql ps1 psm1 bat cmd scala clj ex exs erl hrl hs lua ml mli dart r jl zig vue svelte".split())
_PROTECTED = re.compile(
    r"(?:^|[./_ -])(?:seed[s]?|hooks?|githooks|security|secrets?|auth|oauth|authn|authz|"
    r"authentication|authorization|credentials?|permissions?|crypto|release[s]?|deploy(?:ment)?|"
    r"publish|public|api|openapi|swagger|contracts?|schemas?|proto|graphql|migrations?|"
    r"build.pack|upgrade.wavefoundry)(?:$|[./_ -])", re.I)
_EFFECT = re.compile(
    r"\b(?:public (?:api|response|interface|behavior|behaviour|schema)|external (?:contract|api)|"
    r"api (?:contract|response|schema)|security (?:control|policy)|authentication|authorization|"
    r"release (?:process|artifact)|hook (?:contract|behavior)|seed prompt)\b", re.I)


class Unverified(ValueError):
    """An actionable reason to require ordinary review."""


def _header(text):
    return text.partition("\n## ")[0]


def _unique_fields(pairs):
    fields = dict(pairs)
    if len(fields) != len(pairs):
        raise ValueError("Duplicate admission field.")
    return fields


def read_selection(wave_text: str, *, marker=MARKER) -> dict | None:
    lines = [line for line in _header(wave_text).splitlines()
             if line.lstrip().lower().startswith(marker)]
    if not lines:
        return None
    if len(lines) == 1 and lines[0].startswith(marker + " "):
        try:
            data = json.loads(lines[0][len(marker):], object_pairs_hook=_unique_fields)
            if isinstance(data, dict) and set(data) == _FIELDS | {"change_id", "baseline", "admission_reasons"}:
                validate_request({k: data[k] for k in _FIELDS})
                if (isinstance(data["change_id"], str) and isinstance(data["baseline"], str)
                        and isinstance(data["admission_reasons"], list)
                        and all(isinstance(x, str) for x in data["admission_reasons"])):
                    return data
        except (ValueError, TypeError, RecursionError):
            pass
    return {"admission_reasons": ["The wave's small-change admission is malformed or ambiguous."]}


def add_header(text: str, line: str) -> str:
    header, marker, tail = text.partition("\n## ")
    return header.rstrip("\r\n") + "\n" + line + "\n" + marker + tail


def selection_line(selection: dict, *, marker=MARKER) -> str:
    return marker + " " + json.dumps(selection, sort_keys=True, separators=(",", ":"))


def validate_request(request):
    if not isinstance(request, dict) or set(request) != _FIELDS:
        raise ValueError("Provide operator_direction, intended_diff, and paths for this admission.")
    for key in ("operator_direction", "intended_diff"):
        value = request[key]
        if not isinstance(value, str) or not value.strip() or len(value) > 2000 or any(ord(c) < 32 for c in value):
            raise ValueError(f"Provide one nonempty line of at most 2000 characters for {key}.")
    if re.search(r"[.!?]\s+\S", request["intended_diff"]):
        raise ValueError("Describe the intended diff in one sentence.")
    paths = request["paths"]
    if not isinstance(paths, list) or len(paths) > 64 or not all(isinstance(p, str) and len(p) <= 1024 for p in paths):
        raise ValueError("Provide a bounded list of exact repository-relative file paths.")


def _path_reason(path):
    parts = path.split("/")
    if (not path or any(x in {"", ".", ".."} for x in parts) or PureWindowsPath(path).drive
            or any(c in path for c in "\\:*?[]<>|\"") or any(ord(c) < 32 for c in path)
            or any(x.rstrip(" .") != x or re.fullmatch(r"(?i)(?:con|prn|aux|nul|(?:com|lpt)[1-9¹²³])(?:\..*)?", x) for x in parts)
            or ".git" in {x.casefold() for x in parts}):
        return "Declare canonical repository-relative paths without traversal, globs, or aliases."
    lower = path.lower()
    if (_PROTECTED.search(re.sub(r"(?<=[a-z])(?=[A-Z])", "_", path)) or
            any(part in {".github", ".husky", ".githooks", "workflows", "ci"} for part in lower.split("/"))
            or lower.startswith("docs/") or lower.endswith((".proto", ".graphql", ".gql", ".d.ts"))):
        return f"Protected surface requires ordinary review: {path}."
    if Path(path).suffix[1:].lower() not in _CODE and not {"test", "tests", "fixture", "fixtures", "testdata"}.intersection(lower.split("/")[:-1]):
        return f"Declare only internal code, test, or fixture files: {path}."
    return None


def _git(root, *args, allow=(0,), data=None):
    # No shell, no caller-supplied Git directory and no index writes on preview.
    from index_state_store import _run_git
    cmd = ["git", "--no-optional-locks", "--no-replace-objects",
           *([] if args[0] == "check-ignore" else ["--literal-pathspecs"]), "-C", str(root),
           "-c", "core.fsmonitor=false", "-c", "core.untrackedCache=false", "-c", "core.fileMode=true", *args]
    with tempfile.TemporaryFile() as stream:
        try:
            result = _run_git(cmd, stdout=stream, stderr=subprocess.DEVNULL, timeout=10, input=data)
        except (OSError, subprocess.SubprocessError) as exc:
            raise Unverified(f"Could not verify Git {args[0]} ({type(exc).__name__}).") from exc
        if result.returncode not in allow:
            raise Unverified(f"Could not verify Git {args[0]} against the admission checkout.")
        stream.seek(0)
        raw = stream.read(_LIMIT + 1)
    if len(raw) > _LIMIT:
        raise Unverified("The Git scope exceeds the verification limit.")
    return raw


def _records(raw):
    if raw and not raw.endswith(b"\0"):
        raise Unverified("Incomplete Git path evidence.")
    return raw.decode("utf-8").split("\0")[:-1]


def _head(root):
    if Path(os.fsdecode(_git(root, "rev-parse", "--show-toplevel").rstrip(b"\n"))).resolve() != root.resolve():
        raise Unverified("Admission requires the configured repository to be the Git checkout root.")
    value = _git(root, "rev-parse", "--verify", "HEAD^{commit}").strip().decode("ascii")
    if not _SHA.fullmatch(value):
        raise Unverified("The Git checkout has no verifiable HEAD commit.")
    return value


def _file(root, rel):
    try:
        data, opened = contained_files.read_contained(root, root / rel, max_bytes=_LIMIT, follow_links=False)
    except FileNotFoundError:
        return None, None
    current = (root / rel).lstat()
    def identity(s):
        return (s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    if (identity(opened) != identity(current) or len(data) != opened.st_size or opened.st_nlink != 1
            or not stat.S_ISREG(current.st_mode)):
        raise Unverified(f"File identity or contents could not be verified: {rel}.")
    return data, opened


def _reviewed_file_id(st, rel):
    """A persistent file index and creation/change time, independent of mount device number."""
    inode = getattr(st, "st_ino", None)
    if type(inode) is not int or inode <= 0:
        raise Unverified(f"No verifiable filesystem file index for {rel}.")
    for field in ("st_birthtime_ns", "st_ctime_ns"):
        stamp = getattr(st, field, None)
        if type(stamp) is int and stamp > 0:
            return [inode, field, stamp]
    raise Unverified(f"No verifiable filesystem identity timestamp for {rel}.")


def _regular_git_modes(root, baseline, paths):
    entries = _records(_git(root, "ls-tree", "-z", baseline, "--", *paths))
    entries.extend(_records(_git(root, "ls-files", "--stage", "-z", "--", *paths)))
    for entry in entries:
        if entry.partition(" ")[0] not in {"100644", "100755"}:
            raise Unverified("A declared path is a directory, submodule, link, or unsupported Git file type.")


def _baseline_blob(root, baseline, rel):
    entries = _records(_git(root, "ls-tree", "-z", baseline, "--", rel))
    if not entries:
        return b""
    if len(entries) != 1 or not entries[0].startswith("100644 blob "):
        raise Unverified(f"Unsupported baseline bookkeeping file: {rel}.")
    return _git(root, "cat-file", "blob", baseline + ":" + rel)


def _generated(root, wave_md, baseline, rel):
    import gen_codebase_map as maps
    handoff = "docs/agents/session-handoff.md"
    if rel not in {handoff, maps.OUTPUT_REL_PATH, maps.REPO_INDEX_REL_PATH}:
        return False
    data, st = _file(root, rel)
    if data is None or st.st_mode & 0o111:
        return False
    current = data.decode().replace("\r\n", "\n")
    original = _baseline_blob(root, baseline, rel).decode().replace("\r\n", "\n")
    if rel == handoff:
        from wf_server.edit_gate_handlers import _update_handoff_wave_ref
        expected = _update_handoff_wave_ref(original, wave_md.parent.name)
        # Pause may have run on an earlier date. Only its canonical date line varies.
        date = re.search(r"(?m)^Last verified: (\d{4}-\d\d-\d\d)$", current)
        if date and datetime.date.fromisoformat(date[1]) <= datetime.date.today():
            expected = re.sub(r"(?m)^Last verified: \d{4}-\d\d-\d\d$", date[0], expected)
        return current == expected
    model = maps.compute_areas(root)
    if rel == maps.OUTPUT_REL_PATH:
        date = re.search(r"(?m)^Last verified: (\d{4}-\d\d-\d\d)$", current)
        return bool(date and current == maps.render_markdown(model, last_verified=date[1], root=root))
    begin, end = maps.REPO_INDEX_MARKER_BEGIN, maps.REPO_INDEX_MARKER_END
    before, marker, tail = original.partition(begin)
    _, closing, after = tail.partition(end)
    return bool(marker and closing and current == before + marker + maps._render_repo_index_modules(model) + closing + after)


def _check_special_files(root):
    """Git omits sockets, devices and FIFOs even from its untracked listing."""
    from reconcile_scan import _scan_directory
    ignored = {p.rstrip("/") for p in _records(_git(
        root, "ls-files", "--others", "--ignored", "--exclude-standard", "--directory", "-z"))}
    pending = [root]
    remaining = 200_000
    deadline = time.monotonic() + 10
    while pending:
        folder = pending.pop()
        with _scan_directory(root, folder) as entries:
            for entry in entries:
                remaining -= 1
                if remaining < 0 or time.monotonic() > deadline:
                    raise Unverified("The checkout exceeds the complete file verification limit.")
                rel = (folder / entry.name).relative_to(root).as_posix()
                if entry.name == ".git" or rel in ignored or entry.is_symlink():
                    continue
                if entry.is_dir(follow_symlinks=False):
                    if contained_files._is_windows_link(str(folder / entry.name)):
                        raise Unverified(f"Directory identity cannot be verified: {rel}.")
                    pending.append(folder / entry.name)
                elif not entry.is_file(follow_symlinks=False):
                    raise Unverified(f"Unsupported checkout file type: {rel}.")


def _scope(root, wave_md, selection, admission):
    from lifecycle_gate_support import _wave_change_doc_path, _plan_change_doc_path
    baseline = selection["baseline"]
    head = _head(root)
    if not _SHA.fullmatch(baseline):
        raise Unverified("The pinned admission commit is missing or malformed.")
    _git(root, "merge-base", "--is-ancestor", baseline, head)
    git_dir = Path(os.fsdecode(_git(root, "rev-parse", "--absolute-git-dir").rstrip(b"\n")))
    if any(os.path.lexists(git_dir / marker) for marker in
           ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply", "sequencer", "BISECT_LOG", "index.lock")):
        raise Unverified("Finish the unresolved Git operation before relying on a narrow review.")
    tracked = _records(_git(root, "ls-files", "-v", "-z"))
    if any(not line.startswith("H ") for line in tracked):
        raise Unverified("Git index flags or conflicts prevent verification of the complete worktree.")
    _check_special_files(root)
    paths = sorted(set(selection["paths"]))
    _regular_git_modes(root, baseline, paths)
    ignored = _records(_git(root, "check-ignore", "-z", "--stdin", allow=(0, 1),
                                data=b"".join(p.encode() + b"\0" for p in paths)))
    if ignored:
        raise Unverified(f"Git ignores a declared path: {ignored[0]}.")
    status = _records(_git(root, "status", "--porcelain=v1", "-z", "--no-renames", "--untracked-files=all", "--ignore-submodules=none"))
    changed = set(_records(_git(root, "diff", "--no-renames", "--ignore-submodules=none", "--name-only", "-z", baseline, head, "--")))
    seen = set()
    for entry in status:
        xy, rel = entry[:2], entry[3:]
        if len(entry) < 4 or entry[2] != " " or not rel:
            raise Unverified("Incomplete Git status evidence.")
        if (xy != "??" and xy.strip() not in {"M", "A", "D"}) or rel in seen:
            raise Unverified(f"Unexpected staged/worktree differences or file type at {rel}.")
        seen.add(rel)
        changed.add(rel)
    change_id = selection["change_id"]
    staged = _plan_change_doc_path(root, change_id)
    member = _wave_change_doc_path(root, wave_md, change_id)
    owned = {p.relative_to(root).as_posix() for p in
             (wave_md, wave_md.with_name(review_evidence.EVENTS_FILENAME), member, staged)}
    # The original staged spec may disappear when admission moves it. A new
    # copy in that slot after admission is an unrelated/ambiguous change.
    if not admission and os.path.lexists(staged):
        raise Unverified("The admitted spec also exists at its former staging path.")
    _regular_git_modes(root, baseline, sorted(owned))
    for rel in sorted(changed & owned):
        _file(root, rel)
    product = sorted(changed - owned)
    if not admission:
        product = [p for p in product if not _generated(root, wave_md, baseline, p)]
    if admission and (head != baseline or product):
        raise Unverified("Admission requires a clean product scope; changed paths: " + ", ".join(product[:4] or ["HEAD"]) + ".")
    extra = sorted(set(product) - set(paths))
    if extra:
        raise Unverified("Undeclared product paths require ordinary review: " + ", ".join(extra[:4]) + ".")
    proof = []
    observed_identities = []
    for rel in paths:
        raw, st = _file(root, rel)
        if raw is None:
            proof.append([rel, "absent"])
            observed_identities.append(None)
        else:
            proof.append([rel, "100755" if st.st_mode & stat.S_IXUSR else "100644",
                          len(raw), hashlib.sha256(raw).hexdigest(), _reviewed_file_id(st, rel)])
            observed_identities.append((st.st_dev, st.st_ino, st.st_size, st.st_mode, st.st_mtime_ns, st.st_ctime_ns))
    digest = hashlib.sha256(json.dumps(proof, ensure_ascii=True, separators=(",", ":")).encode()).hexdigest()
    return product, digest, observed_identities


def _result(reasons, paths=(), digest=None):
    return {"eligible": not reasons, "reasons": list(reasons), "changed_paths": list(paths), "content_digest": digest}


def assess(root: Path, wave_md: Path, selection: dict, member_ids, *, admission=False) -> dict:
    reasons = list(selection.get("admission_reasons", ()))
    if reasons:
        return _result(reasons)
    try:
        from lifecycle_gate_support import _wave_change_doc_path, _plan_change_doc_path
        # The server accepts aliases for the checkout root (e.g. /var on
        # macOS), while record discovery may already return its canonical path.
        if not wave_md.is_relative_to(root) and wave_md.is_relative_to(root.resolve()):
            root = root.resolve()
        wave_data, _ = _file(root, wave_md.relative_to(root).as_posix())
        wave_text = wave_data.decode()
        source, errors = review_evidence.parse_review_evidence_source(wave_text)
        if source != review_evidence.EVENTS_FILENAME or errors:
            raise Unverified("Small review requires a wave with declared typed review evidence.")
        if list(member_ids) != [selection["change_id"]] or EXPANDED in _header(wave_text).splitlines():
            raise Unverified("A small-change wave must have exactly its originally selected spec.")
        if admission:
            from lifecycle_gate_support import _read_workflow_config
            config = _read_workflow_config(root)
            lanes = set(review_policy.extract_requested_review_lanes(wave_text))
            for phase in ("prepare", "close"):
                lanes.update(review_policy.project_lanes_for_phase(config, phase))
            additional = sorted(lanes - {"code-reviewer"})
            if additional:
                raise Unverified("Additional specialist required: " + ", ".join(additional) + ".")
        paths = set(selection["paths"])
        if not 1 <= len(paths) <= 3:
            raise Unverified("Small review permits one to three distinct declared paths.")
        if len({unicodedata.normalize("NFC", p).casefold() for p in paths}) != len(paths):
            raise Unverified("Declared paths contain ambiguous aliases.")
        for p in sorted(paths):
            if reason := _path_reason(p):
                raise Unverified(reason)
        path = _wave_change_doc_path(root, wave_md, selection["change_id"])
        if admission and not os.path.lexists(path):
            path = _plan_change_doc_path(root, selection["change_id"])
        spec, _ = _file(root, path.relative_to(root).as_posix())
        if spec is None:
            raise Unverified("The spec describing the intended effect is missing.")
        effect = review_policy.normalized_review_text(spec) + "\n" + selection["intended_diff"]
        triggers = review_policy.extract_full_council_triggers([effect])
        match = _EFFECT.search(effect)
        if triggers or match:
            raise Unverified("The described effect requires ordinary review: " + ", ".join(triggers or [match.group()]) + ".")
        first = _scope(root, wave_md, selection, admission)
        if first != _scope(root, wave_md, selection, admission):
            raise Unverified("The Git scope or reviewed file identities, modes, or contents changed during verification.")
        return _result([], first[0], first[1])
    except Unverified as exc:
        return _result([str(exc)])
    except contained_files.ContainedFileRefused as exc:
        return _result([f"A selected or lifecycle file {exc.cause}; verify its path and type."])
    except (ValueError, UnicodeError, OSError, TypeError, KeyError, AttributeError, RuntimeError) as exc:
        return _result([f"Small-change evidence could not be verified ({type(exc).__name__}); use ordinary review."])


def admission_policy_reason(root, wave_text):
    """Legacy/prose or disabled policy cannot consume narrow typed receipts."""
    from lifecycle_gate_support import _read_workflow_config
    source, errors = review_evidence.parse_review_evidence_source(wave_text)
    if source != review_evidence.EVENTS_FILENAME or errors:
        return "This wave uses legacy or invalid review evidence; its ordinary review policy applies."
    config = _read_workflow_config(root)
    policy, errors = review_policy.normalize_wave_review_policy(config.get("wave_review"))
    if errors or not policy or not policy["enabled"]:
        return "This repository has no enabled typed review policy; its ordinary review policy applies."
    return None


def capture(root, wave_md, change_id, request, member_ids, *, policy_reason=None):
    validate_request(request)
    selection = {**request, "paths": sorted(set(request["paths"])), "change_id": change_id, "baseline": "", "admission_reasons": []}
    try:
        selection["baseline"] = _head(root)
    except (OSError, ValueError) as exc:
        selection["admission_reasons"] = [str(exc)]
    if policy_reason:
        selection["admission_reasons"].insert(0, policy_reason)
    result = assess(root, wave_md, selection, member_ids, admission=True)
    selection["admission_reasons"] = result["reasons"]
    return selection, result
