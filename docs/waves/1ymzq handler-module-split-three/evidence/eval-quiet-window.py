from pathlib import Path
import subprocess, sys, threading
repo=Path('/Users/coryhacking/Developer/wavefoundry')
sys.path.insert(0,str(repo/'.wavefoundry/framework/scripts'))
from indexer import mark_reindex_pending
stop=threading.Event()
def quiet():
    while not stop.is_set():
        mark_reindex_pending(repo/'.wavefoundry/index')
        stop.wait(10)
thread=threading.Thread(target=quiet,daemon=True)
thread.start()
try:
    result=subprocess.run([sys.executable,'-B',str(repo/'.wavefoundry/framework/scripts/retrieval_eval.py'),'--root',str(repo),'--fixtures','docs/evals/retrieval-quality-golden.json',*sys.argv[1:]],cwd=repo)
finally:
    stop.set()
    thread.join()
raise SystemExit(result.returncode)
