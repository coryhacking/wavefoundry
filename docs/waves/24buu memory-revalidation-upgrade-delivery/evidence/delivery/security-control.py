from unittest import mock, TestResult
import test_spec_tool_permissions as t

original = t.stp._outside_holds

def over_hold(routes, prefix, held, recommend, files):
    original(routes, prefix, held, recommend, files)
    if held:
        for route in routes.values():
            held.setdefault(route, "conservative mutant")

case=t.SpecPermissionMigrationTests("test_ac4_outside_restrictions_hold_routes_and_are_never_written")
with mock.patch.object(t.stp, "_outside_holds", over_hold):
    result=TestResult()
    case.run(result)
print("errors",len(result.errors),"skips",len(result.skipped),"failed subtests",len(result.failures))
for case, failure in result.failures:
    print(str(case),failure)
assert not result.errors and not result.skipped and len(result.failures)==5
