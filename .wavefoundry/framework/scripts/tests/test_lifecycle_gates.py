"""Behavioral polarity coverage for every registered lifecycle gate (1y044 AC-2)."""
from __future__ import annotations

import inspect
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import lifecycle_gates as gates
import lifecycle_gate_support as support
from server_tools_support import load_server
from test_lifecycle_golden import (
    build_fixtures, _APPROVAL_INTEGRITY, _approval_evidence, _stub_validate,
)

PHASE_TUPLES = (
    'PREPARE_PREFLIGHT_GATES', 'PREPARE_POLICY_GATES',
    'PREPARE_ACTIVATION_GATES', 'PREPARE_READINESS_GATES',
    'REVIEW_GATES', 'CLOSE_SHARED_GATES', 'CLOSE_HARD_GATES',
)


def polarity(gate_name):
    """Mark a test that executes both accepted and rejected inputs for a unit."""
    def decorate(test):
        test.gate_polarity = (gate_name, {'pass', 'fail'})
        return test
    return decorate


def missing_coverage(tuples, case):
    coverage = {}
    for name in unittest.defaultTestLoader.getTestCaseNames(case):
        metadata = getattr(getattr(case, name), 'gate_polarity', None)
        if metadata:
            gate_name, polarities = metadata
            coverage.setdefault(gate_name, set()).update(polarities)
    return sorted({gate.__name__ for group in tuples for gate in group
                   if coverage.get(gate.__name__, set()) != {'pass', 'fail'}})


class LifecycleGateBehaviorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.fixtures = build_fixtures(Path(self.tmp.name), self.srv)

    def context(self, name='active_typed_approvals', *, phase='prepare', mode='ready'):
        root, wave_id = self.fixtures[name]
        wave_md = root / 'docs' / 'waves' / wave_id / 'wave.md'
        return gates.GateContext(root, wave_md, wave_md.read_text(encoding='utf-8'),
                                 mode, _stub_validate(root), phase)

    def codes(self, result):
        self.assertIsInstance(result, gates.GateResult)
        return [row['code'] for row in result.diagnostics]

    def delivery_approvals(self, ctx):
        for event, key in [('run', None), ('approval', 'code-reviewer'),
                           ('approval', 'wave-council-delivery'),
                           ('approval', 'operator-signoff')]:
            kwargs = {'run_kind': 'initial_delivery'} if key is None else {
                'signoff_key': key, 'approval_phase': 'delivery'}
            actor = ('wave-council' if key is None or key.startswith('wave-council')
                     else 'operator' if key == 'operator-signoff' else key)
            with patch.object(self.srv, '_run_post_write_lint', return_value={'mode': 'stubbed'}):
                response = self.srv.wf_review_event_response(
                    ctx.root, ctx.wave_md.parent.name, event, actor,
                    f'gate-unit-{key or "delivery-run"}', mode='create',
                    fresh_context=True, independent=True,
                    evidence=_approval_evidence(actor),
                    integrity_checks=dict(_APPROVAL_INTEGRITY), **kwargs)
            self.assertNotEqual(response['status'], 'error', response)
        return replace(ctx, wave_text=ctx.wave_md.read_text(encoding='utf-8'))

    @polarity('required_sensors_gate')
    def test_required_sensors_gate_pass_fail(self):
        import sys
        ctx = self.context(phase='close', mode='create')
        config_path = ctx.root / 'docs' / 'workflow-config.json'
        config = json.loads(config_path.read_text())
        config['phase_gates'] = {'close': {'required_sensors': ['probe']}}
        for exit_code in (0, 7):
            config['sensors'] = [{'name': 'probe', 'command': [sys.executable, '-c', f'raise SystemExit({exit_code})']}]
            config_path.write_text(json.dumps(config))
            result = gates.required_sensors_gate(ctx)
            self.assertEqual('phase_sensor_failed' in self.codes(result), exit_code != 0)
            self.assertEqual(result.data['configured_gates'][0]['outcome'], 'passed' if exit_code == 0 else 'failed')

    def test_evidence_section_constant_is_decoupled_from_the_marker_tuple(self):
        """1yd99 AC-3: prepending to the marker tuple changes nothing an operator reads.

        Three dimensions, because a partial repoint passes if any one is missed.
        The two configuration defaults each read the constant twice, once as the
        `.get` default and once as the `or` fallback for a value that is empty
        after stripping, and they sit one in each branch of the same normalizer.
        The three remedy reads sit behind the typed-authority test, one on the
        typed branch and two on the legacy branch, so a typed-only harness
        reaches one of three.
        """
        import review_evidence

        canonical = review_evidence.REVIEW_EVIDENCE_SECTION
        prepended = ("## Legacy Review Evidence",) + review_evidence.REVIEW_EVIDENCE_PROSE_MARKERS

        ctx = self.context(phase='close')
        config_path = ctx.root / 'docs' / 'workflow-config.json'
        config = json.loads(config_path.read_text())

        def default_for(block):
            config['wave_review'] = block
            config_path.write_text(json.dumps(config))
            policy = support._read_wave_council_policy(ctx.root)
            return policy.get("evidence_section")

        # Both branches of the one normalizer: the disabled-policy early return
        # and the enabled return, each with the `.get` default and the `or`
        # fallback for a value that is empty after stripping.
        for enabled in (False, True):
            for blank in (None, "   "):
                with self.subTest(branch='disabled' if not enabled else 'enabled', value=blank):
                    block = {"enabled": enabled, "delivery_mode": "targeted" if enabled else "disabled"}
                    if blank is not None:
                        block["evidence_section"] = blank
                    self.assertEqual(default_for(block), canonical)
                    with patch.object(review_evidence, 'REVIEW_EVIDENCE_PROSE_MARKERS', prepended):
                        self.assertEqual(default_for(block), canonical)

        # The three remedy reads, across both authority branches.  These are
        # message-construction sites behind the typed-authority test, one on the
        # typed branch and two on the legacy branch, so a typed-only harness
        # would reach one of three.  Rendering them directly is what makes the
        # branch split observable without standing up two whole wave fixtures.
        import inspect

        council_src = inspect.getsource(gates.council_signoff_gate)
        shared_src = inspect.getsource(gates._evaluate_shared_delivery_state)
        for label, src in (('council', council_src), ('shared delivery', shared_src)):
            with self.subTest(site=label):
                self.assertNotIn('REVIEW_EVIDENCE_PROSE_MARKERS[0]', src)
                self.assertIn('REVIEW_EVIDENCE_SECTION', src)

        # Render the three remedies through their producing gates rather than
        # rebuilding the strings here.  An earlier version compared a local
        # f-string builder with itself under the patch, which was tautological:
        # patching the marker tuple cannot change a constant the builder reads
        # directly.  A delivery lane caught that.
        def remedy_messages():
            out = []
            for typed in (True, False):
                real = gates.resolve_review_authority(ctx.root, ctx.wave_md, wave_text=ctx.wave_text)
                authority = replace(real, typed=typed)
                gctx = gates.GateContext(ctx.root, ctx.wave_md, ctx.wave_text, 'create',
                                         _stub_validate(ctx.root), 'prepare')
                with patch.object(gates, 'resolve_review_authority', return_value=authority):
                    out.extend(d.get('recovery_usage', '') + ' ' + d['message']
                               for d in gates.council_signoff_gate(gctx).diagnostics)
                    out.extend(d.get('recovery_usage', '') + ' ' + d['message']
                               for d in gates.shared_delivery_gate(
                                   replace(gctx, phase='close')).diagnostics)
            return [m for m in out if 'Review Evidence' in m]

        before = remedy_messages()
        self.assertTrue(before, 'the producing gates must emit messages naming the section')
        with patch.object(review_evidence, 'REVIEW_EVIDENCE_PROSE_MARKERS', prepended):
            after = remedy_messages()
        self.assertEqual(before, after, 'prepending to the tuple must change no remedy message')
        for message in before:
            self.assertIn(canonical, message)
            self.assertNotIn('## Legacy Review Evidence', message)

    def test_provenance_rule_is_derived_and_documented_at_every_site(self):
        """1yd99 AC-5: the keyless-response rule, derived from code and installed everywhere.

        The rule is stated over the producing layer rather than over call order,
        because one member returns from an `except` clause after the handler was
        invoked and raised.  The derivation keys on each member's literal
        diagnostic code, resolving through a single-diagnostic refusal helper
        whether the return is a call to one or a return of a local bound from one,
        which is the shape all three tool bodies use.  It fails below five, so
        under-deriving the tool-body member is red rather than green.
        """
        import ast

        srv = load_server()
        source = Path(srv.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        expected = {
            "lifecycle_mutation_locked", "lifecycle_lock_unavailable",
            "upgrade_in_progress", "project_publication_busy", "unknown_arguments",
        }

        # Derive the candidate set from the rule's own scope, then compare.  An
        # earlier version filtered candidates by `value in expected`, which made
        # `derived` a subset of `expected` by construction: it could only detect
        # under-derivation, never a sixth keyless class, so the drift protection
        # this criterion exists to give did not exist.  Two delivery lanes proved
        # that by inserting a third response-producing wrapper and watching the
        # test stay green.
        functions = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}

        def refusal_codes(fn, depth=1):
            """Diagnostic codes this function returns without calling a handler.

            Resolves one hop through a single-diagnostic refusal helper, whether
            the return is a call to one or a return of a local bound from one,
            which is the shape all three lifecycle tool bodies use.
            """
            codes = set()
            for node in ast.walk(fn):
                if not isinstance(node, ast.Return) or node.value is None:
                    continue
                returned = ast.unparse(node.value)
                if returned.startswith("fn(") or returned == "result":
                    continue          # forwards the wrapped callable's own result
                for inner in ast.walk(node):
                    if not isinstance(inner, ast.Call):
                        continue
                    called = ast.unparse(inner.func).split(".")[-1]
                    if called == "_diagnostic" and inner.args and isinstance(inner.args[0], ast.Constant):
                        codes.add(inner.args[0].value)
                    elif depth and called in functions and called not in {"_response"}:
                        codes |= refusal_codes(functions[called], depth - 1)
            if not codes:
                # A single-diagnostic refusal helper may bind its response to a
                # local and return that name, which is the shape the tool bodies'
                # argument refusal uses.  Attribute its one code when the whole
                # function carries exactly one, which is what makes it single.
                own = {inner.args[0].value for inner in ast.walk(fn)
                       if isinstance(inner, ast.Call)
                       and ast.unparse(inner.func).split(".")[-1] == "_diagnostic"
                       and inner.args and isinstance(inner.args[0], ast.Constant)}
                if len(own) == 1:
                    codes |= own
            return codes

        # Registration wrappers: module-level functions that rebind `tool.fn`.
        wrappers = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                    and "tool.fn =" in ast.unparse(n)]
        self.assertGreaterEqual(len(wrappers), 2, "the registration wrappers must be discoverable")

        # The three lifecycle tool bodies, and the helpers their pre-handler
        # refusals delegate to.  A tool body binds the refusal to a local and
        # returns the name, so the helper is resolved by following that call.
        lifecycle_tools = ("wf_prepare_wave", "wf_review_wave", "wf_close_wave")
        helper_names = set()
        for name in lifecycle_tools:
            body = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name), None)
            self.assertIsNotNone(body, name)
            handler_call = f"{name}_response"
            for node in ast.walk(body):
                if not isinstance(node, ast.Call):
                    continue
                called = ast.unparse(node.func).split(".")[-1]
                if called == handler_call:
                    break             # everything after this is the handler's own work
                if called.startswith("_ensure_"):
                    helper_names.add(called)
        self.assertTrue(helper_names, "the tool bodies must carry a pre-handler refusal helper")

        derived = set()
        for wrapper in wrappers:
            derived |= refusal_codes(wrapper)
        for helper in helper_names:
            fn = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == helper), None)
            self.assertIsNotNone(fn, helper)
            derived |= refusal_codes(fn)

        self.assertEqual(derived, expected,
                         "the documented set must equal the set derived from the code: an "
                         "added keyless class reddens here, and a missing one does too")

        # Every one of the four documentation sites states the rule, keyed on the
        # tool-body half.  The registration-wrapper half is already present at the
        # cross-cutting site, so keying on it would be green today and blind to a
        # partial installation.
        repo = srv.SCRIPTS_DIR.parents[2]
        disjunct = "returned by a tool body before it calls its handler"
        cross = (repo / "docs/architecture/cross-cutting-concerns.md").read_text(encoding="utf-8")
        surface = (repo / "docs/specs/mcp-tool-surface.md").read_text(encoding="utf-8")
        self.assertIn(disjunct, cross)
        self.assertEqual(surface.count(disjunct), 3, "all three tool bullets state the rule")
        # No site may present a registration-wrapper refusal as the only keyless class.
        for text, label in ((cross, "cross-cutting"), (surface, "tool surface")):
            with self.subTest(document=label):
                self.assertNotIn("A registration-wrapper refusal carries no such key.", text)
        # The docs-constants claim on the bullet this change edits survives verbatim.
        self.assertIn("configured_gates outcomes: `would_run/passed/failed/invalid`", surface)

    def test_publication_contention_at_the_two_call_sites(self):
        """1yd99 AC-4: one site gains a clause, the other keeps its wrapper.

        The two call sites of the publication helper are not symmetric.
        `wf_mark_ac` is absent from the publication writer registry, so its site
        raises unhandled today and is the one this change edits.  `wf_prepare_wave`
        is a registered writer whose wrapper already returns the typed busy
        envelope, so an inner clause there would shadow it and turn a fail-fast
        refusal into an in-band diagnostic.  The prepare half is therefore a
        deliberate no-change pin, stated as the converse.
        """
        import ast
        import publication_control
        import review_evidence

        srv = load_server()
        source = Path(srv.__file__).read_text(encoding="utf-8")

        # The asymmetry the requirement rests on.
        registered = set(publication_control.registered_publication_tool_names())
        self.assertIn("wf_prepare_wave", registered)
        self.assertNotIn("wf_mark_ac", registered)
        self.assertTrue(issubclass(review_evidence.ProjectPublicationUnavailable, RuntimeError))

        # The prepare call site is unchanged: still the narrow tuple, no inner clause.
        tree = ast.parse(source)
        prepare_fn = next(n for n in ast.walk(tree)
                          if isinstance(n, ast.FunctionDef) and n.name == "wf_prepare_wave_response")
        prepare_handlers = [h for n in ast.walk(prepare_fn) if isinstance(n, ast.Try)
                            for h in n.handlers
                            if any("_publish_prepare_policy_state" in ast.unparse(b) for b in n.body)]
        self.assertTrue(prepare_handlers)
        for handler in prepare_handlers:
            self.assertNotIn("ProjectPublicationUnavailable", ast.unparse(handler.type))

        # The mark-criterion site gained the distinct clause, ahead of the tuple.
        mark_fn = next(n for n in ast.walk(tree)
                       if isinstance(n, ast.FunctionDef) and n.name == "_mark_change_item_response")
        mark_tries = [n for n in ast.walk(mark_fn) if isinstance(n, ast.Try)
                      and any("_publish_prepare_policy_state" in ast.unparse(b) for b in n.body)]
        self.assertTrue(mark_tries)
        names = [ast.unparse(h.type) for t_ in mark_tries for h in t_.handlers]
        self.assertIn("ProjectPublicationUnavailable", names[0])
        self.assertIn("project_publication_busy", ast.unparse(mark_tries[0]))
        # The busy response preserves the published contract: nothing was changed.
        busy = ast.unparse(mark_tries[0].handlers[0])
        self.assertIn("'changed': False", busy)
        self.assertIn("'review_receipt_refreshed': False", busy)

        # AC-4 states the oracle behaviourally, so inject the fault rather than
        # only reading the source: a clause that parses but fails at runtime,
        # carries the wrong payload, or is marked advisory would pass an AST pin.
        ctx = self.context(phase='close')
        change = next(q for q in ctx.wave_md.parent.glob('*.md') if q.name != 'wave.md')
        with patch.object(srv, '_publish_prepare_policy_state',
                          side_effect=review_evidence.ProjectPublicationUnavailable('lock held')):
            response = srv._mark_change_item_response(
                ctx.root, ctx.wave_md.parent.name, change.stem, 'AC-1', '~',
                target_section='Acceptance Criteria', reason='probe', mode='create')
        self.assertEqual(response['status'], 'error', response)
        codes = [d['code'] for d in response.get('diagnostics', [])]
        self.assertEqual(codes, ['project_publication_busy'], response)
        busy_diag = response['diagnostics'][0]
        self.assertIsNot(busy_diag.get('advisory'), True, 'contention must not be advisory')
        self.assertFalse(response['data']['changed'])
        self.assertFalse(response['data']['review_receipt_refreshed'])

    def test_evidence_guard_conjuncts(self):
        """1yd99 AC-7: the dead conjunct is gone and the lookalike is intact.

        Two corrections in two different functions, and one of them has a
        dangerous lookalike.  Removing an unreachable conjunct is behaviourally
        undetectable, so the first half is a structural assertion.  The second
        half drives the validator-error path, where deleting the neighbouring
        `not result.errors` conjunct would read a local bound only inside the
        branch above it and raise.
        """
        import ast

        source = Path(gates.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        approval = next(n for n in ast.walk(tree)
                        if isinstance(n, ast.FunctionDef) and n.name == "_approval_evidence_diagnostics")
        # Resolve the guard by what it calls, not by its position in the body.
        # An earlier version of this assertion indexed the function's top-level
        # `If` nodes; the guard it names is nested inside `if records is None:`,
        # so it read an unrelated statement and stayed green when the removed
        # conjunct was reinstated. A delivery mutation caught that.
        guard = next(n for n in ast.walk(approval)
                     if isinstance(n, ast.If)
                     and "_wave_uses_external_review_evidence" in ast.unparse(n.test))
        self.assertNotIn("wave_md is None", ast.unparse(guard.test),
                         "the guard above already returns on a None wave_md")
        self.assertNotIsInstance(guard.test, ast.BoolOp)
        # The guard immediately above it is the one that makes the conjunct dead.
        preceding = [n for n in ast.walk(approval)
                     if isinstance(n, ast.If) and "root is None" in ast.unparse(n.test)]
        self.assertTrue(preceding, "the None-argument guard must still return early")

        translator = next(n for n in ast.walk(tree)
                          if isinstance(n, ast.FunctionDef) and n.name == "_review_evidence_diagnostics")
        self.assertTrue(
            any(isinstance(n, ast.BoolOp) and "raw_projection" in ast.unparse(n)
                and "result.errors" in ast.unparse(n) for n in ast.walk(translator)),
            "the load-bearing conjunct guarding a branch-local binding must stay",
        )

        # The validator-error path still produces its diagnostics without raising.
        ctx = self.context(phase='close')
        (ctx.wave_md.parent / 'events.jsonl').write_text('{"record_type": "nonsense"}\n', encoding='utf-8')
        result = gates._review_evidence_diagnostics(
            ctx.wave_text, root=ctx.root, wave_md=ctx.wave_md, closure=True)
        self.assertTrue(result)
        self.assertTrue(any(d['code'] == 'review_evidence_invalid' for d in result))

    def test_absent_argument_message_names_the_record_path(self):
        """1yd99 AC-5 coverage: the reworded message, checked against its symbol."""
        result = gates._review_evidence_diagnostics("", root=None, wave_md=None)
        self.assertEqual(len(result), 1)
        self.assertIn("wave record path", result[0]["message"])
        self.assertNotIn("wave key", result[0]["message"])

    @polarity('shared_delivery_gate')
    def test_shared_delivery_gate_pass_fail(self):
        ctx = self.context(phase='close')
        rejected = gates.shared_delivery_gate(ctx)
        self.assertIn('missing_operator_signoff', self.codes(rejected))
        self.assertFalse(rejected.data['operator_current'])
        accepted = gates.shared_delivery_gate(self.delivery_approvals(ctx))
        self.assertEqual(self.codes(accepted), [])
        self.assertTrue(accepted.data['operator_current'])
        self.assertTrue(all(row['recorded_signoff'] for row in accepted.data['lane_results']))

    @polarity('gardener_gate')
    def test_gardener_gate_pass_fail(self):
        for phase in ('prepare', 'close'):
            ctx = self.context(phase=phase)
            with self.subTest(phase=phase):
                self.assertEqual(self.codes(gates.gardener_gate(ctx, garden_passed=True)), [])
                rejected = gates.gardener_gate(ctx, garden_passed=False)
                self.assertEqual(self.codes(rejected), ['docs_gardener_failed'])
                self.assertEqual(rejected.diagnostics[0]['message'], f'docs_gardener failed during {phase}.')

    @polarity('close_checkbox_gate')
    def test_close_checkbox_gate_pass_fail(self):
        ctx = self.context(phase='close')
        self.assertEqual(self.codes(gates.close_checkbox_gate(ctx)), [])
        change = next(path for path in ctx.wave_md.parent.glob('*.md') if path.name != 'wave.md')
        change.write_text(change.read_text(encoding='utf-8').replace('- [x] AC-1:', '- [ ] AC-1:'), encoding='utf-8')
        result = gates.close_checkbox_gate(ctx)
        self.assertEqual(self.codes(result), ['silent_unchecked_items_at_close'])
        self.assertIn('AC-1', result.diagnostics[0]['message'])
        change.unlink()
        self.assertEqual(self.codes(gates.close_checkbox_gate(ctx)), ['change_doc_missing'])

    @polarity('framework_receipt_gate')
    def test_framework_receipt_gate_pass_fail(self):
        ctx = self.context(phase='close')
        absent = gates.framework_receipt_gate(ctx)
        self.assertEqual(self.codes(absent), [])
        self.assertEqual(absent.data['framework_test_receipt']['state'], 'not_applicable')
        runner = ctx.root / support._FRAMEWORK_TEST_RUNNER_REL
        runner.parent.mkdir(parents=True, exist_ok=True)
        # A tiny isolated runner implements the real receipt-reader protocol.
        # Its cache comes from disk, so the gate must actually compare identities.
        runner.write_text("import json\nfrom pathlib import Path\n"
                          "def _hash_inputs(): return 'current'\n"
                          "def _read_cache(): return json.loads(Path(__file__).with_name('test-cache.json').read_text())\n", encoding='utf-8')
        receipt = runner.with_name('test-cache.json')
        receipt.write_text(json.dumps({'result': 'ok', 'inputs_hash': 'current', 'test_count': 3}), encoding='utf-8')
        self.assertEqual(gates.framework_receipt_gate(ctx).data['framework_test_receipt']['state'], 'proven')
        self.assertEqual(self.codes(gates.framework_receipt_gate(ctx)), [])
        receipt.write_text(json.dumps({'result': 'ok', 'inputs_hash': 'old'}), encoding='utf-8')
        rejected = gates.framework_receipt_gate(ctx)
        self.assertEqual(self.codes(rejected), ['framework_test_receipt_not_proven'])
        self.assertEqual(rejected.data['framework_test_receipt']['state'], 'stale')

    @polarity('review_prelude_gate')
    def test_review_prelude_gate_pass_fail(self):
        ctx = self.context(phase='review')
        accepted = gates.review_prelude_gate(ctx, review_phase='prepare')
        self.assertEqual(self.codes(accepted), [])
        self.assertTrue(accepted.data['authority'].typed)
        missing = self.context('missing_lane', phase='review')
        rejected = gates.review_prelude_gate(missing, review_phase='prepare')
        self.assertIn('review_evidence_invalid', self.codes(rejected))
        self.assertTrue(any('readiness' in row['message'] for row in rejected.diagnostics))

    @polarity('lint_gate')
    def test_lint_gate_pass_fail(self):
        ctx = self.context()
        self.assertEqual(self.codes(gates.lint_gate(ctx)), [])
        broken = replace(ctx, lint_result={'passed': False, 'errors': ['broken link'], 'warnings': []})
        rejected = gates.lint_gate(broken)
        self.assertEqual(self.codes(rejected), ['docs_lint_error'])
        self.assertEqual(rejected.diagnostics[0]['message'], 'broken link')
        self.assertEqual(self.codes(gates.lint_gate(broken, review_phase='implementation')), [])

    @polarity('review_lanes_gate')
    def test_review_lanes_gate_pass_fail(self):
        accepted = gates.review_lanes_gate(self.context(), required_lanes=('code-reviewer',))
        self.assertEqual(self.codes(accepted), [])
        self.assertEqual(accepted.data['lane_results'], [{'lane': 'code-reviewer', 'recorded_signoff': True}])
        rejected = gates.review_lanes_gate(self.context('missing_lane'), required_lanes=('code-reviewer',))
        self.assertEqual(self.codes(rejected), ['missing_required_lane'])
        self.assertIn('typed approval', rejected.diagnostics[0]['message'])
        self.assertEqual(rejected.data['missing'], ['code-reviewer'])

    @polarity('wave_policy_gate')
    def test_wave_policy_gate_pass_fail(self):
        ctx = self.context()
        self.assertEqual(self.codes(gates.wave_policy_gate(ctx)), [])
        config_path = ctx.root / 'docs' / 'workflow-config.json'
        config = json.loads(config_path.read_text(encoding='utf-8'))
        config['wave_review'] = {'enabled': True, 'delivery_mode': 'invalid-mode'}
        config_path.write_text(json.dumps(config), encoding='utf-8')
        result = gates.wave_policy_gate(ctx)
        self.assertEqual(self.codes(result), ['review_policy_reprepare_required'])

    @polarity('evidence_gate')
    def test_evidence_gate_pass_fail(self):
        ctx = self.context()
        self.assertEqual(self.codes(gates.evidence_gate(ctx)), [])
        ledger = ctx.wave_md.with_name('events.jsonl')
        with ledger.open('a', encoding='utf-8') as stream:
            stream.write('{broken-json\n')
        result = gates.evidence_gate(ctx)
        self.assertIn('review_evidence_invalid', self.codes(result))
        self.assertTrue(any('JSON' in row['message'] for row in result.diagnostics))

    @polarity('change_location_gate')
    def test_change_location_gate_pass_fail(self):
        ctx = self.context()
        change = next(path for path in ctx.wave_md.parent.glob('*.md') if path.name != 'wave.md')
        accepted = gates.change_location_gate(ctx, admitted_change=change.stem)
        self.assertEqual(self.codes(accepted), [])
        self.assertEqual(accepted.data['change_path'], change)
        self.assertFalse(accepted.data['skip'])
        staged = ctx.root / 'docs' / 'plans' / change.name
        staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_bytes(change.read_bytes())
        duplicate = gates.change_location_gate(ctx, admitted_change=change.stem)
        self.assertEqual(self.codes(duplicate), ['duplicate_change_doc_locations'])
        self.assertTrue(duplicate.data['skip'])
        change.unlink()
        dry = gates.change_location_gate(replace(ctx, mode='dry_run'), admitted_change=change.stem)
        self.assertEqual(self.codes(dry), ['change_doc_not_relocated'])
        ready = gates.change_location_gate(ctx, admitted_change=change.stem)
        self.assertEqual(self.codes(ready), [])
        self.assertTrue(ready.data['needs_relocation'])
        self.assertTrue(staged.exists(), 'a gate must not perform the orchestrator relocation')
        staged.unlink()
        self.assertEqual(self.codes(gates.change_location_gate(ctx, admitted_change=change.stem)), ['change_not_found'])

    @polarity('change_sections_gate')
    def test_change_sections_gate_pass_fail(self):
        ctx = self.context()
        change = next(path for path in ctx.wave_md.parent.glob('*.md') if path.name != 'wave.md')
        text = change.read_text(encoding='utf-8')
        self.assertEqual(self.codes(gates.change_sections_gate(ctx, admitted_change=change.stem, change_text=text)), [])
        missing = gates.change_sections_gate(ctx, admitted_change=change.stem, change_text=text.replace('## Requirements', '## Removed'))
        self.assertEqual(self.codes(missing), ['change_doc_missing_sections'])
        self.assertIn('Requirements', missing.diagnostics[0]['message'])
        placeholder = text.replace('| required |', '| required / important / nice-to-have / not-this-scope |')
        advisory = gates.change_sections_gate(ctx, admitted_change=change.stem, change_text=placeholder)
        self.assertEqual(self.codes(advisory), ['ac_priority_unpopulated'])
        self.assertTrue(advisory.diagnostics[0]['advisory'])

    @polarity('policy_errors_gate')
    def test_policy_errors_gate_pass_fail(self):
        ctx = self.context()
        self.assertEqual(self.codes(gates.policy_errors_gate(ctx, policy_state_errors=[])), [])
        rejected = gates.policy_errors_gate(ctx, policy_state_errors=['receipt digest unavailable'])
        self.assertEqual(self.codes(rejected), ['review_policy_receipt_stale'])
        self.assertEqual(rejected.diagnostics[0]['message'], 'receipt digest unavailable')
        self.assertIn(ctx.wave_md.parent.name, rejected.diagnostics[0]['recovery_usage'])

    @polarity('policy_advisory_gate')
    def test_policy_advisory_gate_pass_fail(self):
        ctx = self.context(mode='dry_run')
        self.assertEqual(self.codes(gates.policy_advisory_gate(ctx, policy_state={})), [])
        change = next(path for path in ctx.wave_md.parent.glob('*.md') if path.name != 'wave.md')
        change.write_text(change.read_text(encoding='utf-8').replace('Fixture requirement.', 'Changed requirement.'), encoding='utf-8')
        rejected = gates.policy_advisory_gate(ctx, policy_state={})
        self.assertEqual(self.codes(rejected), ['review_policy_receipt_stale'])
        self.assertTrue(rejected.diagnostics[0]['advisory'])
        self.assertEqual(self.codes(gates.policy_advisory_gate(replace(ctx, mode='ready'), policy_state={})), [])

    @polarity('council_signoff_gate')
    def test_council_signoff_gate_pass_fail(self):
        accepted = gates.council_signoff_gate(self.context('planned_with_verdict'))
        self.assertEqual(self.codes(accepted), [])
        self.assertIn('wave-council-readiness', accepted.data['required_council_signoffs'])
        rejected = gates.council_signoff_gate(self.context('missing_lane'))
        self.assertEqual(self.codes(rejected), ['missing_wave_council_signoff'])
        self.assertIn('typed approval', rejected.diagnostics[0]['message'])

    @polarity('single_open_gate')
    def test_single_open_gate_pass_fail(self):
        ctx = self.context('planned_with_verdict', mode='create')
        self.assertEqual(self.codes(gates.single_open_gate(ctx, other_active=None)), [])
        other = {'wave_id': 'other-wave', 'path': str(ctx.root / 'docs' / 'waves' / 'other-wave' / 'wave.md')}
        rejected = gates.single_open_gate(ctx, other_active=other)
        self.assertEqual(self.codes(rejected), ['another_wave_active'])
        self.assertEqual(rejected.data, {'active_wave_id': 'other-wave', 'active_wave_path': 'docs/waves/other-wave/wave.md'})
        self.assertEqual(self.codes(gates.single_open_gate(replace(ctx, mode='ready'), other_active=other)), [])

    @polarity('readiness_gate')
    def test_readiness_gate_pass_fail(self):
        self.assertEqual(self.codes(gates.readiness_gate(self.context('planned_with_verdict'))), [])
        result = gates.readiness_gate(self.context('missing_lane'))
        self.assertIn('review_evidence_invalid', self.codes(result))
        self.assertTrue(any('readiness' in row['message'] for row in result.diagnostics))


class GateCoverageTests(unittest.TestCase):
    def test_every_phase_tuple_unit_has_both_behavioral_polarities(self):
        groups = [getattr(gates, name) for name in PHASE_TUPLES]
        for name, group in zip(PHASE_TUPLES, groups):
            self.assertIsInstance(group, tuple, name)
            self.assertTrue(group, f'{name} must exercise real units')
            for gate in group:
                self.assertTrue(inspect.isfunction(gate), repr(gate))
                self.assertEqual(gate.__module__, gates.__name__)
        self.assertEqual(missing_coverage(groups, LifecycleGateBehaviorTests), [])

    def test_meta_detects_removed_polarity_coverage(self):
        groups = [getattr(gates, name) for name in PHASE_TUPLES]
        test = LifecycleGateBehaviorTests.test_framework_receipt_gate_pass_fail
        with patch.object(test, 'gate_polarity', ('framework_receipt_gate', {'pass'})):
            self.assertIn('framework_receipt_gate', missing_coverage(groups, LifecycleGateBehaviorTests))

    def test_meta_detects_an_uncovered_gate(self):
        def uncovered_gate(ctx):
            return gates.GateResult()
        self.assertEqual(missing_coverage([(uncovered_gate,)], LifecycleGateBehaviorTests), ['uncovered_gate'])


if __name__ == '__main__':
    unittest.main()
