# Plans

Owner: Engineering
Status: active
Last verified: 2026-05-01

Hub for in-flight planning work. Active change documents live here until admitted into a wave, at which point **Prepare wave** relocates them into `docs/waves/<wave-id>/`.

## Active Plans

*(None — no in-flight changes yet)*

## Template

New change documents use `docs/plans/plan-template.md`. Generate change IDs with:

```bash
python3 .wavefoundry/framework/scripts/lifecycle_id.py --kind <kind> --slug <slug>
```

Kind options: `feat`, `bug`, `enh`, `change`, `doc`, `debt`, `ref`, `task`, `maint`, `ops`.