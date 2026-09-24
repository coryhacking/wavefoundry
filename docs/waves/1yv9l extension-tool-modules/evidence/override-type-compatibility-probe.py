import pathlib,sys,tempfile,shutil,subprocess,os,json
src=pathlib.Path('.wavefoundry/framework/scripts').resolve()
sys.path.insert(0,str(src/'tests'))
import test_extension_tool_modules as t
# Existing public build+call driver; only change annotation of an override.
driver=t._DRIVER.replace('def wf_create_wave(slug: str, mode:', 'def wf_create_wave(slug: int, mode:')
with tempfile.TemporaryDirectory() as d:
 s=pathlib.Path(d)/'scripts';shutil.copytree(src,s,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
 r=subprocess.run([sys.executable,'-B','-c',driver,'ext'],cwd=s,env=dict(os.environ,PYTHONPATH=str(s)),text=True,capture_output=True)
 print('returncode',r.returncode);print(r.stderr[-7000:]);print(r.stdout[-1000:])
