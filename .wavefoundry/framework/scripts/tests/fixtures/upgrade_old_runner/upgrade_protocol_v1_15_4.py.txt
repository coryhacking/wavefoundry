"""Versioned distribution/runner protocol metadata."""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Mapping

import subprocess_util


UPGRADE_PROTOCOL_VERSION = 2
MINIMUM_RUNNER_PROTOCOL = 2
PROTOCOL_METADATA_ARCNAME = ".wavefoundry/framework/UPGRADE-PROTOCOL.json"
PROTOCOL_METADATA_FILENAME = "UPGRADE-PROTOCOL.json"
SUPPORTED_RUNNER_PROTOCOLS = (1, 2)
MANDATORY_FEATURE_MODULES = (
    "upgrade_wavefoundry.py",
    "upgrade_extensions.py",
    "upgrade_protocol.py",
    "lifecycle_lock.py",
    "publication_control.py",
    "review_policy.py",
    "review_policy_reconcile.py",
    "review_policy_upgrade.py",
)


class UpgradeProtocolError(ValueError):
    code = "upgrade_protocol_invalid"


def build_protocol_metadata(
    *, release_version: str, build_id: str, artifact_type: str
) -> dict[str, Any]:
    if artifact_type not in {"feature", "bridge"}:
        raise UpgradeProtocolError("artifact_type must be feature or bridge")
    return {
        "schema_version": 1,
        "artifact_type": artifact_type,
        "release_version": release_version,
        "build_id": build_id,
        "upgrade_protocol_version": UPGRADE_PROTOCOL_VERSION,
        "minimum_runner_protocol": MINIMUM_RUNNER_PROTOCOL,
    }


