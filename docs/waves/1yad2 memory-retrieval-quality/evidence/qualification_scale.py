"""Run from the repository root; synthetic component timing, never ranking qualification."""
import sys,tempfile,time,json,math,platform,argparse
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'.wavefoundry/framework/scripts'))
import sqlite_vector_store as s
import memory_eval as e
parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
report={'platform':platform.platform(),'purpose':'Synthetic timing-only exact SQL scan and BM25 scaling; no quality or native cross-platform claim','cases':[]}
def dist(v):
 v=sorted(v);return {str(p):v[math.ceil(p*len(v))-1] for p in [.5,.95,.99]}
with tempfile.TemporaryDirectory(prefix='wf-memory-scale-') as t:
 for count,duplicates in [(119,1),(1190,1),(11900,1),(119,100),(1190,25)]:
  p=Path(t)/f'{count}-{duplicates}';p.mkdir();db=p/s.FILENAME;c=s.runtime.connect(db)
  c.execute('CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT)');c.execute('INSERT INTO meta VALUES(?,?)',('store_schema_version','8'))
  c.execute('CREATE TABLE chunks_docs(id INTEGER PRIMARY KEY,path TEXT NOT NULL)');c.execute('CREATE INDEX chunks_docs_path ON chunks_docs(path)');c.execute('CREATE TABLE vectors_docs(chunk_id INTEGER PRIMARY KEY,embedding BLOB)')
  paths=[f'docs/agents/memory/m{i}.md' for i in range(count)];vector=[1.]+[0.]*(s.DIMENSIONS-1);blob=s.pack_vector(vector)
  c.execute('BEGIN')
  c.executemany('INSERT INTO chunks_docs VALUES(?,?)',((i*duplicates+j+1,path) for i,path in enumerate(paths) for j in range(duplicates)))
  c.executemany('INSERT INTO vectors_docs VALUES(?,?)',((i+1,blob) for i in range(count*duplicates)))
  c.execute('COMMIT');c.close()
  records=[{'memory_id':f'm{i}','title':'Local evaluation fixture','summary':f'Preserve atomic index publication evidence for cache policy {i}','target_refs':['src/index.py'],'evidence_refs':['fixture'],'keywords':['publication']} for i in range(count)]
  times=[];lex=[]
  for _ in range(100):
   start=time.perf_counter();result=s.dense_path_scores(p,'docs',vector,paths);times.append((time.perf_counter()-start)*1000)
   assert result['complete'] and result['eligible_chunks']==count*duplicates and len(result['scores'])==20
  for _ in range(100):
   start=time.perf_counter();out=e.lexical_bm25_scores(records,'atomic publication cache');lex.append((time.perf_counter()-start)*1000);assert len(out)==count
  case={'records':count,'chunks_per_record':duplicates,'physical_chunks':count*duplicates,'returned_records':20,'sql_ms':dist(times),'lexical_ms':dist(lex),'calls_each':100};report['cases'].append(case);print(case,flush=True)
args.output.write_text(json.dumps(report,indent=2))
