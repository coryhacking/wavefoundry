# Release delivery seat

Owner: Engineering
Status: active
Last verified: 2026-11-24

Approve the release lane for the two local 1.53.0 candidates. The rotating seat recommends accepting the upgrade outcome for the exercised Phase 1 installation. Each of six hops passed eighteen checks and ended with exactly one cleanup-complete summary and no upgrade lock. The primary checkpoints identify which entry completed cleanup by itself.

| Entry | 1.51.0 to q5u0 | q5u0 to q5u1 |
| --- | --- | --- |
| Direct archive | Automatic | Automatic |
| Installed CLI | One separate cleanup | Automatic |
| Stdio MCP | Explicit cleanup | Explicit cleanup |

The strongest manual alternative is to require an operator to inspect the primary checkpoint and run cleanup on every upgrade. This remains appropriate for MCP and the legacy installed CLI. Applied to the successor CLI, it adds a needless step and would have concealed the original defect. The terminal inventory alone had passed on the faulty pair after intervention. Review the primary checkpoint with the terminal log.

I independently recomputed both SHA-256 values, checked inner and outer CRCs, compared all 285 feature members with their outer copies and checked all 238 shipped scripts and seeds against the reviewed live checkout. The final q5u1 archive reached the incoming runner on an intentionally incomplete fixture. Removing its single scripts-path insertion reproduced the missing module error. Five focused checks separately covered direct archives, installed cleanup and clean/mixed baseline rendering. Full hops were run by the coordinator. I checked every retained primary checkpoint, terminal summary count, inventory result and final lock snapshot.

Both SHA-256 values and the per-hop results are in release-final.log. Coverage is local Apple Silicon with offline CPU/INT8 and stock Phase 1 prompts. The direct archive preserved verified ZIPs whose parent ownership it could not prove. Field adoption, completed Phase 2, other operating systems and full-suite qualification are outside this seat's verification.
