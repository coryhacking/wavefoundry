"""Synthetic Windows stat metadata; no native filesystem qualification."""
from types import SimpleNamespace

MISSING_TAG = object()


def nt_stat(info, tag=MISSING_TAG, *, reparse=True, zero_identity=False):
    values = {name: getattr(info, name) for name in dir(info) if name.startswith('st_')}
    values['st_file_attributes'] = 0x400 if reparse else 0
    if tag is not MISSING_TAG:
        values['st_reparse_tag'] = tag
    if zero_identity:
        values.update(st_dev=0, st_ino=0, st_nlink=0)
    return SimpleNamespace(**values)
