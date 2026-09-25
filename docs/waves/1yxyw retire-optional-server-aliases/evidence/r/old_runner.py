"""Wave 1yxyw old-runner upgrade matrix (Requirement 7, AC-4).

For each installed source (v1.25.0, v1.26.0 and the 1.27.0 source commit
902f7edc; no v1.27.0 tag exists), a scratch root whose path contains a space
gets that tree (``git archive``). A git tree carries no MANIFEST (the source
repository never commits one), so the proven case writes the MANIFEST the
release pack would have carried, with that source's own ``build_pack``; the
unproven case (``--unproven``) leaves it absent. The new pack is built from a
scratch copy of the current framework. The installed runner upgrades to it,
cleanup runs, and the tree must reach a working server (``server.py
--dry-run`` and a stdio ``wf_server_info``) with the retired flat files either
pruned (proven) or kept and reported (unproven). ``--confirm-hosts-stopped``
lets the installed process continue past the storage gate (no hosts run in the
scratch root), so pruning and its hook run in the installed runner; the run may
then pause for historical-memory validation (exit 4), which comes after pruning.
"""
import io, json, os, shutil, subprocess, sys, tarfile, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
PY = str(Path.home() / ".wavefoundry/venv/bin/python")
SCRIPTS_REL = ".wavefoundry/framework/scripts"
RETIRED = ("mcp_tool_registry", "codenav_handlers", "graph_handlers", "techdocs_handlers",
           "memory_handlers", "index_handlers", "upgrade_handlers", "edit_gate_handlers",
           "docs_handlers", "context_efficiency_handlers")
UNPROVEN = "--unproven" in sys.argv[1:]
SOURCES = [a for a in sys.argv[1:] if not a.startswith("--")] or ["v1.25.0", "v1.26.0", "902f7edc"]


def run(argv, cwd=None, timeout=1800):
    result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return result.returncode, result.stdout, result.stderr


def build_pack(work: Path) -> Path:
    framework = work / "pack source" / ".wavefoundry" / "framework"
    shutil.copytree(REPO / ".wavefoundry/framework", framework,
                    ignore=shutil.ignore_patterns("__pycache__", "index", "test-cache.json", "tests"))
    shutil.copy2(REPO / "CHANGELOG.md", framework.parent.parent / "CHANGELOG.md")
    sys.path.insert(0, str(framework / "scripts"))
    import build_pack
    out = work / "packs"
    out.mkdir()
    return build_pack.build_zip(out, "1.27.0", "r1yxyw", framework_dir=framework,
                                write_version=True, update_manifest=False)


def stdio_server_info(root: Path) -> dict:
    code = (
        "import asyncio, json, sys\n"
        "from mcp import ClientSession, StdioServerParameters\n"
        "from mcp.client.stdio import stdio_client\n"
        "async def main():\n"
        "    params = StdioServerParameters(command=sys.executable, args=[sys.argv[1], '--root', sys.argv[2]])\n"
        "    async with stdio_client(params) as (r, w):\n"
        "        async with ClientSession(r, w) as s:\n"
        "            await s.initialize()\n"
        "            res = await s.call_tool('wf_server_info', {})\n"
        "            print(json.dumps(json.loads(res.content[0].text)))\n"
        "asyncio.run(main())\n"
    )
    rc, out, err = run([PY, "-B", "-c", code, str(root / SCRIPTS_REL / "server.py"), str(root)], timeout=600)
    if rc != 0:
        return {"error": err[-2000:]}
    return json.loads(out.strip().splitlines()[-1])


def install(work: Path, source: str) -> Path:
    root = work / f"installed {source}"
    root.mkdir()
    archive = subprocess.run(["git", "-C", str(REPO), "archive", source], capture_output=True, check=True).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(root, filter="data")
    if not UNPROVEN:
        framework = root / ".wavefoundry" / "framework"
        code = ("import sys; from pathlib import Path; sys.path.insert(0, sys.argv[1]); import build_pack; "
                "fw = Path(sys.argv[2]); build_pack.write_manifest(fw, build_pack.collect_files(fw))")
        rc, _out, err = run([PY, "-B", "-c", code, str(framework / "scripts"), str(framework)])
        assert rc == 0, err[-2000:]
    for args in (["init", "-q"], ["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@example.invalid",
                                                  "commit", "-q", "-m", "installed"]):
        subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
    return root


def main() -> int:
    ok = True
    with tempfile.TemporaryDirectory(prefix="wf 1yxyw old runner ") as temp:
        work = Path(temp)
        pack = build_pack(work)
        print(json.dumps({"pack": pack.name, "unproven": UNPROVEN}), flush=True)
        for source in SOURCES:
            root = install(work, source)
            scripts = root / SCRIPTS_REL
            entry = {"manifest_installed": (root / ".wavefoundry/framework/MANIFEST").is_file(),
                     "retired_before": sorted(n for n in RETIRED if (scripts / f"{n}.py").is_file())}
            rc, out, err = run([PY, "-B", str(scripts / "upgrade_wavefoundry.py"),
                                "--root", str(root), "--pack", str(pack), "--yes", "--confirm-hosts-stopped"])
            text = out + err
            entry["upgrade_exit"] = rc
            entry["upgrade_tail"] = text.strip().splitlines()[-15:]
            entry["pruning_phase_ran"] = "Phase 2: Pruning" in text
            entry["prune_lines"] = [l.strip() for l in text.splitlines()
                                    if "Prune mode" in l or "Pruning complete" in l or "pruning is unproven" in l
                                    or "could not be proven" in l][:4]
            entry["hook_warning"] = [l.strip() for l in text.splitlines() if "retired flat server module" in l]
            rc, out, err = run([PY, "-B", str(scripts / "upgrade_wavefoundry.py"), "--root", str(root),
                                "--cleanup", "--yes"])
            entry["cleanup_exit"] = rc
            entry["retired_after"] = sorted(n for n in RETIRED if (scripts / f"{n}.py").is_file())
            entry["retained_aliases_ok"] = all(
                (scripts / f"{n}.py").read_text().startswith("import importlib")
                for n in ("server_impl", "dashboard_handlers"))
            rc, out, err = run([PY, "-B", str(scripts / "server.py"), "--root", str(root), "--dry-run"])
            entry["dry_run"] = {"exit": rc, "tail": (out + err).strip().splitlines()[-2:],
                                "stderr_warning": "retired flat server module" in err}
            info = stdio_server_info(root)
            entry["wf_server_info"] = ({"status": info.get("status"),
                                        "server_impl_version": (info.get("data") or {}).get("server_impl_version"),
                                        "diagnostic_codes": [d.get("code") for d in info.get("diagnostics") or []]}
                                       if "error" not in info else info)
            if UNPROVEN:
                expected_left = entry["retired_before"]
                good = (entry["retired_after"] == expected_left
                        and (not expected_left or (entry["hook_warning"] and entry["dry_run"]["stderr_warning"]
                             and "retired_flat_module_leftover" in entry["wf_server_info"].get("diagnostic_codes", []))))
            else:
                good = entry["retired_after"] == [] and not entry["hook_warning"]
            good = good and entry["upgrade_exit"] in (0, 4) and entry["pruning_phase_ran"] \
                and entry["dry_run"]["exit"] == 0 \
                and entry["wf_server_info"].get("status") == "ok" and entry["retained_aliases_ok"]
            entry["verdict"] = "ok" if good else "FAILED"
            ok &= good
            print(json.dumps({source: entry}, indent=1), flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
