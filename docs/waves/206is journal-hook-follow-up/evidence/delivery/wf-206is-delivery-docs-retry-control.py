import os
import unittest
from test_upgrade_protocol import JournalIncomingRunnerTests

class DocsRetryContractControl(unittest.TestCase):
    def test_retry_claim_matches_actual_older_runner_observation(self):
        fixture = JournalIncomingRunnerTests('test_cached_old_modules_and_descendants_restore_after_success_and_idempotent_retry')
        fixture.setUp()
        try:
            fixture._pack()
            fixture._dispatch()
            fixture._assert_restored()
            fixture._dispatch()
            fixture._assert_restored()
            invocations = (fixture.root / 'invocations.txt').read_text().splitlines()
            claim = os.environ.get('DOC_RETRY_CLAIM', 'once_per_invocation')
            expected = 1 if claim == 'exactly_once_across_retry' else 2
            self.assertEqual(len(invocations), expected, 'documentation retry count must match the actual older-runner dispatch')
            self.assertEqual((fixture.root / 'idempotent-effect.txt').read_text(), 'once')
        finally:
            fixture.doCleanups()

if __name__ == '__main__':
    unittest.main(verbosity=2)
