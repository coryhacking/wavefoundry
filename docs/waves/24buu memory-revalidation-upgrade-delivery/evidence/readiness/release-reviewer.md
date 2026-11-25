# Release-reviewer readiness review, wave 24buu

Owner: Engineering
Status: active
Last verified: 2026-11-24

Verdict: approve. No demonstrated defect in packaging, distribution or upgrade-path compatibility.

## 24bn7
- Zip entry code is the zip's own `__main__.py` (upgrade_bundle source, `build_pack.build_upgrade_bundle`), so the fix is delivered with the 1.52.0 zip and takes effect on every hop; there is no old-code window. Older protocol-1 installs only run the zip; they never import its members, so a path set-up inside the zip cannot affect them.
- `build_upgrade_bundle` assembles the feature zip plus four runner members; the feature members under `.wavefoundry/framework/scripts/` are already in the same archive, so zipimport can resolve `contained_files` with no new member. `upgrade_bundle._materializer` `allowed_runner` and `tests/test_upgrade_protocol.py` member pins stay unchanged (AC-2). F3 and F11 are correctly absorbed.
- The retained re-entry (`next_argv` runs `retained["path"]` again) re-executes the same zip entry, so the path set-up also covers the continuation.
- Implementation notes: append (not prepend) `<zip>/.wavefoundry/framework/scripts` to `sys.path`, so the scripts copies of `upgrade_bundle`, `subprocess_util` and `embedded_model_bundle` cannot shadow the top-level runner members; build the path with `os.path.join`/`Path` from `__file__` or `sys.argv[0]`, never a separator literal; do it before the first call into `retain`. The combined `.with-models.zip` shares this `__main__`; run the AC-1 test on both forms if cheap.

## 24bn9, 24ax3, 24bn8 by hop
- 1.51.0 to 1.52.0: 24ax3 and 24bn8 run in the Phase 1 render child of the freshly extracted code (specs say so), so they deliver on this hop. 24bn9 does not (the installed 1.51.0 primary prints the old message); the spec states this and requires the release note to say one `--cleanup` is still needed from 1.51.0 on the CLI. MCP `wf_upgrade` from 1.51.0 already sequences cleanup.
- 1.52.0 to later: 24bn9 takes effect; the MCP handler passes `--no-auto-cleanup` (F8).
- Changelog requirements are accurate: 24bn9 AC-6 names the 1.51.0 `--cleanup`; 24ax3 AC-8 names remaining manual cases (outside-layer holds, pattern rules, Cursor) and that outside layers are read only.

## Notes (not blocking)
1. 24bn9 R6/AC-6 pin seed 160, its self-hosted copy and the module docstring. Other live statements will drift once the CLI cleans up itself: seed 160 "The primary phase can exit zero while cleanup remains pending" (about line 327), `docs/prompts/upgrade-wavefoundry.prompt.md`, `docs/architecture/data-and-control-flow.md`, `docs/references/native-windows-support.md`. The implementer should sweep these.
2. `docs/prompts/package-wavefoundry.prompt.md` "Upgrade Path Coverage" (the `python3 <combined.zip> ...` statement) is made true, not false, by 24bn7; no edit required.
3. 24bn8 and 24ax3 changelog entries need not mention hops; the wave's two-hop rehearsal watchpoint records the remaining interventions.
