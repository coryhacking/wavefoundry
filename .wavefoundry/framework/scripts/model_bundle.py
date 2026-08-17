"""Build and safely materialize the optional offline Wavefoundry model bundle.

The bundle contains only declared Hugging Face cache *snapshots*.  Snapshot
links are dereferenced while building and never accepted from an incoming ZIP;
the target cache therefore remains usable on hosts where links are unavailable.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path
from typing import Any

BUNDLE_SCHEMA = 1
BUNDLE_PREFIX = "wavefoundry-models-"
MODEL_SET_VERSION = "3"
# Wave 1vglb (1vgla): set 3 corrects ONE reference byte in set 2 (a trailing newline
# in a ``refs/main`` member) and changes no model weight, so the embedding identity
# is deliberately unchanged: every set-2 index stays valid and nothing re-embeds.
# Bump this fingerprint only when weights, pooling, or precision change.
EMBEDDING_COMPATIBILITY_FINGERPRINT = "wf-model-set-2-20260811-arctic-s"
_HOME = Path("~/.wavefoundry").expanduser()
_FASTEMBED_DEFAULT = _HOME / "cache" / "fastembed"
_ONNX_DEFAULT = _HOME / "cache" / "onnx-src"
_MANIFEST_NAME = "model-bundle-manifest.json"
_MARKER_NAME = ".wavefoundry-model-bundle.json"
_VERIFICATION_MANIFEST_NAME = "model-set-verification-manifest.json"

# Cache directory names are deliberately exact.  Updating a model requires a
# new policy/version, provenance review, and an index compatibility decision.
COMPONENTS = (
    ("embedding-fastembed", "fastembed", "models--snowflake--snowflake-arctic-embed-s", "Apache-2.0", "Snowflake/snowflake-arctic-embed-s"),
    ("embedding-clean-onnx", "onnx-src", "models--Snowflake--snowflake-arctic-embed-s", "Apache-2.0", "Snowflake/snowflake-arctic-embed-s"),
    ("reranker-clean-onnx", "onnx-src", "models--Xenova--ms-marco-MiniLM-L-6-v2", "Apache-2.0", "Xenova/ms-marco-MiniLM-L-6-v2"),
)
_LICENSE_TEXT = {
    "MIT": "MIT License\n\nPermission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the \"Software\"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, subject to the following conditions: The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.\n\nTHE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND.\n",
}
APPROVED_LICENSES = frozenset({"Apache-2.0", "MIT"})


def _license_text(license_id: str) -> str:
    if license_id == "Apache-2.0":
        license_path = Path(__file__).resolve().parents[3] / "LICENSE"
        text = license_path.read_text(encoding="utf-8")
        if "Apache License" not in text:
            raise RuntimeError("canonical Apache-2.0 license text is unavailable")
        return text
    return _LICENSE_TEXT[license_id]

def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()



def _is_ref_member(relative: str) -> bool:
    """True for a huggingface_hub symbolic-revision file (``refs/<name>``)."""
    parts = Path(relative).parts
    return len(parts) == 2 and parts[0] == "refs"


def _normalized_ref_bytes(data: bytes) -> bytes:
    """Canonical bytes for a ``refs/<name>`` member: the bare revision, no trailing newline.

    Wave 1vglb (1vgla): huggingface_hub resolves a symbolic revision by reading
    ``refs/main`` VERBATIM and matching it against snapshot directory names, so a
    trailing newline (``<sha>\n``, 41 bytes) never matches the 40-char directory and
    every ``local_files_only=True`` lookup misses. Model set 2 shipped exactly that
    for one component and its manifest pinned the defective byte-shape, which made
    the asset unrebuildable once the miss triggered an unpinned re-download. Every
    place that reads a ref for packing, hashing, or writing normalizes through here
    so build, manifest, and install agree on the 40-byte form regardless of what a
    local cache holds.
    """
    return data.strip()


def _normalize_refs_in_place(destination: Path) -> list[tuple[Path, bytes]]:
    """Rewrite any ``refs/*`` under a component whose raw bytes are not the normalized form.

    Returns ``(path, original_bytes)`` for every file rewritten so callers can roll back.
    Wave 1vglb (F-1vglb-03): a legacy set-2 cache carries one 41-byte ref; every path that
    asserts the cache IS the declared set (attest, the already-installed skip in materialize)
    normalizes the bytes too, so the defect cannot outlive the first setup or upgrade even
    when the set-3 asset is not in reach.
    """
    changed: list[tuple[Path, bytes]] = []
    refs = destination / "refs"
    if not refs.is_dir():
        return changed
    for ref in sorted(refs.iterdir()):
        if not ref.is_file():
            continue
        raw = ref.read_bytes()
        normalized = _normalized_ref_bytes(raw)
        if raw != normalized:
            ref.write_bytes(normalized)
            changed.append((ref, raw))
    return changed


def _cache_member_sha256(candidate: Path, relative: str) -> str:
    """sha256 of an on-disk cache file as the manifest describes it (refs normalized).

    Non-ref members (the weights) stream through ``_file_sha256`` so status, attest,
    and install never hold a whole model file in memory; only the tiny ref is read whole.
    """
    if _is_ref_member(relative):
        return _sha256(_cache_member_bytes(candidate, relative))
    return _file_sha256(candidate)


def _cache_member_bytes(candidate: Path, relative: str) -> bytes:
    """Read a cache file for packing/hashing, normalizing ``refs/*`` members."""
    data = candidate.read_bytes()  # dereference only trusted local cache links
    return _normalized_ref_bytes(data) if _is_ref_member(relative) else data

def _version_key(value: object) -> tuple[int, ...]:
    """Parse the deliberately small dotted-integer model-set version contract."""
    if not isinstance(value, str) or not value or any(not part.isdigit() for part in value.split(".")):
        raise RuntimeError("model bundle has an invalid model-set version")
    return tuple(int(part) for part in value.split("."))

def _target_root(target: str) -> Path:
    if target == "fastembed":
        return Path(os.getenv("FASTEMBED_CACHE_PATH") or str(_FASTEMBED_DEFAULT))
    if target == "onnx-src":
        return Path(os.getenv("WAVEFOUNDRY_ONNX_SRC_CACHE") or str(_ONNX_DEFAULT))
    raise ValueError(f"unsupported model-bundle target: {target}")

def bundle_name(model_set_version: str = MODEL_SET_VERSION) -> str:
    """Return the independently versioned public model-set asset name."""
    _version_key(model_set_version)
    return f"{BUNDLE_PREFIX}{model_set_version}.zip"


def manual_recovery_guidance(model_set_version: str = MODEL_SET_VERSION) -> str:
    """Return the operator recovery path when an online model warm cannot complete."""
    asset = bundle_name(model_set_version)
    return (
        f"To recover without a model download, manually download '{asset}' from the same Wavefoundry release "
        "(or an approved internal distribution), leave it zipped, and place it in the target repository root, "
        "~/, ~/.wavefoundry/, ~/.wavefoundry/dist/, or ~/Downloads/. Then rerun 'wf setup'. Setup validates the "
        "model set, component hashes, and licenses before replacing the cache; an invalid bundle leaves the verified "
        "cache unchanged."
    )


def find_local_bundle(search_dirs: tuple[Path, ...], model_set_version: str = MODEL_SET_VERSION) -> Path | None:
    """Find the exact model-set asset in ordered, operator-controlled locations."""
    name = bundle_name(model_set_version)
    seen: set[Path] = set()
    for directory in search_dirs:
        directory = directory.expanduser()
        if directory in seen:
            continue
        seen.add(directory)
        candidate = directory / name
        if candidate.is_file():
            return candidate
    return None


def canonical_verification_manifest_path() -> Path:
    """Return the installed framework-root verification authority."""
    return Path(__file__).resolve().parent.parent / _VERIFICATION_MANIFEST_NAME


def _manifest_from_cache(root: Path) -> dict[str, Any]:
    """Describe the complete declared cache set (used to verify a companion build)."""
    components: list[dict[str, Any]] = []
    for component_id, target, directory, license_id, upstream in COMPONENTS:
        source = root / target / directory
        snapshots, refs = source / "snapshots", source / "refs"
        if not snapshots.is_dir() or not refs.is_dir():
            raise RuntimeError(f"required warmed model cache is missing: {source}")
        files: list[dict[str, str]] = []
        for candidate in sorted([*refs.rglob("*"), *snapshots.rglob("*")]):
            if not candidate.is_file():
                continue
            relative = candidate.relative_to(source).as_posix()
            if relative.startswith("/") or ".." in Path(relative).parts:
                raise RuntimeError(f"unsafe cache path: {candidate}")
            files.append({"path": f"models/{target}/{directory}/{relative}", "sha256": _sha256(_cache_member_bytes(candidate, relative))})
        if not files:
            raise RuntimeError(f"required warmed model cache is empty: {source}")
        components.append({"id": component_id, "target": target, "directory": directory,
                           "upstream": upstream, "revision": (refs / "main").read_text(encoding="utf-8").strip(),
                           "license": license_id, "attribution": f"Model artifact from {upstream}.",
                           "redistribution_decision": "approved-direct-distribution", "files": files})
    return {"schema_version": BUNDLE_SCHEMA, "model_set_version": MODEL_SET_VERSION,
            "embedding_compatibility_fingerprint": EMBEDDING_COMPATIBILITY_FINGERPRINT,
            "components": components}


def load_canonical_verification_manifest(manifest_path: Path | None = None) -> dict[str, Any]:
    """Load and validate the checked-in, release-pinned model-set authority."""
    source = manifest_path or canonical_verification_manifest_path()
    manifest = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise RuntimeError("canonical model verification manifest is invalid")
    _validate_manifest_contract(manifest)
    return manifest


def build_bundle(
    output_dir: Path,
    *,
    cache_root: Path | None = None,
) -> Path:
    """Create an independently versioned model-set archive from a warmed cache."""
    root = cache_root.expanduser() if cache_root else _HOME / "cache"
    canonical_manifest = load_canonical_verification_manifest()
    built_manifest = _manifest_from_cache(root)
    if built_manifest != canonical_manifest:
        raise RuntimeError("warmed model cache does not match the canonical verification manifest")
    payload: list[tuple[str, bytes]] = []
    for component_id, target, directory, license_id, upstream in COMPONENTS:
        source = root / target / directory
        snapshots = source / "snapshots"
        refs = source / "refs"
        if not snapshots.is_dir() or not refs.is_dir():
            raise RuntimeError(f"required warmed model cache is missing: {source}")
        for candidate in sorted([*refs.rglob("*"), *snapshots.rglob("*")]):
            if not candidate.is_file():
                continue
            relative = candidate.relative_to(source).as_posix()
            if relative.startswith("/") or ".." in Path(relative).parts:
                raise RuntimeError(f"unsafe cache path: {candidate}")
            data = _cache_member_bytes(candidate, relative)
            arc = f"models/{target}/{directory}/{relative}"
            payload.append((arc, data))
    out = output_dir / bundle_name()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(_MANIFEST_NAME, json.dumps(canonical_manifest, sort_keys=True, indent=2) + "\n")
        for license_id in ("Apache-2.0", "MIT"):
            archive.writestr(f"THIRD_PARTY_LICENSES/{license_id}.txt", _license_text(license_id))
        for arc, data in payload:
            archive.writestr(arc, data)
    return out

def _safe_member(name: str, info: zipfile.ZipInfo) -> bool:
    return (not name.startswith("/") and ".." not in Path(name).parts
            and not (info.external_attr >> 16 & stat.S_IFLNK))

def _component_file_map(component: dict[str, Any]) -> dict[str, str]:
    target, directory = component["target"], component["directory"]
    prefix = f"models/{target}/{directory}/"
    file_map: dict[str, str] = {}
    for item in component["files"]:
        path, digest = item.get("path"), item.get("sha256")
        if not isinstance(path, str) or not path.startswith(prefix) or not isinstance(digest, str):
            raise RuntimeError("model bundle manifest has an invalid file entry")
        relative = path[len(prefix):]
        if not relative or ".." in Path(relative).parts:
            raise RuntimeError("model bundle manifest has an unsafe file entry")
        if relative in file_map:
            raise RuntimeError("model bundle manifest has duplicate file entries")
        file_map[relative] = digest
    if not file_map:
        raise RuntimeError("model bundle component has no declared files")
    return file_map


def _validate_manifest_contract(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate the shared model-set identity contract without requiring payload bytes."""
    if manifest.get("schema_version") != BUNDLE_SCHEMA:
        raise RuntimeError("unsupported model bundle schema")
    _version_key(manifest.get("model_set_version"))
    if manifest.get("embedding_compatibility_fingerprint") != EMBEDDING_COMPATIBILITY_FINGERPRINT:
        raise RuntimeError("model bundle does not match the installed model compatibility policy")
    expected_components = {(item[0], item[1], item[2], item[3], item[4]) for item in COMPONENTS}
    declared_components: set[tuple[str, str, str, str, str]] = set()
    components = manifest.get("components")
    if not isinstance(components, list):
        raise RuntimeError("model bundle has no component list")
    for component in components:
        if not isinstance(component, dict):
            raise RuntimeError("model bundle has an invalid component")
        identity = tuple(component.get(key) for key in ("id", "target", "directory", "license", "upstream"))
        if identity not in expected_components:
            raise RuntimeError("model bundle declares an unsupported component")
        if identity in declared_components:
            raise RuntimeError("model bundle declares a duplicate component")
        declared_components.add(identity)
        if component.get("redistribution_decision") != "approved-direct-distribution" or not component.get("attribution"):
            raise RuntimeError("model bundle component lacks redistribution provenance")
        if not isinstance(component.get("revision"), str) or not component["revision"].strip():
            raise RuntimeError("model bundle component lacks an upstream revision")
        file_map = _component_file_map(component)
        if "refs/main" not in file_map:
            raise RuntimeError("model bundle component lacks its main revision reference")
    if declared_components != expected_components:
        raise RuntimeError("model bundle component set is incomplete")
    return components


def _cached_component_file_map(destination: Path) -> dict[str, str] | None:
    """Hash the snapshot and ref files that define a cache component identity."""
    files: dict[str, str] = {}
    for root_name in ("refs", "snapshots"):
        root = destination / root_name
        if not root.is_dir():
            return None
        for candidate in sorted(root.rglob("*")):
            if candidate.is_file():
                relative = candidate.relative_to(destination).as_posix()
                files[relative] = _cache_member_sha256(candidate, relative)
    return files


def attest_online_cache(manifest_path: Path | None = None) -> bool:
    """Mark a fully verified, normally downloaded cache as the declared model set.

    Missing, unreadable, or mismatched verification data is deliberately a
    non-fatal no-op: online setup retains its existing acquisition behavior and
    only complete release-identical caches receive markers.
    """
    try:
        manifest = load_canonical_verification_manifest(manifest_path)
        components = manifest["components"]
    except (OSError, ValueError, RuntimeError):
        return False

    incoming_version = _version_key(manifest["model_set_version"])
    pending: list[tuple[Path, dict[str, Any]]] = []
    for component in components:
        destination = _target_root(component["target"]) / component["directory"]
        files = _component_file_map(component)
        if _cached_component_file_map(destination) != files:
            return False
        try:
            if (destination / "refs" / "main").read_text(encoding="utf-8").strip() != component["revision"].strip():
                return False
        except OSError:
            return False
        expected = {
            "model_set_version": manifest["model_set_version"],
            "fingerprint": manifest["embedding_compatibility_fingerprint"],
            "files": files,
        }
        marker = destination / _MARKER_NAME
        installed = _verified_marker(destination, marker) if marker.is_file() else None
        if installed is not None:
            installed_version = _version_key(installed["model_set_version"])
            if installed_version > incoming_version:
                return False
            if installed_version == incoming_version and installed != expected:
                return False
        pending.append((marker, expected))

    written: list[tuple[Path, bytes | None]] = []
    try:
        for marker, expected in pending:
            written.extend(_normalize_refs_in_place(marker.parent))
            if marker.is_file() and _verified_marker(marker.parent, marker) == expected:
                continue
            original = marker.read_bytes() if marker.exists() else None
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=marker.parent,
                prefix=f".{_MARKER_NAME}.",
                delete=False,
            ) as staged:
                staged.write(json.dumps(expected, sort_keys=True) + "\n")
                staged_path = Path(staged.name)
            staged_path.replace(marker)
            written.append((marker, original))
    except OSError:
        for marker, original in reversed(written):
            try:
                if original is None:
                    marker.unlink(missing_ok=True)
                else:
                    marker.write_bytes(original)
            except OSError:
                pass
        return False
    return True


def _verified_marker(destination: Path, marker: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(marker.read_text(encoding="utf-8"))
        files = value.get("files")
        if not isinstance(files, dict) or not files:
            return None
        for relative, digest in files.items():
            if not isinstance(relative, str) or not isinstance(digest, str):
                return None
            candidate = destination / relative
            if not candidate.is_file():
                return None
            if _cache_member_sha256(candidate, relative) != digest:
                # Markers written before wave 1vglb pinned a ref's VERBATIM digest (model set 2
                # shipped one 41-byte ref); accept that legacy shape so an installed set 2 reads
                # as an older managed set, not as a mixed cache, until set 3 replaces it.
                if not (_is_ref_member(relative) and _file_sha256(candidate) == digest):
                    return None
        _version_key(value.get("model_set_version"))
        if not isinstance(value.get("fingerprint"), str):
            return None
        return value
    except (OSError, ValueError, RuntimeError):
        return None


def local_model_set_status() -> str:
    """Classify the installed managed model set without changing an upstream cache."""
    statuses: list[str] = []
    expected_version = _version_key(MODEL_SET_VERSION)
    for _component_id, target, directory, _license_id, _upstream in COMPONENTS:
        destination = _target_root(target) / directory
        marker = _verified_marker(destination, destination / _MARKER_NAME)
        if marker is None:
            statuses.append("unmanaged")
            continue
        installed_version = _version_key(marker["model_set_version"])
        if installed_version < expected_version:
            statuses.append("older")
        elif installed_version > expected_version:
            statuses.append("newer")
        elif marker["fingerprint"] != EMBEDDING_COMPATIBILITY_FINGERPRINT:
            statuses.append("incompatible")
        else:
            statuses.append("current")
    return statuses[0] if len(set(statuses)) == 1 else "mixed"


def _validate_manifest(manifest: dict[str, Any], infos: dict[str, zipfile.ZipInfo]) -> list[dict[str, Any]]:
    components = _validate_manifest_contract(manifest)
    expected_components = {(item[0], item[1], item[2], item[3], item[4]) for item in COMPONENTS}
    declared: dict[str, str] = {}
    for component in components:
        file_map = _component_file_map(component)
        declared.update({f"models/{component['target']}/{component['directory']}/{relative}": digest
                         for relative, digest in file_map.items()})
    for license_id in {component[3] for component in expected_components}:
        if f"THIRD_PARTY_LICENSES/{license_id}.txt" not in infos:
            raise RuntimeError("model bundle lacks a required license notice")
    actual = {name for name in infos if name.startswith("models/")}
    if actual != set(declared):
        raise RuntimeError("model bundle payload differs from its manifest")
    return components


def materialize_bundle(
    bundle: Path,
    *,
    expected_model_set_version: str | None = None,
) -> dict[str, Any]:
    """Validate a bundle and atomically publish its declared cache directories."""
    with zipfile.ZipFile(bundle) as archive:
        members = archive.infolist()
        infos = {item.filename: item for item in members}
        if len(infos) != len(members) or _MANIFEST_NAME not in infos or any(not _safe_member(name, info) for name, info in infos.items()):
            raise RuntimeError("model bundle contains a missing manifest, unsafe path, or link")
        manifest = json.loads(archive.read(_MANIFEST_NAME))
        if expected_model_set_version and manifest.get("model_set_version") != expected_model_set_version:
            raise RuntimeError("model bundle does not match the selected model set")
        canonical = load_canonical_verification_manifest()
        if manifest != canonical:
            raise RuntimeError("model bundle manifest does not match the installed canonical model set")
        components = _validate_manifest(manifest, infos)
        for component in components:
            for relative, digest in _component_file_map(component).items():
                name = f"models/{component['target']}/{component['directory']}/{relative}"
                if _sha256(archive.read(name)) != digest:
                    raise RuntimeError(f"model bundle hash mismatch: {name}")
            revision_name = f"models/{component['target']}/{component['directory']}/refs/main"
            if archive.read(revision_name).decode("utf-8").strip() != component["revision"].strip():
                raise RuntimeError("model bundle revision does not match its cache reference")
        pending: list[tuple[dict[str, Any], Path, Path, Path]] = []
        for component in components:
            target = _target_root(component["target"])
            destination = target / component["directory"]
            marker = destination / _MARKER_NAME
            files = _component_file_map(component)
            expected = {"model_set_version": manifest["model_set_version"], "fingerprint": manifest["embedding_compatibility_fingerprint"], "files": files}
            installed = _verified_marker(destination, marker) if marker.is_file() else None
            if installed is not None:
                installed_version = _version_key(installed["model_set_version"])
                incoming_version = _version_key(manifest["model_set_version"])
                if installed_version > incoming_version:
                    continue
                if installed_version == incoming_version:
                    if installed["fingerprint"] != expected["fingerprint"]:
                        raise RuntimeError("model bundle conflicts with the installed model-set identity")
                    if installed["files"] == files:
                        _normalize_refs_in_place(destination)
                        continue
            target.mkdir(parents=True, exist_ok=True)
            staging_parent = Path(tempfile.mkdtemp(prefix=".wf-model-", dir=target))
            staging = staging_parent / component["directory"]
            for item in component["files"]:
                path = item["path"]
                rel = Path(path).relative_to("models") / ""
                # Strip models/<target>/<directory>/ from archive path.
                rel = Path(*rel.parts[2:])
                output = staging / rel
                output.parent.mkdir(parents=True, exist_ok=True)
                payload = archive.read(path)
                # Wave 1vglb: install-side normalization is defensive and independent
                # of build-side normalization. A set-3 asset already packs the 40-byte
                # form (the manifest gates above pin it), so this only matters if a
                # future canonical manifest ever pinned a non-normalized ref again.
                if _is_ref_member(rel.as_posix()):
                    payload = _normalized_ref_bytes(payload)
                output.write_bytes(payload)
            (staging / _MARKER_NAME).write_text(json.dumps(expected, sort_keys=True) + "\n", encoding="utf-8")
            pending.append((component, destination, staging_parent, staging))

        published: list[tuple[Path, Path, Path]] = []
        try:
            for _component, destination, staging_parent, staging in pending:
                backup = destination.with_name(destination.name + ".wf-replaced")
                if backup.exists():
                    shutil.rmtree(backup)
                if destination.exists():
                    destination.replace(backup)
                try:
                    staging.replace(destination)
                except Exception:
                    if backup.exists() and not destination.exists():
                        backup.replace(destination)
                    raise
                published.append((destination, backup, staging_parent))
        except Exception:
            for destination, backup, _staging_parent in reversed(published):
                try:
                    if destination.exists():
                        shutil.rmtree(destination)
                    if backup.exists():
                        backup.replace(destination)
                except OSError:
                    pass
            raise
        finally:
            for _component, _destination, staging_parent, _staging in pending:
                shutil.rmtree(staging_parent, ignore_errors=True)

        for _destination, backup, _staging_parent in published:
            shutil.rmtree(backup, ignore_errors=True)
    return {"model_set_version": manifest["model_set_version"], "published_components": len(published),
            "embedding_compatibility_fingerprint": manifest["embedding_compatibility_fingerprint"]}
