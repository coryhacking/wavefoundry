"""Run against two consumer classifiers with identical source and a missing import setup."""
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile
import sys
import subprocess
from test_upgrade_protocol import UpgradeProtocolTests

def main():
    repo = Path(__file__).resolve().parents[4]
    case = UpgradeProtocolTests()
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        package = Path(sys.argv[1]).resolve()
        altered = base / 'altered.zip'
        with zipfile.ZipFile(package) as z, zipfile.ZipFile(altered, 'w') as mutant:
            stamp = z.read('.wavefoundry/framework/VERSION').decode().strip()
            prefix = '.wavefoundry/framework/scripts/'
            scripts = [p for p in (Path(__file__).parent/'paths.txt').read_text().splitlines() if p.startswith(prefix) and '/tests/' not in p and not p.endswith('/run_tests.py')]
            drift = [p for p in scripts if z.read(p) != (repo/p).read_bytes()]
            print('package', package.name, hashlib.sha256(package.read_bytes()).hexdigest(), 'stamp', stamp, 'compared_scripts', len(scripts), 'drift', drift, flush=True)
            for member in z.infolist():
                b = z.read(member)
                if member.filename == '__main__.py':
                    hook = b'    _add_bundle_scripts_path(Path(sys.argv[0]).resolve())'
                    assert b.count(hook) == 1
                    b = b.replace(hook, b'    pass')
                mutant.writestr(member, b)
        # An absent installed runner makes a good package stop after materialization,
        # before launch. The bad archive fails earlier at retain's function import.
        for label, bundle in [('good', package), ('bad',altered)]:
            result, root = case._run_direct_entry(base,bundle,label)
            print(label, result.returncode, result.stdout[-1600:], result.stderr[-1300:], flush=True)
            if label == 'bad':
                assert result.returncode and "No module named 'contained_files'" in result.stderr
            else:
                assert "No module named 'contained_files'" not in result.stderr
                assert 'upgrade_protocol_invalid' not in result.stdout
                assert 'contained_files' not in result.stdout
if __name__ == '__main__':
    main()
