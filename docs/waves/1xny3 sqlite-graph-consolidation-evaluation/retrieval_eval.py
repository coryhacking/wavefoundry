#!/usr/bin/env python3
"""Scratch-only real-pipeline graph-order experiment (wave 1xny3).

Run only with a coordinator-frozen source/index snapshot and approved judgments.
No production edits, live graph refresh, model downloads, or shared-cache writes.
A is deployed search_combined including its separately reranked graph rescue.
B admits graph before main rerank within A's TOTAL cross-encoder passage budget.
C permits min(30, floor(A_total*0.25)) extra passages. No baseline candidate is
removed. Inputs are checked by content digest across arms. Final top-K is fixed
at seven for evaluation; production's variable citation list is retained in count.

Minimum-anchor gold is deliberately incomplete: path precision is a non-semantic
proxy and unjudged citations are retained. It cannot independently prove the
plan's exhaustive final precision gate. An unavailable model/provider, deadline,
input drift, or absent full-tool observations yields unqualified evidence.
"""
from __future__ import annotations
import argparse, copy, hashlib, json, math, os, pathlib, resource, shutil
import signal, statistics, sys, time, threading, re, platform, importlib.metadata


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def owned(path, root):
    path, root = pathlib.Path(path).resolve(), pathlib.Path(root).resolve()
    if path == root or root not in path.parents:
        raise ValueError(f'Path is outside dedicated scratch root: {path}')
    return path


def percentile(values, q):
    if not values:
        return None
    x = sorted(values); pos = (len(x)-1)*q; low = math.floor(pos)
    return x[low] + (x[min(low+1,len(x)-1)]-x[low])*(pos-low)


def slim(candidate):
    return {k:candidate.get(k) for k in ('id','path','lines','kind','section','score','_symbol','from_graph') if k in candidate}


def identity(candidate):
    return (str(candidate.get('path') or ''), tuple(candidate.get('lines') or ()))


def metrics(query, candidates):
    hits=[]
    for anchor in query['required_anchors']:
        symbol=anchor['symbol'].split('.')[-1]
        found=False
        for c in candidates:
            lines=c.get('lines') or []
            text=str(c.get('text') or c.get('excerpt') or '')
            if c.get('path')==anchor['path'] and len(lines)==2 and lines[0]<=anchor['lines'][1] and lines[1]>=anchor['lines'][0] and symbol in text and c.get('kind')!='code-summary':
                found=True; break
        hits.append(found)
    relevant=sum(c.get('path') in query['relevant_paths'] for c in candidates)
    chain=[hits[e['from']] and hits[e['to']] for e in query['required_chain']]
    return {'anchor_hits':hits,'required_anchor_recall':sum(hits)/len(hits),
            'required_anchor_pair_coverage':sum(chain)/len(chain) if chain else None,
            'required_anchor_pair_hits':chain,
            'gold_path_precision_proxy':relevant/len(candidates) if candidates else 0,
            'unjudged_citations':len(candidates)-relevant,
            'exact_owner_rank_one':bool(candidates and candidates[0].get('path')==query['required_anchors'][0]['path'] and len(candidates[0].get('lines') or [])==2 and candidates[0]['lines'][0]<=query['required_anchors'][0]['lines'][0] and candidates[0]['lines'][1]>=query['required_anchors'][0]['lines'][0] and re.search(r'\bdef\s+'+re.escape(query['required_anchors'][0]['symbol'].split('.')[-1])+r'\s*\(',str(candidates[0].get('text') or candidates[0].get('excerpt') or '')) and candidates[0].get('kind')!='code-summary') if query['category']=='exact_owner' else None,
            'count':len(candidates)}


