#!/usr/bin/env python3
"""1p7it bench: build the code+docs semantic index at a forced embed_buffer_chunks,
bypassing the EMBED_BATCH_SIZE floor, so we can measure peak RSS vs buffer size.

Run under `/usr/bin/time -l` to capture peak RSS:
  /usr/bin/time -l ~/.wavefoundry/venv/bin/python -B experiments/buffer_bench.py --buffer 256
"""
import argparse
import importlib.util
import sys
from pathlib import Path

ROOT = Path("/Users/coryhacking/Developer/wavefoundry")


def _load(name):
    spec = importlib.util.spec_from_file_location(
        name, ROOT / ".wavefoundry/framework/scripts" / f"{name}.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--buffer", type=int, required=True)
    ap.add_argument("--limit", type=int, default=0, help="cap the corpus to the first N walked files (0 = all)")
    ap.add_argument("--max-file-bytes", type=int, default=0, help="skip files larger than this (drops the giant scripts that dominate CPU time)")
    ap.add_argument("--batch", type=int, default=0, help="forward-pass batch size (EMBED_BATCH_SIZE) — the onnxruntime activation-tensor width; 0 = leave default")
    ap.add_argument("--content", default="all", help="docs | code | all — isolate a single model (docs=arctic-xs, code=bge-small)")
    args = ap.parse_args()
    indexer = _load("indexer")
    # Force the streaming-flush buffer to the requested size, bypassing the
    # max(val, EMBED_BATCH_SIZE) floor so we can probe sub-256 values.
    indexer._resolve_embed_buffer_chunks = lambda root: args.buffer
    # Forward-pass batch width: the actual onnxruntime activation-tensor size
    # (batch x seq x hidden), distinct from the flush buffer. THIS is the suspected
    # CPU memory driver — a 256x512 bge-small pass materializes multi-GB attention.
    if args.batch:
        indexer.EMBED_BATCH_SIZE = args.batch
    # Smaller-corpus mode: drop giant files (they front-load chunk count + CPU
    # time) and/or cap the count — keeps CPU runs fast while still exceeding the
    # buffer so 256 vs 2048 flush differently.
    if args.limit or args.max_file_bytes:
        _orig_walk = indexer.walk_repo

        def _capped(root, **kw):
            files = _orig_walk(root, **kw)
            if args.max_file_bytes:
                files = [f for f in files if f.stat().st_size <= args.max_file_bytes]
            if args.limit:
                files = files[: args.limit]
            return files

        indexer.walk_repo = _capped
    # Throwaway index dir: never touch the live .wavefoundry/index (the capped
    # corpus would truncate it) or contend on its build lock.
    bench_index = "/tmp/wf_bench_index"
    print(f"== content={args.content}, buffer_chunks={args.buffer}, batch={args.batch or 'default'}, limit={args.limit or 'all'} files ==", flush=True)
    return indexer.main(
        ["--content", args.content, "--full", "--root", str(ROOT), "--index-dir", bench_index]
    )


if __name__ == "__main__":
    sys.exit(main())
