"""Wave 1yxyw: graph definition ownership after the retired aliases are removed.

Compares the live project graph (built for the E2' receipt) with the recorded
wave 1yzd0 after-move summary. Expected: no retired flat file in the graph, the
two retained flat aliases define nothing, every package file owns the same
definition count as after 1yzd0 except server_impl (+2: retired_flat_leftovers
and _retired_flat_leftover_warning), and handler-to-server_impl call edges are
unchanged.
"""
import json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO / "docs/waves/1yzd0 server-package-boundary/evidence/m"))
import graph_ownership as prior  # the 1yzd0 summarizer, reused unchanged

RETIRED = ["mcp_tool_registry", "codenav_handlers", "graph_handlers", "techdocs_handlers", "memory_handlers",
           "index_handlers", "upgrade_handlers", "edit_gate_handlers", "docs_handlers",
           "context_efficiency_handlers"]


def main() -> int:
    recorded = (REPO / "docs/waves/1yzd0 server-package-boundary/evidence/m/graph_ownership.out").read_text()
    before = json.loads(recorded[:recorded.index("RESULT:")])["after"]
    now = prior.summarize(REPO / ".wavefoundry/index/index.sqlite")
    print(json.dumps({"after_1yzd0": before, "after_1yxyw": now}, indent=1))
    expected = {n: v["package"] + (2 if n == "server_impl" else 0) for n, v in before["definition_owners"].items()}
    owners_ok = all(now["definition_owners"][n]["flat"] == 0 and now["definition_owners"][n]["package"] == expected[n]
                    for n in prior.MOVED)
    files_ok = (not set(RETIRED) & set(now["flat_alias_files_present"])
                and sorted(now["package_files_present"]) == sorted(prior.MOVED))
    edges_ok = now["handler_to_server_impl_calls"] == before["handler_to_server_impl_calls"]
    result = "OK" if owners_ok and files_ok and edges_ok else f"owners_ok={owners_ok} files_ok={files_ok} edges_ok={edges_ok}"
    print("RESULT:", result)
    return 0 if result == "OK" else 1


if __name__ == "__main__":
    sys.exit(main())
