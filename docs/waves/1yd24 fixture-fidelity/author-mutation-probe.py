import inspect,io,json,unittest
import server_tools_support as support
import test_declared_wave_fixtures as tests
mutants=[
 ('omit-readiness-run','make_declared_wave','if readiness_run:', 'if False:',tests.DeclaredWaveFixtureTests,'test_valid_fixture_and_independent_readiness_oracle'),
 ('omit-approvals','make_declared_wave','for key in approvals:', 'for key in ():',tests.DeclaredWaveFixtureTests,'test_valid_fixture_and_independent_readiness_oracle'),
 ('skip-receipt-proof','make_declared_wave','if errors or not any(r.get("record_type") == "review_policy_receipt" for r in records):','if False:',tests.DeclaredWaveFixtureTests,'test_missing_receipt_cannot_hide_behind_expected_initial_refusal'),
 ('leak-scoped-stubs','declared_wave_doc_gates','with contextlib.ExitStack() as stack:', 'if (stack := contextlib.ExitStack()):',tests.DeclaredWaveFixtureTests,'test_refusals_fail_at_the_producer_and_restore_all_stubs'),
 ('filewide-helper-exemption','declaration_sites','valid = any(', 'valid = "make_declared_wave(" in source or any(',tests.DeclarationCensusTests,'test_unrelated_helper_or_comment_cannot_exempt_a_site'),
 ('ignore-fstring-segments','declaration_sites',"string_types = {tokenize.STRING, getattr(tokenize, 'FSTRING_MIDDLE', tokenize.STRING)}",'string_types = {tokenize.STRING}',tests.DeclarationCensusTests,'test_classifications_and_multiline_and_fstring_literal_segments'),
 ('distant-comment-exemption','declaration_sites',"comments.get(token.start[0] - 1, '')", "comments.get(token.start[0] - 1, '') or comments.get(token.start[0] - 2, '')",tests.DeclarationCensusTests,'test_unrelated_helper_or_comment_cannot_exempt_a_site'),
]
rows=[]
for name,fn,old,new,cls,method in mutants:
 owner=support if fn!='declaration_sites' else tests
 original=getattr(owner,fn);binding=getattr(tests,fn,None)
 source=inspect.getsource(original);assert old in source
 # Preserve all server seams even for the intentionally leaking ExitStack mutant.
 srv=support.load_server();seams={key:getattr(srv,key) for key in tests.fixture_doc_stubs()}
 try:
  exec(compile(source.replace(old,new),'<fixture-mutant>','exec'),owner.__dict__)
  if fn != 'declared_wave_doc_gates' and binding is not None:setattr(tests,fn,getattr(owner,fn))
  stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(cls(method))
  rows.append({'mutant':name,'test':method,'killed':not result.wasSuccessful(),'failures':len(result.failures),'errors':len(result.errors),'output':stream.getvalue()})
 finally:
  setattr(owner,fn,original)
  if binding is not None:setattr(tests,fn,binding)
  for key,value in seams.items():setattr(srv,key,value)
print(json.dumps(rows,indent=2));assert all(r['killed'] for r in rows)
