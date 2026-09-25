"""Wave 1yxyw fresh install: the new pack's members extracted into an empty
repository whose path contains a space. The pack carries only the two retained
flat aliases, and the server starts with no leftover warning."""
import json, subprocess, sys, tempfile, zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from old_runner import PY, RETIRED, SCRIPTS_REL, build_pack, run, stdio_server_info


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="wf 1yxyw fresh ") as temp:
        work = Path(temp)
        pack = build_pack(work)
        with zipfile.ZipFile(pack) as zf:
            names = zf.namelist()
            root = work / "fresh install"
            (root / "docs").mkdir(parents=True)
            zf.extractall(root, [m for m in names if m.startswith(".wavefoundry/")])
        for args in (["init", "-q"], ["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@example.invalid",
                                                      "commit", "-q", "-m", "fresh"]):
            subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
        flat = {m.rsplit("/", 1)[1][:-3] for m in names
                if m.startswith(".wavefoundry/framework/scripts/") and m.count("/") == 3 and m.endswith(".py")}
        entry = {"pack": pack.name,
                 "retired_in_pack": sorted(set(RETIRED) & flat),
                 "retained_in_pack": sorted({"server_impl", "dashboard_handlers"} & flat),
                 "manifest_lists_retired": sorted(n for n in RETIRED if f"scripts/{n}.py" in
                                                  (root / ".wavefoundry/framework/MANIFEST").read_text().splitlines())}
        rc, out, err = run([PY, "-B", str(root / SCRIPTS_REL / "server.py"), "--root", str(root), "--dry-run"])
        entry["dry_run"] = {"exit": rc, "stderr_warning": "retired flat server module" in err,
                            "tail": (out + err).strip().splitlines()[-1:]}
        info = stdio_server_info(root)
        entry["wf_server_info"] = ({"status": info.get("status"),
                                    "diagnostic_codes": [d.get("code") for d in info.get("diagnostics") or []]}
                                   if "error" not in info else info)
        good = (not entry["retired_in_pack"] and entry["retained_in_pack"] == ["dashboard_handlers", "server_impl"]
                and not entry["manifest_lists_retired"] and rc == 0 and not entry["dry_run"]["stderr_warning"]
                and entry["wf_server_info"].get("status") == "ok"
                and "retired_flat_module_leftover" not in entry["wf_server_info"].get("diagnostic_codes", []))
        entry["verdict"] = "ok" if good else "FAILED"
        print(json.dumps(entry, indent=1))
        return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())
