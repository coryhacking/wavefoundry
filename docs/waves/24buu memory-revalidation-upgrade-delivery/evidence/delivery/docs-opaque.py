"""Compare identical externally maintained policy at undisclosed and disclosed paths."""
from pathlib import Path
import os
import json
from unittest import mock
from test_spec_tool_permissions import SpecPermissionMigrationTests, P, roster, surfaces

for disclosed in [False, True]:
    case = SpecPermissionMigrationTests()
    case.setUp()
    try:
        case.all_old_allowed()
        policy = case.write("policy.json", {"permissions": {"deny": [P + "wf_get_change"]}}, root=case.outside)
        original = policy.read_bytes()
        with mock.patch.dict(os.environ):
            if disclosed:
                os.environ["WAVEFOUNDRY_MANAGED_SETTINGS_PATH"] = str(policy)
            assert set(roster.spec_permission_holds(case.root)) == set(case.routes.values())
            assert surfaces.main(["--repo-root", str(case.root), "--include-permissions"]) == 0
            held = set(roster.spec_permission_holds(case.root))
            receipt = case.receipt("wf_get_spec").exists()
            print(json.dumps({"disclosed": disclosed, "held": sorted(held), "receipt": receipt,
                              "outside_bytes_preserved": original == policy.read_bytes()}))
            assert original == policy.read_bytes()
            assert held == ({"wf_get_spec"} if disclosed else set())
            assert receipt is (not disclosed)
    finally:
        case.doCleanups()
