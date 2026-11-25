import hashlib
import json
import zipfile
from pathlib import Path
r = Path(".wavefoundry/work/24buu/rehearsal")
for route in ("final-cli/cli", "final-installed/cli", "final-mcp/mcp"):
    for hop in (1,2):
        base = r / route
        def read(s):
            return json.loads((base / f"hop{hop}-{s}.json").read_text())
        terminal = [json.loads(line.split("WAVE_UPGRADE_SUMMARY_JSON:",1)[1]) for line in (base/f"hop{hop}-terminal.upgrade.log").read_text().splitlines() if "WAVE_UPGRADE_SUMMARY_JSON:" in line]
        assert sum(s["cleanup_complete"] is True for s in terminal) == 1
        assert read("terminal.summary") == [s for s in terminal if s["cleanup_complete"]]
        checks = read("inspect.checks")["checks"]
        assert len(checks) == 18 and all(v is True for v in checks.values())
        assert read("inspect.snapshot")["held_lock"] is False
        checkpoint = read("primary-checkpoint")
        expect_retained = route == "final-mcp/mcp" or (route == "final-installed/cli" and hop == 1)
        assert (checkpoint is not None) == expect_retained
        print(route, hop, len(checks), "passed, terminal count 1, primary retained", expect_retained)
for filename, recorded in json.loads((r/"final-archives.json").read_text()).items():
    assert hashlib.file_digest(open(filename,"rb"),"sha256").hexdigest() == recorded["archive_sha256"]
    with zipfile.ZipFile(filename) as z:
        files = [x for x in z.namelist() if x.startswith((".wavefoundry/framework/scripts/",".wavefoundry/framework/seeds/")) and not x.endswith("/")]
        assert len(files) == 238
        assert all(Path(f).read_bytes()==z.read(f) for f in files)
    print(recorded["version"], "238 live matches")
