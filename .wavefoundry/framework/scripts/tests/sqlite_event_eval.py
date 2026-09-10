"""Real quiet-period monitor/public-reader comparison on disposable corpora.

Run after golden timing, once per isolated frozen runtime. This uses real model
inference, filesystem edits, the production background refresh and public search
responses. It changes neither the source corpus nor the developer's live index.
"""
from __future__ import annotations

import argparse
import asyncio
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import threading

from sqlite_update_eval import distribution


FILES = ("docs/benchmark-publication-a.md", "docs/benchmark-publication-b.md",
         "src/benchmark_publication_a.py", "src/benchmark_publication_b.py")
QUERY = "fluxor sentinel benchmark publication current revision"


def content(revision):
    marker = f"revision_epoch_{revision}"
    return tuple(
        f"# Fluxor sentinel benchmark publication {letter}\n\nCurrent revision is {marker}.\n"
        for letter in ("a", "b")) + tuple(
        f'def benchmark_publication_{letter}():\n    """Fluxor sentinel benchmark publication is {marker}."""\n'
        f'    return "{marker}"\n' for letter in ("a", "b"))


def result_markers(response):
    found = {}
    for row in response.get("data", {}).get("results", []):
        if row.get("path") in FILES:
            found.setdefault(row["path"], set()).update(
                re.findall(r"revision_epoch_[A-Za-z0-9]+", json.dumps(row)))
    return {path: sorted(markers) for path, markers in found.items()}


def validate_markers(markers, reader, revision):
    expected_paths = set(FILES[2:] if reader % 2 else FILES[:2])
    if revision is None:
        if markers:
            raise RuntimeError("Deleted sentinel appears in published search")
    elif not expected_paths.issubset(markers) or any(
            values != [f"revision_epoch_{revision}"] for values in markers.values()):
        raise RuntimeError(f"Published sentinel coverage/revision is wrong: {markers}")


def response_classification(status, mode, diagnostics):
    if status == "ok":
        return "indexed" if mode in {"semantic", "hybrid"} else "degraded"
    if status == "error" and "index_not_ready" in diagnostics:
        return "epoch_refusal"
    return "unexpected_error"


def compare_reports(baseline, candidate):
    checks = {
        "complete_protocol": all(r["status"] == "measured" and r["requested_cycles"] >= 10
                                 and len(r["cycles"]) == 2 * r["requested_cycles"]
                                 and all(all(c["coverage"].values()) and not c["reader_errors"]
                                         for c in r["cycles"]) for r in (baseline, candidate)),
        "same_schedule_and_models": all(baseline[key] == candidate[key] for key in (
            "reader_count", "queries_per_reader_per_phase", "schedule_seconds", "requested_cycles",
            "monitor", "provider_request", "models", "observed_models", "initial_inventory")),
        "stable_models": all(r["observed_models"] == r["final_observed_models"] for r in (baseline, candidate)),
        "observed_native_sessions": all(
            r["observed_models"]["embedders"] and r["observed_models"]["reranker"]
            and all(model and model["session_providers"] and model["input_shapes"]
                    for model in [*r["observed_models"]["embedders"].values(), r["observed_models"]["reranker"]])
            for r in (baseline, candidate)),
        "same_attempts": baseline["attempted"] == candidate["attempted"],
        "no_additional_unavailable": candidate["unavailable"] <= baseline["unavailable"],
        "no_errors_or_mixed_epochs": all(r["errors"] == r["unexpected_error_responses"] == r["accepted_mixed"] == 0
                                        for r in (baseline, candidate)),
        "event_p95_within_budget": candidate["event_to_searchable"]["p95_ms"] <= 1.10 * baseline["event_to_searchable"]["p95_ms"],
    }
    return {"passed": all(checks.values()), "checks": checks}


