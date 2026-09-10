"""Disposable vector lifecycle/cold-process comparison; run once per paired cycle."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time

PROCESS_START = time.perf_counter()
parser = argparse.ArgumentParser()
parser.add_argument('--backend', choices=['lance', 'lance-exact', 'lance-flat', 'sqlite', 'sqlite-scalar'], required=True)
parser.add_argument('--source', required=True)
parser.add_argument('--scale', choices=[1, 2], type=int, default=1)
parser.add_argument('--work-dir', required=True)
parser.add_argument('--harness-dir', default=str(Path(__file__).resolve().parent))
args = parser.parse_args()
work = Path(args.work_dir)
work.mkdir(parents=True, exist_ok=False)
result = {'backend': args.backend, 'source': args.source, 'scale': args.scale, 'status': 'running',
          'scope': 'single fresh build/update/maintenance cycle, no embedding; aggregate 3 paired runs externally',
          'cold_scope': 'new Python process per query; OS caches not flushed; parent-created store',
          'process_scope': 'driver body timer excludes initial interpreter/stdlib startup; child external wall includes interpreter startup'}

CHILD = r'''
import json,sys,time
request=json.load(sys.stdin)
start=time.perf_counter()
sys.path.insert(0, request['harness_dir'])
import vector_backend_eval as e
import_ms=(time.perf_counter()-start)*1000
opened=time.perf_counter()
store=e.Store(request['backend'],request['path'],request['dimensions'],existing=True)
open_ms=(time.perf_counter()-opened)*1000
query_start=time.perf_counter()
case=dict(vector=e.np.asarray(request['vector'],dtype=e.np.float32),k=request['k'],sql=request['sql'],complex=False)
rows=store.search(case)
query_ms=(time.perf_counter()-query_start)*1000
import resource
rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
peak_rss_bytes=rss if sys.platform=='darwin' else rss*1024
print(json.dumps({'peak_rss_bytes':peak_rss_bytes,'import_ms':import_ms,'open_ms':open_ms,'query_ms':query_ms,'import_open_query_ms':(time.perf_counter()-start)*1000,'rows':rows}))
'''

try:
    imported = time.perf_counter()
    sys.path.insert(0, args.harness_dir)
    import vector_backend_eval as e
    result['harness_import_ms'] = (time.perf_counter() - imported)*1000
    rows, vectors = e.load_corpus(args.source, args.scale)
    result.update(rows=len(rows), dimensions=vectors.shape[1],
                  vector_hash=hashlib.sha256(vectors.tobytes()).hexdigest(),
                  payload_hash=hashlib.sha256(''.join(r['payload'] for r in rows).encode()).hexdigest())
    store_path = work / ('lance' if args.backend.startswith('lance') else 'vectors.db')
    store, result['open_including_backend_import_ms'] = e.elapsed(lambda:e.Store(args.backend, store_path, vectors.shape[1]))
    _, result['storage_build_ms'] = e.elapsed(lambda:store.add(rows, vectors))
    _, result['initial_maintenance_ms'] = e.elapsed(store.maintain)
    expected = {r['rid']:(r['payload'],v.tobytes()) for r,v in zip(rows,vectors)}
    assert store.snapshot() == expected, 'initial snapshot mismatch'
    extra = dict(rows[0], rid=len(rows))
    _, result['append_ms'] = e.elapsed(lambda:store.add([extra],vectors[:1]))
    _, result['delete_ms'] = e.elapsed(lambda:store.delete(len(rows)))
    _, result['maintenance_ms'] = e.elapsed(store.maintain)
    _, result['reopen_ms'] = e.elapsed(store.reopen)
    assert store.snapshot() == expected, 'reopen snapshot mismatch'
    result['roundtrip'] = 'passed'
    result['post_maintenance_bytes'] = e.sizes(work)
    case = e.query_slices(rows,vectors)[0]
    reference = e.exact_reference(vectors, case['vector'], case['eligible'], len(case['eligible']))
    request = json.dumps(dict(backend=args.backend,dimensions=vectors.shape[1],harness_dir=args.harness_dir,path=str(store_path),vector=case['vector'].tolist(),k=case['k'],sql=case['sql']))
    samples = []
    for iteration in range(9):
        started = time.perf_counter()
        child = subprocess.run([sys.executable,'-B','-c',CHILD], input=request, text=True,
                               capture_output=True, timeout=60, check=True)
        wall_ms = (time.perf_counter()-started)*1000
        sample = json.loads(child.stdout)
        found = sample.pop('rows')
        sample['process_wall_ms'] = wall_ms
        sample['assessment'] = e.assess_rows(found,reference,eligible_indices=case['eligible'],expected_count=min(case['k'],len(case['eligible'])))
        assert all(r['payload']==json.loads(rows[r['rid']]['payload']) for r in found), 'cold payload mismatch'
        if child.stderr:
            sample['stderr'] = child.stderr[-2000:]
        if iteration >= 2:
            samples.append(sample)
    result['cold_process'] = {'query':'unfiltered', 'warmups':2, 'samples':samples,
        'median_process_wall_ms':statistics.median(s['process_wall_ms'] for s in samples),
        'p95_process_wall_ms':max(s['process_wall_ms'] for s in samples),
        'median_import_open_query_ms':statistics.median(s['import_open_query_ms'] for s in samples),
        'p95_import_open_query_ms':max(s['import_open_query_ms'] for s in samples)}
    result['status'] = 'passed' if all(s['assessment']['contract_ok'] for s in samples) else 'contract_failed'
    result['resource_scope'] = 'fresh child query process including interpreter, numpy, harness and selected backend; no input corpus, Arrow load, oracle or roundtrip snapshot; OS cache not flushed'
    result['quality_note'] = 'nearest-set mismatch evaluated against paired baseline independently; status covers shape/filter/distance/hydration only'
except Exception as exc:
    result.update(status='error',error_type=type(exc).__name__,error=str(exc))
    raise
finally:
    result['driver_body_ms']=(time.perf_counter()-PROCESS_START)*1000
    (work/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':result['status'],'rows':result['rows']}))
