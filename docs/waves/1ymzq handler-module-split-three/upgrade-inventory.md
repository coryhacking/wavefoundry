# Upgrade Move Inventory

Owner: Engineering
Status: active
Last verified: 2026-09-21

Pre-move source SHA256: `8f89b92362605351fa83085bd6b952cfb719db2e47138d1377585cc47985592c`. MCP navigation preceded AST bulk enumeration. Inventory is a durable artifact, not Git commit.

## Classified set

Definitions: `wf_upgrade_response`, `_bounded_upgrade_response_envelope`, `wf_audit_install_response`, `_bounded_upgrade_summary`, `_parse_bridge_release_required`, `_upgrade_next_step`, `wf_upgrade_status_response`, `_load_upgrade_lib`, `_upgrade_summary_sentinel`, `_parse_upgrade_summary`, `_install_artifact_display`, `_install_audit_row_brief`, `_project_retired_model_cleanup_fields`, `_cutover_restart_required`.

Objects: `UPGRADE_OUTPUT_CAP_CHARS`, `UPGRADE_SUMMARY_CAP_CHARS`, `UPGRADE_SUMMARY_VALUE_CAP_CHARS`, `UPGRADE_SUMMARY_MAX_ITEMS_PER_COLLECTION`, `UPGRADE_RESPONSE_CAP_CHARS`, `UPGRADE_BRIDGE_ARGV_CAP_CHARS`, `UPGRADE_SUMMARY_KEY_CAP_CHARS`, `UPGRADE_SUMMARY_METADATA_CAP_CHARS`, `UPGRADE_SUMMARY_TERMINAL_KEYS`, `RETIRED_MODEL_CLEANUP_KEYS`, `_RETIRED_MODEL_CLEANUP_ITEM_RE`, `_CUTOVER_RESTART_INSTRUCTION`.

Stayers: `_read_framework_pack_version` serves import-time identity; `_setup_notice_key` belongs to ImplHandler; publication middleware stays. Per-call root reaches: `DOCS_LINT_VERDICT_GAP_PREFIX`, `UPGRADE_SUMMARY_TERMINAL_KEYS`, `__file__`, `_bounded_subprocess_output`, `_load_script`, `_mcp_subprocess_run`, `_preferred_python`, `_response`, `run_validate`. Direct owners: `from lifecycle_gate_support import _diagnostic`, `from lifecycle_gate_support import _docs_lint_warning_diagnostics`, `from lifecycle_gate_support import _repo_rel`, `from pathlib import Path`, `from typing import Any`, `from typing import Mapping`, `from typing import Optional`, `import json`, `import os`, `import re`, `import sys`, `import uuid`.

## Runner and old-code window

The old runner executes main including post-extraction phases; fresh cleanup process handles dashboard restart against the extracted tree, so its direct dashboard_handlers import is valid. Archive pre-extract hook imports installed scripts and therefore falls back on ImportError to modern then legacy server stop names. Memory publication remains server_impl._memory_backfill_batch_locked and its source pin is unchanged. Only executable server import remaining in runner is that memory seam; server_impl mentions in comments describe historical identity/runtime policy. Measured code/docs retrieval tools do not reach upgrade responses, so upgrade_handlers is not added to evaluator membership.

## Callers, patch and source anchors

This text occurrence census includes comments/string anchors, not all entries are executable calls. Ten dashboard module-injection sites: four cleanup start cases, three modern stop cases repointed to dashboard_handlers, three legacy cases retain server_impl with dashboard_handlers=None. Three current _load_upgrade_lib patches move owner; the archived-server fixture patch stays with that historical server. Two TERMINAL_KEYS patches remain observed by root call-time reads. The reload source census follows the moved call into upgrade_handlers while retaining exactly two production call sites.