class QueryDeadline(BaseException):
    """BaseException avoids production broad Exception fallback swallowing timeout."""


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--scratch',required=True);ap.add_argument('--snapshot',required=True)
    ap.add_argument('--source',required=True);ap.add_argument('--output',required=True);ap.add_argument('--qa',required=True)
    ap.add_argument('--questions',default=str(pathlib.Path(__file__).with_name('retrieval_queries.json')))
    ap.add_argument('--runs',type=int,default=3);ap.add_argument('--query-timeout',type=float,default=5)
    ap.add_argument('--time-limit',type=float,default=1800);ap.add_argument('--rss-mib',type=int,default=4096)
    ap.add_argument('--scratch-limit-mib',type=int,default=8192);args=ap.parse_args()
    started=time.monotonic();scratch=pathlib.Path(args.scratch).resolve();snapshot=pathlib.Path(args.snapshot).resolve()
    if snapshot!=scratch: owned(snapshot,scratch)
    if not (scratch/'snapshot.json').is_file(): raise ValueError('Coordinator snapshot receipt missing')
    source=pathlib.Path(args.source).resolve()
    if pathlib.Path(args.output).is_symlink() or pathlib.Path('/tmp/graph-1xny3-retrieval.json').is_symlink():raise ValueError('Output symlink rejected')
    output=pathlib.Path(args.output).resolve()
    if output!=pathlib.Path('/tmp/graph-1xny3-retrieval.json').resolve(): owned(output,scratch)
    if snapshot==source or (source/'.wavefoundry/index').resolve()==(snapshot/'.wavefoundry/index').resolve():
        raise ValueError('Live-index snapshot rejected')
    questions_path=pathlib.Path(args.questions);questions_bytes=questions_path.read_bytes();suite=json.loads(questions_bytes)
    qa=json.loads(pathlib.Path(args.qa).read_text());qhash=hashlib.sha256(questions_bytes).hexdigest()
    if qa.get('questions_sha256')!=qhash or qa.get('verdict')!='approved':
        raise ValueError('Independent QA judgment approval absent or stale')
    # Validate source mapping against the frozen source, before any retrieval.
    for q in suite['queries']:
        for a in q['required_anchors']:
            if hashlib.sha256((snapshot/a['path']).read_bytes()).hexdigest()!=a['source_sha256']:
                raise ValueError('Judgment source differs from snapshot: '+a['path'])
    import fcntl
    lock_handle=(scratch/'.benchmark.lock').open('a+')
    fcntl.flock(lock_handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
    scripts=snapshot/'.wavefoundry/framework/scripts';sys.path.insert(0,str(scripts));sys.dont_write_bytecode=True
    import ctypes, subprocess
    if sys.platform!='darwin':raise ValueError('This bounded RSS monitor is qualified on macOS only')
    libproc=ctypes.CDLL('/usr/lib/libproc.dylib')
    libproc.proc_pidinfo.argtypes=[ctypes.c_int,ctypes.c_int,ctypes.c_uint64,ctypes.c_void_p,ctypes.c_int]
    libproc.proc_pidinfo.restype=ctypes.c_int
    def resident_bytes(pid):
        info=(ctypes.c_uint64*12)()
        result=libproc.proc_pidinfo(pid,4,0,ctypes.byref(info),ctypes.sizeof(info))
        if result!=96:
            if pid==os.getpid():raise RuntimeError('Owned-worker RSS unavailable')
            return 0
        return int(info[1])
    children=[];real_popen=subprocess.Popen
    class TrackedPopen(real_popen):
        def __init__(self,*a,**kw):
            super().__init__(*a,**kw);children.append(self)
    subprocess.Popen=TrackedPopen
    def aggregate_rss():
        return (resident_bytes(os.getpid())+sum(resident_bytes(p.pid) for p in children if p.poll() is None))/1048576
    def stop_owned_children():
        # Only exact Popen handles created in this worker are eligible.
        for child in children:
            if child.poll() is None:child.terminate()
        for child in children:
            try:child.wait(timeout=.5)
            except subprocess.TimeoutExpired:child.kill();child.wait(timeout=1)
    monitor_stop=threading.Event();resource_samples={'samples':0,'peak_rss_mib':0.0,'peak_scratch_mib':0.0}
    def monitor_resources():
        while not monitor_stop.wait(.5):
            try:
                rss=aggregate_rss()
                disk=sum(p.lstat().st_size for p in scratch.rglob('*') if p.is_file() and not p.is_symlink())/1048576
                resource_samples['samples']+=1
                resource_samples['peak_rss_mib']=max(resource_samples['peak_rss_mib'],rss)
                resource_samples['peak_scratch_mib']=max(resource_samples['peak_scratch_mib'],disk)
                reason=('aggregate RSS budget' if rss>args.rss_mib else 'scratch allocation budget' if disk>args.scratch_limit_mib else 'configuration time limit' if time.monotonic()-started>args.time_limit else None)
                if reason:
                    try: current=json.loads(output.read_text())
                    except Exception: current={}
                    current.update(status='bounded_stop',decision='defer_adoption_unqualified',stop_reason=reason,resources=resource_samples)
                    output.write_text(json.dumps(current,indent=2)+'\n');stop_owned_children();os._exit(125)
            except FileNotFoundError:continue
    monitor=threading.Thread(target=monitor_resources,daemon=True);monitor.start()
    cache=owned(scratch/'.wavefoundry/index/evaluation-model-cache',scratch);cache.mkdir(exist_ok=True)
    existing_bytes=sum(p.lstat().st_size for p in scratch.rglob('*') if p.is_file() and not p.is_symlink())
    copy_bytes=sum(p.lstat().st_size for name in ('onnx-src','fastembed') if not (cache/name).exists() for p in (pathlib.Path.home()/'.wavefoundry/cache'/name).rglob('*') if p.is_file() and not p.is_symlink())
    if existing_bytes+copy_bytes>args.scratch_limit_mib*1048576:raise ValueError('Model-cache copy exceeds scratch allocation')
    for name in ('onnx-src','fastembed'):
        target=cache/name
        if target.is_symlink():raise ValueError('Cache directory symlink rejected')
        if not target.exists():
            shutil.copytree(pathlib.Path.home()/'.wavefoundry/cache'/name,target,symlinks=True)
        for p in target.rglob('*'):
            if p.is_symlink() and target.resolve() not in p.resolve().parents:
                raise ValueError('Model-cache symlink escapes scratch')
    temp_dir=owned(scratch/'.wavefoundry/index/evaluation-temp',scratch);temp_dir.mkdir(exist_ok=True)
    os.environ['TMPDIR']=str(temp_dir)+'/'
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',
                      FASTEMBED_CACHE_PATH=str(cache/'fastembed'),PYTHONDONTWRITEBYTECODE='1')
    import accel_embedder as ae
    for attr,sub in [('_ONNX_CACHE','onnx'),('_COREML_CACHE','coreml'),('_CLEAN_ONNX_CACHE','onnx-src')]:
        setattr(ae,attr,cache/sub)
    # Child runs the identical production safety probe with only output/cache paths
    # redirected. Neither provider availability nor probe verdict is substituted.
    import subprocess_util
    real_run=subprocess_util.isolated_run
    cache_setup='import pathlib, accel_embedder as ae\n'+''.join(f'ae.{attr}=pathlib.Path({str(cache/sub)!r})\n' for attr,sub in [('_ONNX_CACHE','onnx'),('_COREML_CACHE','coreml'),('_CLEAN_ONNX_CACHE','onnx-src')])
    def isolated_run(command,*a,**kw):
        if isinstance(command,list) and '-c' in command:
            i=command.index('-c')+1
            if 'import accel_embedder as ae' in command[i]:
                command=list(command);command[i]=cache_setup+command[i]
        return real_run(command,*a,**kw)
    subprocess_util.isolated_run=isolated_run
    import server_impl as server, graph_query as gq, graph_indexer as gi
    payload=gi.read_graph_payload(snapshot)
    if not payload.get('present'):raise ValueError('Frozen graph missing')
    frozen=gq.GraphQueryIndex(payload)
    def query_index(root,*,layer='project'):
        if pathlib.Path(root).resolve()!=snapshot or layer!='project':raise ValueError('Unexpected graph root/layer')
        return frozen
    gq.get_query_index=query_index
    # Fix script loader module identities so graph reads cannot trigger refresh via
    # a second dynamic graph_query module instance.
    server._load_graph_query=lambda:gq
    attempts=[];initial_inputs={};baseline_cost={};first_metadata={}
    class ExperimentIndex(server.WaveIndex):
        def _start_background_model_downloads_after_startup(self):pass
        def begin(self,arm,qid):
            self.arm=arm;self.qid=qid;self.calls=[];self.initial=[];self.admitted=[];self.pregraph=[];self.reranked_pool=[];self.phase='candidate_retrieval';self.pending_passages=0
        def _embed_query(self,text,model_name):
            self.phase='query_embedding'
            result=super()._embed_query(text,model_name)
            self.phase='dense_lexical_candidate_retrieval'
            return result
        def _agent_rerank(self,query,candidates):
            first=not self.calls
            if first:
                sig=digest([{k:c.get(k) for k in ('id','path','lines','text','kind','section','score')} for c in candidates])
                prior=initial_inputs.setdefault(self.qid,sig)
                if prior!=sig:raise ValueError('Initial retrieval candidates changed between variants')
                self.initial=copy.deepcopy(candidates)
                if self.arm!='A':
                    allowance=baseline_cost[self.qid]-len(candidates)
                    if self.arm=='C':allowance+=min(30,math.floor(baseline_cost[self.qid]*.25))
                    allowance=max(0,allowance)
                    graph=super()._graph_signal_candidates(query,candidates,cap=min(30,max(allowance,server.AGENT_GRAPH_SIGNAL_CAP)))
                    seen={identity(c) for c in candidates};self.pregraph=copy.deepcopy(graph)
                    for c in graph:
                        if identity(c) not in seen and len(self.admitted)<allowance:
                            seen.add(identity(c));c['from_graph']=True;self.admitted.append(c);candidates.append(c)
            self.reranked_pool.extend(copy.deepcopy(candidates))
            self.phase='main_rerank' if first else 'rescue_rerank';self.pending_passages=len(candidates)
            t=time.monotonic();ok=super()._agent_rerank(query,candidates)
            self.calls.append({'passages':len(candidates),'seconds':time.monotonic()-t,'ok':ok})
            if not ok:raise ValueError('Cross-encoder failed or unavailable; no lexical substitution')
            self.phase='selection';self.pending_passages=0
            return ok
        def _graph_signal_candidates(self,query,candidates,*,cap):
            if self.arm=='A':return super()._graph_signal_candidates(query,candidates,cap=cap)
            return self.pregraph[:cap]
        def _merge_graph_into_citations(self,query,graph_src,results,*,reranked):
            if self.arm=='A':return super()._merge_graph_into_citations(query,graph_src,results,reranked=reranked)
            return 0
    idx=ExperimentIndex(snapshot);idx._ensure_loaded()
    walked=idx._indexer_module().walk_repo(snapshot,respect_ignore=True)
    if any(cache in p.resolve().parents or temp_dir in p.resolve().parents for p in walked):raise ValueError('Model cache/temp visible to frozen repository walker')
    walked_identity=digest(sorted(str(p.relative_to(snapshot)) for p in walked))
    # Startup is not a warm query; model construction can legitimately exceed 5s.
    warm_start=time.monotonic();idx._get_reranker()
    for name in (idx._indexer_constant('DOCS_MODEL'),idx._indexer_constant('CODE_MODEL')):
        idx._get_embedder(name)
    reranker=idx._get_reranker()
    if reranker is None:raise ValueError('Reranker unavailable')
    def embedding_providers(model):
        pending=[model];seen=set()
        for _ in range(4):
            nxt=[]
            for obj in pending:
                if id(obj) in seen:continue
                seen.add(id(obj))
                if callable(getattr(obj,'get_providers',None)):return obj.get_providers()
                if isinstance(getattr(obj,'provider',None),str):return [obj.provider]
                for name in ('model','_model','session','_session'):
                    child=getattr(obj,name,None)
                    if child is not None:nxt.append(child)
            pending=nxt
        return ['not_introspectable']
    provider=dict(reranker_model=reranker.model_name,reranker_provider=reranker.provider,
                  embedding=[{'model':k,'provider':embedding_providers(v)} for k,v in idx._embedders.items()])
    startup=time.monotonic()-warm_start
    prior_attempt=json.loads(output.read_text()) if output.exists() else None
    receipt={'prior_attempt':prior_attempt,'schema_version':1,'status':'running','scope':'real search_combined pipeline and code_ask response on frozen scratch; no model or candidate simulation',
             'questions_sha256':qhash,'harness_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'snapshot_sha256':hashlib.sha256((scratch/'snapshot.json').read_bytes()).hexdigest(),'runtime':{'python':sys.version,'os':platform.platform(),'machine':platform.machine(),'packages':{name:importlib.metadata.version(name) for name in ('apsw','sqlite-vec','onnxruntime','fastembed')}},'qa':qa,'provider':provider,'model_startup_seconds':startup,'walker_cache_temp_excluded':True,'walked_paths_sha256':walked_identity,'walked_path_count':len(walked),'temp_directory':str(temp_dir),'coreml_probe_verdicts':{str(k):v for k,v in ae._coreml_static_probe_cache.items()},'warmup_observations':[],
             'graph_counts':payload.get('counts'),'resource_samples':resource_samples,'resource_monitor':'macOS proc_pidinfo for owned worker and directly tracked Popen children; no host process census', 'final_top_k':7,'rows':attempts,
             'budget_policy':'B total passages <= A initial+rescue; C <= A total + min(30,floor(A total*.25)); no initial candidate displacement',
             'limitations':['Questions name implementation identifiers heavily; no generalization to purely conceptual queries.','Anchor-pair coverage measures co-evidence, not graph edge-path correctness.','Gold anchors/path set is minimum required evidence, not exhaustive relevance; precision is a path-match proxy.','Warm interleaved in one process; OS cache not flushed.','Top 7 projection is fixed across arms; production returns a variable larger citation list.']}
    def save():output.write_text(json.dumps(receipt,indent=2)+'\n')
    def deadline_exit():
        # A Python signal alone can be delayed by native inference. The owned
        # worker watchdog records the stop and exits this process, never a host.
        receipt['status']='bounded_stop';receipt['stop_reason']='hard query deadline exceeded'
        receipt['decision']='defer_adoption_unqualified';receipt['stop_stage']={'phase':idx.phase,'pending_passages':idx.pending_passages,'completed_reranker_calls':idx.calls};save();stop_owned_children();os._exit(124)
    def timed_query(q):
        receipt['active_query']={'question':q['id'],'arm':idx.arm,'started_monotonic':time.monotonic()};save()
        timer=threading.Timer(args.query_timeout+.1,deadline_exit);timer.daemon=True;timer.start()
        signal.setitimer(signal.ITIMER_REAL,args.query_timeout)
        try:return server.code_ask_response(idx,snapshot,q['question'])
        finally:signal.setitimer(signal.ITIMER_REAL,0);timer.cancel();receipt.pop('active_query',None)
    def alarm(*_):raise QueryDeadline('query exceeded fixed deadline')
    signal.signal(signal.SIGALRM,alarm)
    def rss_mib():return aggregate_rss()
    def guard():
        if time.monotonic()-started>args.time_limit:raise QueryDeadline('configuration time limit')
        if rss_mib()>args.rss_mib:raise QueryDeadline('aggregate RSS budget')
        disk=sum(p.lstat().st_size for p in scratch.rglob('*') if p.is_file() and not p.is_symlink())/1048576
        if disk>args.scratch_limit_mib:raise QueryDeadline('scratch allocation budget')
        return disk
    try:
        # Ten warmups use the frozen judgments but do not contribute to quality or
        # latency aggregates. Models are already constructed before this stage.
        for warm in range(10):
            q=suite['queries'][warm%len(suite['queries'])];guard();idx.begin('A',q['id'])
            t=time.monotonic();response=timed_query(q)
            if not (response.get('data') or {}).get('reranked'):raise ValueError('Warmup reranker unavailable')
            receipt['warmup_observations'].append({'question':q['id'],'seconds':time.monotonic()-t})
            baseline_cost[q['id']]=sum(c['passages'] for c in idx.calls)
            save()
        for run in range(args.runs):
            for q in suite['queries']:
                # First paired block establishes A's observed rescue passage budget.
                order=('A','B','C') if run==0 else (('B','C','A') if run%2 else ('C','A','B'))
                for arm in order:
                    disk=guard();idx.begin(arm,q['id']);start=time.monotonic()
                    response=timed_query(q)
                    elapsed=time.monotonic()-start;data=response.get('data') or {}
                    if not data.get('reranked') or data.get('fallback_reason'):
                        raise ValueError('Unqualified retrieval response: '+str(data.get('fallback_reason')))
                    if provider['reranker_provider']!=idx._get_reranker().provider:raise ValueError('Reranker provider changed')
                    cost=sum(c['passages'] for c in idx.calls)
                    if arm=='A':
                        old=baseline_cost.setdefault(q['id'],cost)
                        if old!=cost:raise ValueError('Baseline reranker cost changed')
                    budget=baseline_cost[q['id']]+(min(30,math.floor(baseline_cost[q['id']]*.25)) if arm=='C' else 0)
                    if cost>budget:raise ValueError('Reranker passage budget exceeded')
                    citations=(data.get('citations') or [])[:7]
                    row={'run':run,'question':q['id'],'category':q['category'],'arm':arm,'wall_seconds':elapsed,
                         'vector_ms':data.get('vector_ms'),'rerank_ms':data.get('rerank_ms'),'reranker_calls':idx.calls,
                         'initial_count':len(idx.initial),'initial_hash':initial_inputs[q['id']],'admitted_graph_count':len(idx.admitted),
                         'candidate_budget':budget,'actual_reranker_passages':cost,'candidate_metrics':metrics(q,list({identity(c):c for c in idx.reranked_pool}.values())),
                         'final_metrics':metrics(q,citations),'citations':[slim(c) for c in citations],
                         'production_citation_count':len(data.get('citations') or []),'rss_mib':rss_mib(),'scratch_mib':disk}
                    attempts.append(row);save();print(json.dumps({k:row[k] for k in ('run','question','arm','wall_seconds','admitted_graph_count')}),flush=True)
        receipt['status']='complete';receipt['decision']='retain_current_ordering_unqualified_precision_gold'
    except (Exception,QueryDeadline) as exc:
        receipt['status']='bounded_stop';receipt['stop_reason']=type(exc).__name__+': '+str(exc)
        receipt['decision']='defer_adoption_unqualified'
        receipt['stop_stage']={'phase':idx.phase,'pending_passages':idx.pending_passages,'completed_reranker_calls':idx.calls}
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        receipt['elapsed_seconds']=time.monotonic()-started
        receipt['summary']={arm:{'observations':len(values:=[r for r in attempts if r['arm']==arm]),
                               'warm_p50_seconds':percentile([r['wall_seconds'] for r in values],.5),
                               'warm_p95_seconds':percentile([r['wall_seconds'] for r in values],.95),
                               'mean_anchor_recall':statistics.mean(r['final_metrics']['required_anchor_recall'] for r in values) if values else None,
                               'mean_gold_path_precision_proxy':statistics.mean(r['final_metrics']['gold_path_precision_proxy'] for r in values) if values else None} for arm in ('A','B','C')}
        receipt['paired_quality_deltas']=[]
        for run in range(args.runs):
            for q in suite['queries']:
                found={r['arm']:r for r in attempts if r['run']==run and r['question']==q['id']}
                if 'A' not in found:continue
                a=found['A']['final_metrics']
                for arm in ('B','C'):
                    if arm not in found:continue
                    b=found[arm]['final_metrics']
                    receipt['paired_quality_deltas'].append({'run':run,'question':q['id'],'arm':arm,
                        'anchor_recall_delta':b['required_anchor_recall']-a['required_anchor_recall'],
                        'gold_precision_proxy_delta':b['gold_path_precision_proxy']-a['gold_path_precision_proxy'],
                        'lost_required_anchors':[i for i,(old,new) in enumerate(zip(a['anchor_hits'],b['anchor_hits'])) if old and not new],
                        'lost_exact_owner':a['exact_owner_rank_one'] is True and b['exact_owner_rank_one'] is False})
        save()
    monitor_stop.set()
    lock_handle.close()
    return 0 if receipt['status']=='complete' else 2

if __name__=='__main__':
    try: status=main()
    except Exception as exc:
        if '--output' in sys.argv:
            target=pathlib.Path(sys.argv[sys.argv.index('--output')+1])
            if target.is_symlink() or pathlib.Path('/tmp/graph-1xny3-retrieval.json').is_symlink():raise ValueError('Output symlink rejected')
            if target.resolve()!=pathlib.Path('/tmp/graph-1xny3-retrieval.json').resolve():
                owned(target,pathlib.Path(sys.argv[sys.argv.index('--scratch')+1]))
            try: previous=json.loads(target.read_text())
            except (OSError,ValueError): previous=None
            target.write_text(json.dumps({'prior_attempt':previous,'schema_version':1,'status':'initialization_failed','decision':'defer_adoption_unqualified','stop_reason':type(exc).__name__+': '+str(exc)},indent=2)+'\n')
        raise
    raise SystemExit(status)
