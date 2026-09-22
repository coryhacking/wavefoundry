import pathlib,subprocess,json,os
os.environ["PYTHONPATH"]="/private/tmp/1ymzq-code-review-scratch/.wavefoundry/framework/scripts"
s=pathlib.Path('/private/tmp/1ymzq-code-review-scratch/.wavefoundry/framework/scripts')
cases=[('containment boundary','path_containment.py','return candidate if candidate.is_relative_to(root) else None','return candidate','test_path_containment.ContainedPathTests.test_parent_escape_with_missing_tail'),('symlink component refusal','path_containment.py','if stat.S_ISLNK(mode):','if False:','test_path_containment.ContainedPathTests.test_leave_and_reenter_link'),('loop uncertainty','path_containment.py','path.stat()','pass','test_path_containment.ContainedPathTests.test_loop_refused_on_each_interpreter_branch'),('CE patch transparency','context_efficiency_handlers.py','cfg = server_impl._read_ce_projection_config(root)','cfg = _read_ce_projection_config(root)','test_index_source_guard.SourceGuardTests.test_same_process_build_excludes_monitor_and_unlocked_carrier_allows_write'),('upgrade old tree fallback','upgrade_extensions.py','except ImportError:\n            # The new archive hook','except ImportError:\n            raise\n            # The new archive hook','test_upgrade_wavefoundry.RuntimeLockCutoverMigrationTests.test_cutover_module_absence_uses_installed_modern_stop')]
rows=[]
for name,file,before,after,test in cases:
 p=s/file; orig=p.read_text(); assert before in orig
 baseline=subprocess.run(['python3','-B','-m','unittest',test],cwd=s/'tests',text=True,capture_output=True,timeout=45)
 p.write_text(orig.replace(before,after,1))
 try:r=subprocess.run(['python3','-B','-m','unittest',test],cwd=s/'tests',text=True,capture_output=True,timeout=45);row=dict(mechanism=name,test=test,baseline=baseline.returncode,mutant=r.returncode,output=r.stderr[-2500:])
 except subprocess.TimeoutExpired:row=dict(mechanism=name,test=test,baseline=baseline.returncode,mutant='timeout')
 finally:p.write_text(orig)
 rows.append(row);print(json.dumps(row),flush=True)
pathlib.Path('/private/tmp/1ymzq-code-mutations.json').write_text(json.dumps(rows,indent=2))
