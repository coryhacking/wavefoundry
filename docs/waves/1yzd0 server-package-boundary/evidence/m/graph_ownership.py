"""Wave 1yzd0 AC-6: graph definition ownership and handler-to-composition-root
call edges, baseline (E0 commit, scratch graph build) versus after the move."""
import json, sqlite3, sys
from pathlib import Path

PREFIX = ".wavefoundry/framework/scripts/"
MOVED = ["server_impl", "mcp_tool_registry", "codenav_handlers", "graph_handlers", "techdocs_handlers",
         "memory_handlers", "index_handlers", "upgrade_handlers", "edit_gate_handlers",
         "dashboard_handlers", "docs_handlers", "context_efficiency_handlers"]
DEFINITION_KINDS = ("function", "method", "class")


def summarize(db: Path) -> dict:
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    flat = {n: PREFIX + n + ".py" for n in MOVED}
    pkg = {n: PREFIX + "wf_server/" + n + ".py" for n in MOVED}
    q = ("SELECT source_file, COUNT(*) FROM graph_nodes WHERE kind IN (%s) GROUP BY source_file"
         % ",".join("?" * len(DEFINITION_KINDS)))
    defs = dict(conn.execute(q, DEFINITION_KINDS).fetchall())
    owners = {n: {"flat": defs.get(flat[n], 0), "package": defs.get(pkg[n], 0)} for n in MOVED}
    handler_files = [flat[n] for n in MOVED if n.endswith("_handlers")] + [pkg[n] for n in MOVED if n.endswith("_handlers")]
    impl_files = (flat["server_impl"], pkg["server_impl"])
    edges = conn.execute(
        "SELECT COUNT(*) FROM graph_edges e JOIN graph_nodes t ON t.node_id = e.target_id "
        "WHERE e.relation = 'calls' AND e.source_file IN (%s) AND t.source_file IN (?, ?)"
        % ",".join("?" * len(handler_files)), (*handler_files, *impl_files)).fetchone()[0]
    files = {row[0] for row in conn.execute("SELECT DISTINCT source_file FROM graph_nodes")}
    conn.close()
    return {"definition_owners": owners, "handler_to_server_impl_calls": edges,
            "flat_alias_files_present": sorted(n for n in MOVED if flat[n] in files),
            "package_files_present": sorted(n for n in MOVED if pkg[n] in files)}


def main() -> int:
    baseline, after = (summarize(Path(p)) for p in sys.argv[1:3])
    print(json.dumps({"baseline": baseline, "after": after}, indent=1))
    moved_ok = all(after["definition_owners"][n]["flat"] == 0
                   and after["definition_owners"][n]["package"] == baseline["definition_owners"][n]["flat"]
                   for n in MOVED)
    edges_ok = after["handler_to_server_impl_calls"] == baseline["handler_to_server_impl_calls"]
    print("RESULT:", "OK" if moved_ok and edges_ok else f"moved_ok={moved_ok} edges_ok={edges_ok}")
    return 0 if moved_ok and edges_ok else 1


if __name__ == "__main__":
    sys.exit(main())
