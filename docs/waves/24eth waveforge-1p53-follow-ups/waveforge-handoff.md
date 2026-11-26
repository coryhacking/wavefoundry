# Waveforge upgrade rehearsal

Owner: Engineering
Status: draft
Last verified: 2026-11-26

Draft for the operator to review and send before Waveforge applies the upgrade.

Before applying an upgrade to a scratch checkout, account for retired models in the shared workstation cache. A rehearsal that reaches cleanup removes eligible components from that cache for every repository. The installed 1.53 runner cannot list those components in advance. After upgrading, the updated runner lists eligible component IDs in `wf upgrade --dry-run`. The preview uses the installed runner’s allowlist. At apply, cleanup checks the active model set and index epoch after reindexing.
