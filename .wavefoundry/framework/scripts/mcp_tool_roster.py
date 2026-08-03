#!/usr/bin/env python3
"""Canonical MCP tool roster with permission tiers (wave 1u2b0 / 1u2az).

Single stdlib-only source of truth for the wavefoundry MCP tool surface as a
*permission* concern: every first-party tool name plus a dedicated permission
tier. Consumed by:

* ``render_platform_surfaces.render_claude_permissions``, which derives the
  provenance-tracked ``permissions.allow`` allowlist rendered into the
  committed ``.claude/settings.json`` on the upgrade/install path only.
* ``server_impl.register_mcp_surface``, a fail-safe registration parity check
  (warns on stderr when the registered surface and this roster drift; the
  hard gate is the AST parity test in
  ``tests/test_render_platform_surfaces.py``).

Why a dedicated tier attribute instead of the MCP ``readOnlyHint``: the
retrieval tools are deliberately registered ``_OBSERVATIONAL_TOOL`` with
``readOnlyHint: False`` because they write telemetry (context-efficiency
ledgers). The permission tier is a *risk* classification for host allow
rules, not an MCP semantics claim, so it lives here as its own datum.

Tier semantics:

* ``read``: retrieval, listing, status, search, and report-only diagnostics.
  Rendered into the distributed default allowlist.
* ``write``: mutating lifecycle, memory, index, dashboard, and upgrade
  operations (plus anything not proven report-only). Rendered ONLY when the
  operator-owned knob (``render_platform_surfaces.PERMISSIONS_WRITE_TIER_KEY``
  in ``.claude/settings.json``) is set by the operator.

Runner-registered reload-survivor tools (registered by ``server.py``, not
``server_impl.register_mcp_surface``) ARE roster members: they are part of
the published agent-facing tool surface and need allow rules like any other
tool. They are additionally listed in ``RUNNER_TOOLS`` so the
``register_mcp_surface`` parity check can exclude them from the
implementation-side comparison.

This module must stay stdlib-only and import-light: the renderer runs in
hosts without the MCP runtime installed.
"""
from __future__ import annotations

TIER_READ = "read"
TIER_WRITE = "write"

# Fully-qualified Claude Code MCP rule prefix for first-party wavefoundry tools.
MCP_RULE_PREFIX = "mcp__wavefoundry__"

# Tools registered by the server.py runner (reload survivors) rather than by
# server_impl.register_mcp_surface. Roster members; excluded from the
# implementation-side registration parity comparison.
RUNNER_TOOLS: frozenset[str] = frozenset({"wf_reload_mcp"})

