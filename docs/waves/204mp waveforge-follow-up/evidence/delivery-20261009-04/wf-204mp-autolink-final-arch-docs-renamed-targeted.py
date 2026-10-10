import os,sys,tempfile,shutil,subprocess,json
from pathlib import Path
sys.path[:0]=[str(Path.cwd()/'.wavefoundry/framework/scripts'),str(Path.cwd()/'.wavefoundry/framework/scripts/tests')]
from record_layout_support import apply_profile,load_profile
src=Path.cwd()/'.wavefoundry/framework'
with tempfile.TemporaryDirectory() as d:
 root=Path(d)/'framework'
 shutil.copytree(src,root,ignore=shutil.ignore_patterns('__pycache__','*.pyc','index','test-cache.json','test-run.lock'))
 apply_profile(root/'scripts',load_profile('prompt-names'))
 e=dict(os.environ,PYTHONPATH=str(root/'scripts')+os.pathsep+str(root/'scripts/tests'),PYTHONDONTWRITEBYTECODE='1',WAVEFOUNDRY_TEST_PROFILE='prompt-names')
 r=subprocess.run([sys.executable,'-B','-m','unittest','test_distribution_seams.LiteralReconcileKeyTests','test_council_signoff_keys.DigestInputTests','test_vocabulary_prompt_names.ValidationTests.test_a_chain_validates','test_vocabulary_prompt_names.ValidationTests.test_example_names_are_neutral','test_vocabulary_prompt_names.ProfileConsumerTests.test_names_and_paths_follow_the_profile','test_legacy_council_actors'],cwd=root/'scripts',env=e,capture_output=True,text=True,timeout=200)
 print(r.stdout);print(r.stderr);print('EXIT',r.returncode)
 Path('/tmp/wf-204mp-autolink-final-arch-docs-renamed-targeted-result.json').write_text(json.dumps({'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr},indent=2))
