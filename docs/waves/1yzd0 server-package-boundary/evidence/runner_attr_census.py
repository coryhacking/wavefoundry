"""Which server_impl attributes does each runner/consumer read, and does HEAD's
server_impl module namespace still bind them? (old-runner matrix evidence)

PREDICATE: attribute reads ``server_impl.<name>`` (and ``srv.<name>`` in
memory_eval where ``import server_impl as srv``) in the given sources, vs the
set of names bound at module top level of HEAD server_impl.py (def/class/
assign/annassign/import/import-from targets, incl. inside module-level try/if).
"""
import ast
import subprocess
from pathlib import Path

REPO = Path("/Users/coryhacking/Developer/wavefoundry")
SP = ".wavefoundry/framework/scripts/"


def git_show(rev, rel):
    return subprocess.run(["git", "-C", str(REPO), "show", f"{rev}:{SP}{rel}"], capture_output=True, text=True, check=True).stdout


def bound_names(src):
    tree = ast.parse(src)
    names = set()

    def visit(body):
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(node.name)
            elif isinstance(node, ast.Assign):
                for t in node.targets:
                    for n in ast.walk(t):
                        if isinstance(n, ast.Name):
                            names.add(n.id)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                names.add(node.target.id)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for a in node.names:
                    names.add((a.asname or a.name).split(".")[0])
            elif isinstance(node, (ast.If, ast.Try, ast.With, ast.For)):
                for field in ("body", "orelse", "finalbody"):
                    visit(getattr(node, field, []) or [])
                for h in getattr(node, "handlers", []) or []:
                    visit(h.body)
    visit(tree.body)
    return names


def reads(src, aliases=("server_impl",)):
    out = set()
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id in aliases:
            out.add(n.attr)
    return out


head_names = bound_names((REPO / SP / "server_impl.py").read_text())
cases = [
    ("v1.25.0", "server.py", ("server_impl",)),
    ("v1.26.0", "server.py", ("server_impl",)),
    ("HEAD", "server.py", ("server_impl",)),
    ("v1.25.0", "upgrade_wavefoundry.py", ("server_impl",)),
    ("v1.26.0", "upgrade_wavefoundry.py", ("server_impl",)),
    ("v1.26.0", "upgrade_extensions.py", ("server_impl",)),
    ("HEAD", "memory_eval.py", ("srv",)),
    ("HEAD", "retrieval_eval.py", ("server", "loaded_server")),
]
for rev, rel, aliases in cases:
    src = git_show(rev, rel) if rev != "HEAD" else (REPO / SP / rel).read_text()
    r = reads(src, aliases)
    missing = sorted(r - head_names)
    print(f"{rev}:{rel}: reads {len(r)} attrs; missing from HEAD server_impl namespace: {missing}")
print(f"HEAD server_impl top-level bound names: {len(head_names)}")
