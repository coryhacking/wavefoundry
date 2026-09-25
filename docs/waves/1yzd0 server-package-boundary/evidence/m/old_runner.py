"""Wave 1yzd0 old-runner upgrade matrix (Requirement 6, AC-5).

For each installed release, a scratch root whose path contains a space gets
the tagged tree (``git archive``). The new pack is built from a scratch copy
of the current framework. The installed runner then upgrades to it, cleanup
runs, and the upgraded tree must reach a working server: ``server.py
--dry-run`` and a stdio ``wf_server_info`` call. Recorded evidence on this
machine only: tags and tests are not present in consumer checkouts.
"""
import json, os, shutil, subprocess, sys, tarfile, tempfile, io
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
PY = str(Path.home() / ".wavefoundry/venv/bin/python")
SCRIPTS_REL = ".wavefoundry/framework/scripts"
TAGS = [a for a in sys.argv[1:] if not a.startswith("--")] or ([] if "--fresh" in sys.argv[1:] else ["v1.25.0", "v1.26.0"])
# ``--confirm-hosts-stopped`` lets the installed process continue past the
# storage gate itself, so the whole old-code window runs in the installed
# runner; without it the process stops at the gate and new code resumes.
DASHBOARD = "--with-dashboard" in sys.argv[1:]
FRESH = "--fresh" in sys.argv[1:]
EXTRA = [a for a in sys.argv[1:] if a.startswith("--") and a not in ("--with-dashboard", "--fresh")]


def run(argv, cwd=None, timeout=1800, env=None):
    result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)
    return result.returncode, result.stdout, result.stderr


