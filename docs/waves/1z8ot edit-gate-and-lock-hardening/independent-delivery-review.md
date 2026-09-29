# Independent delivery review

Owner: Engineering
Status: active
Last verified: 2026-09-28

## Verdict

Request changes. DEL-F4 and DEL-F5 are recorded through the typed review tools. No implementation edits or operator signoff were made.

## Findings

- **DEL-F4:** `render_platform_surfaces.copilot_is_edit` classifies the text-editor tools by name alone. Their read-only `command: view` is treated as an edit. Both an independent hook reviewer and the coordinator executed the composed hooks: viewing a protected seed returned 2; the `str_replace` mutation control returned 2; viewing an ordinary document through the post hook returned 1 with failing lint and created a pending reindex marker. Expected: reads return 0 without lint/index work, while the mutation stays blocked. Recognize known read-only commands in the shared classifier; retain fail-closed handling for mutation and unknown commands. The current eight focused hook tests pass despite this defect.
- **DEL-F5:** `venv_bootstrap.disable_onnxruntime_telemetry` unconditionally invokes the disable API, even when the operator sets `ORT_DISABLE_TELEMETRY=0`. Fresh subprocess probes through `provider_policy.available_onnx_providers` with a recording ONNX Runtime stub showed disable calls for unset, empty, `1`, and `0`. The environment value is preserved, but the advertised opt-in does not preserve API-controlled events. Honor the opt-in in the helper or narrow the documented promise, and test the caller path. This does not claim that initialization telemetry is disabled by the API: upstream documents those as distinct controls.
- **Nonblocking:** an explicit Claude `Read` payload containing a protected seed path is refused, despite Requirement 3's non-edit-tool allowance. The current matcher excludes Read, so this is not reachable through normal dispatch.

## Verification

- Full-suite receipt independently hashed: current, green, 9,900 tests. This review did not rerun that suite.
- Telemetry and bootstrap: canonical focused runner, 59 tests passed, no skips. A bare unittest attempt initially lacked numpy; the canonical runner supplied the supported environment.
- Hooks: eight focused tests passed; five deliberately broken variants were caught (notebook path, strict refusal, replacements parsing, all multi-file paths, Windsurf reindex).
- Runtime locks and upgrade bridge: 53 focused tests passed; seven broken variants were caught (directory no-follow, Windows links, OneDrive discrimination, bounded retries). A directory renamed and replaced by an outside symlink after opening remained anchored to the original descriptor for acquisition, metadata writes, and bridge locks; outside targets stayed empty. Descriptors closed on success and refusal.
- Python 3.11: two simulated-Windows lock tests passed with unrelated consumer imports stubbed. Native Windows was not exercised.
- No native agent-host integration, real network telemetry capture, or independent repeat of the recorded ONNX Runtime 1.30 scratch-home experiment. No claim of reproducing the macOS spurious ENOENT frequency.

## Stable reviewed fingerprints

Git blob hashes matched before and after the relevant reviews:

| File (under framework scripts unless noted) | Hash |
| --- | --- |
| render_platform_surfaces.py | 9046f45e20ce900a52dc2c1eddbeed7a7b436bad |
| tests/test_render_platform_surfaces.py | 777f02deab012bf25e4e381876da572b90bca426 |
| runtime_lock.py | 3170c47d864ace7cb8dc886dad6da544b84d4f89 |
| upgrade_bridge_bootstrap.py | d82e5b070585416535ce9600f3cf62a426fe19b8 |
| tests/test_runtime_lock.py | 64b3ab672ea99ea5a274d07cb15bff57575bb41f |
| tests/test_upgrade_protocol.py | f0a363be008b66bdc26892438e54450a95a50b1b |
| venv_bootstrap.py | e6a97c77e917e656e90dca5d9b7518e0bc5eb23a |
| tests/test_onnxruntime_telemetry.py | ddf541e56c73f64eef2827c6bf9552b20ee15be3 |

Primary API references: [text-editor commands](https://platform.claude.com/docs/en/agents-and-tools/tool-use/text-editor-tool), [ONNX Runtime privacy controls](https://github.com/microsoft/onnxruntime/blob/main/docs/Privacy.md).
