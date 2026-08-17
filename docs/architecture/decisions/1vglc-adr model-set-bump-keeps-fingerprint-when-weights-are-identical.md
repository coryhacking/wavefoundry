# 1vglc-adr — A model-set bump keeps the embedding fingerprint when no weight changes; set 3 corrects one reference byte in set 2

Owner: Engineering
Status: accepted
Last verified: 2026-08-16

## Context

Wavefoundry ships offline models as an independently versioned asset (`wavefoundry-models-<set>.zip`) at the permanent `models` release tag. Two identity constants govern it: `MODEL_SET_VERSION` selects which asset an upgrade installs, and `EMBEDDING_COMPATIBILITY_FINGERPRINT` is the embedding identity every project index is keyed on (`indexer.py`, `upgrade_wavefoundry.py`); a fingerprint change forces every consumer to re-embed.

Model set 2 shipped one defective member: the arctic clean-ONNX component's `refs/main` carried a trailing newline (41 bytes instead of the 40-character sha), and the canonical verification manifest pinned the sha256 of that byte-shape. huggingface_hub resolves the symbolic revision `main` by reading `refs/main` verbatim, so every `local_files_only=True` lookup on a bundle-provisioned cache missed; the cached-first download fell through to an unpinned Hub download that repointed the cache at a newer head; and `build_bundle`'s exact-manifest gate then refused forever ("warmed model cache does not match the canonical verification manifest"). Because `--release` requires `--with-models`, releases 1.16.4 and 1.17.0 shipped by hand. No local byte state could satisfy both huggingface_hub and the manifest.

The arctic weights are byte-identical across the two Hub revisions involved (`d3c1d2d4...` and `e596f507...`): fp16 export, int8 export, and tokenizer all hash equal (executed 2026-08-16, wave `1vglb`). Only reference bytes differ.

## Decision

Model set 3 is published to correct the reference byte, and it **keeps `EMBEDDING_COMPATIBILITY_FINGERPRINT` unchanged** (`wf-model-set-2-20260811-arctic-s`). The rule this sets: a model-set bump changes the fingerprint **only when weights, pooling, or precision change**; a bump that alters packaging, references, manifests, or metadata while leaving every weight byte identical keeps the fingerprint so no existing index re-embeds. The decision rests on an executed byte comparison recorded in the wave, not on the assertion that reference-only bumps are safe in general; a future bump must re-execute the comparison before reusing this precedent.

Alongside: `refs/*` members are normalized (stripped) at build, in the manifest, at install, and in every on-disk cache hasher, through one helper (`_normalized_ref_bytes`), and the cached-first online fallback pins the canonical revision for managed repos so a cache miss can never drift the cache again.

## Consequences

**Positive:**
- Every 1.16.x/1.17.0 index stays valid; set 3 installs over set 2 atomically on the next upgrade via the existing version compare, with no re-embed.
- Fresh installs resolve `main` offline on the first lookup; the 100 MB unpinned re-download on first index build disappears.
- `--with-models` builds again on the release machine, restoring the one-command `--release`.
- The manifest describes bytes as huggingface_hub reads them, so build, install, and attestation agree.

**Negative / tradeoffs:**
- Two set numbers now share one fingerprint, which reads as unusual; the constant's comment and this ADR explain why.
- The `models` tag carries both `wavefoundry-models-2.zip` (for older feature packs that declare set 2) and `wavefoundry-models-3.zip`.

**Constraints imposed:**
- A future model-set bump that changes any weight byte MUST change the fingerprint; the executed byte compare is the required evidence either way.
- `refs/*` bytes are never packed, hashed, or written verbatim; every path goes through the normalizing helper.
- The cached-first online branch stays pinned; removing the pin reopens the drift class.

## Alternatives Considered

| Alternative | Reason rejected |
|-------------|----------------|
| Tolerant code only, keep set 2 published | Leaves a defective asset at the `models` tag and every fresh install one index build away from an unpinned re-download. |
| Regenerate the manifest against the drifted local cache | Would canonize a two-snapshot cache and drift the shipped contract; set 2 is published. |
| Bump the fingerprint with set 3 | Forces every consumer to re-embed for a change that touches no weight; the executed byte compare shows nothing to re-embed for. |
| Pin the fallback only, no set 3 | Stops the drift but not the first-lookup miss on the newline. |
| Add an escape flag to the `--release`-requires-`--with-models` pre-flight | Reintroduces the by-hand release class the invariant exists to prevent. |
