import importlib
import sys

sys.modules[__name__] = importlib.import_module("wf_server.mcp_tool_registry")
