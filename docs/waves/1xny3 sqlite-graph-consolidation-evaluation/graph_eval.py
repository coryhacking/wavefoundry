"""Isolated, non-shipping graph experiment. Never opens the live graph API.

Run with the Wavefoundry tool interpreter, -B, and --help. All mutations require
an invocation-owned scratch root; SQLite snapshots include committed WAL data.
"""
from __future__ import annotations
import argparse, collections, contextlib, gc, gzip, hashlib, json, os, platform, fcntl
import random, resource, shutil, signal, sqlite3, statistics, subprocess, sys, ctypes
import tempfile, threading, time, calendar, stat
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCRIPTS = REPO / '.wavefoundry/framework/scripts'
sys.path.insert(0, str(SCRIPTS))
import apsw
from sqlite_runtime import backup, connect
from graph_query import GraphQueryIndex

MIB = 1024 ** 2
MEM_CAP = 4 * 1024 ** 3  # measured host RAM=32GiB; smaller than its 25% ceiling
MARKER = '.graph-evaluation-owned'
CHILDREN = {}
_ORIGINAL_POPEN = subprocess.Popen

def tracked_popen(*args, **kwargs):
    kwargs.setdefault('start_new_session', True)
    process = _ORIGINAL_POPEN(*args, **kwargs)
    CHILDREN[process.pid] = process
    return process
subprocess.Popen = tracked_popen

def child_rss(pid):
    if sys.platform == 'darwin':
        # A producer thread may be reaping this owned child while poll's
        # nonblocking waitpid lock still reports None. Retry that bounded race;
        # a live child whose RSS remains unavailable must still stop the run.
        for attempt in range(5):
            buf=(ctypes.c_uint64*12)()
            n=ctypes.CDLL('/usr/lib/libproc.dylib').proc_pidinfo(pid,4,0,ctypes.byref(buf),96)
            if n==96:return int(buf[1])
            if CHILDREN[pid].poll() is not None:return 0
            if attempt < 4:time.sleep(.005)
        raise RuntimeError('owned-child RSS unavailable')
    try:return int(Path(f'/proc/{pid}/statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')
    except FileNotFoundError:return 0

def aggregate_rss():
    return resident_bytes()+sum(child_rss(pid) for pid,p in list(CHILDREN.items()) if p.poll() is None)

def stop_owned_children():
    for pid,p in list(CHILDREN.items()):
        if p.poll() is None:
            try:os.killpg(pid,signal.SIGTERM);p.wait(timeout=1)
            except ProcessLookupError:pass
            except subprocess.TimeoutExpired:os.killpg(pid,signal.SIGKILL);p.wait()



def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(MIB), b''): h.update(b)
    return h.hexdigest()


def owned(root, path=None):
    root = Path(root).resolve()
    if not (root / MARKER).is_file() or root == REPO or root.is_relative_to(REPO):
        raise ValueError('scratch ownership required')
    target = Path(path or root).resolve()
    if not target.is_relative_to(root): raise ValueError('scratch escape refused')
    return target


def rss():
    n = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return n if sys.platform == 'darwin' else n * 1024