def build_pack(work: Path) -> Path:
    framework = work / "pack source" / ".wavefoundry" / "framework"
    base = os.environ.get("PACK_FROM_COMMIT")
    if base:
        # Control run: the same matrix against a pack built from a pre-move commit.
        source = work / "pack source"
        source.mkdir()
        archive = subprocess.run(["git", "-C", str(REPO), "archive", base, ".wavefoundry/framework", "CHANGELOG.md"],
                                 capture_output=True, check=True).stdout
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(source, filter="data")
        shutil.rmtree(framework / "scripts" / "tests", ignore_errors=True)
    else:
        shutil.copytree(REPO / ".wavefoundry/framework", framework,
                        ignore=shutil.ignore_patterns("__pycache__", "index", "test-cache.json", "tests"))
        shutil.copy2(REPO / "CHANGELOG.md", framework.parent.parent / "CHANGELOG.md")
    sys.path.insert(0, str(framework / "scripts"))
    import build_pack
    out = work / "packs"
    out.mkdir()
    return build_pack.build_zip(out, "1.27.0", "m1yzd0", framework_dir=framework,
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


def identity_probe(root: Path) -> dict:
    code = (
        "import json, sys\n"
        "sys.path.insert(0, sys.argv[1])\n"
        "import server_impl, dashboard_handlers\n"
        "print(json.dumps({'server_impl': server_impl.__name__, 'server_impl_file': server_impl.__file__,"
        " 'dashboard_is_package': dashboard_handlers is sys.modules['wf_server.dashboard_handlers'],"
        " 'scripts_dir': str(server_impl.SCRIPTS_DIR)}))\n"
    )
    rc, out, err = run([PY, "-B", "-c", code, str(root / SCRIPTS_REL)])
    return json.loads(out.strip().splitlines()[-1]) if rc == 0 else {"error": err[-2000:]}


def dashboard(root: Path, action: str) -> dict:
    """Start or stop the dashboard through whatever dashboard_handlers the tree has."""
    code = (
        "import json, os, sys\n"
        "os.environ['WAVEFOUNDRY_SUPPRESS_DASHBOARD_BROWSER'] = '1'\n"
        "sys.path.insert(0, sys.argv[1])\n"
        "from pathlib import Path\n"
        "try:\n"
        "    import dashboard_handlers\n"
        "except ImportError:  # 1.25 kept the dashboard handlers in server_impl\n"
        "    import server_impl as dashboard_handlers\n"
        "root = Path(sys.argv[2])\n"
        "fn = dashboard_handlers.wf_start_dashboard_response if sys.argv[3] == 'start' else dashboard_handlers.wf_stop_dashboard_response\n"
        "res = fn(root)\n"
        "print(json.dumps({'status': res.get('status'), 'module': dashboard_handlers.__name__,"
        " 'handler_file': dashboard_handlers.__file__}))\n"
    )
    rc, out, err = run([PY, "-B", "-c", code, str(root / SCRIPTS_REL), str(root), action], timeout=300)
    return json.loads(out.strip().splitlines()[-1]) if rc == 0 else {"error": err[-1500:]}


def main() -> int:
    results = {}
    with tempfile.TemporaryDirectory(prefix="wf 1yzd0 old runner ") as temp:
        work = Path(temp)
        pack = build_pack(work)
        results["pack"] = pack.name
        if FRESH:
            # Fresh install: the pack's members extracted into an empty repository.
            import zipfile
            root = work / "fresh install"
            (root / "docs").mkdir(parents=True)
            with zipfile.ZipFile(pack) as zf:
                members = [m for m in zf.namelist() if m.startswith(".wavefoundry/")]
                zf.extractall(root, members)
            for args in (["init", "-q"], ["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@example.invalid",
                                                          "commit", "-q", "-m", "fresh"]):
                subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
            entry = {"package_present": (root / SCRIPTS_REL / "wf_server" / "server_impl.py").is_file(),
                     "flat_alias_present": (root / SCRIPTS_REL / "server_impl.py").is_file()}
            rc, out, err = run([PY, "-B", str(root / SCRIPTS_REL / "server.py"), "--root", str(root), "--dry-run"])
            entry["dry_run"] = {"exit": rc, "tail": (out + err).strip().splitlines()[-2:]}
            entry["identity"] = identity_probe(root)
            info = stdio_server_info(root)
            entry["wf_server_info"] = ({"status": info.get("status"),
                                        "server_impl_version": (info.get("data") or {}).get("server_impl_version")}
                                       if "error" not in info else info)
            print(json.dumps({"fresh": entry}, indent=1), flush=True)
        for tag in TAGS:
            root = work / f"installed {tag}"
            root.mkdir()
            archive = subprocess.run(["git", "-C", str(REPO), "archive", tag], capture_output=True, check=True).stdout
            with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
                tar.extractall(root, filter="data")
            for args in (["init", "-q"], ["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@example.invalid",
                                                          "commit", "-q", "-m", "installed"]):
                subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
            entry = {}
            if DASHBOARD:
                entry["dashboard_before_upgrade"] = dashboard(root, "start")
            rc, out, err = run([PY, "-B", str(root / SCRIPTS_REL / "upgrade_wavefoundry.py"),
                                "--root", str(root), "--pack", str(pack), "--yes", *EXTRA])
            entry["upgrade_exit"] = rc
            entry["upgrade_tail"] = (out + err).strip().splitlines()[-12:]
            entry["upgrade_dashboard_lines"] = [l for l in (out + err).splitlines() if "Dashboard" in l][:6]
            if DASHBOARD:
                entry["dashboard_stop_after_upgrade"] = dashboard(root, "stop")
                entry["dashboard_start_new_code"] = dashboard(root, "start")
                entry["dashboard_stop_new_code"] = dashboard(root, "stop")
            rc, out, err = run([PY, "-B", str(root / SCRIPTS_REL / "upgrade_wavefoundry.py"),
                                "--root", str(root), "--cleanup", "--yes"])
            entry["cleanup_exit"] = rc
            entry["cleanup_tail"] = (out + err).strip().splitlines()[-6:]
            entry["package_present"] = (root / SCRIPTS_REL / "wf_server" / "server_impl.py").is_file()
            entry["flat_alias_bytes_ok"] = (root / SCRIPTS_REL / "server_impl.py").read_text().startswith("import importlib")
            rc, out, err = run([PY, "-B", str(root / SCRIPTS_REL / "server.py"), "--root", str(root), "--dry-run"])
            entry["dry_run"] = {"exit": rc, "tail": (out + err).strip().splitlines()[-2:]}
            entry["identity"] = identity_probe(root)
            info = stdio_server_info(root)
            entry["wf_server_info"] = ({"status": info.get("status"),
                                        "framework_version": (info.get("data") or {}).get("framework_version"),
                                        "server_impl_version": (info.get("data") or {}).get("server_impl_version")}
                                       if "error" not in info else info)
            results[tag] = entry
            print(json.dumps({tag: entry}, indent=1), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
