"""Discover CA bundles for clients using the framework scripts directory on sys.path."""
from __future__ import annotations

import os


# 1p7iu: TLS-inspecting corporate proxies put the root CA in the OS trust store but not in the venv's
# bundled certifi, so model downloads fail CERTIFICATE_VERIFY_FAILED while curl/system tools succeed.
# These are POSIX paths only — on native Windows this middle "platform" tier is effectively empty
# (the OS trust store is the registry cert store, not a PEM file). Windows corporate-proxy users
# therefore rely on the host-agent / operator env tiers (`CODEX_CA_CERTIFICATE` /
# `CLAUDE_CODE_CERT_STORE` / `NODE_EXTRA_CA_CERTS` / `SSL_CERT_FILE`, wave 1p7s6)
# and the certifi-default last resort.
_OS_CA_BUNDLE_CANDIDATES = (
    "/etc/ssl/certs/ca-certificates.crt",   # Debian/Ubuntu/WSL2
    "/etc/pki/tls/certs/ca-bundle.crt",     # RHEL/CentOS/Fedora
    "/etc/ssl/ca-bundle.pem",               # OpenSUSE
    "/etc/ssl/cert.pem",                    # Alpine / macOS LibreSSL
)


# Wave 1p7s6: host coding agents expose their OWN CA-bundle env vars for corporate-proxy / private-root-CA
# environments — when set, the host has already declared the authoritative bundle. Codex's
# CODEX_CA_CERTIFICATE explicitly "takes precedence over SSL_CERT_FILE", so host-agent vars go FIRST.
_HOST_AGENT_CA_ENV_VARS = ("CODEX_CA_CERTIFICATE", "CLAUDE_CODE_CERT_STORE", "NODE_EXTRA_CA_CERTS")
_GENERIC_CA_ENV_VARS = ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE")


def _certifi_default_bundle() -> "str | None":
    """The certifi default CA bundle path (the TLS baseline), or ``None`` if certifi is unavailable."""
    try:
        import certifi
        path = certifi.where()
    except Exception:  # noqa: BLE001
        return None
    return path if path and os.path.isfile(path) else None


def trust_bundle_candidates() -> list[str]:
    """Return existing bundle paths in setup order, retaining each path's first occurrence.

    Host-agent settings precede operator settings, platform paths and the optional
    certifi default. Discovery reads the current environment on each call.
    """
    candidates: list[str] = []
    seen: set[str] = set()

    def _add(path: "str | None") -> None:
        if path and os.path.isfile(path) and path not in seen:
            seen.add(path)
            candidates.append(path)

    for env in (*_HOST_AGENT_CA_ENV_VARS, *_GENERIC_CA_ENV_VARS):
        _add(os.environ.get(env))
    for path in _OS_CA_BUNDLE_CANDIDATES:
        _add(path)
    _add(_certifi_default_bundle())
    return candidates
