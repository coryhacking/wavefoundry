"""Setup-owned orchestration of the existing storage conversion protocol.

The installed checkout is the source. No archive selection, framework extraction
or authored-document upgrade is performed here.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import uuid

import sqlite_storage_migration as migration
import upgrade_lib
import storage_identity

MigrationRequired = migration.MigrationRequired
_TRANSIENT_DIRS = {"__pycache__", ".pytest_cache", "index"}
_TRANSIENT_FILES = {"MANIFEST", "test-cache.json", "test-run.lock", ".DS_Store"}
_PUBLISHER_ENV = "WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN"


def _receipt_fingerprint(receipt: dict) -> str:
    return hashlib.sha256(json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def framework_fingerprint(root: Path) -> str:
    """Hash installed behavior bytes, including names and VERSION, without Git."""
    framework = migration._safe(Path(root) / ".wavefoundry/framework")
    if not framework.is_dir():
        raise MigrationRequired("storage_setup_source_missing: installed framework is missing")
    digest = hashlib.sha256()
    for directory, dirs, files in os.walk(framework, followlinks=False):
        dirs[:] = sorted(name for name in dirs if name not in _TRANSIENT_DIRS)
        for name in dirs:
            migration._safe(Path(directory) / name)
        for name in sorted(files):
            if name in _TRANSIENT_FILES or name.endswith((".pyc", ".pyo")):
                continue
            path = migration._safe(Path(directory) / name)
            relative = path.relative_to(framework).as_posix().encode()
            content = path.read_bytes()
            digest.update(len(relative).to_bytes(8, "big") + relative)
            digest.update(len(content).to_bytes(8, "big") + content)
    return digest.hexdigest()


def validate_source_binding(root: Path, receipt: dict) -> None:
    """Completed receipts are history; unfinished setup work binds exact bytes."""
    if receipt.get("entry_path") != "setup" or receipt.get("state") == "complete":
        return
    expected = receipt.get("installed_framework_sha256")
    if not expected or framework_fingerprint(root) != expected:
        raise MigrationRequired(
            "storage_setup_source_changed: restore the recorded installed framework "
            "before rerunning wf setup; index, receipt and recovery sources are retained")


@contextmanager
def _environment(name: str, value: str | None):
    previous = os.environ.get(name)
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = previous


class session:
    """Hold setup ownership across provisioning, conversion and publication."""

    def __init__(self, root: Path, args: list[str]):
        self.root = Path(root).resolve()
        self.confirmed = "--confirm-hosts-stopped" in args
        self.rebuild = "--rebuild-storage" in args
        self.args = [arg for arg in args if arg not in
                     {"--confirm-hosts-stopped", "--rebuild-storage"}]
        import setup_index
        setup_index.parse_args(self.args)
        self.requires_index = False
        self._transaction = None
        self._completed = False
        self._published = False
        self._fingerprint = None

    def _inspect(self):
        receipt = migration.read_receipt(self.root / ".wavefoundry/index")
        checkpoint = upgrade_lib.read_upgrade_lock(self.root)
        if receipt and receipt["state"] != "complete":
            if receipt.get("entry_path") != "setup" or receipt.get("pack_path") or receipt.get("pack_sha256"):
                raise MigrationRequired("storage_setup_foreign_upgrade: resume the recorded upgrade; its receipt and archive remain authoritative")
            validate_source_binding(self.root, receipt)
        if checkpoint is not None:
            if (not isinstance(checkpoint, dict) or checkpoint.get("entry_path") != "setup"
                    or checkpoint.get("zip_path")):
                raise MigrationRequired("storage_setup_foreign_upgrade: finish the recorded upgrade before wf setup; checkpoint retained")
            if checkpoint.get("installed_framework_sha256") != framework_fingerprint(self.root):
                raise MigrationRequired("storage_setup_source_changed: restore the recorded framework before wf setup")
            if not storage_identity.compare_identity(checkpoint.get("root_identity"), migration._identity(self.root))["matches"]:
                raise MigrationRequired("storage_setup_checkpoint_mismatch: repository identity changed")
            if (receipt and checkpoint.get("storage_migration_id") != receipt["migration_id"]):
                # A crash can fall between writing the chained schema-8 fence
                # and checkpointing its new id. Only its embedded, completed
                # parent proves continuity; unrelated or missing ids refuse.
                parent = receipt.get("supersedes") or {}
                recorded_parent = checkpoint.get("setup_completed_parent") or {}
                observed_completed_parent = (
                    isinstance(parent, dict) and isinstance(recorded_parent, dict)
                    and recorded_parent.get("migration_id") == parent.get("migration_id")
                    and recorded_parent.get("receipt_sha256") == _receipt_fingerprint(parent))
                if (not isinstance(parent, dict) or parent.get("state") != "complete"
                        or parent.get("migration_id") != checkpoint.get("storage_migration_id")
                        or not parent.get("migration_id")
                        or (not observed_completed_parent and any(parent.get(key) != receipt.get(key) for key in
                               ("entry_path", "root_identity", "installed_framework_sha256", "index_dir")))):
                    raise MigrationRequired("storage_setup_checkpoint_mismatch: receipt and checkpoint retained")
        return receipt, checkpoint

    def __enter__(self):
        # Read first: foreign ownership refuses even before setup defaults/render.
        receipt, checkpoint = self._inspect()
        import lifecycle_lock
        # The durable checkpoint fences children. Do not hold the publication
        # OS lock across a child which must acquire it to finalize its epoch.
        self._transaction = lifecycle_lock.lifecycle_mutation_lock(self.root, strict=True)
        try:
            self._transaction.__enter__()
        except (lifecycle_lock.LifecycleLockBusy, lifecycle_lock.LifecycleLockUnavailable) as exc:
            self._transaction = None
            raise MigrationRequired(f"storage_setup_busy: {exc}") from exc
        publication = None
        try:
            import review_evidence
            pending_lock = review_evidence.project_state_publication_lock(self.root, wait=False)
            pending_lock.__enter__()
            publication = pending_lock
            receipt, checkpoint = self._inspect()
            state = migration.detect(self.root / ".wavefoundry/index")
            if state["authority_diagnostic"]:
                raise MigrationRequired(state["authority_diagnostic"] + ": preserve both databases")
            self._hosts = []
            if state["authority_role"] is None:
                self._hosts, _ = migration.discover_hosts(self.root)
            self.requires_index = bool(state["migration_required"] or self._hosts
                                       or (receipt and receipt["state"] != "complete") or checkpoint)
            if self.rebuild and not self.requires_index:
                raise MigrationRequired("storage_rebuild_not_applicable: no pending storage conversion")
            if self.requires_index:
                if any(arg in self.args for arg in {"--deps-only", "--prewarm-only"}):
                    raise MigrationRequired("storage_setup_publication_required: rerun ordinary wf setup to reconcile all layers")
                self._fingerprint = framework_fingerprint(self.root)
                version_file = self.root / ".wavefoundry/framework/VERSION"
                version = version_file.read_text().strip() if version_file.exists() else "installed"
                completed_parent = ({"setup_completed_parent": {
                    "migration_id": receipt["migration_id"], "receipt_sha256": _receipt_fingerprint(receipt)}}
                    if checkpoint is None and receipt and receipt["state"] == "complete" else {})
                if checkpoint is None:
                    upgrade_lib.write_upgrade_lock(self.root, version, version, runner_protocol=2)
                self._update(entry_path="setup", installed_framework_sha256=self._fingerprint,
                             root_identity=(checkpoint["root_identity"] if checkpoint is not None
                                            else receipt["root_identity"] if receipt else migration._identity(self.root)),
                             setup_args=self.args, pid=os.getpid(), current_phase="setup_storage",
                             failed_phase=None,
                             **completed_parent,
                             **({"storage_migration_id": receipt["migration_id"]} if receipt else {}))
                self._ctx = SimpleNamespace(root=self.root, zip_path=None, from_version=version,
                    to_version=version, dry_run=False, storage_migration_protocol=2,
                    storage_old_hosts=self._hosts, rebuild_storage=self.rebuild,
                    entry_path="setup", installed_framework_sha256=self._fingerprint,
                    setup_args=self.args)
            publication.__exit__(None, None, None)
            publication = None
            return self
        except BaseException:
            if publication is not None:
                publication.__exit__(*sys.exc_info())
            self._transaction.__exit__(*sys.exc_info())
            self._transaction = None
            raise

    def _update(self, **fields):
        if not upgrade_lib.update_upgrade_lock(self.root, **fields):
            raise MigrationRequired("storage_checkpoint_write_failed")

    def _validate(self):
        if self.requires_index and framework_fingerprint(self.root) != self._fingerprint:
            raise MigrationRequired("storage_setup_source_changed: installed source changed during setup; restore recorded source and retry")

    def prepare(self):
        if not self.requires_index:
            return
        self._validate()
        # A bootstrap interpreter may have been unable to probe an already
        # current database. Reclassify after canonical dependency provisioning.
        state = migration.detect(self.root / ".wavefoundry/index")
        pending = state["receipt"] and state["receipt"]["state"] != "complete"
        if not state["migration_required"] and not pending and not self._hosts:
            self._inspect()
            upgrade_lib.remove_upgrade_lock(self.root)
            self.requires_index = False
            return
        with _environment(migration.CONFIRM_ENV, "1" if self.confirmed else None):
            receipt = migration.prepare_upgrade(self._ctx)
        import setup_index
        state = migration.detect(self.root / ".wavefoundry/index")
        if not migration.rebuild_requested(receipt) and any(name in state["legacy"] for name in ("docs.lance", "code.lance")):
            setup_index.ensure_migration_deps(self.root)
        if migration.rebuild_requested(receipt):
            rc = setup_index.main([*self.args, "--prewarm-only"])
            if rc:
                raise MigrationRequired("storage_rebuild_models_unavailable: source and receipt retained")
        self._validate()
        migration.migrate_legacy(self.root)
        self._update(current_phase="setup_index")

    def index_args(self, args):
        if not self.requires_index:
            return list(args)
        result = [arg for arg in args if arg not in
                  {"--background-code", "--background-docs", "--docs-only", "--code-only", "--graph-only"}]
        receipt = migration.read_receipt(self.root / ".wavefoundry/index")
        if migration.rebuild_requested(receipt) and "--full" not in result:
            result.append("--full")
        return result

    @contextmanager
    def publication(self):
        # Setup owns a direct epoch CAS, never an inherited upgrade parent's
        # staged-finalization destination or publisher authorization.
        with _environment("WAVEFOUNDRY_UPGRADE_PARENT_FINALIZE_RECEIPT", None), _environment(_PUBLISHER_ENV, None):
            if not self.requires_index:
                yield
                return
            self._validate()
            migration.begin_upgrade_publication(self.root)
            token = uuid.uuid4().hex
            self._update(publisher_grant=token, current_phase="setup_index")
            with _environment(_PUBLISHER_ENV, token):
                yield
            self._published = True

    def complete(self):
        if not self.requires_index:
            self._completed = True
            return
        self._validate()
        if not self._published:
            raise MigrationRequired("storage_all_layer_publication_unverified: rerun wf setup")
        migration.record_upgrade_publication(self.root)
        import subprocess_util
        import venv_bootstrap
        venv_python = venv_bootstrap.tool_venv_python()
        python = str(venv_python) if venv_python.exists() else sys.executable
        result = subprocess_util.isolated_run(
            [python, str(self.root / ".wavefoundry/framework/scripts/sqlite_storage_migration.py"),
             "--verify", str(self.root)], cwd=str(self.root), check=False,
            capture_output=True, text=True)
        if result.returncode:
            raise MigrationRequired("storage_new_process_verification_failed: rerun wf setup; cleanup remains blocked. "
                                    + str(getattr(result, "stderr", "") or "").strip())
        self._validate()
        cleaned = migration.cleanup_legacy(self.root)
        if cleaned.get("state") != "complete":
            raise MigrationRequired("storage_cleanup_incomplete: rerun wf setup; checkpoint retained")
        self._inspect()
        upgrade_lib.remove_upgrade_lock(self.root)
        self._completed = True

    def __exit__(self, exc_type, exc, tb):
        try:
            if self.requires_index and not self._completed:
                checkpoint = upgrade_lib.read_upgrade_lock(self.root) or {}
                if checkpoint.get("entry_path") == "setup" and checkpoint.get("current_phase") != "storage_restart_required":
                    self._update(failed_phase=checkpoint.get("current_phase", "setup_storage"),
                                 failed_at=time.time(), setup_failure=str(exc or "setup did not complete"))
        finally:
            if self._transaction is not None:
                self._transaction.__exit__(exc_type, exc, tb)
        return False
