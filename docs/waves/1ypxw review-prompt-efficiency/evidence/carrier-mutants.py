"""Run from repository root: python3 -B <this file>. In-memory mutants only."""
import io
import sys
import unittest
sys.path.insert(0, ".wavefoundry/framework/scripts/tests")
import test_render_agent_surfaces as tests
original = tests.ras.REVIEW_PROTOCOL_CARRIER_BLOCK
try:
    for label, mutated in (
        ("restore_actionability", original + "\nApply the four-way actionability gate."),
        ("remove_tool", original.replace("`wf_review_event`", "the writer")),
    ):
        tests.ras.REVIEW_PROTOCOL_CARRIER_BLOCK = mutated
        suite = unittest.TestSuite([tests.ReviewProtocolCarrierRegistryTests(
            "test_carrier_blocks_carry_chain_aware_independence_contract")])
        output = io.StringIO()
        result = unittest.TextTestRunner(stream=output).run(suite)
        assert len(result.failures) == 1 and not result.errors, output.getvalue()
        print(label + ": KILLED")
finally:
    tests.ras.REVIEW_PROTOCOL_CARRIER_BLOCK = original
