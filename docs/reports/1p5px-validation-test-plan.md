# Validation Test Plan — wave 1p5px (pack 1.6.1+p5qb)

Owner: Engineering
Status: active
Last verified: 2026-06-15

Test plan for downstream validation of wave `1p5px post-release-field-hardening` via the
provisional test pack **`wavefoundry-1.6.1.p5qb.zip`** (not a release — no tag, no GitHub
Release; `1.6.1` so it cleanly supersedes the shipped `1.6.0` on upgrade). Two independent
changes to validate, plus the upgrade itself. Captures the feedback this plan is seeking so
results map back to specific open questions.

Pack contents confirmed: `provider_policy.detect_cuda12_abi_gap`,
`accel_embedder._handle_cuda12_gap` (CUDA shim + warning), and the `1p5pz` secrets-gate change.

## 0. Upgrade + sanity (any host)

1. Place the zip in the repo root or `~/.wavefoundry/dist/`, run the upgrade, confirm
   `VERSION` shows `1.6.1+p5qb`.
2. Trigger an index build (`wave_index_build` or setup); confirm it completes and search works
   (`code_ask` / `code_search` return sane results).

**Feedback wanted:** did `1.6.0 → 1.6.1` apply cleanly (no migration errors, no manual steps)?
Index healthy afterward?

## A. CUDA-13 GPU warning — primary test (Arch/CachyOS, RTX 50xx, CUDA 13.x)

**Updated after field report 091yn/091yp:** the auto-shim was **removed** — a `.so.12→.so.13`
soname symlink can't work (CUDA 13 cuBLAS exports different ELF VERNEED symbols). `1p5py` is now
**warning-only**: actually using the GPU requires building `onnxruntime-gpu` from source against
CUDA 13 (operator action). This test now just confirms the warning is **loud, accurate, and not
silent**.

Run an index build (`wave_index_build` / setup) on the CUDA-13 host and confirm:

- A prominent, greppable **`[wavefoundry][GPU] WARNING: …`** line appears, naming the CUDA-12-ABI
  cause and the remediation **build onnxruntime-gpu from source / await a CUDA-13 wheel** (it must
  NOT suggest a `.so.12→.so.13` symlink).
- It fires **even on a fresh install** where the CUDA libs aren't on the linker path and ORT
  doesn't list `CUDAExecutionProvider` (091yn) — i.e. the warning is no longer silent.
- The build completes on CPU (no crash).

**Feedback wanted:**

1. Does the warning print? Paste the exact line.
2. Does it fire on a fresh install (CUDA libs not yet on the linker path)? *(091yn — the silent
   case we're fixing.)*
3. Is the remediation accurate/actionable (build-from-source), with no stale symlink suggestion?
4. (Optional) If you build `onnxruntime-gpu` from source against CUDA 13, does the GPU then
   engage and the warning stop? Rough GPU vs CPU timings.

## B. Secrets-gate new model `1p5pz` (any host — non-destructive)

Exercise with **synthetic** findings (no real secrets) and `dry_run` (no mutations). Create a
throwaway `docs/scan-findings.json` with entries at each status (redacted/fake `matched_text`),
then run `wave_close(mode='dry_run')` on an otherwise-closeable wave and observe:

| Finding status | Expected at `wave_close` |
| -------------- | ------------------------ |
| `pending` | **blocks** (`secrets_gate_unresolved`) |
| `suspected-secret` | **blocks** (even with a stale `acknowledged_for_wave`) |
| typo / unknown status | **blocks** (fail-closed) |
| `confirmed-secret` | **does NOT block**; response `data` has `confirmed_secrets` + `secrets_reminder` |
| `false-positive` (cleared) | clears silently, no reminder |

Then run the security reviewer (`seed-213`) on a `pending` finding and confirm it steers
"real secret → `confirmed-secret`" (never `false-positive`).

**Feedback wanted:**

1. With a `confirmed-secret` present, does the agent **surface the `secrets_reminder` on every
   close** (success and blocked paths)? Prominent enough?
2. Is "classify → `confirmed-secret` is non-blocking, just reminds" intuitive vs the old block?
3. Friction from `acknowledged_for_wave`/`override_reason` being dropped (e.g. legacy findings)?
4. Does fail-closed (unknown status blocks) ever get in the way?

## C. No-regression (Apple Silicon / CPU-only host, if available)

On a non-NVIDIA host, run an index build and confirm **no** `[wavefoundry][GPU] WARNING:` fires
and CoreML/CPU behaves exactly as on `1.6.0`.

**Feedback wanted:** confirm the CUDA path is fully inert off-NVIDIA (no spurious warnings, no
perf change).

## Report-back shape

Per test: PASS / FAIL / N/A, the outcome letter (A/B) for the CUDA test, exact warning/reminder
text, correctness + timing notes, and anything surprising.
