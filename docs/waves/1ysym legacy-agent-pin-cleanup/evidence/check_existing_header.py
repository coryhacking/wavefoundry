"""Run from repository root: python3 -B <this file>. Temporary roots only."""
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
sys.path.insert(0, str(Path('.wavefoundry/framework/scripts').resolve()))
import render_agent_surfaces as ras

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    role = root / 'docs/agents/guru.md'
    role.parent.mkdir(parents=True)
    role.write_text('# Guru\n\nRole: guru\n')
    wrapper = root / '.claude/agents/guru.md'
    wrapper.parent.mkdir(parents=True)
    header = '---\nname: guru\ntools: Read\nmodel: sonnet\neffort: high\ncustom: keep\n---\n'
    wrapper.write_text(header + '\nOld generated body\n')
    ras.render_agent_surfaces(root)
    original = wrapper.read_bytes()
    assert original.startswith(header.encode())
    # Explicitly selected inherited fields only; body and other header bytes stay intact.
    cleaned = original.replace(b'model: sonnet\n', b'').replace(b'effort: high\n', b'')
    wrapper.write_bytes(cleaned)
    ras.render_agent_surfaces(root)
    assert wrapper.read_bytes() == cleaned, 'existing cleaned header changed on render'
    ras.render_agent_surfaces(root)
    assert wrapper.read_bytes() == cleaned, 'second render restored a pin'
    wrapper.write_bytes(original)
    ras.render_agent_surfaces(root)
    assert wrapper.read_bytes() == original, 'intentional pin changed'
    # Known-bad control: fresh-default reinsertion must fail the cleaned-header oracle.
    wrapper.write_bytes(cleaned)
    mutant = ras.CLAUDE_GURU_AGENT.replace('name: guru\n', 'name: guru\nmodel: sonnet\n')
    with patch.object(ras, 'CLAUDE_GURU_AGENT', mutant), patch.object(ras, '_claude_agent_frontmatter', return_value=''):
        ras.render_agent_surfaces(root)
    assert wrapper.read_bytes() != cleaned, 'known-bad control was not observable'
print('PASS: existing cleaned header stable; intentional pin preserved; reinsertion control detected')