| File | Line | Reference |
| --- | --- | --- |
| `.wavefoundry/framework/scripts/server_impl.py` | 467 | `2. **this script's own install location** — ``server_impl.py`` always lives at` |
| `.wavefoundry/framework/scripts/server_impl.py` | 3408 | `UPGRADE_OUTPUT_CAP_CHARS = 60_000` |
| `.wavefoundry/framework/scripts/server_impl.py` | 3409 | `UPGRADE_SUMMARY_CAP_CHARS = 24_000` |
| `.wavefoundry/framework/scripts/server_impl.py` | 3410 | `UPGRADE_SUMMARY_VALUE_CAP_CHARS = 2_000` |
| `.wavefoundry/framework/scripts/server_impl.py` | 3411 | `UPGRADE_SUMMARY_MAX_ITEMS_PER_COLLECTION = 100` |
| `.wavefoundry/framework/scripts/server_impl.py` | 3412 | `UPGRADE_RESPONSE_CAP_CHARS = 100_000` |
| `.wavefoundry/framework/scripts/server_impl.py` | 3413 | `UPGRADE_BRIDGE_ARGV_CAP_CHARS = 24_000` |
| `.wavefoundry/framework/scripts/server_impl.py` | 3414 | `UPGRADE_SUMMARY_KEY_CAP_CHARS = 128` |
| `.wavefoundry/framework/scripts/server_impl.py` | 3415 | `UPGRADE_SUMMARY_METADATA_CAP_CHARS = 4_000` |
| `.wavefoundry/framework/scripts/server_impl.py` | 3416 | `RETIRED_MODEL_CLEANUP_KEYS = (` |
| `.wavefoundry/framework/scripts/server_impl.py` | 3423 | `_RETIRED_MODEL_CLEANUP_ITEM_RE = re.compile(` |
| `.wavefoundry/framework/scripts/server_impl.py` | 3429 | `def _project_retired_model_cleanup_fields(value: object) -> dict[str, Any]:` |
| `.wavefoundry/framework/scripts/server_impl.py` | 3443 | `for key in RETIRED_MODEL_CLEANUP_KEYS[1:]:` |
| `.wavefoundry/framework/scripts/server_impl.py` | 3455 | `if _RETIRED_MODEL_CLEANUP_ITEM_RE.fullmatch(base):` |
| `.wavefoundry/framework/scripts/server_impl.py` | 3461 | `UPGRADE_SUMMARY_TERMINAL_KEYS = {` |
| `.wavefoundry/framework/scripts/server_impl.py` | 3484 | `*RETIRED_MODEL_CLEANUP_KEYS,` |
| `.wavefoundry/framework/scripts/server_impl.py` | 4418 | `"server_impl_version matches framework_version on disk."` |
| `.wavefoundry/framework/scripts/server_impl.py` | 7680 | `def _install_artifact_display(root: Path, artifact: Path) -> str:` |
| `.wavefoundry/framework/scripts/server_impl.py` | 7726 | `import subprocess  # local import — server_impl imports subprocess per-function (convention)` |
| `.wavefoundry/framework/scripts/server_impl.py` | 7969 | `# with it. Mirror the three sibling spawns (server_impl.py:3487, :6654, setup_index.py).` |
| `.wavefoundry/framework/scripts/server_impl.py` | 9934 | `def wf_audit_install_response(root: Path, phase: Optional[int] = None) -> dict[str, Any]:` |
| `.wavefoundry/framework/scripts/server_impl.py` | 9952 | `# from server_impl (it currently doesn't, but defensive).` |
| `.wavefoundry/framework/scripts/server_impl.py` | 10080 | `first_display = _install_artifact_display(root, first_path)` |
| `.wavefoundry/framework/scripts/server_impl.py` | 10086 | `"row": _install_audit_row_brief(first_row),` |
| `.wavefoundry/framework/scripts/server_impl.py` | 10090 | `"row": _install_audit_row_brief(r),` |
| `.wavefoundry/framework/scripts/server_impl.py` | 10091 | `"expected_artifact": _install_artifact_display(root, p),` |
| `.wavefoundry/framework/scripts/server_impl.py` | 10108 | `f"{r.target!r} does not exist at {_install_artifact_display(root, p)}."` |
| `.wavefoundry/framework/scripts/server_impl.py` | 10145 | `"row": _install_audit_row_brief(next_row),` |
| `.wavefoundry/framework/scripts/server_impl.py` | 10160 | `def _install_audit_row_brief(row: Any) -> dict[str, Any]:` |
| `.wavefoundry/framework/scripts/server_impl.py` | 10929 | `def _load_upgrade_lib() -> Any:` |
| `.wavefoundry/framework/scripts/server_impl.py` | 10945 | `def _upgrade_summary_sentinel() -> str:` |
| `.wavefoundry/framework/scripts/server_impl.py` | 10957 | `def _parse_upgrade_summary(output: str) -> dict[str, Any] / None:` |
| `.wavefoundry/framework/scripts/server_impl.py` | 10968 | `sentinel = _upgrade_summary_sentinel()` |
| `.wavefoundry/framework/scripts/server_impl.py` | 10984 | `def _bounded_upgrade_summary(summary: Mapping[str, Any]) -> dict[str, Any]:` |
| `.wavefoundry/framework/scripts/server_impl.py` | 10995 | `**_project_retired_model_cleanup_fields(summary),` |
| `.wavefoundry/framework/scripts/server_impl.py` | 10997 | `cleanup_list_keys = RETIRED_MODEL_CLEANUP_KEYS[1:]` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11028 | `if key in UPGRADE_SUMMARY_TERMINAL_KEYS` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11029 | `and chars <= UPGRADE_SUMMARY_VALUE_CAP_CHARS` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11031 | `unknown_scalar_budget = max(0, UPGRADE_SUMMARY_CAP_CHARS - terminal_chars)` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11048 | `if key_chars > UPGRADE_SUMMARY_KEY_CAP_CHARS:` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11055 | `is_terminal = key in UPGRADE_SUMMARY_TERMINAL_KEYS` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11057 | `if value_chars <= UPGRADE_SUMMARY_VALUE_CAP_CHARS and fits_aggregate:` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11079 | `<= UPGRADE_SUMMARY_METADATA_CAP_CHARS` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11089 | `if key_chars > UPGRADE_SUMMARY_KEY_CAP_CHARS:` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11096 | `returned = values[:UPGRADE_SUMMARY_MAX_ITEMS_PER_COLLECTION]` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11114 | `if collection_chars + candidate_chars + 1 <= UPGRADE_SUMMARY_CAP_CHARS:` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11130 | `bounded["summary_collection_cap_chars"] = UPGRADE_SUMMARY_CAP_CHARS` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11131 | `bounded["summary_scalar_cap_chars"] = UPGRADE_SUMMARY_CAP_CHARS` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11140 | `bounded["summary_scalar_metadata_cap_chars"] = UPGRADE_SUMMARY_METADATA_CAP_CHARS` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11150 | `bounded["summary_key_cap_chars"] = UPGRADE_SUMMARY_KEY_CAP_CHARS` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11151 | `bounded["summary_value_cap_chars"] = UPGRADE_SUMMARY_VALUE_CAP_CHARS` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11153 | `UPGRADE_SUMMARY_MAX_ITEMS_PER_COLLECTION` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11159 | `def _bounded_upgrade_response_envelope(response: dict[str, Any]) -> dict[str, Any]:` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11171 | `code[:UPGRADE_SUMMARY_KEY_CAP_CHARS]` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11178 | `if len(message) > UPGRADE_SUMMARY_VALUE_CAP_CHARS:` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11180 | `message[:UPGRADE_SUMMARY_VALUE_CAP_CHARS]` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11190 | `item[:UPGRADE_SUMMARY_KEY_CAP_CHARS]` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11197 | `:UPGRADE_SUMMARY_VALUE_CAP_CHARS` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11215 | `data["memory_backfill"] = _bounded_upgrade_summary(memory_gate)` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11217 | `data["response_cap_chars"] = UPGRADE_RESPONSE_CAP_CHARS` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11222 | `if total_before <= UPGRADE_RESPONSE_CAP_CHARS:` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11231 | `excess = max(0, current - UPGRADE_RESPONSE_CAP_CHARS)` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11244 | `> UPGRADE_RESPONSE_CAP_CHARS` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11254 | `> UPGRADE_RESPONSE_CAP_CHARS` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11284 | `compacted["next_step"] = next_step[:UPGRADE_SUMMARY_VALUE_CAP_CHARS]` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11294 | `if len(json.dumps(response, ensure_ascii=False, default=str)) > UPGRADE_RESPONSE_CAP_CHARS:` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11302 | `for key in RETIRED_MODEL_CLEANUP_KEYS` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11312 | `if len(json.dumps(response, ensure_ascii=False, default=str)) > UPGRADE_RESPONSE_CAP_CHARS:` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11336 | `if len(json.dumps(response, ensure_ascii=False, default=str)) > UPGRADE_RESPONSE_CAP_CHARS:` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11345 | `:UPGRADE_SUMMARY_KEY_CAP_CHARS` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11348 | `:UPGRADE_SUMMARY_VALUE_CAP_CHARS` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11354 | `if len(json.dumps(response, ensure_ascii=False, default=str)) > UPGRADE_RESPONSE_CAP_CHARS:` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11369 | `<= UPGRADE_BRIDGE_ARGV_CAP_CHARS` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11374 | `:UPGRADE_SUMMARY_KEY_CAP_CHARS` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11383 | `"phase": str(data.get("phase") or "")[:UPGRADE_SUMMARY_KEY_CAP_CHARS]` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11386 | `"state": str(data.get("state") or "")[:UPGRADE_SUMMARY_KEY_CAP_CHARS]` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11392 | `"response_cap_chars": UPGRADE_RESPONSE_CAP_CHARS,` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11400 | `:UPGRADE_SUMMARY_KEY_CAP_CHARS` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11413 | `if len(json.dumps(response, ensure_ascii=False, default=str)) > UPGRADE_RESPONSE_CAP_CHARS:` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11419 | `:UPGRADE_SUMMARY_KEY_CAP_CHARS` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11424 | `:UPGRADE_SUMMARY_KEY_CAP_CHARS` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11431 | `"response_cap_chars": UPGRADE_RESPONSE_CAP_CHARS,` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11449 | `def _parse_bridge_release_required(output: str) -> dict[str, Any] / None:` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11506 | `or len(parsed[key]) > UPGRADE_SUMMARY_KEY_CAP_CHARS` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11521 | `> UPGRADE_BRIDGE_ARGV_CAP_CHARS` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11530 | `if isinstance(value, str) and len(value) > UPGRADE_SUMMARY_VALUE_CAP_CHARS:` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11532 | `value[:UPGRADE_SUMMARY_VALUE_CAP_CHARS]` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11548 | `_CUTOVER_RESTART_INSTRUCTION = (` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11556 | `def _cutover_restart_required(root: Path, summary: dict[str, Any] / None) -> bool:` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11570 | `_ulib = _load_upgrade_lib()` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11582 | `def _upgrade_next_step(phase: str) -> tuple[str, list[str]]:` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11621 | `def wf_upgrade_response(` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11744 | `return _bounded_upgrade_response_envelope(` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11762 | `cap_chars=UPGRADE_OUTPUT_CAP_CHARS,` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11784 | `summary = _parse_upgrade_summary(output)` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11786 | `data["summary"] = _bounded_upgrade_summary(summary)` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11835 | `_next_step, _next_tools = _upgrade_next_step(phase)` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11875 | `return _bounded_upgrade_response_envelope(response)` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11896 | `return _bounded_upgrade_response_envelope(response)` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11902 | `_ulib = _load_upgrade_lib()` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11965 | `return _bounded_upgrade_response_envelope(action)` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11967 | `bridge_handoff = _parse_bridge_release_required(output)` |
| `.wavefoundry/framework/scripts/server_impl.py` | 11989 | `return _bounded_upgrade_response_envelope(handoff)` |
| `.wavefoundry/framework/scripts/server_impl.py` | 12016 | `return _bounded_upgrade_response_envelope(err)` |
| `.wavefoundry/framework/scripts/server_impl.py` | 12023 | `cutover_restart = mode == "apply" and _cutover_restart_required(root, summary)` |
| `.wavefoundry/framework/scripts/server_impl.py` | 12028 | `"Upgrade complete. " + _CUTOVER_RESTART_INSTRUCTION + " After "` |
| `.wavefoundry/framework/scripts/server_impl.py` | 12033 | `_next_step = _next_step + " " + _CUTOVER_RESTART_INSTRUCTION` |
| `.wavefoundry/framework/scripts/server_impl.py` | 12043 | `# code_ask, etc.) use the freshly-extracted server_impl. Without this, the` |
| `.wavefoundry/framework/scripts/server_impl.py` | 12054 | `+ _CUTOVER_RESTART_INSTRUCTION,` |
| `.wavefoundry/framework/scripts/server_impl.py` | 12072 | `return _bounded_upgrade_response_envelope(resp)` |
| `.wavefoundry/framework/scripts/server_impl.py` | 12075 | `def wf_upgrade_status_response(root: Path) -> dict[str, Any]:` |
| `.wavefoundry/framework/scripts/server_impl.py` | 12077 | `_ulib = _load_upgrade_lib()` |
| `.wavefoundry/framework/scripts/server_impl.py` | 12097 | `cleanup_projection = _project_retired_model_cleanup_fields(lock)` |
| `.wavefoundry/framework/scripts/server_impl.py` | 12624 | `1. Scan ``server.py`` in addition to ``server_impl.py`` — ``wf_reload_mcp``` |
| `.wavefoundry/framework/scripts/server_impl.py` | 12645 | `# server_impl.py defines the rest of the surface.` |
| `.wavefoundry/framework/scripts/server_impl.py` | 12649 | `for src_file in ("server.py", "server_impl.py"):` |
| `.wavefoundry/framework/scripts/server_impl.py` | 17123 | `# harness importing server_impl directly).` |
| `.wavefoundry/framework/scripts/server_impl.py` | 17245 | `# them at index time AND server_impl.py's code_callhierarchy defense-in-depth` |
| `.wavefoundry/framework/scripts/server_impl.py` | 18688 | `# module __getattr__ fallback. A standalone server_impl with no runner process reports null.` |
| `.wavefoundry/framework/scripts/server_impl.py` | 18739 | `# server_impl reports an explicit null identity, never a fake value.` |
| `.wavefoundry/framework/scripts/server_impl.py` | 19708 | `can. A standalone server_impl with no runner process never calls this and keeps the` |
| `.wavefoundry/framework/scripts/server_impl.py` | 19751 | `"server_impl_version": impl_version,` |
| `.wavefoundry/framework/scripts/server_impl.py` | 21406 | ```server_impl > _classify_question``; rows produced only by the BM25 pass omit the field` |
| `.wavefoundry/framework/scripts/server_impl.py` | 23040 | `return wf_upgrade_response(handler.root, phase=phase,` |
| `.wavefoundry/framework/scripts/server_impl.py` | 23065 | `return wf_upgrade_status_response(get_handler().root)` |
| `.wavefoundry/framework/scripts/server_impl.py` | 23106 | `return wf_audit_install_response(get_handler().root, phase=phase)` |
| `.wavefoundry/framework/scripts/upgrade_wavefoundry.py` | 75 | `# line prefixed with this sentinel (alongside the human prose). ``server_impl.wf_upgrade_response``` |
| `.wavefoundry/framework/scripts/upgrade_wavefoundry.py` | 80 | `_RETIRED_MODEL_CLEANUP_KEYS = (` |
| `.wavefoundry/framework/scripts/upgrade_wavefoundry.py` | 132 | `for key in _RETIRED_MODEL_CLEANUP_KEYS[1:]:` |
| `.wavefoundry/framework/scripts/upgrade_wavefoundry.py` | 331 | `# indexer, server_impl) already branch on os.name. _pid_is_running uses tasklist on` |
| `.wavefoundry/framework/scripts/upgrade_wavefoundry.py` | 3066 | `for key in _RETIRED_MODEL_CLEANUP_KEYS[1:]:` |
| `.wavefoundry/framework/scripts/upgrade_wavefoundry.py` | 3160 | `import server_impl` |
| `.wavefoundry/framework/scripts/upgrade_wavefoundry.py` | 3165 | `restart = server_impl.wf_start_dashboard_response(` |
| `.wavefoundry/framework/scripts/upgrade_wavefoundry.py` | 3726 | ```restart_required`` boolean) into the machine-readable channel so ``wf_upgrade_response`` can` |
| `.wavefoundry/framework/scripts/upgrade_wavefoundry.py` | 3801 | ```wf_upgrade_response`` parses this single line into ``data['summary']``. Rendered from the` |
| `.wavefoundry/framework/scripts/upgrade_wavefoundry.py` | 4271 | `# Wave 1p8eu/1p8kz — emit the summary machine-readably so wf_upgrade_response parses it into` |
| `.wavefoundry/framework/scripts/upgrade_wavefoundry.py` | 5809 | `import server_impl` |
| `.wavefoundry/framework/scripts/upgrade_wavefoundry.py` | 5815 | `) = server_impl._memory_backfill_batch_locked(` |
| `.wavefoundry/framework/scripts/upgrade_extensions.py` | 338 | `import server_impl` |
| `.wavefoundry/framework/scripts/upgrade_extensions.py` | 341 | `# installed server_impl may predate the wf_ tool rename and expose` |
| `.wavefoundry/framework/scripts/upgrade_extensions.py` | 344 | `server_impl, "wf_stop_dashboard_response", None` |
| `.wavefoundry/framework/scripts/upgrade_extensions.py` | 345 | `) or getattr(server_impl, "wave_dashboard_stop_response", None)` |
| `.wavefoundry/framework/scripts/upgrade_extensions.py` | 349 | `"wf_stop_dashboard_response nor wave_dashboard_stop_response"` |
| `.wavefoundry/framework/scripts/upgrade_extensions.py` | 934 | `wrapper = namespace.get("wf_upgrade_response")` |
| `.wavefoundry/framework/scripts/upgrade_extensions.py` | 937 | `or caller.f_code.co_name != "wf_upgrade_response"` |
| `.wavefoundry/framework/scripts/upgrade_extensions.py` | 944 | `original = namespace.get("_bounded_upgrade_response_envelope")` |
| `.wavefoundry/framework/scripts/upgrade_extensions.py` | 951 | `namespace["_bounded_upgrade_response_envelope"] = bounded` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 133 | `# MCP-reachable modules — `server_impl` AND the in-process secrets-scan fallback` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 136 | `# `subprocess_util.isolated_run` (inherently isolated); server_impl keeps `_mcp_subprocess_run`` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 142 | `SCRIPTS_ROOT / "server_impl.py",` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 182 | `"""Wave 1p8gu: the breadth guard now spans EVERY framework script (not just server_impl +` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 256 | `# legitimately remain (server_impl's _mcp_subprocess_run **kwargs delegation + 3 detached Popens` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 409 | `# definition of the consolidated helper remains (anti-drift). server_impl keeps a thin` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 430 | `# server_impl's retained alias must DELEGATE, not re-implement the getattr lookup.` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 431 | `si_src = (SCRIPTS_ROOT / "server_impl.py").read_text(encoding="utf-8")` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 654 | `for fname in ("server_impl.py", "upgrade_wavefoundry.py"):` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 704 | `# The PowerShell cmdline scan is MCP-reachable via server_impl's dashboard reconciliation.` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 825 | `server script's OWN install location (``parents[3]`` of ``server_impl.py``). Priority:` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 827 | `REAL ``server_impl.__file__`` points at the live wavefoundry repo (which carries the marker), the` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 846 | `"""A fake ``server_impl.py`` path whose ``parents[3]`` is a markerless tree (no` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 859 | `# server_impl.py at <repo>/.wavefoundry/framework/scripts/ → parents[3] is the repo; the` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 995 | `self.assertIn("server_impl_version", result["data"])` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 998 | `self.assertEqual(result["data"]["server_impl_version"], self.srv.SERVER_IMPL_VERSION)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 1375 | `self.srv.wf_audit_install_response,` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 2457 | `# AC-4: a server_impl context with no runner process reports explicit nulls.` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 2466 | `# AC-4: no code path may silently serve the retired literal "1". server_impl` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 2527 | `"""Wave 1u2b0 repair: a torn mid-upgrade tree (this runner + an OLDER server_impl whose` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 2728 | `self.srv = load_server()          # server_impl (impl namespace)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 2760 | `self.assertTrue(result["data"]["server_impl_version"])` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 2796 | `for path in (SERVER_PATH, SCRIPTS_ROOT / "server_impl.py"):` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 2811 | `self.assertEqual([name for name, _line in observed], ["server.py", "server_impl.py"])` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 2937 | `# Two reloads in a row — server_impl module didn't change between them,` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 3349 | `# No handler but root known → lazy-build via server_impl.build_handler, no raise.` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 3350 | `import server_impl` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 3360 | `with patch.object(server_impl, "build_handler", side_effect=fake_build):` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 3371 | `import server_impl` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 3372 | `with patch.object(server_impl, "build_handler",` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4060 | `import server_impl` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4065 | `patch.object(server_impl, "_pid_is_running", return_value=True), \` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4077 | `import server_impl` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4092 | `import server_impl` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4095 | `patch.object(server_impl, "_pid_is_running", return_value=True):` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4104 | `import server_impl` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4114 | `patch.object(server_impl, "DASHBOARD_START_WAIT_SECONDS", 0.0), \` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4180 | `import server_impl` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4187 | `patch.object(server_impl, "_pid_is_running", return_value=True):` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4205 | `import server_impl` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4211 | `patch.object(server_impl, "_pid_is_running", return_value=False), \` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4212 | `patch.object(server_impl, "DASHBOARD_START_WAIT_SECONDS", 0.0):` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4224 | `import server_impl` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4230 | `patch.object(server_impl, "_pid_is_running", return_value=True):` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4253 | `import server_impl` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4263 | `patch.object(server_impl, "DASHBOARD_START_WAIT_SECONDS", 0.0), \` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4288 | `import server_impl` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4291 | `patch.object(server_impl, "_pid_is_running", return_value=False):` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4304 | `import server_impl` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4308 | `patch.object(server_impl, "_pid_is_running", return_value=True):` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4309 | `result = server_impl.wf_open_dashboard_response(self.root)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4344 | `import server_impl` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4358 | `patch.object(server_impl, "_pid_is_running", return_value=False):` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4378 | `import server_impl` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4384 | `patch.object(server_impl, "_pid_is_running", return_value=False), \` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4397 | `import server_impl` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4402 | `patch.object(server_impl, "_pid_is_running", return_value=False), \` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4403 | `patch.object(server_impl, "DASHBOARD_START_WAIT_SECONDS", 0.0):` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4414 | `import server_impl` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4423 | `self.assertTrue(server_impl._dashboard_url_reachable("http://127.0.0.1:1/x"))` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4427 | `self.assertFalse(server_impl._dashboard_url_reachable("http://127.0.0.1:1/x"))` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4430 | `self.assertFalse(server_impl._dashboard_url_reachable(""))` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4481 | `import server_impl` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4485 | `patch.object(server_impl, "_pid_is_running", return_value=False):` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4495 | `self.srv.wf_upgrade_response(self.root, phase="preflight_to_docs_gate")` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4505 | `"""Tests for wf_upgrade_status_response (AC-5 / R5)."""` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4534 | `result = self.srv.wf_upgrade_status_response(self.root)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4541 | `result = self.srv.wf_upgrade_status_response(self.root)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4560 | `result = self.srv.wf_upgrade_status_response(self.root)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4562 | `{key: result["data"][key] for key in self.srv.RETIRED_MODEL_CLEANUP_KEYS},` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4581 | `result = self.srv.wf_upgrade_status_response(self.root)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4610 | `result = self.srv.wf_upgrade_status_response(self.root)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4641 | `result = self.srv.wf_upgrade_status_response(self.root)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4703 | `"""Tests for wf_upgrade_response (AC-2–AC-5 / 12r0b)."""` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4738 | `result = self.srv.wf_upgrade_response(self.root)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4754 | `failed = self.srv.wf_upgrade_response(self.root)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4777 | `response = self.srv.wf_upgrade_response(self.root)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4789 | `self.assertLessEqual(len(json.dumps(response, ensure_ascii=False)), self.srv.UPGRADE_RESPONSE_CAP_CHARS)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4792 | `stale = self.srv.wf_upgrade_response(self.root)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4801 | `result = self.srv.wf_upgrade_response(self.root, mode=mode)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4806 | `result = self.srv.wf_upgrade_response(self.root, phase="bad_phase")` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4817 | `result = self.srv.wf_upgrade_response(self.root, phase="preflight_to_docs_gate")` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4829 | `result = self.srv.wf_upgrade_response(self.root, phase="preflight_to_docs_gate")` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4848 | `result = self.srv.wf_upgrade_response(self.root)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4872 | `result = self.srv.wf_upgrade_response(self.root)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4906 | `+ self.srv._upgrade_summary_sentinel()` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4912 | `result = self.srv.wf_upgrade_response(self.root)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4915 | `self.assertLessEqual(envelope_chars, self.srv.UPGRADE_RESPONSE_CAP_CHARS)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4929 | `{key: bounded[key] for key in self.srv.RETIRED_MODEL_CLEANUP_KEYS},` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4954 | `stdout = self.srv._upgrade_summary_sentinel() + json.dumps(summary) + "\n"` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4959 | `result = self.srv.wf_upgrade_response(self.root)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 4977 | `UPGRADE_SUMMARY_VALUE_CAP_CHARS and came back as ``None`` with a truncated flag. As two` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5007 | `self.assertGreater(legacy_value_chars, self.srv.UPGRADE_SUMMARY_VALUE_CAP_CHARS)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5008 | `legacy_bounded = self.srv._bounded_upgrade_summary(` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5036 | `stdout = self.srv._upgrade_summary_sentinel() + json.dumps(summary) + "\n"` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5039 | `result = self.srv.wf_upgrade_response(self.root)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5054 | `self.srv.UPGRADE_RESPONSE_CAP_CHARS,` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5071 | `stdout = self.srv._upgrade_summary_sentinel() + json.dumps(summary) + "\n"` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5074 | `result = self.srv.wf_upgrade_response(self.root)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5094 | `stdout = self.srv._upgrade_summary_sentinel() + json.dumps(summary) + "\n"` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5097 | `result = self.srv.wf_upgrade_response(self.root)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5101 | `self.srv.UPGRADE_RESPONSE_CAP_CHARS,` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5126 | `stdout = self.srv._upgrade_summary_sentinel() + json.dumps(summary) + "\n"` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5129 | `result = self.srv.wf_upgrade_response(self.root)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5133 | `self.srv.UPGRADE_RESPONSE_CAP_CHARS,` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5159 | `stdout = self.srv._upgrade_summary_sentinel() + json.dumps(summary) + "\n"` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5162 | `result = self.srv.wf_upgrade_response(self.root)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5166 | `self.srv.UPGRADE_RESPONSE_CAP_CHARS,` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5193 | `stdout = self.srv._upgrade_summary_sentinel() + json.dumps(summary) + "\n"` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5196 | `result = self.srv.wf_upgrade_response(self.root)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5200 | `self.srv.UPGRADE_RESPONSE_CAP_CHARS,` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5221 | `stdout = self.srv._upgrade_summary_sentinel() + json.dumps(summary) + "\n"` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5224 | `result = self.srv.wf_upgrade_response(self.root)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5228 | `self.srv.UPGRADE_RESPONSE_CAP_CHARS,` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5251 | `stdout = self.srv._upgrade_summary_sentinel() + json.dumps(summary) + "\n"` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5254 | `result = self.srv.wf_upgrade_response(self.root)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5258 | `self.srv.UPGRADE_RESPONSE_CAP_CHARS,` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5274 | `result = self.srv.wf_upgrade_response(self.root)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5292 | `result = self.srv.wf_upgrade_response(self.root)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5296 | `self.srv.UPGRADE_RESPONSE_CAP_CHARS,` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5319 | `result = self.srv.wf_upgrade_response(self.root)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5323 | `self.srv.UPGRADE_RESPONSE_CAP_CHARS,` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5343 | `result = self.srv.wf_upgrade_response(self.root)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5347 | `self.srv.UPGRADE_RESPONSE_CAP_CHARS,` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5365 | `self.srv.UPGRADE_BRIDGE_ARGV_CAP_CHARS,` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5369 | `self.srv.UPGRADE_RESPONSE_CAP_CHARS,` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5375 | `result = self.srv.wf_upgrade_response(self.root)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5379 | `self.srv.UPGRADE_RESPONSE_CAP_CHARS,` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5385 | `result = self.srv._bounded_upgrade_response_envelope(` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5394 | `self.srv.UPGRADE_RESPONSE_CAP_CHARS,` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5398 | `self.srv.UPGRADE_SUMMARY_KEY_CAP_CHARS,` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5403 | `result = self.srv._bounded_upgrade_response_envelope(` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5425 | `self.srv.UPGRADE_RESPONSE_CAP_CHARS,` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5434 | `result = self.srv.wf_upgrade_response(self.root)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5438 | `self.srv.UPGRADE_RESPONSE_CAP_CHARS,` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5473 | `patch.object(self.srv, "_load_upgrade_lib", return_value=upgrade_lib), \` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5475 | `result = self.srv.wf_upgrade_response(self.root)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5508 | `patch.object(self.srv, "_load_upgrade_lib", return_value=upgrade_lib), \` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5510 | `result = self.srv.wf_upgrade_response(self.root)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5528 | `patch.object(self.srv, "_load_upgrade_lib", return_value=upgrade_lib):` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5529 | `result = self.srv.wf_upgrade_response(self.root)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5540 | `self.srv.wf_upgrade_response(self.root, phase="update_index")` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5552 | `self.srv.wf_upgrade_response(self.root, phase="rebuild_index")` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5564 | `self.srv.wf_upgrade_response(self.root, phase="cleanup")` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5576 | `result = self.srv.wf_upgrade_response(self.root, phase="resume_after_gate", mode="apply")` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5591 | `result = self.srv.wf_upgrade_response(self.root, phase="resume_after_gate", mode="apply")` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5611 | `result = self.srv.wf_upgrade_response(` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5629 | `result = self.srv.wf_upgrade_response(self.root, mode="dry_run")` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5647 | `stdout=self.srv._upgrade_summary_sentinel() + json.dumps(summary) + "\n",` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5651 | `result = self.srv.wf_upgrade_response(self.root, mode="dry_run")` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5653 | `{key: result["data"]["summary"][key] for key in self.srv.RETIRED_MODEL_CLEANUP_KEYS},` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5654 | `{key: summary[key] for key in self.srv.RETIRED_MODEL_CLEANUP_KEYS},` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5659 | `result = self.srv.wf_upgrade_response(self.root, mode="bad_mode")` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5666 | `When phase='cleanup' and mode='apply' succeed, wf_upgrade_response` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5680 | `"server_impl_version": "v1", "impl_matches_disk": True,` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5689 | `result = self.srv.wf_upgrade_response(self.root, phase="cleanup", mode="apply")` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5739 | `result = self.srv.wf_upgrade_response(` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5789 | `result = self.srv.wf_upgrade_response(` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5812 | `result = self.srv.wf_upgrade_response(` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5834 | `"server_impl_version": "v1", "impl_matches_disk": True},` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5839 | `result = self.srv.wf_upgrade_response(` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5871 | `result = self.srv.wf_upgrade_response(` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5907 | `result = self.srv.wf_upgrade_response(self.root, phase="update_index")` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5932 | `result = self.srv.wf_upgrade_response(` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5957 | `result = self.srv.wf_upgrade_response(self.root, phase="update_index")` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5973 | `result = self.srv.wf_upgrade_response(` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5987 | `result = self.srv.wf_upgrade_response(self.root, phase="update_index")` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 5999 | `result = self.srv.wf_upgrade_response(self.root, phase="update_index")` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 6012 | `result = self.srv.wf_upgrade_response(self.root, phase="update_index")` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 6017 | `def test_parse_upgrade_summary_helper_fail_safe(self):` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 6019 | `self.assertIsNone(self.srv._parse_upgrade_summary(""))` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 6020 | `self.assertIsNone(self.srv._parse_upgrade_summary("no sentinel here"))` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 6021 | `self.assertIsNone(self.srv._parse_upgrade_summary("WAVE_UPGRADE_SUMMARY_JSON:[1,2,3]"))  # not a dict` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 6022 | `parsed = self.srv._parse_upgrade_summary('WAVE_UPGRADE_SUMMARY_JSON:{"pruned_count": 9}')` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 6025 | `def test_parse_upgrade_summary_deeply_nested_no_exception(self):` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 6029 | `self.assertIsNone(self.srv._parse_upgrade_summary(line))` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 6032 | `# TA-1: server_impl must use the single constant from upgrade_wavefoundry, never a redefinition.` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 6034 | `self.assertEqual(self.srv._upgrade_summary_sentinel(), _uw.WAVE_UPGRADE_SUMMARY_SENTINEL)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 6037 | `"server_impl must NOT redefine the sentinel constant (TA-1)",` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 6041 | `# TA-1: capture _print_operator_summary's real stdout and feed it to _parse_upgrade_summary —` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 6052 | `parsed = self.srv._parse_upgrade_summary(buf.getvalue())` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 6091 | `parsed = self.srv._parse_upgrade_summary(buf.getvalue())` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 6100 | `# cannot itself produce must survive _parse_upgrade_summary +` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 6101 | `# _bounded_upgrade_summary into wf_upgrade_response's data['summary'],` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 6109 | `result = self.srv.wf_upgrade_response(self.root, phase="update_index")` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 6122 | `"summary_source_degraded", self.srv.UPGRADE_SUMMARY_TERMINAL_KEYS` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 6136 | `stdout = self.srv._upgrade_summary_sentinel() + json.dumps(summary) + "\n"` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 6139 | `result = self.srv.wf_upgrade_response(self.root)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 6154 | `for key in self.srv.UPGRADE_SUMMARY_TERMINAL_KEYS` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 6162 | `self.srv, "UPGRADE_SUMMARY_TERMINAL_KEYS", stale_terminal_keys` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 6164 | `result = self.srv.wf_upgrade_response(self.root)` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 6183 | `"summary_schema_version", self.srv.UPGRADE_SUMMARY_TERMINAL_KEYS` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 6195 | `#    not exhaust the budget: `_bounded_upgrade_summary` decrements it only` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 6210 | `stdout = self.srv._upgrade_summary_sentinel() + json.dumps(summary) + "\n"` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 6213 | `result = self.srv.wf_upgrade_response(self.root, phase="cleanup")` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 6228 | `for key in self.srv.UPGRADE_SUMMARY_TERMINAL_KEYS` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 6232 | `self.srv, "UPGRADE_SUMMARY_TERMINAL_KEYS", stale_terminal_keys` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 6234 | `unregistered = self.srv.wf_upgrade_response(self.root, phase="cleanup")` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 6252 | `result = self.srv.wf_upgrade_response(self.root, phase="preflight_to_docs_gate")` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 6682 | `src = (SCRIPTS_ROOT / "server_impl.py").read_text(encoding="utf-8")` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 7610 | `import server_impl` |
| `.wavefoundry/framework/scripts/tests/test_server_tools.py` | 7612 | `self.impl, self.lib = server_impl, dashboard_lib` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 856 | `ul = _load_upgrade_lib()` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 906 | `def _load_upgrade_lib():` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 921 | `self.lib = _load_upgrade_lib()` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 1003 | `self.lib = _load_upgrade_lib()` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 1049 | `self.lib = _load_upgrade_lib()` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 1165 | `self.lib = _load_upgrade_lib()` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 1250 | `with patch.dict(sys.modules, {"server_impl": fake_server}):` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 1329 | `with patch.dict(sys.modules, {"server_impl": fake_server}):` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 1347 | `with patch.dict(sys.modules, {"server_impl": fake_server}):` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 1529 | `self.lib = _load_upgrade_lib()` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 2643 | `), patch.dict(sys.modules, {"server_impl": fake_server}):` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 3004 | `lib = _load_upgrade_lib()` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 3082 | `self.lib = _load_upgrade_lib()` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 3755 | `scripts.joinpath("server_impl.py").write_text("# old server\n", encoding="utf-8")` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 3769 | `"server_impl.py",` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 3834 | `scripts.joinpath("server_impl.py").read_text(encoding="utf-8"),` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 4126 | `with patch.dict(sys.modules, {"server_impl": self._fake_server()}):` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 4140 | `server_impl that may predate the wf_ tool rename (field report:` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 4153 | `pre_rename = types.SimpleNamespace(wave_dashboard_stop_response=old_stop)` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 4154 | `with patch.dict(sys.modules, {"server_impl": pre_rename}):` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 4171 | `wave_dashboard_stop_response=old_stop,` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 4173 | `with patch.dict(sys.modules, {"server_impl": both}):` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 4180 | `with patch.dict(sys.modules, {"server_impl": types.SimpleNamespace()}):` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 4182 | `RuntimeError, "wave_dashboard_stop_response"` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 4194 | `with patch.dict(sys.modules, {"server_impl": self._fake_server()}):` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 4216 | `with patch.dict(sys.modules, {"server_impl": self._fake_server()}):` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 6738 | `lib = _load_upgrade_lib()` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 7007 | `lib = _load_upgrade_lib()` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 7439 | `# layers (the wf_upgrade_response-level test lives in` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 7441 | `import server_impl` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 7443 | `parsed = server_impl._parse_upgrade_summary(out)` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 7445 | `bounded = server_impl._bounded_upgrade_summary(parsed)` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 7995 | `import server_impl as srv` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 8294 | `import server_impl` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 8311 | `server_impl.memory_backfill_response(` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 8315 | `server_impl.memory_validate_response(` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 8981 | `batch = source.index("server_impl._memory_backfill_batch_locked(", post_hook)` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 9007 | `SERVER_MEMBER = ".wavefoundry/framework/scripts/server_impl.py"` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 9108 | `server._load_upgrade_lib = lambda: None` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 9111 | `def wf_upgrade_response(root, phase="preflight_to_docs_gate", mode="apply"):` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 9113 | `lock = server._load_upgrade_lib().read_upgrade_lock(root) or {}` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 9129 | `server.wf_upgrade_response = wf_upgrade_response` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 9133 | `name = f"archived_server_impl_{build}_{id(self)}"` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 9137 | `server.__file__ = str(SCRIPTS_ROOT / "server_impl.py")` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 9385 | `patch.object(server, "_load_upgrade_lib", return_value=legacy_lib), \` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 9387 | `result = server.wf_upgrade_response(self.root)` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 9953 | `import server_impl` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 9974 | `server_impl.memory_backfill_response(` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 9978 | `validated = server_impl.memory_validate_response(` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 10235 | `lib = _load_upgrade_lib()` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 10589 | `self.lib = _load_upgrade_lib()` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 10769 | `lib = _load_upgrade_lib()` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 10851 | `lib = _load_upgrade_lib()` |
| `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` | 10868 | `lib = _load_upgrade_lib()` |

## Extraction verification

Fourteen function ASTs match the captured pre-move source after normalizing only inserted local server imports and documented server attribute qualification. All twelve object ASTs match exactly. Nested symtable scan found no unresolved globals. Registrar, ImplHandler and cost middleware byte-identity checks passed at extraction. The runner retains exactly one executable server import for the source-pinned memory seam. The new installed-module-absence test killed an in-memory mutant replacing the ImportError fallback body with bare raise. Full named-suite results are recorded in the change Progress Log when complete.