# name -> tier. Keep alphabetical within each group for reviewability; the
# derivation helpers sort, so ordering here is cosmetic.
TOOL_TIERS: dict[str, str] = {
    # ── Retrieval / navigation (observational; telemetry writes do not make
    #    a tool mutating for permission purposes) ──────────────────────────
    "code_ask": TIER_READ,
    "code_callgraph": TIER_READ,
    "code_callhierarchy": TIER_READ,
    "code_commit_provenance": TIER_READ,
    "code_constants": TIER_READ,
    "code_definition": TIER_READ,
    "code_dependencies": TIER_READ,
    "code_graph_community": TIER_READ,
    "code_graph_path": TIER_READ,
    "code_hover": TIER_READ,
    "code_impact": TIER_READ,
    "code_keyword": TIER_READ,
    "code_lexical": TIER_READ,
    "code_list_files": TIER_READ,
    "code_outline": TIER_READ,
    "code_pattern": TIER_READ,
    "code_read": TIER_READ,
    "code_references": TIER_READ,
    "code_risk_score": TIER_READ,
    "code_search": TIER_READ,
    "docs_search": TIER_READ,
    "seed_get": TIER_READ,
    # ── Listing / status / report-only inspection ────────────────────────
    "index_build_status": TIER_READ,
    "index_health": TIER_READ,
    "memory_brief": TIER_READ,
    "memory_search": TIER_READ,
    "wf_audit": TIER_READ,
    "wf_audit_install": TIER_READ,
    "wf_current_wave": TIER_READ,
    "wf_gate_status": TIER_READ,
    "wf_get_change": TIER_READ,
    "wf_get_handoff": TIER_READ,
    "wf_get_prompt": TIER_READ,
    "wf_gpu_doctor": TIER_READ,
    "wf_graph_report": TIER_READ,
    "wf_help": TIER_READ,
    "wf_list_plans": TIER_READ,
    "wf_list_waves": TIER_READ,
    "wf_map": TIER_READ,
    "wf_server_info": TIER_READ,
    "wf_upgrade_status": TIER_READ,
    "wf_validate_docs": TIER_READ,
    # ── Mutating lifecycle / gates / evidence ────────────────────────────
    "wf_add_change": TIER_WRITE,
    "wf_close_gate": TIER_WRITE,
    "wf_close_wave": TIER_WRITE,
    "wf_create_wave": TIER_WRITE,
    "wf_implement_wave": TIER_WRITE,
    "wf_open_gate": TIER_WRITE,
    "wf_pause_wave": TIER_WRITE,
    "wf_prepare_wave": TIER_WRITE,
    "wf_remove_change": TIER_WRITE,
    "wf_reopen_wave": TIER_WRITE,
    "wf_review_event": TIER_WRITE,
    "wf_review_wave": TIER_WRITE,
    "wf_set_handoff": TIER_WRITE,
    # ── Change-doc creation ──────────────────────────────────────────────
    "wf_new_bug": TIER_WRITE,
    "wf_new_change": TIER_WRITE,
    "wf_new_documentation": TIER_WRITE,
    "wf_new_enhancement": TIER_WRITE,
    "wf_new_feature": TIER_WRITE,
    "wf_new_maintenance": TIER_WRITE,
    "wf_new_operations": TIER_WRITE,
    "wf_new_refactor": TIER_WRITE,
    "wf_new_task": TIER_WRITE,
    "wf_new_tech_debt": TIER_WRITE,
    # ── Memory writes ────────────────────────────────────────────────────
    "memory_add": TIER_WRITE,
    "memory_backfill": TIER_WRITE,
    "memory_consolidate": TIER_WRITE,
    "memory_propose": TIER_WRITE,
    "memory_purge": TIER_WRITE,
    "memory_reconcile": TIER_WRITE,
    "memory_validate": TIER_WRITE,
    # ── Index / surfaces / docs mutation ─────────────────────────────────
    "index_build": TIER_WRITE,
    "index_optimize": TIER_WRITE,
    "wf_garden_docs": TIER_WRITE,
    "wf_sync_surfaces": TIER_WRITE,
    # ── Evals / sensors / scans (not proven report-only: they persist
    #    findings or eval artifacts) ──────────────────────────────────────
    "wf_context_efficiency_eval": TIER_WRITE,
    "wf_memory_eval": TIER_WRITE,
    "wf_run_sensors": TIER_WRITE,
    "wf_scan_secrets": TIER_WRITE,
    # ── Dashboard / process / upgrade ────────────────────────────────────
    "wf_open_dashboard": TIER_WRITE,
    "wf_restart_dashboard": TIER_WRITE,
    "wf_start_dashboard": TIER_WRITE,
    "wf_stop_dashboard": TIER_WRITE,
    "wf_upgrade": TIER_WRITE,
    # ── Runner-registered reload survivors (see RUNNER_TOOLS) ────────────
    "wf_reload_mcp": TIER_WRITE,
}


def tools_for_tiers(include_write: bool = False) -> tuple[str, ...]:
    """Sorted tool names for the selected tiers (read always; write opt-in)."""
    tiers = {TIER_READ} | ({TIER_WRITE} if include_write else set())
    return tuple(sorted(name for name, tier in TOOL_TIERS.items() if tier in tiers))


def allow_rules(include_write: bool = False) -> tuple[str, ...]:
    """Sorted Claude Code ``permissions.allow`` rule strings for the selected tiers."""
    return tuple(MCP_RULE_PREFIX + name for name in tools_for_tiers(include_write=include_write))
