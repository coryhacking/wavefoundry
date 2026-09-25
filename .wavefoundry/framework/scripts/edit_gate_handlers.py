import importlib
import sys

sys.modules[__name__] = importlib.import_module("wf_server.edit_gate_handlers")
