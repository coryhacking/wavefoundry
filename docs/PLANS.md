# Plans

Owner: Engineering
Status: active
Last verified: 2026-04-28

Hub for in-flight planning work. Active change documents live here until admitted into a wave, at which point **Prepare wave** relocates them into `docs/waves/<wave-id>/`.

Legacy completed-plan folders are retired. Completed admitted change docs stay in `docs/waves/<wave-id>/` as part of the wave archive.

## Active Plans

*(None — no in-flight changes yet)*

## Template

New change documents use `docs/plans/plan-template.md`. Generate change IDs with:

```bash
python3 .wavefoundry/framework/scripts/lifecycle_id.py --kind <kind> --slug <slug>
```

Kind options: `feat`, `bug`, `enh`, `change`, `doc`, `debt`, `ref`, `task`, `maint`, `ops`.
