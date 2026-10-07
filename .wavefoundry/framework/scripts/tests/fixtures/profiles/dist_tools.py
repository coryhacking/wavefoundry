"""Fixture extension module for the ``declared`` profile asset (wave 1zyb3,
change 1zxnu).

``record_layout_support.apply_profile`` copies this file into a copied scripts
directory as ``dist_tools.py`` (the asset's ``module_files``); it is never
imported from this fixtures directory. It serves one new tool with its own
input schema and replaces one core name, so the declared golden pins both.
"""
import server_impl


def register(mcp, get_handler):
    @mcp.tool()
    def dist_inventory(area: str, limit: int = 10, kinds: "list[str] | None" = None,
                       include_archived: bool = False, **kwargs):
        bad = server_impl.ensure_no_extra_args("dist_inventory", kwargs)
        if bad is not None:
            return bad
        return {"status": "ok", "data": {"area": area, "limit": limit, "kinds": list(kinds or []),
                                         "include_archived": include_archived}}

    @mcp.tool()
    def wf_open_dashboard(view: str = "overview", **kwargs):
        bad = server_impl.ensure_no_extra_args("wf_open_dashboard", kwargs)
        if bad is not None:
            return bad
        return {"status": "ok", "data": {"view": view}}
