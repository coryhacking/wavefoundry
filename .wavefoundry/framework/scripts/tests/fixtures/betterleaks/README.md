# Scanner reference fixtures

Owner: Engineering
Status: active
Last verified: 2026-11-06

These source-only fixtures test Wavefoundry's Python scanner against pinned
reference behavior. Compressed oracle records contain synthetic credential-shaped
inputs and expected findings. They are detection tests, not application credentials;
do not remove them or suppress their matches inside the test engine. Packaging
excludes `scripts/tests/`, including these oracles.

`upstream.toml` and `baseline.toml` retain their reference provenance. Their
example-value allowlist regexes use a singleton character class in the key prefix
to preserve matching without storing contiguous key-shaped example strings. They
are semantically adapted references, not byte-identical upstream files. The active
ruleset uses the same representation. Tests compare actual Expr/CEL evaluation and
retain a non-allowlisted positive detector control; they do not contact providers
or assert that every upstream example was independently verified invalid.

Keep the compressed oracle bytes unchanged when changing explanatory prose. The
framework [scan notices](../../../../scan/NOTICE.md) identify the pinned sources
and licenses. No upstream executable is packaged or required at runtime.

External scanners may still flag synthetic inputs when examining Git history or
decompressing archives. Follow the framework README's
[scanner interoperability guidance](../../../../README.md#synthetic-fixtures-and-other-scanners).
Use observed finding identities for a compatible `.gitleaksignore`; a nested file
is not automatically a policy for GitHub, Wiz or Veracode. External exceptions are
project-owned, narrowly scoped and tested against a retained positive control.
