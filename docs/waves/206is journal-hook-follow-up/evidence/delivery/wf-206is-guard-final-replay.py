import importlib.util,json,pathlib,runpy
p=pathlib.Path('/tmp/wf-206is-guard-replay.py');spec=importlib.util.spec_from_file_location('replay',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.mutants.extend([
 ('executed_trigger_matches_static','upgrade_extensions.py','_load_journal_declaration','elif trigger != expected_trigger:','elif False:',m.P+'test_loaded_trigger_must_match_static_selection_before_dependents','Executed declaration trigger agrees with static selection before dependents'),
 ('runtime_policy_allowed','upgrade_extensions.py','_load_journal_declaration','if not isinstance(trigger, str) or trigger not in _JOURNAL_TRIGGER_POLICIES:','if False:',m.P+'test_loaded_invalid_trigger_is_refused_by_framework_policy_guard','Native loaded type/allowed-policy guard refuses invalid trigger'),
 ('other_binding_kind','upgrade_extensions.py','_static_journal_trigger','other_binding = any(','other_binding = False and any(',m.P+'test_function_class_exception_and_pattern_trigger_bindings_are_invalid_before_execution','Function/class/exception/pattern binding does not default as absent'),
])
m.main()
runpy.run_path('/tmp/wf-206is-guard-annotate.py',run_name='__main__')
p=pathlib.Path('/tmp/wf-206is-guard-pins.json');r=json.loads(p.read_text());initial=json.loads(pathlib.Path('/tmp/wf-206is-guard-pins-initial.json').read_text());r['historical_gap_census']=[row for row in initial['records'] if row['id'] in ('executed_trigger_matches_static','runtime_policy_allowed','other_binding_kind')];r['historical_gap_report']='/tmp/wf-206is-guard-pins-initial.json';r['replay_scripts']=['/tmp/wf-206is-guard-final-replay.py','/tmp/wf-206is-guard-replay.py','/tmp/wf-206is-guard-annotate.py'];p.write_text(json.dumps(r,indent=2))
