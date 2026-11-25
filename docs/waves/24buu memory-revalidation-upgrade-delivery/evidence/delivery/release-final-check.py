from pathlib import Path
from zipfile import ZipFile
import hashlib,io,json
d=Path(__file__).resolve().parent
rehearsal=d.parent/'rehearsal'
root=d.parents[3]
for filename,record in json.loads((rehearsal/'final-archives.json').read_text()).items():
    path=Path(filename)
    with ZipFile(path) as outer:
        archive_hash=hashlib.sha256(path.read_bytes()).hexdigest()
        assert archive_hash==record['archive_sha256']
        version=outer.read('.wavefoundry/framework/VERSION').decode().strip()
        assert version==record['version'] and version.split('+')[1] in path.name
        payload=next(k for k in outer.namelist() if k.startswith('payload/wavefoundry-1.53.') and k.endswith('.zip'))
        with ZipFile(io.BytesIO(outer.read(payload))) as inner:
            files=[k for k in inner.namelist() if k.startswith('.wavefoundry/framework/') and not k.endswith('/')]
            scripts=[k for k in files if k.startswith(('.wavefoundry/framework/scripts/','.wavefoundry/framework/seeds/'))]
            assert len(files)==285 and len(scripts)==238
            assert outer.testzip() is None and inner.testzip() is None
            assert all(outer.read(k)==inner.read(k) for k in files)
            assert all(inner.read(k)==(root/k).read_bytes() for k in scripts)
        print(version,archive_hash,len(files),len(scripts))
for route,track,expected in [('cli','cli',[False,False]),('installed','cli',[True,False]),('mcp','mcp',[True,True])]:
    directory=rehearsal/f'final-{route}'/track
    for hop,retained in enumerate(expected,1):
        head=f'hop{hop}'
        def load(tail):
            return json.loads((directory/f'{head}-{tail}.json').read_text())
        assert bool(load('primary-checkpoint'))==retained
        rows=[json.loads(l.split('WAVE_UPGRADE_SUMMARY_JSON:',1)[1]) for l in (directory/f'{head}-terminal.upgrade.log').read_text().splitlines() if 'WAVE_UPGRADE_SUMMARY_JSON:' in l]
        assert len([r for r in rows if r.get('cleanup_complete') is True])==1
        checks=load('inspect.checks')
        assert len(checks['checks'])==18 and all(v is True for v in checks['checks'].values())
        assert checks['version']==f'1.53.0+q5u{hop-1}'
        assert not load('inspect.snapshot')['held_lock']
        print(route,hop,'primary retained',retained,'terminal summaries',1,'passing checks',18)
