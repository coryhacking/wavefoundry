"""Compare exact skip identities/reasons from unmodified worker output."""
import ast
import json
from pathlib import Path
import re
import sys

root = Path(sys.argv[1])
expected_files = set(json.loads(Path(sys.argv[2]).read_text()))
inventories = {}
for profile in ("default", "second", "declared"):
    rows = sorted((root / profile).glob("test_*.py.json"))
    if not rows:
        raise AssertionError(f"missing {profile} worker outputs")
    assert {path.name.removesuffix(".json") for path in rows} == expected_files, (profile, "incomplete worker capture")
    skips = {}
    tests = 0
    for path in rows:
        record = json.loads(path.read_text())
        assert record["returncode"] == 0, path
        output = record["stderr"] or ""
        tails = list(re.finditer(r"^Ran (\d+) tests? in [\d.]+s$", output, re.M))
        assert tails, path
        tail = tails[-1]
        tests += int(tail.group(1))
        skip_counts = re.findall(r"\bskipped=(\d+)", output[tail.end():])
        count = int(skip_counts[-1]) if skip_counts else 0
        found = []
        heading = None
        for line in output.splitlines():
            match = re.match(r"^((?:test_\w+)|setUpClass) \(([^)]+)\)(?: \.\.\..*)?$", line)
            if match:
                heading = match.groups()
            skipped = re.match(r"^.* \.\.\. skipped (.+)$", line)
            if skipped:
                assert heading is not None, (profile, path.name, line)
                found.append((*heading, skipped.group(1)))
        assert len(found) == count, (profile, path.name, count, found)
        for method, owner, reason in found:
            identity = owner if owner.endswith("." + method) else f"{owner}.{method}"
            assert identity not in skips, (profile, identity)
            skips[identity] = ast.literal_eval(reason)
    inventories[profile] = {"files": len(rows), "tests": tests, "skips": skips}

baseline = inventories["default"]["skips"]
for profile in ("second", "declared"):
    current = inventories[profile]["skips"]
    extra = {key: value for key, value in current.items() if key not in baseline}
    changed = {key: {"default": value, "profile": current[key]}
               for key, value in baseline.items() if key in current and current[key] != value}
    if profile == "declared":
        assert not extra, extra
        assert current == baseline, (profile, "baseline skips differ")
    else:
        assert all(value.startswith("default-profile-only:") for value in extra.values()), extra
        assert all(value["profile"].startswith("default-profile-only:") for value in changed.values()), changed
    inventories[profile]["extra_skips"] = extra
    inventories[profile]["reason_changes"] = changed

(root / "skip-inventory.json").write_text(json.dumps(inventories, indent=2) + "\n")
for profile, report in inventories.items():
    print(f"{profile}: {report['tests']} tests / {report['files']} files / {len(report['skips'])} skips / {len(report.get('extra_skips', {}))} extra")
print("Exact skip identity/reason contract passed.")
