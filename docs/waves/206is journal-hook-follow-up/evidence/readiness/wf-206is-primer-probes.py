import ast,contextlib,importlib.util,json,pathlib,sys,tempfile,types
from unittest.mock import patch
scripts=pathlib.Path.cwd()/".wavefoundry/framework/scripts";sys.path.insert(0,str(scripts))
spec=importlib.util.spec_from_file_location("primer_upgrade_ext",scripts/"upgrade_extensions.py");ext=importlib.util.module_from_spec(spec);spec.loader.exec_module(ext)
results=[]
with tempfile.TemporaryDirectory(prefix="wf-c6-primer-") as td:
 root=pathlib.Path(td);incoming=root/".wavefoundry/framework/scripts";incoming.mkdir(parents=True)
 journals=root/"docs/agents/journals";journals.mkdir(parents=True);(journals/"live.md").write_text("kept content\n")
 (root/".wavefoundry/upgrade-in-progress.json").write_text('{"review_sidecar_cleanup": {}}')
 (incoming/"mcp_tool_extensions.py").write_text('from pathlib import Path\nPath(__file__).with_name("declaration-fired").write_text("yes")\nEXTENSION_JOURNAL_TEMPLATES=()\nEXTENSION_JOURNAL_PRE_MIGRATION_HOOK="primer_hook:prepare"\nEXTENSION_JOURNAL_PRE_MIGRATION_TRIGGER="journals_present"\ndef journal_declaration_problems(): return []\n')
 (incoming/"primer_hook.py").write_text('from pathlib import Path\ndef prepare(root):\n Path(root,"hook-fired").write_text("yes")\n')
 for version in ["1.15.0","1.29.0"]:
  with patch.object(ext,"repair_declaring_scaffold"),patch.object(ext,"_reconcile_graph_builder_doc_claim"):
   ext.pre_docs_gate(types.SimpleNamespace(root=root,from_version=version))
  results.append({"probe":"current_later_version_optin_baseline","version":version,"declaration_executed":(incoming/"declaration-fired").exists(),"hook_called":(root/"hook-fired").exists(),"journal_unchanged":(journals/"live.md").read_text()=="kept content\n"})
 for name in ["contained_files.py","history_paths.py","path_containment.py","record_paths.py"]:(incoming/name).write_bytes((scripts/name).read_bytes())
 before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob("*") if p.is_file()};preview=ext.migrate_journals(root,apply=False)
 after={str(p.relative_to(root)):p.read_bytes() for p in root.rglob("*") if p.is_file()}
 results.append({"probe":"public_preview_declaration_marker","report":preview,"declaration_executed":(incoming/"declaration-fired").exists(),"hook_called":(root/"hook-fired").exists(),"bytes_unchanged":before==after})
 (incoming/"primer_dep.py").write_text('VALUE="INCOMING"\n')
 (incoming/"primer_hook.py").write_text('import primer_dep\nfrom pathlib import Path\ndef prepare(root):\n Path(root,"helper-value").write_text(primer_dep.VALUE)\n')
 old=types.ModuleType("primer_dep");old.VALUE="OLD";sys.modules["primer_dep"]=old
 with ext._scripts_on_sys_path(incoming):ext._load_journal_hook(incoming,"primer_hook:prepare")(root)
 results.append({"probe":"cached_sibling_collision","expected_under_AC4":"INCOMING","observed":(root/"helper-value").read_text()})
 del sys.modules["primer_dep"]
 with ext._scripts_on_sys_path(incoming):ext._load_journal_hook(incoming,"primer_hook:prepare")(root)
 results.append({"probe":"cached_sibling_negative_control","expected":"INCOMING","observed":(root/"helper-value").read_text()})
 for label,source in [("absent","X=1"),("invalid_literal",'EXTENSION_JOURNAL_PRE_MIGRATION_TRIGGER="typo"'),("dynamic",'EXTENSION_JOURNAL_PRE_MIGRATION_TRIGGER=str("journals_present")')]:
  try:observed=repr(ext._static_module_literal(ast.parse(source),"EXTENSION_JOURNAL_PRE_MIGRATION_TRIGGER"))
  except ValueError:observed="ValueError"
  results.append({"probe":"static_trigger_feasibility","case":label,"observed":observed})
print(json.dumps(results,indent=2))