def resident_bytes():
    if sys.platform == 'darwin':
        lib=ctypes.CDLL('/usr/lib/libSystem.B.dylib')
        buf=(ctypes.c_uint64*6)();count=ctypes.c_uint(12)
        if lib.task_info(lib.mach_task_self(),20,ctypes.byref(buf),ctypes.byref(count)) != 0:
            raise RuntimeError('cannot measure current RSS')
        return int(buf[1])
    return int(Path('/proc/self/statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')


def directory_bytes(root):
    total=0
    for p in Path(root).rglob('*'):
        try:info=p.lstat()
        except FileNotFoundError:continue  # owned disposable stage was removed
        if stat.S_ISREG(info.st_mode):total+=info.st_size
    return total


def guard_stop(root,observations,code):
    try:dump(Path(root) / f'worker-stop-{os.getpid()}.json',observations)
    finally:
        try:stop_owned_children()
        finally:os._exit(code)


def guard(root, deadline=1800):
    """Owned worker watchdog, peak-memory and disk sampling, no host kills."""
    cfg = json.loads((Path(root) / 'snapshot.json').read_text())
    end = time.monotonic() + deadline
    stop = threading.Event()
    observations = {'peak_rss_bytes': aggregate_rss(), 'peak_disk_bytes': directory_bytes(root), 'samples': 1}
    def watch():
        while not stop.wait(.05):
            try:
                m = max(rss(),aggregate_rss()); d = directory_bytes(root) if observations['samples']%20==0 else observations['peak_disk_bytes']
            except Exception as exc:
                observations['monitor_failure']=repr(exc)
                guard_stop(root,observations,89)
            observations.update(peak_rss_bytes=max(m, observations['peak_rss_bytes']),
                                peak_disk_bytes=max(d, observations['peak_disk_bytes']),
                                samples=observations['samples']+1)
            if m > cfg['memory_cap_bytes'] or d > cfg['scratch_cap_bytes'] or time.monotonic() > end:
                guard_stop(root,observations,88)
    threading.Thread(target=watch, daemon=True).start()
    return stop, observations


@contextlib.contextmanager
def query_deadline(seconds=5):
    def expired(*_): raise TimeoutError('five-second query budget')
    old = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try: yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


def snapshot():
    root = Path(tempfile.mkdtemp(prefix='wf-graph-1xny3-')).resolve()
    (root / MARKER).write_text('wave1xny3 isolated experiment\n')
    initial_free = shutil.disk_usage(root).free
    cap = min(8 * 1024 ** 3, initial_free // 4)
    index = root / '.wavefoundry/index'; (index / 'graph').mkdir(parents=True)
    live = REPO / '.wavefoundry/index'
    def epoch():
        c=connect(live/'index-state.sqlite',read_only=True)
        try: return list(c.execute('SELECT attempt_id,status,generation FROM build_state'))
        finally: c.close()
    for attempt in range(5):
        before=epoch()
        if before[0][1] != 'complete': time.sleep(1); continue
        backup(live/'index-state.sqlite',index/'index-state.sqlite')
        with sqlite3.connect(f'file:{live}/graph/project-graph-state.sqlite?mode=ro',uri=True) as src:
            with sqlite3.connect(index/'graph/project-graph-state.sqlite') as dst: src.backup(dst)
        hashes={}
        for name in ['project-graph.json','project-graph-clusters.json']:
            src=live/'graph'/name; dst=index/'graph'/name
            hashes[name]=sha(src); shutil.copy2(src,dst)
            if hashes[name] != sha(dst): raise RuntimeError('copy integrity')
        after=epoch()
        if before == after and all(sha(live/'graph'/n)==h for n,h in hashes.items()): break
    else: raise RuntimeError('no stable complete epoch snapshot')
    # Copy tracked inputs so retrieval's definition reads never escape scratch.
    files=subprocess.check_output(['git','ls-files','-z'],cwd=REPO).decode().split('\0')
    for rel in filter(None,files):
        src=REPO/rel
        if src.is_symlink() or not src.is_file(): continue
        dst=root/rel; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
    payload=read_payload(root)
    meta={'epoch':before,'graph_hashes':hashes,'semantic_snapshot_sha256':sha(index/'index-state.sqlite'),
          'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),
          'nodes':len(payload['nodes']),'edges':len(payload['edges']),
          'scratch_root':str(root),'memory_cap_bytes':MEM_CAP,'scratch_cap_bytes':cap,
          'host_memory_bytes':34359738368,'platform':platform.platform(),'machine':platform.machine(),
          'python':sys.version,'sqlite_graph_baseline':sqlite3.sqlite_version,'apsw':apsw.apswversion(),
          'sqlite_candidate':apsw.sqlitelibversion(),'cache_state':'process-cold; OS cache uncontrolled',
          'created_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
          'copied_inputs_count':len(files)-1,'scratch_bytes':directory_bytes(root)}
    dump(root/'snapshot.json',meta)
    print(json.dumps(meta))


def read_payload(root):
    data=(Path(root)/'.wavefoundry/index/graph/project-graph.json').read_bytes()
    obj=json.loads(gzip.decompress(data) if data[:2]==b'\x1f\x8b' else data)
    obj['present']=True
    return obj


SCHEMA='''
CREATE TABLE IF NOT EXISTS graph_keys(id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS graph_nodes(id INTEGER PRIMARY KEY REFERENCES graph_keys(id), ordinal INTEGER NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS graph_edges(ordinal INTEGER PRIMARY KEY, source INTEGER NOT NULL REFERENCES graph_keys(id), target INTEGER NOT NULL REFERENCES graph_keys(id), relation TEXT NOT NULL, payload TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS graph_edges_out ON graph_edges(source,ordinal);
CREATE INDEX IF NOT EXISTS graph_edges_in ON graph_edges(target,ordinal);
CREATE INDEX IF NOT EXISTS graph_edges_out_relation ON graph_edges(source,relation,target);
CREATE INDEX IF NOT EXISTS graph_edges_in_relation ON graph_edges(target,relation,source);
CREATE TABLE IF NOT EXISTS graph_meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
'''


def make_db(root, path, payload, shared=False):
    owned(root,path)
    if path.exists(): path.unlink()
    if shared: backup(Path(root)/'.wavefoundry/index/index-state.sqlite',path)
    c=connect(path)
    c.execute(SCHEMA)
    ids={}
    names=sorted({str(n['id']) for n in payload['nodes']} | {str(e[k]) for e in payload['edges'] for k in ('source','target')})
    ids={name:i+1 for i,name in enumerate(names)}
    c.execute('BEGIN IMMEDIATE')
    try:
        c.executemany('INSERT INTO graph_keys VALUES(?,?)',[(i,n) for n,i in ids.items()])
        c.executemany('INSERT INTO graph_nodes VALUES(?,?,?)',[(ids[n['id']],i,json.dumps(n,separators=(',',':'))) for i,n in enumerate(payload['nodes'])])
        c.executemany('INSERT INTO graph_edges VALUES(?,?,?,?,?)',[(i,ids[e['source']],ids[e['target']],e.get('relation',''),json.dumps(e,separators=(',',':'))) for i,e in enumerate(payload['edges'])])
        c.execute('INSERT INTO graph_meta VALUES(?,?)',('header',json.dumps({k:v for k,v in payload.items() if k not in ('nodes','edges')})))
        c.execute('COMMIT')
    except BaseException: c.execute('ROLLBACK'); raise
    c.execute('PRAGMA wal_checkpoint(PASSIVE)')
    c.close()


class Nodes:
    def __init__(self,c): self.c=c
    def get(self,key,default=None):
        row=self.c.execute('SELECT payload FROM graph_nodes n JOIN graph_keys k ON k.id=n.id WHERE k.name=?',(key,)).fetchone()
        return json.loads(row[0]) if row else default
    def __contains__(self,key): return self.get(key) is not None
    def __getitem__(self,key):
        v=self.get(key)
        if v is None: raise KeyError(key)
        return v
    def values(self): return iter(Sequence(self.c,'graph_nodes'))
    def items(self): return ((n['id'],n) for n in self.values())
    def __iter__(self): return (r[0] for r in self.c.execute('SELECT k.name FROM graph_nodes n JOIN graph_keys k ON n.id=k.id ORDER BY n.ordinal'))
    def __len__(self): return self.c.execute('SELECT count(*) FROM graph_nodes').fetchone()[0]


class Sequence:
    def __init__(self,c,table): self.c,self.table=c,table
    def __iter__(self):
        for (p,) in self.c.execute(f'SELECT payload FROM {self.table} ORDER BY ordinal'): yield json.loads(p)
    def __len__(self): return self.c.execute(f'SELECT count(*) FROM {self.table}').fetchone()[0]
    def __getitem__(self,n):
        if isinstance(n,slice): return list(self)[n]
        return json.loads(self.c.execute(f'SELECT payload FROM {self.table} ORDER BY ordinal LIMIT 1 OFFSET ?',(n,)).fetchone()[0])


class Adjacency:
    def __init__(self,c,direction): self.c,self.direction=c,direction
    def get(self,key,default=None):
        rows=self.c.execute(f'SELECT e.payload FROM graph_edges e WHERE e.{self.direction}=(SELECT id FROM graph_keys WHERE name=?) ORDER BY ordinal',(key,))
        return [json.loads(p) for (p,) in rows]
    def items(self):
        for (name,) in self.c.execute(f'SELECT DISTINCT k.name FROM graph_keys k JOIN graph_edges e ON e.{self.direction}=k.id'):
            yield name,self.get(name)


class SqlGraph(GraphQueryIndex):
    """Reuse the public graph algorithms with SQL-backed lazy collections.

    This isolates storage representation from traversal semantic changes. Global
    algorithms still iterate/materialize their required graph; no RAM saving is
    claimed for work not measured. CTE reachability is a separate measured path.
    """
    def __init__(self,path):
        self.c=connect(Path(path),read_only=True)
        header=json.loads(self.c.execute("SELECT value FROM graph_meta WHERE key='header'").fetchone()[0])
        self.layer=header.get('layer','project'); self.present=True
        self.builder_version=str(header.get('builder_version',''))
        self.auto_rebuild_diagnostic=None
        self.nodes=Sequence(self.c,'graph_nodes'); self.edges=Sequence(self.c,'graph_edges')
        self._node_by_id=Nodes(self.c); self._out=Adjacency(self.c,'source'); self._in=Adjacency(self.c,'target')
        self._external_supertypes={}
        for (target,) in self.c.execute("SELECT DISTINCT k.name FROM graph_edges e JOIN graph_keys k ON e.target=k.id WHERE e.relation IN ('implements','extends') AND k.name LIKE 'external::%'"):
            declared=target[len('external::'):]
            self._external_supertypes.setdefault(declared,set()).add(target)
            self._external_supertypes.setdefault(declared.rsplit('.',1)[-1],set()).add(target)
    def traverse(self,*args,**kwargs):
        with self.c:return super().traverse(*args,**kwargs)
    def one_hop_neighbors(self,*args,**kwargs):
        with self.c:return super().one_hop_neighbors(*args,**kwargs)
    def shortest_path(self,*args,**kwargs):
        with self.c:return super().shortest_path(*args,**kwargs)
    def graph_impact(self,*args,**kwargs):
        with self.c:return super().graph_impact(*args,**kwargs)
    def risk_score(self,*args,**kwargs):
        with self.c:return super().risk_score(*args,**kwargs)
    def report(self,*args,**kwargs):
        with self.c:return super().report(*args,**kwargs)
    def close(self): self.c.close()
    def cte_reachable(self,start,depth=3,relation='calls',reverse=False):
        source,target=('target','source') if reverse else ('source','target')
        end=time.monotonic()+5
        self.c.set_progress_handler(lambda:time.monotonic()>end,1000)
        try:
            rows=list(self.c.execute(f'''WITH RECURSIVE r(id,depth) AS (
                SELECT id,0 FROM graph_keys WHERE name=? UNION
                SELECT e.{target},r.depth+1 FROM r CROSS JOIN graph_edges e INDEXED BY graph_edges_{'in' if reverse else 'out'}_relation ON e.{source}=r.id
                WHERE r.depth<? AND e.relation=? LIMIT 100000)
                SELECT k.name,MIN(r.depth),(SELECT count(*) FROM r) FROM r CROSS JOIN graph_keys k ON k.id=r.id GROUP BY k.name''',(start,depth,relation)))
            if rows and rows[0][2]>=100000: raise TimeoutError('CTE result ceiling')
            return {r[0] for r in rows}
        finally: self.c.set_progress_handler(None)


class BoundedAdjacency:
    def __init__(self,delegate,budget=8*MIB):
        self.delegate=delegate;self.budget=budget;self.cache=collections.OrderedDict();self.used=0
    def clear(self):self.cache.clear();self.used=0
    def get(self,key,default=None):
        if key in self.cache:
            value,size=self.cache.pop(key);self.cache[key]=(value,size);return value
        value=self.delegate.get(key,default)
        size=sum(len(json.dumps(e)) for e in value)+len(key)+64
        if size<=self.budget:
            while self.cache and self.used+size>self.budget:
                _,(_,old)=self.cache.popitem(last=False);self.used-=old
            self.cache[key]=(value,size);self.used+=size
        return value
    def items(self):return self.delegate.items()


class CachedSqlGraph(SqlGraph):
    def __init__(self,path):
        super().__init__(path);self._out=BoundedAdjacency(self._out);self._in=BoundedAdjacency(self._in)
        self._version=self.c.execute('PRAGMA data_version').fetchone()[0]
    def refresh(self):
        version=self.c.execute('PRAGMA data_version').fetchone()[0]
        if version!=self._version:
            self._out.clear();self._in.clear();self._version=version
            self._external_supertypes={}
            for (target,) in self.c.execute("SELECT DISTINCT k.name FROM graph_edges e JOIN graph_keys k ON e.target=k.id WHERE e.relation IN ('implements','extends') AND k.name LIKE 'external::%'"):
                name=target[len('external::'):]
                for label in (name,name.rsplit('.',1)[-1]): self._external_supertypes.setdefault(label,set()).add(target)
    def _cached_query(self,name,*args,**kwargs):
        # BEGIN alone does not establish a snapshot. Pin it with a real read
        # before validating the cache, so later SQL hydration cannot cross epochs.
        with self.c:
            self.c.execute('SELECT count(*) FROM graph_meta').fetchone()
            self.refresh()
            return getattr(super(),name)(*args,**kwargs)
    def graph_impact(self,*args,**kwargs):return self._cached_query('graph_impact',*args,**kwargs)
    def risk_score(self,*args,**kwargs):return self._cached_query('risk_score',*args,**kwargs)
    def report(self,*args,**kwargs):return self._cached_query('report',*args,**kwargs)
    def resolve_symbol(self,*args,**kwargs):return self._cached_query('resolve_symbol',*args,**kwargs)
    def traverse(self,*args,**kwargs):return self._cached_query('traverse',*args,**kwargs)
    def one_hop_neighbors(self,*args,**kwargs):return self._cached_query('one_hop_neighbors',*args,**kwargs)
    def shortest_path(self,*args,**kwargs):return self._cached_query('shortest_path',*args,**kwargs)


class CountedEdges:
    """Snapshot-bound collection: count cheaply, hydrate only if iterated."""
    def __init__(self,owner,key,count):self.owner,self.key,self.count=owner,key,count
    def __len__(self):return self.count
    def __iter__(self):return iter(self.owner.get(self.key))
    def __getitem__(self,n):return self.owner.get(self.key)[n]


class CountedAdjacency(Adjacency):
    def items(self):
        for name,count in self.c.execute(f'SELECT k.name,count(*) FROM graph_edges e JOIN graph_keys k ON k.id=e.{self.direction} GROUP BY e.{self.direction} ORDER BY k.name'):
            yield name,CountedEdges(self,name,count)


class CachedNodes(Nodes):
    def __init__(self,c,budget=16*MIB):
        super().__init__(c);self.budget=budget;self.used=0;self.cache=collections.OrderedDict()
    def clear(self):self.cache.clear();self.used=0
    def get(self,key,default=None):
        if key in self.cache:
            value,size=self.cache.pop(key);self.cache[key]=(value,size)
            return value if value is not None else default
        value=super().get(key)
        size=len(json.dumps(value))+len(key)+64
        if size<=self.budget:
            while self.cache and self.used+size>self.budget:
                _,(_,old)=self.cache.popitem(last=False);self.used-=old
            self.cache[key]=(value,size);self.used+=size
        return value if value is not None else default


class GroupedCachedSqlGraph(CachedSqlGraph):
    """K: bounded nodes plus SQL degrees, avoiding unused edge hydration."""
    def __init__(self,path):
        super().__init__(path)
        self._node_by_id=CachedNodes(self.c)
        self._out=BoundedAdjacency(CountedAdjacency(self.c,'source'))
        self._in=BoundedAdjacency(CountedAdjacency(self.c,'target'))
    def refresh(self):
        before=self._version
        super().refresh()
        if before!=self._version:self._node_by_id.clear()


def canonical(x):
    if isinstance(x,set): return sorted(x)
    if isinstance(x,tuple): return [canonical(v) for v in x]
    return x


def fixture():
    nodes=[{'id':x,'label':x,'kind':'function','source_file':'fixture.py'} for x in list('abcdefxyz')+['external::shared']]
    edges=[]
    def e(s,t,rel='calls',confidence='RECEIVER_RESOLVED',**more):
        edges.append(dict(source=s,target=t,relation=rel,confidence=confidence,**more))
    e('a','b');e('a','c');e('b','d');e('c','d');e('d','a')
    e('a','b',evidence='second');e('a','external::shared','imports');e('external::shared','z','imports')
    e('a','e');e('e','z');e('a','z','imports');e('a','f','reads');e('x','y','extends')
    return {'nodes':nodes,'edges':edges,'layer':'project','present':True,'builder_version':'51'}


def oracles(root):
    path=owned(root,Path(root)/'oracle.sqlite'); p=fixture(); make_db(root,path,p)
    a=GraphQueryIndex(p); b=SqlGraph(path); checks=[]
    for graph in (a,b):
        seen,edges,cycles=graph.traverse('a',relations=['calls'],max_hops=2)
        assert seen==set('abcdez') and cycles is True  # diamond revisit is public has_cycles
        assert len(edges)==6  # public triple de-dup leaves second evidence stored only
        assert [n['node_id'] for n in graph.shortest_path('a','z')['path_nodes']]==['a','e','z']
        assert graph.shortest_path('external::shared','z',relations=['imports'])['found']
        assert not graph.shortest_path('b','external::shared',relations=['imports'])['found']
        assert graph.shortest_path('a','z',relations=['imports'])['hop_count']==1
        assert graph.traverse('a',max_hops=0)[0]=={'a'}
        assert not graph.shortest_path('x','z')['found']
        assert graph.one_hop_neighbors(['a'],max_neighbors=2)['truncated']
        try: graph.shortest_path('a','b',direction='invalid')
        except ValueError: pass
        else: raise AssertionError('invalid direction accepted')
    # External node is a valid endpoint, but cannot bridge unrelated symbols.
    q={'nodes':p['nodes'],'edges':[p['edges'][6],p['edges'][7]],'present':True}
    assert not GraphQueryIndex(q).shortest_path('a','z')['found']
    bridge=root/'oracle-bridge.sqlite';make_db(root,bridge,q);bb=SqlGraph(bridge)
    assert not bb.shortest_path('a','z')['found'];bb.close()
    weighted={'present':True,'nodes':p['nodes'],'edges':[dict(source=u,target=v,relation='calls',confidence=c) for u,v,c in [('a','b','EXTRACTED'),('b','d','EXTRACTED'),('a','c','RECEIVER_RESOLVED'),('c','d','RECEIVER_RESOLVED')]]}
    wp=root/'oracle-weighted.sqlite';make_db(root,wp,weighted);wb=SqlGraph(wp)
    for g in (GraphQueryIndex(weighted),wb):
        assert [x['node_id'] for x in g.shortest_path('a','d')['path_nodes']]==['a','c','d']
        assert not g.shortest_path('a','b',min_confidence='RECEIVER_RESOLVED')['found']
    wb.close()
    assert len(list(b.edges))==len(p['edges'])
    for direction in ('callees','callers','both'):
        for rel in (None,['calls'],['imports'],['reads']):
            for depth in (0,1,2,3):
                assert canonical(a.traverse('a',relations=rel,max_hops=depth,direction=direction))==canonical(b.traverse('a',relations=rel,max_hops=depth,direction=direction))
                checks.append([direction,rel,depth])
    assert b.cte_reachable('a',2)==set('abcdez')
    b.close()
    return {'status':'pass','differential_cases':len(checks),'independent_expected_sets':True,'parallel_evidence_preserved':True,
            'baseline_anomalies':['has_cycles flags diamond revisits; public traversal de-duplicates edge triples'],
            'invalid_direction_rejected':True}


def pct(xs,p): return sorted(xs)[min(len(xs)-1,int((len(xs)-1)*p))]
def timing(fn):
    start=time.perf_counter()
    with query_deadline(): value=fn()
    return (time.perf_counter()-start)*1000,value


def queries(payload):
    counts=collections.Counter(e['source'] for e in payload['edges'] if e.get('relation')=='calls')
    nodeids={n['id'] for n in payload['nodes']}
    ranked=sorted([(n,c) for n,c in counts.items() if n in nodeids],key=lambda x:(-x[1],x[0]))
    chosen=ranked[:3]+ranked[len(ranked)//2:len(ranked)//2+3]+ranked[-3:]
    return [x[0] for x in chosen]


def query_manifest(payload):
    nodeids={n['id'] for n in payload['nodes']}
    def seeds(relation,end):
        counts=collections.Counter(e[end] for e in payload['edges'] if e.get('relation')==relation and e[end] in nodeids)
        ranked=sorted(counts,key=lambda n:(-counts[n],n))
        return list(dict.fromkeys(ranked[:3]+ranked[len(ranked)//2:len(ranked)//2+3]+ranked[-3:]))
    calls=seeds('calls','source')
    pairs=[]
    for s in calls:
        targets=sorted({e['target'] for e in payload['edges'] if e['source']==s and e.get('relation')=='calls' and e['target'] in nodeids})
        if targets:pairs.append([s,targets[0]])
    return {'calls_out_1':calls,'calls_out_3':calls,'calls_in_3':seeds('calls','target'),
            'filtered_imports_3':seeds('imports','source'),'doc_links_3':seeds('doc_references_doc','source'),
            'neighbors_bounded':calls,'weighted_path':pairs,'cte_calls_out_3':calls}


def worker(root,variant,run=0):
    root=owned(root); stop,watch=guard(root); t=time.perf_counter(); cpu=time.process_time()
    if variant=='A': graph=GraphQueryIndex(read_payload(root))
    else: graph=(CachedSqlGraph if variant=='H' else SqlGraph)(root/('graph-b.sqlite' if variant in ('B','H') else 'graph-c.sqlite'))
    startup=(time.perf_counter()-t)*1000
    manifest=json.loads((root/'queries.json').read_text())
    seeds=manifest['calls_out_3'] if isinstance(manifest,dict) else manifest
    funcs={
       'calls_out_1':lambda s:graph.traverse(s,relations=['calls'],max_hops=1),
       'calls_out_3':lambda s:graph.traverse(s,relations=['calls'],max_hops=3),
       'calls_in_3':lambda s:graph.traverse(s,relations=['calls'],max_hops=3,direction='callers'),
       'filtered_imports_3':lambda s:graph.traverse(s,relations=['imports'],max_hops=3),
       'neighbors_bounded':lambda s:graph.one_hop_neighbors([s],max_neighbors=30),
       'weighted_path':lambda s:graph.shortest_path(s[0],s[1],max_hops=5),
       'doc_links_3':lambda s:graph.traverse(s,relations=['doc_references_doc'],max_hops=3),
    }
    if variant!='A': funcs['cte_calls_out_3']=lambda s:graph.cte_reachable(s,3)
    results={}
    for name,fn in funcs.items():
        family_seeds=manifest.get(name,seeds) if isinstance(manifest,dict) else seeds
        times=[]; failures=[]; cold=None; outputs=[]
        for i in range(110):
            try:
                ms,value=timing(lambda:fn(family_seeds[i%len(family_seeds)]))
                if cold is None: cold=ms
                if i>=10:
                    times.append(ms)
                    if isinstance(value,tuple):outputs.append({'nodes':len(value[0]),'edges':len(value[1])})
                    elif isinstance(value,set):outputs.append({'nodes':len(value)})
                    elif name=='weighted_path':outputs.append({'found':value['found'],'hops':value.get('hop_count')})
                    else:outputs.append({'nodes':len(value.get('nodes',[])),'truncated':value.get('truncated',False)})
            except (TimeoutError,apsw.InterruptError) as e:
                failures.append(str(e)); break
        results[name]={'samples_ms':times,'process_first_ms':cold,'errors':failures,'outputs':outputs}
    stop.set()
    result={'variant':variant,'run':run,'startup_ms':startup,'cpu_seconds':time.process_time()-cpu,
            'peak_rss_bytes':rss(),'steady_rss_bytes':resident_bytes(),'watchdog':watch,'families':results,'pid':os.getpid()}
    if variant!='A': graph.close()
    dump(root/f'worker-{variant}-{run}.json',result)


def compare(root):
    root=owned(root); p=read_payload(root); a=GraphQueryIndex(p)
    t=time.perf_counter(); make_db(root,root/'graph-b.sqlite',p); build_ms=(time.perf_counter()-t)*1000
    b=SqlGraph(root/'graph-b.sqlite'); seeds=queries(p); dump(root/'queries.json',query_manifest(p))
    checks=0; failures=[]
    for seed in seeds:
        for rel in (None,['calls'],['imports'],['extends','implements']):
            for depth in (1,2,3):
                for direction in ('callees','callers','both'):
                    try:
                        with query_deadline(): aa=a.traverse(seed,relations=rel,max_hops=depth,direction=direction)
                        with query_deadline(): bb=b.traverse(seed,relations=rel,max_hops=depth,direction=direction)
                        assert canonical(aa)==canonical(bb)
                        checks+=1
                    except (AssertionError,TimeoutError) as e: failures.append([seed,rel,depth,direction,type(e).__name__])
        for cap in (0,1,10,30,None):
            assert a.one_hop_neighbors([seed],max_neighbors=cap)==b.one_hop_neighbors([seed],max_neighbors=cap)
            checks+=1
        assert b.cte_reachable(seed,3)==a.traverse(seed,relations=['calls'],max_hops=3)[0]
    for i,s in enumerate(seeds):
        for direction in ('forward','backward','either'):
            assert a.shortest_path(s,seeds[(i+1)%len(seeds)],direction=direction,max_hops=5)==b.shortest_path(s,seeds[(i+1)%len(seeds)],direction=direction,max_hops=5)
            checks+=1
    rows=list(b.nodes); edges=list(b.edges)
    assert rows==p['nodes'] and edges==p['edges']
    b.close()
    return {'checks':checks,'failures':failures,'build_ms':build_ms,'node_identity_payload_parity':True,'edge_identity_payload_parity':True,
            'nodes':len(rows),'edges':len(edges),'relations':dict(collections.Counter(e.get('relation') for e in edges))}


def shared_probes(root):
    """Actual schema-7 FTS triggers/vector BLOBs plus prototype graph publication.

    These tests prove a shared transaction boundary, not a implemented indexer
    integration, cross-file extraction algorithm, or migrated serving epoch.
    """
    import struct
    root=owned(root); p=read_payload(root); path=root/'graph-c.sqlite'
    make_db(root,path,p,shared=True)
    w=connect(path); r=connect(path,read_only=True)
    row=w.execute('SELECT id,text,payload FROM chunks_code ORDER BY id LIMIT 1').fetchone()
    cid,oldtext,oldpayload=row
    blob=w.execute('SELECT embedding FROM vectors_code WHERE chunk_id=?',(cid,)).fetchone()[0]
    node=w.execute('SELECT id,payload FROM graph_nodes ORDER BY ordinal LIMIT 1').fetchone()
    edge=w.execute('SELECT ordinal,payload FROM graph_edges ORDER BY ordinal LIMIT 1').fetchone()
    w.execute("INSERT INTO graph_meta VALUES('probe_revision','0')")
    def view(c):
        return (c.execute('SELECT text FROM chunks_code WHERE id=?',(cid,)).fetchone()[0],
                bytes(c.execute('SELECT embedding FROM vectors_code WHERE chunk_id=?',(cid,)).fetchone()[0]),
                c.execute('SELECT payload FROM graph_nodes WHERE id=?',(node[0],)).fetchone()[0],
                c.execute('SELECT payload FROM graph_edges WHERE ordinal=?',(edge[0],)).fetchone()[0],
                c.execute("SELECT value FROM graph_meta WHERE key='probe_revision'").fetchone()[0])
    def mutate(marker):
        v=list(struct.unpack('<384f',blob));v[0]+=0.001
        pp=json.loads(oldpayload);pp['text']=marker
        w.execute('UPDATE chunks_code SET text=?,payload=? WHERE id=?',(marker,json.dumps(pp),cid))
        w.execute('UPDATE vectors_code SET embedding=? WHERE chunk_id=?',(struct.pack('<384f',*v),cid))
        np=json.loads(node[1]);np['evaluation_revision']=marker
        ep=json.loads(edge[1]);ep['evaluation_revision']=marker
        w.execute('UPDATE graph_nodes SET payload=? WHERE id=?',(json.dumps(np),node[0]))
        w.execute('UPDATE graph_edges SET payload=? WHERE ordinal=?',(json.dumps(ep),edge[0]))
        w.execute("UPDATE graph_meta SET value=? WHERE key='probe_revision'",(marker,))
        return (marker,struct.pack('<384f',*v),json.dumps(np),json.dumps(ep),marker)
    original=view(r)
    w.execute('BEGIN IMMEDIATE');mutate('graphrollbacktoken');assert view(r)==original
    w.execute('ROLLBACK');assert view(r)==original
    r.execute('BEGIN');assert view(r)==original
    w.execute('BEGIN IMMEDIATE');expected=mutate('graphcommittoken')
    assert view(r)==original
    w.execute('COMMIT');assert view(r)==original
    r.execute('COMMIT');published=view(r);assert published==expected and all(a!=b for a,b in zip(published,original))
    assert published[0]=='graphcommittoken' and published[-1]=='graphcommittoken'
    assert r.execute("SELECT count(*) FROM fts_code WHERE fts_code MATCH 'graphcommittoken'").fetchone()[0]==1
    assert r.execute("SELECT count(*) FROM fts_code WHERE fts_code MATCH 'graphrollbacktoken'").fetchone()[0]==0
    assert bytes(r.execute('SELECT embedding FROM vectors_code WHERE chunk_id=?',(cid,)).fetchone()[0])==expected[1]
    cosine=r.execute('SELECT vec_distance_cosine(embedding,?) FROM vectors_code WHERE chunk_id=?',(blob,cid)).fetchone()[0]
    assert cosine is not None and published[1]!=blob
    # Graph-only publication leaves text/vector data unchanged.
    sem_before=published[:2]
    w.execute('BEGIN IMMEDIATE')
    w.execute("UPDATE graph_meta SET value='graphonly' WHERE key='probe_revision'")
    w.execute("UPDATE graph_nodes SET payload=json_set(payload,'$.evaluation_revision','graphonly') WHERE id=?",(node[0],))
    w.execute("UPDATE graph_edges SET payload=json_set(payload,'$.evaluation_revision','graphonly') WHERE ordinal=?",(edge[0],))
    w.execute('COMMIT')
    assert view(r)[:2]==sem_before and view(r)[2:4]!=published[2:4]
    w.close();r.close()
    code="""import sys,os;from pathlib import Path;sys.path.insert(0,sys.argv[1]);from sqlite_runtime import connect;c=connect(Path(sys.argv[2]));c.execute('BEGIN IMMEDIATE');c.execute(\"UPDATE graph_meta SET value='crash' WHERE key='probe_revision'\");c.execute(\"UPDATE chunks_code SET text='crashtoken' WHERE id=?\",(int(sys.argv[3]),));os._exit(77)"""
    child=subprocess.run([sys.executable,'-B','-c',code,str(SCRIPTS),str(owned(root,path)),str(cid)],timeout=10)
    assert child.returncode==77
    c=connect(path)
    assert c.execute("SELECT value FROM graph_meta WHERE key='probe_revision'").fetchone()[0]=='graphonly'
    assert c.execute("SELECT count(*) FROM fts_code WHERE fts_code MATCH 'crashtoken'").fetchone()[0]==0
    assert c.execute('PRAGMA quick_check').fetchone()[0]=='ok'
    c.execute("INSERT INTO fts_code(fts_code,rank) VALUES('integrity-check',1)")
    checkpoint=list(c.execute('PRAGMA wal_checkpoint(PASSIVE)'))
    pragmas={n:c.execute('PRAGMA '+n).fetchone()[0] for n in ('page_size','cache_size','mmap_size','synchronous','auto_vacuum','wal_autocheckpoint','page_count','freelist_count')}
    # Map chunk ranges to graph source locations; never conflate IDs.
    sample=list(c.execute("SELECT n.id,k.name,ch.id FROM graph_nodes n JOIN graph_keys k ON k.id=n.id JOIN chunks_code ch ON ch.path=json_extract(n.payload,'$.source_file') WHERE CAST(substr(json_extract(n.payload,'$.source_location'),1,instr(json_extract(n.payload,'$.source_location'),':')-1) AS INTEGER) BETWEEN ch.start_line AND ch.end_line LIMIT 20"))
    c.close()
    return {'status':'pass','schema':'actual schema-7 chunks/vectors/FTS plus prototype graph tables',
            'rollback_old_snapshot':True,'readers_before_and_after_commit':True,'fts_atomicity':True,
            'vector_scalar_read_after_commit':True,'graph_only_preserves_semantic':True,
            'owned_child_crash_exit':child.returncode,'restart_integrity':'ok','fts_integrity':'ok',
            'checkpoint':checkpoint,'pragmas':pragmas,'mapping_sample_count':len(sample),
            'limitation':'Does not qualify full indexer integration, cross-file extraction, historical migration or global algorithms.'}


def startup_samples(root):
    root=owned(root)
    out=[]
    code="""import sys,json,time,resource;from pathlib import Path;sys.path.insert(0,sys.argv[1]);import graph_eval as h;r=Path(sys.argv[2]);t=time.perf_counter();g=h.GraphQueryIndex(h.read_payload(r)) if sys.argv[3]=='A' else h.SqlGraph(r/('graph-b.sqlite' if sys.argv[3]=='B' else 'graph-c.sqlite'));print(json.dumps({'startup_ms':(time.perf_counter()-t)*1000,'rss':h.resident_bytes(),'peak_rss':h.rss()}))"""
    for i in range(10):
        for v in ('A','B','C') if i%2==0 else ('C','B','A'):
            p=subprocess.run([sys.executable,'-B','-c',code,str(Path(__file__).parent),str(root),v],capture_output=True,text=True,timeout=10,check=True)
            out.append(dict(json.loads(p.stdout),variant=v,run=i))
    return out


def publication_samples(root):
    from graph_indexer import _write_json, _encode_state_record
    root=owned(root); p=read_payload(root); out=[]; rebuild=[]
    work=root/'publication';work.mkdir(exist_ok=True)
    for i in range(10):
        for v in ('A','B','C') if i%2==0 else ('C','B','A'):
            t=time.perf_counter();cpu=time.process_time()
            if v=='A':
                p['nodes'][0]['evaluation_revision']=i
                _write_json(owned(root,work/'project-graph.json'),p)
                # Re-open/construct exactly the current serving representation.
                aa=GraphQueryIndex(json.loads(gzip.decompress((work/'project-graph.json').read_bytes())))
                assert aa.nodes[0]['evaluation_revision']==i
                del aa
            else:
                c=connect(root/('graph-b.sqlite' if v=='B' else 'graph-c.sqlite'))
                rec=c.execute('SELECT id,payload FROM graph_nodes ORDER BY ordinal LIMIT 1').fetchone()
                n=json.loads(rec[1]);n['evaluation_revision']=i
                c.execute('BEGIN IMMEDIATE'); lockstart=time.perf_counter()
                c.execute('UPDATE graph_nodes SET payload=? WHERE id=?',(json.dumps(n),rec[0]));c.execute('COMMIT')
                lockms=(time.perf_counter()-lockstart)*1000;c.close()
                b=SqlGraph(root/('graph-b.sqlite' if v=='B' else 'graph-c.sqlite'))
                assert b._node_by_id.get(n['id'])['evaluation_revision']==i;b.close()
            out.append({'variant':v,'run':i,'prepared_publication_to_queryable_ms':(time.perf_counter()-t)*1000,
                        'cpu_seconds':time.process_time()-cpu,'writer_lock_ms':lockms if v!='A' else None})
    # Prepared graph persistence only. Never call this source extraction/rebuild.
    for i in range(3):
        for v in ('A','B') if i%2==0 else ('B','A'):
            t=time.perf_counter()
            if v=='A': _write_json(work/'rebuilt-graph.json',p)
            else: make_db(root,work/'rebuilt-graph.sqlite',p)
            rebuild.append({'variant':v,'run':i,'prepared_full_graph_persistence_ms':(time.perf_counter()-t)*1000})
    return {'updates':out,'prepared_graph_rebuild':rebuild,
            'limitation':'Prepared graph persistence/publication only; excludes unchanged extraction, embedding, global resolution and actual lifecycle API integration.'}


def maintenance(root):
    root=owned(root);out={}
    for v in ('B','C'):
        path=root/('graph-b.sqlite' if v=='B' else 'graph-c.sqlite');c=connect(path)
        rows=list(c.execute('SELECT * FROM graph_edges WHERE ordinal%10=0'))
        before=directory_bytes(root)
        start=time.perf_counter();c.execute('BEGIN IMMEDIATE');c.execute('DELETE FROM graph_edges WHERE ordinal%10=0');c.execute('COMMIT')
        free=c.execute('PRAGMA freelist_count').fetchone()[0]
        # Branch-like delete/reinsert: reusable pages, no shrink/grow cycle.
        c.execute('BEGIN IMMEDIATE');c.executemany('INSERT INTO graph_edges VALUES(?,?,?,?,?)',rows);c.execute('COMMIT')
        churnms=(time.perf_counter()-start)*1000
        checkpoint=list(c.execute('PRAGMA wal_checkpoint(PASSIVE)'))
        pages=c.execute('PRAGMA page_count').fetchone()[0];reusedfree=c.execute('PRAGMA freelist_count').fetchone()[0]
        c.execute('PRAGMA optimize'); c.execute('PRAGMA incremental_vacuum(100)')
        assert c.execute('PRAGMA quick_check').fetchone()[0]=='ok'
        c.close()
        out[v]={'delete_reinsert_edges':len(rows),'churn_ms':churnms,'free_pages_after_delete':free,
                'free_pages_after_reinsert':reusedfree,'pages':pages,'checkpoint':checkpoint,
                'disk_delta_bytes':directory_bytes(root)-before,'integrity':'ok','full_vacuum':False}
    return out


def scale(root,factor):
    root=owned(root);p=read_payload(root);nodes=[];edges=[]
    # Disjoint topology-preserving replicas: no invented cross-replica links.
    # This tests corpus residency, not higher local degree; fanout is separate.
    for i in range(factor):
        prefix=f'replica{i}::'
        nodes.extend(dict(n,id=prefix+n['id']) for n in p['nodes'])
        edges.extend(dict(e,source=prefix+e['source'],target=prefix+e['target']) for e in p['edges'])
    q=dict(p,nodes=nodes,edges=edges);path=root/f'scale-{factor}.sqlite'
    make_db(root,path,q);a=GraphQueryIndex(q);b=SqlGraph(path)
    seeds=['replica0::'+s for s in queries(p)];out={}
    for v,g in [('A',a),('B',b)]:
        samples=[]
        for i in range(110):
            ms,value=timing(lambda:g.traverse(seeds[i%len(seeds)],relations=['calls'],max_hops=3))
            if i>=10:samples.append(ms)
        out[v]={'samples_ms':samples,'p95_ms':pct(samples,.95)}
    assert b.traverse(seeds[0],relations=['calls'],max_hops=3)==a.traverse(seeds[0],relations=['calls'],max_hops=3)
    b.close();out.update(factor=factor,nodes=len(nodes),edges=len(edges),disk_bytes=path.stat().st_size,
                        peak_rss_bytes=rss(),limitation='disjoint topology replicas; A/B share this scale process so RSS is not attributable to one variant')
    return out


def fanout(root):
    root=owned(root);n=10000
    p={'present':True,'layer':'project','nodes':[{'id':str(i),'kind':'function'} for i in range(n+1)],
       'edges':[{'source':'0','target':str(i),'relation':'calls','confidence':'EXTRACTED'} for i in range(1,n+1)]}
    path=root/'fanout.sqlite';make_db(root,path,p);a=GraphQueryIndex(p);b=SqlGraph(path);out={}
    for v,g in [('A',a),('B',b)]:
        ms,value=timing(lambda:g.one_hop_neighbors(['0'],max_neighbors=30))
        assert len(value['nodes'])==30 and value['truncated']
        out[v]={'bounded_neighbor_ms':ms,'nodes_returned':len(value['nodes'])}
    assert b.one_hop_neighbors(['0'],max_neighbors=30)==a.one_hop_neighbors(['0'],max_neighbors=30)
    b.close();return out


def safety_probes(root):
    root=owned(root);checks=[]
    for target in (REPO, REPO/'.wavefoundry/index/index-state.sqlite', root/'..'/'escape.sqlite'):
        try: owned(root,target)
        except ValueError: checks.append('outside write refused')
        else: raise AssertionError('ownership guard lost')
    link=root/'escape-link'
    if not link.exists():link.symlink_to(REPO,target_is_directory=True)
    try:
        try:owned(root,link/'bad.sqlite')
        except ValueError: checks.append('symlink escape refused')
        else:raise AssertionError('symlink guard lost')
    finally:link.unlink()
    try:
        with query_deadline(.01):time.sleep(.03)
    except TimeoutError:checks.append('query deadline fires')
    else:raise AssertionError('deadline guard lost')
    # Mutation: bypass boundary function and prove the same assertion detects it.
    def rejects_live(fn):
        try:fn(root,REPO)
        except ValueError:return True
        return False
    assert rejects_live(owned)
    mutant=lambda r,p:Path(p)
    assert not rejects_live(mutant)
    checks.append('ownership bypass mutant detected by outside-root assertion')
    child=subprocess.Popen([sys.executable,'-B','-c','import time; x=bytearray(16*1024*1024); time.sleep(10)'])
    try:
        time.sleep(.15)
        assert child_rss(child.pid)>16*MIB and aggregate_rss()>resident_bytes()
    finally:stop_owned_children()
    assert child.poll() is not None
    checks.append('owned child RSS included and owned process group stopped')
    # A failing diagnostic write must not prevent termination. The mutant
    # removes the finally path and consequently exits with an exception (1).
    prefix="import sys;sys.path.insert(0,sys.argv[1]);import graph_eval as m;from pathlib import Path;root=Path(sys.argv[2]);m.dump=lambda *a:(_ for _ in ()).throw(OSError('injected diagnostic write failure'));"
    good=prefix+"m.guard_stop(root,{},89)"
    bad=prefix+"m.dump(root/'no-write.json',{});m.stop_owned_children();m.os._exit(89)"
    codes=[]
    for code in (good,bad):
        p=subprocess.run([sys.executable,'-B','-c',code,str(Path(__file__).parent),str(root)],capture_output=True,timeout=5)
        codes.append(p.returncode)
    assert codes==[89,1],codes
    checks.append('diagnostic-write failure still terminates; removed-finally mutant detected')
    # Probe the configured boundary without allocating gigabytes on the host.
    code="import sys,time,json;sys.path.insert(0,sys.argv[1]);import graph_eval as m;from pathlib import Path;r=Path(sys.argv[2]);cap=json.loads((r/'snapshot.json').read_text())['memory_cap_bytes'];m.aggregate_rss=lambda:cap+1;m.guard(r);time.sleep(2)"
    p=subprocess.run([sys.executable,'-B','-c',code,str(Path(__file__).parent),str(root)],capture_output=True,timeout=5)
    assert p.returncode==88,p.returncode
    checks.append('synthetic cap-plus-one sample trips configured aggregate RSS guard')
    return {'status':'pass','checks':checks}


def extended_probes(root):
    """Adapter parity, a real commit between reads, and cache invalidation."""
    root=owned(root);p=read_payload(root);a=GraphQueryIndex(p);path=root/'extended.sqlite';make_db(root,path,p)
    b=SqlGraph(path);h=CachedSqlGraph(path);rows=[]
    # Global scans remain globally materialized by the same existing algorithms.
    selected=queries(p)[:3]
    scope=next(n['source_file'] for n in p['nodes'] if n['id']==selected[0])
    cases=[('impact',lambda g:g.graph_impact(selected[0],max_hops=2)),
           ('path_filter',lambda g:g.risk_score(scope,max_hops=1,candidate_cap=200)),
           ('report',lambda g:g.report(limit=5,sections=['fan_in','fan_out','orphan_docs']))]
    for name,fn in cases:
        result={'name':name,'variants':{}}
        expected=None
        for v,g in [('A',a),('B',b),('H',h)]:
            try:
                ms,value=timing(lambda:fn(g))
                if v=='A':expected=value
                if expected is not None:assert value==expected
                result['variants'][v]={'ms':ms,'result_bytes':len(json.dumps(value)),'parity':True if expected is not None else 'unqualified: A stopped'}
            except (TimeoutError,apsw.InterruptError) as e:
                result['variants'][v]={'bounded_stop':str(e),'parity':'unqualified'}
        rows.append(result)
    b.close();h.close()
    # A writer commits during a lazy traversal. Every read in that traversal
    # must retain the old snapshot, then the next query must see the new edge.
    q=fixture();small=root/'interleave.sqlite';make_db(root,small,q)
    b=SqlGraph(small);w=connect(small);original=b._out.get;fired=[]
    def during(key,default=None):
        value=original(key,default)
        if not fired:
            fired.append(True)
            w.execute("DELETE FROM graph_edges WHERE source=(SELECT id FROM graph_keys WHERE name='b')")
        return value
    b._out.get=during
    assert b.traverse('a',relations=['calls'],max_hops=2)==GraphQueryIndex(q).traverse('a',relations=['calls'],max_hops=2)
    b._out.get=original
    changed=dict(q,edges=[e for e in q['edges'] if e['source']!='b'])
    assert b.traverse('a',relations=['calls'],max_hops=2)==GraphQueryIndex(changed).traverse('a',relations=['calls'],max_hops=2)
    b.close();w.close()
    make_db(root,small,q);h=CachedSqlGraph(small);w=connect(small)
    h.traverse('a',max_hops=3);h.graph_impact('d');h.report(limit=5)
    w.execute("DELETE FROM graph_edges WHERE relation='calls'")
    changed=dict(q,edges=[e for e in q['edges'] if e['relation']!='calls']);expected=GraphQueryIndex(changed)
    for fn in [lambda g:g.traverse('a',max_hops=3),lambda g:g.graph_impact('d'),lambda g:g.report(limit=5),lambda g:g.risk_score('fixture.py')]:
        assert fn(h)==fn(expected)
    h.close();w.close()
    make_db(root,small,q);h=CachedSqlGraph(small);w=connect(small)
    old_neighborhood=h.one_hop_neighbors(['a']);oldrefresh=h.refresh;fired=[]
    def publish_after_validation():
        oldrefresh()
        if not fired:
            fired.append(True)
            w.execute("DELETE FROM graph_edges WHERE relation='calls'")
            w.execute("UPDATE graph_nodes SET payload=json_set(payload,'$.label','changed-during-query') WHERE id=(SELECT id FROM graph_keys WHERE name='b')")
    h.refresh=publish_after_validation
    assert h.one_hop_neighbors(['a'])==old_neighborhood
    h.refresh=oldrefresh
    assert h.traverse('a',max_hops=3)==expected.traverse('a',max_hops=3)
    h.close();w.close()
    # Known bad: validate before establishing the read snapshot. Old cached
    # edges then hydrate newly committed node labels; the same assertion fails.
    make_db(root,small,q);h=CachedSqlGraph(small);w=connect(small)
    old_neighborhood=h.one_hop_neighbors(['a']);oldrefresh=h.refresh;fired=[]
    h.refresh=publish_after_validation
    def unpinned(name,*args,**kwargs):
        h.refresh()
        return getattr(SqlGraph,name)(h,*args,**kwargs)
    h._cached_query=unpinned
    assert h.one_hop_neighbors(['a'])!=old_neighborhood
    h.close();w.close()
    # Symbol/chunk identity is a zero/one/many overlap mapping, never an FK
    # requiring exactly one semantic chunk per symbol.
    chunks=[(1,1,4),(2,3,8),(3,12,15)]
    def mapped(start,end):return [cid for cid,lo,hi in chunks if lo<=end and hi>=start]
    assert mapped(20,21)==[] and mapped(12,12)==[3] and mapped(3,4)==[1,2]
    return {'status':'pass','global_consumers':rows,'read_transaction_interleaving':True,
            'cache_commit_invalidation':True,'cache_validation_interleaving':True,'unpinned_cache_mutant_detected':True,'zero_one_many_mapping_oracle':True,
            'limits':'Leiden/igraph construction and complete tool-call epoch coherence remain unqualified.'}


def public_worker(root,variant,run):
    root=owned(root);stop,watch=guard(root)
    import server_impl
    import graph_query
    g=GraphQueryIndex(read_payload(root)) if variant=='A' else (CachedSqlGraph if variant=='H' else SqlGraph)(root/('graph-c.sqlite' if variant=='C' else 'graph-b.sqlite'))
    accesses=[]
    def frozen(requested,**kwargs):
        assert Path(requested).resolve()==root
        accesses.append(True)
        return g
    original_loader=server_impl._load_graph_query
    graph_query.get_query_index=frozen
    # The producer normally loads a distinct namespaced script module. Detect
    # the known-bad patching-only-the-public-module configuration explicitly.
    assert original_loader().get_query_index is not frozen
    server_impl._load_graph_query=lambda:graph_query
    assert server_impl._load_graph_query().get_query_index is frozen
    # A missing symbol must fail the test, never trigger extraction/rebuild.
    server_impl._graph_refresh_and_resolve=lambda *a,**k:(_ for _ in ()).throw(AssertionError('unexpected refresh'))
    m=json.loads((root/'queries.json').read_text());out={}
    families={
      'callhierarchy':(m['calls_out_3'],lambda s:server_impl.code_callhierarchy_response(root,s,direction='both')),
      'graph_path':(m['weighted_path'],lambda s:server_impl.code_graph_path_response(root,s[0],s[1],max_hops=5))}
    for name,(seeds,fn) in families.items():
        times=[];digests=[];failures=[];cold=None
        for i in range(110):
            try:
                def invoke():
                    value=fn(seeds[i%len(seeds)])
                    assert value['status']=='ok',value
                    return json.dumps(value,sort_keys=True,separators=(',',':'))
                ms,value=timing(invoke)
                if cold is None:cold=ms
                if i>=10:times.append(ms);digests.append(hashlib.sha256(value.encode()).hexdigest())
            except (TimeoutError,apsw.InterruptError) as e:failures.append(str(e));break
        out[name]={'samples_ms':times,'response_hashes':digests,'errors':failures,'first_ms':cold}
    stop.set()
    assert accesses, 'frozen backend accessor was bypassed'
    if variant!='A':g.close()
    dump(root/f'public-{variant}-{run}.json',{'variant':variant,'run':run,'families':out,'watchdog':watch,
          'backend_accessor_calls':len(accesses),'scope':'real producer plus response JSON encoding; frozen graph accessor, no MCP transport or model pipeline'})


def broad_worker(root, variant, run):
    """Round 2: actual risk/report producers, shared H and per-request M.

    M deliberately includes full hydration and adjacency construction in every
    measured call. Community artifacts remain frozen separate inputs here;
    lifecycle publication is qualified by the separate source experiment.
    """
    root=owned(root)
    snapshot_meta=json.loads((root/'snapshot.json').read_text())
    started=calendar.timegm(time.strptime(snapshot_meta['created_at'],'%Y-%m-%dT%H:%M:%SZ'))
    remaining=started+4*3600-time.time()
    if remaining<=0:raise RuntimeError('four-hour original evaluation envelope exhausted')
    stop,watch=guard(root,min(1800,remaining))
    import server_impl, graph_query
    assert variant in ('A','H','M','J','K')
    g=GraphQueryIndex(read_payload(root)) if variant=='A' else (GroupedCachedSqlGraph if variant=='K' else CachedSqlGraph)(root/'graph-c.sqlite')
    accesses=[]
    def frozen(requested, **kwargs):
        assert Path(requested).resolve()==root
        accesses.append(True)
        if variant not in ('M','J'):return g
        header=json.loads(g.c.execute("SELECT value FROM graph_meta WHERE key='header'").fetchone()[0])
        if variant=='J':
            # A single decoder per array shares repeated JSON keys like A's
            # whole-file decoder. Per-row loads needlessly allocate those keys
            # once for every node/edge. Include assembly/decoding in timing/RSS.
            arrays={key:json.loads('['+','.join(r[0] for r in g.c.execute(
                'SELECT payload FROM '+table+' ORDER BY ordinal'))+']')
                for key,table in [('nodes','graph_nodes'),('edges','graph_edges')]}
            return GraphQueryIndex(dict(header,**arrays))
        return GraphQueryIndex(dict(header,nodes=list(g.nodes),edges=list(g.edges)))
    original_loader=server_impl._load_graph_query
    graph_query.get_query_index=frozen
    assert original_loader().get_query_index is not frozen
    server_impl._load_graph_query=lambda:graph_query
    assert server_impl._load_graph_query().get_query_index is frozen
    server_impl._graph_refresh_and_resolve=lambda *a,**k:(_ for _ in ()).throw(AssertionError('unexpected refresh'))
    scopes=['.wavefoundry/framework/scripts/sqlite_runtime.py',
            '.wavefoundry/framework/scripts/sqlite_vector_store.py',
            '.wavefoundry/framework/scripts/indexer.py']
    families={
        'risk_scopes':(scopes,lambda s:server_impl.code_risk_score_response(root,scope=s,max_hops=3,top=20,candidate_cap=500)),
        'report_default':([None],lambda _:server_impl.wf_graph_report_response(root,limit=20)),
        'report_filtered':([None],lambda _:server_impl.wf_graph_report_response(root,limit=20,exclude_generated=True,exclude_external=True))}
    manifest={'round':2,'budget_warm_p95_ms':500,'warmups':10,'timed_per_family':100,
              'risk_scopes':scopes,'report_limit':20,'scope':'complete producer plus response encoding; no MCP transport or model work',
              'variants':{'A':'current resident GraphQueryIndex','H':'cached lazy graph in shared semantic DB','M':'shared DB; materialize graph per broad request'},
              'community_input':'frozen separate artifact; not a complete shared response publication proof'}
    manifest_path=root/'round2-query-manifest.json'
    if manifest_path.exists():assert json.loads(manifest_path.read_text())==manifest
    else:dump(manifest_path,manifest)
    result={'variant':variant,'run':run,'families':{},'manifest':manifest,
            'manifest_variant':'M' if variant=='J' else 'H' if variant=='K' else variant,
            'cache_strategy':'K:16MiB serialized node budget +2x8MiB serialized adjacency budgets; groupedSQLdegree; not an RSS bound' if variant=='K' else 'original',
            'materialization_strategy':('bulk JSON array decode per request; same rows and algorithms' if variant=='J' else 'per-row JSON decode per request' if variant=='M' else 'resident or lazy'),
            'executed_harness_sha256':sha(__file__),'watchdog':watch}
    cpu=time.process_time()
    for name,(seeds,fn) in families.items():
        times=[];hashes=[];errors=[];first=None
        for i in range(len(seeds) if run<0 else 110):
            def invoke():
                # Pin the entire producer, including callbacks outside report().
                with (contextlib.nullcontext() if variant=='A' else g.c):
                    if variant!='A':
                        g.c.execute('SELECT count(*) FROM graph_meta').fetchone();g.refresh()
                    value=fn(seeds[i%len(seeds)])
                    assert value['status']=='ok',value
                    data=value['data']
                    assert not any(d.get('code')=='evidence_partition_degraded' for d in value.get('diagnostics',[])),value
                    if name=='risk_scopes':
                        assert data['scope']==seeds[i%len(seeds)]
                        assert 0<data['candidate_count']<=data['candidate_cap']==500
                        assert data['results'] and not data.get('over_candidate_cap',False)
                    else:
                        assert isinstance(data['communities'],list) and isinstance(data['evidence_communities'],list)
                        assert len(data['communities'])+len(data['evidence_communities'])>0
                    return json.dumps(value,sort_keys=True,separators=(',',':'))
            try:
                ms,value=timing(invoke)
                if first is None:first=ms
                if i>=10 or run<0:
                    times.append(ms);hashes.append(hashlib.sha256(value.encode()).hexdigest())
            except (TimeoutError,apsw.InterruptError) as exc:
                errors.append(str(exc));break
        result['families'][name]={'samples_ms':times,'response_hashes':hashes,'errors':errors,'first_ms':first}
        result.update(cpu_seconds=time.process_time()-cpu,backend_accessor_calls=len(accesses),steady_rss_bytes=resident_bytes())
        dump(root/f'broad-{variant}-{run}.json',result)
        print(json.dumps({'variant':variant,'run':run,'family':name,'count':len(times),'p95_ms':pct(times,.95) if times else None,'errors':errors}),flush=True)
    stop.set()
    if variant!='A':g.close()
    expected=sum(len(seeds) if run<0 else 110 for seeds,_ in families.values())
    assert len(accesses)==expected or any(x['errors'] for x in result['families'].values())


def candidate_probes(root):
    path=root/'candidate-oracles.sqlite';payload=fixture();make_db(root,path,payload)
    g=GroupedCachedSqlGraph(path)
    try:
        with g.c:
            for adjacency,direction in [(g._out,'source'),(g._in,'target')]:
                for key,bucket in adjacency.items():
                    expected=[e for e in payload['edges'] if e[direction]==key]
                    assert len(bucket)==len(expected) and list(bucket)==expected
                    assert bucket[:]==expected
        small=CachedNodes(g.c,256)
        for node in payload['nodes']:
            assert small.get(node['id'])==node and small.used<=256
        assert len(small.cache)<len(payload['nodes'])
        assert small.get('missing',{'fallback':True})=={'fallback':True}
        assert small.get('missing',42)==42
        tiny=CachedNodes(g.c,1)
        assert tiny.get('a')==payload['nodes'][0] and tiny.used==0 and not tiny.cache
        before=g._cached_query('get_node','a')
        w=connect(path)
        def write_label(label):
            with w:
                w.execute("UPDATE graph_nodes SET payload=json_set(payload,'$.label',?) WHERE id=(SELECT id FROM graph_keys WHERE name='a')",(label,))
        write_label('new-label')
        assert g._cached_query('get_node','a')['label']=='new-label'
        assert before['label']!='new-label'
        # Known-bad node-cache invalidation must retain the wrong cached label.
        g._node_by_id.clear=lambda:None
        write_label('must-invalidate')
        stale=g._cached_query('get_node','a')['label']
        assert stale!='must-invalidate', 'removed-clear control was not detected'
        w.close()
    finally:g.close()
    return {'status':'pass','degree_count_and_order':True,'bounded_node_cache':True,
            'node_cache_invalidation':True,'removed_clear_mutant_detected':True,
            'scope':'tiny real SQL fixtures; whole shared public producers separately benchmarked'}


def prepare_databases(root):
    p=read_payload(root)
    make_db(root,root/'graph-b.sqlite',p)
    make_db(root,root/'graph-c.sqlite',p,shared=True)
    dump(root/'queries.json',query_manifest(p))
    return {'status':'ready','graph_sha256':sha(root/'.wavefoundry/index/graph/project-graph.json')}


def planner_probe(root):
    p=root/'graph-b.sqlite';g=SqlGraph(p);seeds=json.loads((root/'queries.json').read_text())['calls_out_3'];out={}
    for state in ['before_optimize','after_optimize']:
        if state=='after_optimize':
            w=connect(p);w.execute('PRAGMA optimize=0x10002');w.close()
        times=[]
        for i in range(110):
            ms,value=timing(lambda:g.cte_reachable(seeds[i%len(seeds)],3))
            if i>=10:times.append(ms)
        out[state]={'samples_ms':times,'p95_ms':pct(times,.95)}
    g.close();return out


def main():
    ap=argparse.ArgumentParser();ap.add_argument('command',choices=['snapshot','oracles','compare','worker','shared','startup','publication','maintenance','scale','fanout','safety','extended','public','broad','candidates','planner','prepare']);ap.add_argument('--root');ap.add_argument('--variant',default='A');ap.add_argument('--run',type=int,default=0);ap.add_argument('--factor',type=int,default=5);args=ap.parse_args()
    if args.command=='snapshot': snapshot();return
    root=owned(args.root)
    if (root/'.stop-final-rerun').exists():raise SystemExit(90)
    lock_handle=open(root/'.benchmark.lock','a')
    try:fcntl.flock(lock_handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise RuntimeError('another owned benchmark is active; serialize workers')
    if args.command=='worker': worker(root,args.variant,args.run);return
    if args.command=='public':public_worker(root,args.variant,args.run);return
    if args.command=='broad':broad_worker(root,args.variant,args.run);return
    stop,watch=guard(root)
    commands={'oracles':oracles,'compare':compare,'shared':shared_probes,'startup':startup_samples,'publication':publication_samples,'maintenance':maintenance,'fanout':fanout,'safety':safety_probes,'extended':extended_probes,'planner':planner_probe,'prepare':prepare_databases,'candidates':candidate_probes,'scale':lambda r:scale(r,args.factor)}
    result=commands[args.command](root);stop.set()
    dump(root/(args.command+(str(args.factor) if args.command=='scale' else '')+'.json'),result);print(json.dumps(result)[:3000])

if __name__=='__main__':main()
