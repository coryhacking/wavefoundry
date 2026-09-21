from pathlib import Path
import contextlib, io, json, sys, tempfile
from unittest.mock import patch
import upgrade_wavefoundry as upgrade
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp); scripts=root/'scripts';scripts.mkdir()
    script=scripts/'render_platform_surfaces.py'
    marker=root/'renderer-version.txt'
    script.write_text('raise RuntimeError("old renderer must not run")\n')
    # Replace disk code after importing the orchestrator, as extraction does.
    script.write_text('from pathlib import Path\nPath('+repr(str(marker))+').write_text("new renderer")\n')
    with patch.object(upgrade,'SCRIPTS_DIR',scripts), patch.object(upgrade,'_preferred_python',return_value=sys.executable), patch.object(upgrade.venv_bootstrap,'ensure_python_resolves',return_value=None), contextlib.redirect_stdout(io.StringIO()):
        upgrade.phase_surface_rendering(root)
    assert marker.read_text()=='new renderer'
    print(json.dumps({'phase':'phase_surface_rendering','fresh_disk_renderer':True,'scope':'temporary root; no host/model calls'}))
