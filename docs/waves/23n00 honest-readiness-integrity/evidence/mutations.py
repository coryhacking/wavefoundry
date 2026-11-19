import contextlib, inspect, io, json, sys, unittest
sys.path[:0]=['.wavefoundry/framework/scripts/tests','.wavefoundry/framework/scripts']
import review_evidence as r
import test_readiness_known_bad as t
identity=inspect.getsource(r._specialist_readiness_identity)
record=inspect.getsource(r._specialist_readiness_record)
validator=inspect.getsource(r._validated_integrity_checks)
shape=inspect.getsource(r._validate_evidence_shape)
mutants=[]
for fragment in ['_nonempty_string(signoff_key)','actor == signoff_key','actor != "operator"','not is_council_actor(actor)','signoff_key != "operator-signoff"','not is_council_signoff_key(signoff_key)','phase == "readiness"']:
 mutants.append(('identity:'+fragment, '_specialist_readiness_identity', identity.replace(fragment,'True',1), 'test_write_and_read_boundary_matrix'))
mutants += [
 ('record:claim kind','_specialist_readiness_record',record.replace('record.get("claim_kind") == "approval"','True',1),'test_write_and_read_boundary_matrix'),
 ('record:phase','_specialist_readiness_record',record.replace('approval_record_phase(record)','"readiness"',1),'test_write_and_read_boundary_matrix'),
 ('writer:null carveout removed','_validated_integrity_checks',validator.replace('specialist_readiness and field == "known_bad_detected"','False',1),'test_explicit_null_round_trip_and_other_checks_are_true'),
 ('writer:null allowed all fields','_validated_integrity_checks',validator.replace('specialist_readiness and field == "known_bad_detected"','specialist_readiness',1),'test_false_missing_and_other_null_checks_remain_refused'),
 ('writer:false accepted','_validated_integrity_checks',validator.replace('elif executed and field_value is not True:','elif False:',1),'test_false_missing_and_other_null_checks_remain_refused'),
 ('writer:blank rationale','_validated_integrity_checks',validator.replace('if not _nonempty_string(method):','if False:',1),'test_false_missing_and_other_null_checks_remain_refused'),
 ('reader:type restriction removed','_validate_evidence_shape',shape.replace('not_applicable_allowed = _accepts_not_applicable_integrity(record)','not_applicable_allowed = True',1),'test_write_and_read_boundary_matrix'),
 ('reader:execution restriction removed','_validate_evidence_shape',shape.replace('if record.get("execution_status") == "executed" and not (','if False and not (',1),'test_false_missing_and_other_null_checks_remain_refused'),
 ('reader:blank rationale','_validate_evidence_shape',shape.replace('        "known_bad_detection_method",\n','',1),'test_false_missing_and_other_null_checks_remain_refused'),
]
results=[]
for name,symbol,source,test in mutants:
 old=getattr(r,symbol)
 try:
  exec(source,r.__dict__)
  suite=unittest.TestSuite([t.ReadinessKnownBadTests(test)])
  out=io.StringIO()
  with contextlib.redirect_stderr(out): result=unittest.TextTestRunner(stream=out).run(suite)
  results.append({'mutation':name,'test':test,'detected':not result.wasSuccessful(),'failures':len(result.failures),'errors':len(result.errors)})
 finally: setattr(r,symbol,old)
print(json.dumps(results,indent=2))
if not all(row['detected'] for row in results):sys.exit(1)