def run(args):
    if args.cycles < 1 or args.schedule_seconds < 1 or args.query_interval_seconds < 1:
        raise ValueError("Cycles, schedule duration and query interval must be positive")
    schedule = list(range(0, args.schedule_seconds, args.query_interval_seconds))
    runtime = args.runtime.resolve()
    sys.path.insert(0, str(runtime))
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
                      WAVEFOUNDRY_EMBED_PROVIDER=args.provider)
    os.environ.pop("WAVEFOUNDRY_DISABLE_RERANKER", None)
    os.environ.pop("WAVEFOUNDRY_DISABLE_LEXICAL_FUSION", None)
    import indexer
    import index_state_store as state
    import server_impl as server
    import apsw

    root = args.work.resolve()
    receipt_path = root.with_name(root.name + ".event-result.json")
    log_path = root.with_name(root.name + ".initial-build.log")
    if root.exists():
        raise RuntimeError("Use a new disposable output directory")
    shutil.copytree(args.source.resolve(), root, ignore=shutil.ignore_patterns(
        "index-state.sqlite", "index-state.sqlite-wal", "index-state.sqlite-shm",
        "index-build.lock", "sqlite-migration.json", "upgrade.lock",
        "upgrade-in-progress.json", "__pycache__"))
    index_dir = root / ".wavefoundry/index"
    source_conn = apsw.Connection(str(args.source.resolve() / ".wavefoundry/index/index-state.sqlite"),
                                 flags=apsw.SQLITE_OPEN_READONLY)
    dest_conn = apsw.Connection(str(index_dir / "index-state.sqlite"))
    try:
        with dest_conn.backup("main", source_conn, "main") as backup:
            while not backup.done:
                backup.step(256)
    finally:
        dest_conn.close()
        source_conn.close()
    # The corpus contains a historical installed runner. Keep identical corpus
    # bytes in both lanes, but route its real background subprocess to the
    # selected frozen implementation. No monitor, model or publication logic is
    # replaced. This common fixture launcher is indexed identically in both lanes.
    os.environ["WAVEFOUNDRY_EVAL_RUNTIME"] = str(runtime)
    (root / ".wavefoundry/framework/scripts/indexer.py").write_text(
        "import os,runpy,sys\nfrom pathlib import Path\n"
        "runtime=Path(os.environ['WAVEFOUNDRY_EVAL_RUNTIME'])\n"
        "sys.path.insert(0,str(runtime))\n"
        "sys.argv[0]=str(runtime/'indexer.py')\n"
        "runpy.run_path(sys.argv[0],run_name='__main__')\n")
    config_path = root / "docs/workflow-config.json"
    config = json.loads(config_path.read_text())
    config.setdefault("indexing", {})["monitor"] = {
        "enabled": True, "interval_seconds": 5, "quiet_period_seconds": 5}
    config_path.write_text(json.dumps(config, indent=2) + "\n")
    for rel, text in zip(FILES, content("initial")):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    # Normal foreground convergence happens before measurement. No fake
    # embedder, precision shim, clock patch or manual publication token.
    with log_path.open("w") as log:
        built = subprocess.run([sys.executable, "-B", str(runtime / "indexer.py"),
                                "--root", str(root), "--content", "all"],
                               stdout=log, stderr=subprocess.STDOUT, timeout=900)
    if built.returncode or state.build_epoch_token(index_dir) is None:
        raise RuntimeError(f"Initial real index convergence failed; inspect {log_path}")

    handler = server.ImplHandler(root)
    handler._stop_ce_projection_monitor()
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP("sqlite-event-evaluation")
    server.register_mcp_surface(mcp, lambda: handler)
    tracing = threading.local()
    original_epoch = server._epoch_state
    def observed_epoch(path):
        value = original_epoch(path)
        rows = getattr(tracing, "rows", None)
        if rows is not None:
            rows.append({"at": time.perf_counter(), "state": value})
        return value
    server._epoch_state = observed_epoch  # observation only: actual returned state is unchanged
    report = {"lane": args.lane, "status": "running", "source": str(args.source.resolve()),
              "runtime": str(runtime), "provider_request": args.provider,
              "monitor": server._read_monitor_config(root), "cycles": [],
              "reader_count": 4, "queries_per_reader_per_phase": len(schedule),
              "schedule_seconds": schedule,
              "requested_cycles": args.cycles, "minimum_cycles_met": args.cycles >= 10,
              "background_runtime_routing": "identical disposable indexer launcher; real frozen indexer via WAVEFOUNDRY_EVAL_RUNTIME",
              "models": state.export_meta_snapshot(index_dir).get("model_versions"),
              "source_hashes": {name: hashlib.sha256((runtime / name).read_bytes()).hexdigest()
                                for name in ("indexer.py", "server_impl.py", "index_state_store.py", "accel_embedder.py")}}

    def observed_models():
        def identity(model):
            if model is None:
                return None
            session = getattr(model, "session", None)
            if session is None:
                # fastembed.TextEmbedding -> OnnxTextEmbedding -> ORT session.
                session = getattr(getattr(model, "model", None), "model", None)
            return {"type": type(model).__name__, "model": getattr(model, "model_name", None),
                    "provider": getattr(model, "provider", None),
                    "session_providers": session.get_providers() if session else None,
                    "input_shapes": [item.shape for item in session.get_inputs()] if session else None}
        return {"embedders": {name: identity(model) for name, model in handler.index._embedders.items()},
                "reranker": identity(handler.index._reranker)}

    def search(reader):
        name = "code_search" if reader % 2 else "docs_search"
        arguments = {"query": QUERY, "limit": 7}
        if reader % 2:
            arguments.update(kind="code", max_per_file=1, graph=False)
        return asyncio.run(mcp._tool_manager.call_tool(
            name, arguments, context=mcp.get_context(), convert_result=False))

    def inventory():
        result = {}
        predicate = "path IN (" + ",".join("'" + path + "'" for path in FILES) + ")"
        for layer in ("docs", "code"):
            if args.lane == "sqlite":
                import sqlite_vector_store as vectors
                rows = vectors.payload_rows(index_dir, layer, predicate=predicate, include_vector=True)
            else:
                table = indexer._get_lance_db(index_dir).open_table(layer)
                rows = table.search().where(predicate).limit(None).to_list()
            result[layer] = {row["id"]: {"path": row["path"], "text": row.get("text", "")} for row in rows}
        return result

    def assert_public(response, reader, revision):
        mode = response.get("data", {}).get("search_mode")
        if response.get("status") != "ok" or mode not in {"semantic", "hybrid"}:
            raise RuntimeError(f"Expected published semantic retrieval: {response.get('diagnostics')}")
        markers = result_markers(response)
        validate_markers(markers, reader, revision)

    def readers(reader, origin):
        rows = []
        for scheduled in schedule:
            delay = origin + scheduled - time.perf_counter()
            if delay > 0:
                time.sleep(delay)
            start = time.perf_counter()
            tracing.rows = []
            try:
                response = search(reader)
                mode = response.get("data", {}).get("search_mode")
                indexed = response.get("status") == "ok" and mode in {"semantic", "hybrid"}
                epochs = tracing.rows
                stable = bool(len(epochs) >= 2 and epochs[0]["state"] == epochs[-1]["state"]
                              and epochs[0]["state"] and epochs[0]["state"][1] == "complete")
                markers = result_markers(response)
                diagnostics = [d.get("code") for d in response.get("diagnostics", [])]
                rows.append({"reader": reader, "scheduled_s": scheduled,
                             "started_s": start - origin, "ended_s": time.perf_counter() - origin,
                             "late_start_ms": max(0, start - origin - scheduled) * 1000,
                             "latency_ms": (time.perf_counter() - start) * 1000,
                             "status": response.get("status"), "search_mode": mode,
                             "available": response.get("status") == "ok", "accepted_indexed": indexed,
                             "epoch_reads": [{"at_s": item["at"] - origin, "state": item["state"]} for item in epochs],
                             "epoch_guard_violation": indexed and not stable, "markers": markers,
                             "diagnostics": diagnostics,
                             "classification": response_classification(response.get("status"), mode, diagnostics)})
            except Exception as exc:
                rows.append({"reader": reader, "scheduled_s": scheduled, "available": False,
                             "accepted_indexed": False, "classification": "exception",
                             "error": f"{type(exc).__name__}: {exc}"})
            finally:
                tracing.rows = None
        return rows

    try:
        initial = inventory()
        if not all(initial.values()):
            raise RuntimeError("Both sentinel layer inventories must exist before mutation")
        for reader in range(4):
            assert_public(search(reader), reader, "initial")
        report["initial_inventory"] = initial
        report["observed_models"] = observed_models()
        revision = "initial"
        with ThreadPoolExecutor(max_workers=4) as pool:
            for cycle in range(args.cycles):
                for action in ("delete", "reinsert"):
                    previous_poll = handler._index_monitor_status.get("last_checked_at")
                    deadline = time.perf_counter() + 30
                    while time.perf_counter() < deadline:
                        status = handler._index_monitor_status
                        if (status.get("last_checked_at") != previous_poll
                                and status.get("reason") == "current_or_undetermined"):
                            break
                        time.sleep(.02)
                    else:
                        raise RuntimeError("No clean monitor poll before the next change")
                    prior = original_epoch(root)
                    if not prior or prior[1] != "complete":
                        raise RuntimeError("Mutation requires a complete prior epoch")
                    origin = time.perf_counter()
                    if action == "delete":
                        for rel in FILES:
                            (root / rel).unlink()
                        desired = None
                    else:
                        for rel, text in zip(FILES, content(str(cycle))):
                            (root / rel).write_text(text)
                        desired = str(cycle)
                    futures = [pool.submit(readers, reader, origin) for reader in range(4)]
                    observed = None
                    observations = []
                    published = None
                    while time.perf_counter() - origin < 90:
                        token = original_epoch(root)
                        observations.append({"at_s": time.perf_counter() - origin, "state": token})
                        if token and token[1] == "complete" and token != prior:
                            actual = inventory()
                            expected = {layer: {} if desired is None else {
                                key: {"path": row["path"], "text": row["text"].replace(
                                    "revision_epoch_initial", f"revision_epoch_{desired}")}
                                for key, row in rows.items()} for layer, rows in initial.items()}
                            if actual != expected:
                                raise RuntimeError("Complete epoch does not match both exact sentinel inventories")
                            for reader in (0, 1):
                                assert_public(search(reader), reader, desired)
                            observed = (time.perf_counter() - origin) * 1000
                            published = token
                            break
                        time.sleep(.1)
                    results = [row for future in futures for row in future.result(timeout=120)]
                    epoch_reads = [item for row in results for item in row.get("epoch_reads", [])]
                    coverage = {"before": any(item["state"] == prior for item in epoch_reads),
                                "during": any(item["state"] and item["state"][1] == "building" for item in epoch_reads),
                                "after": any(item["state"] == published for item in epoch_reads)}
                    errors = []
                    for row in results:
                        if row.get("epoch_guard_violation"):
                            errors.append("registered tool accepted unstable/incomplete epoch")
                        if row.get("accepted_indexed") and not row.get("epoch_guard_violation"):
                            captured = row["epoch_reads"][0]["state"]
                            expected_revision = revision if captured == prior else desired if captured == published else "unknown"
                            try:
                                if expected_revision == "unknown":
                                    raise RuntimeError("Unrecognized complete epoch")
                                validate_markers(row["markers"], row["reader"], expected_revision)
                            except RuntimeError as exc:
                                errors.append(str(exc))
                        if row.get("classification") in {"unexpected_error", "exception"}:
                            errors.append(f"Public reader {row['classification']}: {row.get('diagnostics', row.get('error'))}")
                    entry = {"cycle": cycle, "action": action, "event_to_searchable_ms": observed,
                             "prior_epoch": prior, "published_epoch": published, "coverage": coverage,
                             "reader_errors": errors, "readers": results, "observed_epochs": observations,
                             "monitor_last": dict(handler._index_monitor_status)}
                    report["cycles"].append(entry)
                    receipt_path.write_text(json.dumps(report, indent=2) + "\n")
                    print(json.dumps({"cycle": cycle, "action": action, "event_ms": observed,
                                      "coverage": coverage, "errors": errors}), flush=True)
                    if observed is None or not all(coverage.values()):
                        raise RuntimeError("Inconclusive: fixed reader schedule missed publication coverage")
                    if errors:
                        raise RuntimeError("Public reader failed epoch/content consistency")
                    revision = desired
        events = [entry["event_to_searchable_ms"] for entry in report["cycles"]]
        calls = [row for entry in report["cycles"] for row in entry["readers"]]
        report["final_observed_models"] = observed_models()
        report.update(status="measured", event_to_searchable=distribution(events),
                      attempted=len(calls), available=sum(row["available"] for row in calls),
                      accepted_indexed=sum(row["accepted_indexed"] for row in calls),
                      unavailable=sum(not row["available"] for row in calls),
                      errors=sum("error" in row for row in calls),
                      unexpected_error_responses=sum(row.get("classification") == "unexpected_error" for row in calls),
                      epoch_refusals=sum(row.get("classification") == "epoch_refusal" for row in calls),
                      accepted_mixed=sum(row.get("epoch_guard_violation", False) for row in calls))
    finally:
        server._epoch_state = original_epoch
        handler.close()
        receipt_path.write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(json.dumps({"status": report["status"], "lane": args.lane,
                      "result": str(receipt_path)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", choices=("baseline", "sqlite"), required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--provider", default="coreml")
    parser.add_argument("--cycles", type=int, default=10)
    parser.add_argument("--schedule-seconds", type=int, default=30)
    parser.add_argument("--query-interval-seconds", type=int, default=3)
    run(parser.parse_args())