def validate_protocol_metadata(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise UpgradeProtocolError("protocol metadata must be an object")
    required = {
        "schema_version", "artifact_type", "release_version", "build_id",
        "upgrade_protocol_version", "minimum_runner_protocol",
    }
    if set(value) != required:
        raise UpgradeProtocolError(
            "protocol metadata fields must be exactly: " + ", ".join(sorted(required))
        )
    for field in ("schema_version", "upgrade_protocol_version", "minimum_runner_protocol"):
        item = value.get(field)
        if not isinstance(item, int) or isinstance(item, bool) or item <= 0:
            raise UpgradeProtocolError(f"{field} must be a positive integer")
    if value["schema_version"] != 1:
        raise UpgradeProtocolError("unsupported protocol metadata schema")
    if value["artifact_type"] not in {"feature", "bridge"}:
        raise UpgradeProtocolError("unknown artifact_type")
    for field in ("release_version", "build_id"):
        if not isinstance(value.get(field), str) or not str(value[field]).strip():
            raise UpgradeProtocolError(f"{field} must be a non-empty string")
    protocol = value["upgrade_protocol_version"]
    minimum = value["minimum_runner_protocol"]
    if protocol != UPGRADE_PROTOCOL_VERSION or minimum != MINIMUM_RUNNER_PROTOCOL:
        raise UpgradeProtocolError("unsupported or decreasing upgrade protocol metadata")
    return dict(value)


def read_pack_protocol(path: Path) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(path, "r") as archive:
            raw = archive.read(PROTOCOL_METADATA_ARCNAME)
    except (OSError, KeyError, zipfile.BadZipFile) as exc:
        raise UpgradeProtocolError(f"pack protocol metadata is unavailable: {exc}") from exc
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise UpgradeProtocolError(f"pack protocol metadata is malformed: {exc}") from exc
    return validate_protocol_metadata(value)


def _pack_module_names(names: set[str]) -> set[str]:
    prefix = ".wavefoundry/framework/scripts/"
    return {
        Path(name).stem
        for name in names
        if name.startswith(prefix) and name.endswith(".py") and "/" not in name[len(prefix):]
    }


def _validate_imports(tree: ast.AST, module_name: str, available: set[str]) -> None:
    for node in ast.walk(tree):
        imported: list[str] = []
        if isinstance(node, ast.Import):
            imported = [alias.name.split(".", 1)[0] for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imported = [node.module.split(".", 1)[0]]
        for name in imported:
            if name not in available and name not in sys.stdlib_module_names:
                raise UpgradeProtocolError(
                    f"mandatory module {module_name} has unavailable import {name}"
                )


def _assigned_integer(tree: ast.AST, name: str) -> int | None:
    for node in getattr(tree, "body", []):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id == name:
            if isinstance(node.value, ast.Constant) and type(node.value.value) is int:
                return node.value.value
    return None


def _validate_mandatory_imports_in_subprocess(
    archive: zipfile.ZipFile, names: set[str]
) -> None:
    """Import the mandatory pack modules in an isolated child before extraction."""

    prefix = ".wavefoundry/framework/scripts/"
    with tempfile.TemporaryDirectory(prefix="wf-pack-import-") as temporary:
        scripts = Path(temporary) / "scripts"
        scripts.mkdir()
        for name in names:
            if not name.startswith(prefix) or not name.endswith(".py"):
                continue
            relative = Path(name.removeprefix(prefix))
            if relative.is_absolute() or ".." in relative.parts:
                raise UpgradeProtocolError("mandatory module path escapes the pack")
            destination = scripts / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(archive.read(name))
        modules = [Path(filename).stem for filename in MANDATORY_FEATURE_MODULES]
        probe = (
            "import importlib, json, pathlib, sys\n"
            "sys.path.insert(0, sys.argv[1])\n"
            "mods = [importlib.import_module(name) for name in json.loads(sys.argv[2])]\n"
            "protocol = importlib.import_module('upgrade_protocol')\n"
            "assert protocol.UPGRADE_PROTOCOL_VERSION == 2\n"
            "assert protocol.MINIMUM_RUNNER_PROTOCOL == 2\n"
        )
        kwargs: dict[str, Any] = {}
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        try:
            child_env = {
                key: value
                for key, value in os.environ.items()
                if key.upper() in {
                    "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "TMPDIR",
                }
            }
            child_env.update(
                {"PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}
            )
            interpreter = subprocess_util.windowless_pythonw() or sys.executable
            completed = subprocess.run(
                [interpreter, "-I", "-B", "-c", probe, str(scripts), json.dumps(modules)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=20,
                check=False,
                cwd=temporary,
                env=child_env,
                **kwargs,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise UpgradeProtocolError(
                f"mandatory protocol modules could not be imported in isolation: {exc}"
            ) from exc
        if completed.returncode != 0:
            detail = completed.stderr.strip().splitlines()[-1:] or ["unknown import failure"]
            raise UpgradeProtocolError(
                "mandatory protocol modules are not importable: " + detail[0][:500]
            )


def validate_feature_pack(path: Path) -> dict[str, Any]:
    """Validate protocol-2 code required before the feature can be extracted.

    Every non-stdlib top-level import used by a mandatory module must be
    supplied by the same archive. The mandatory modules are then imported by
    an isolated child interpreter before any feature extraction occurs.
    """

    metadata = read_pack_protocol(path)
    if metadata.get("artifact_type") != "feature":
        raise UpgradeProtocolError("Upgrade requires a feature pack, not a bridge pack")
    prefix = ".wavefoundry/framework/scripts/"
    try:
        with zipfile.ZipFile(path, "r") as archive:
            names = set(archive.namelist())
            available = _pack_module_names(names)
            trees: dict[str, ast.AST] = {}
            for filename in MANDATORY_FEATURE_MODULES:
                arcname = prefix + filename
                if arcname not in names:
                    raise UpgradeProtocolError(
                        f"mandatory protocol module is missing: {filename}"
                    )
                try:
                    source = archive.read(arcname).decode("utf-8")
                    trees[filename] = ast.parse(source, filename=arcname)
                except (UnicodeError, SyntaxError) as exc:
                    raise UpgradeProtocolError(
                        f"mandatory protocol module is not importable: {filename}: {exc}"
                    ) from exc
            for filename, tree in trees.items():
                _validate_imports(tree, filename, available)
            protocol_tree = trees["upgrade_protocol.py"]
            if (
                _assigned_integer(protocol_tree, "UPGRADE_PROTOCOL_VERSION")
                != UPGRADE_PROTOCOL_VERSION
                or _assigned_integer(protocol_tree, "MINIMUM_RUNNER_PROTOCOL")
                != MINIMUM_RUNNER_PROTOCOL
            ):
                raise UpgradeProtocolError(
                    "mandatory upgrade_protocol declarations do not match protocol 2"
                )
            extension = trees["upgrade_extensions.py"]
            functions = {
                node.name for node in extension.body if isinstance(node, ast.FunctionDef)
            }
            if "post_preflight" not in functions:
                raise UpgradeProtocolError(
                    "mandatory upgrade extension lacks the protocol refusal hook"
                )
            extension_source = archive.read(prefix + "upgrade_extensions.py").decode("utf-8")
            if "bridge_release_required" not in extension_source:
                raise UpgradeProtocolError(
                    "mandatory upgrade extension lacks bridge_release_required"
                )
            _validate_mandatory_imports_in_subprocess(archive, names)
    except (OSError, zipfile.BadZipFile) as exc:
        raise UpgradeProtocolError(f"feature pack code is unavailable: {exc}") from exc
    return metadata


def runner_compatibility(runner_protocol: int, metadata: Mapping[str, Any]) -> str:
    if not isinstance(runner_protocol, int) or isinstance(runner_protocol, bool):
        raise UpgradeProtocolError("runner protocol must be an integer")
    if runner_protocol not in SUPPORTED_RUNNER_PROTOCOLS:
        raise UpgradeProtocolError("unknown or unsupported runner protocol")
    validated = validate_protocol_metadata(metadata)
    minimum = int(validated["minimum_runner_protocol"])
    if runner_protocol < minimum:
        return "legacy_optional_extension"
    if runner_protocol == UPGRADE_PROTOCOL_VERSION:
        return "compatible"
    raise UpgradeProtocolError("unknown or unsupported runner protocol")


__all__ = [
    "MINIMUM_RUNNER_PROTOCOL", "PROTOCOL_METADATA_ARCNAME",
    "PROTOCOL_METADATA_FILENAME", "SUPPORTED_RUNNER_PROTOCOLS",
    "UPGRADE_PROTOCOL_VERSION", "UpgradeProtocolError", "build_protocol_metadata",
    "MANDATORY_FEATURE_MODULES", "read_pack_protocol", "runner_compatibility",
    "validate_feature_pack", "validate_protocol_metadata",
]
