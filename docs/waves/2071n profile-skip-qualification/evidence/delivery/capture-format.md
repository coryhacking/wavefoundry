# Qualification worker capture format

Owner: Engineering
Status: active
Last verified: 2026-10-09

The initial and final raw worker captures retain the original unittest stdout, stderr, argv and return code. Each stdout/stderr string is stored as ordered chunks of at most 1024 characters so every evidence line remains within the scanner limit. Concatenate the chunks to recover the original string; null remains null.

`original_capture_sha256` authenticates the original capture JSON bytes. Reconstruct a dictionary in the order argv, returncode, stdout, stderr, then serialize with Python `json.dumps(record, indent=2).encode()` without a trailing newline. The conversion checked exact byte equality before writing each initial capture. The external originals remain unchanged for the exact skip auditor.

These artifacts observe test output. They do not modify test results, bypass a skipped assertion, or establish live operator-index qualification.

## Retention

The worker manifests and qualification summaries retain the historical complete-run identities, hashes and return codes. After independent audit, uncited routine green bodies were pruned on operator instruction; retained raw bodies contain skips, failures or direct references. Reproduce current qualification through the canonical runner. Historical audit scripts describe the original complete captures and cannot be replayed against the pruned subset. See wave.md for the cleanup disposition.
