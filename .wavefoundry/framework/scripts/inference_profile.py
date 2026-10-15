"""Distribution-owned inference declaration; never read target repository settings.

Downstream distributions may select local or extension and declare the latter's
flat module in mcp_tool_extensions.EXTENSION_HELPER_MODULES.
"""

PROVIDER = "tensorwell"  # tensorwell | local | extension
ADAPTER_MODULE = ""  # extension: a declared helper exporting create_provider
