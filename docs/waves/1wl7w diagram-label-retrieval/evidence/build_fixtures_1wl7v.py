"""Fixture builder for change 1wl7v-enh (wave 1wl7w diagram-label-retrieval).

Builds the committed diagrams-golden-set fixtures through the CANONICAL
producer algorithms (the faithful-fixture rule), never hand-shaped
approximations:

* ``drawio/platform-architecture.drawio`` — the canonical draw.io COMPRESSED
  save: each ``<diagram>`` body is URL-encode -> raw deflate -> base64 of the
  inner ``mxGraphModel`` XML, exactly as app.diagrams.net writes it. Two
  meaningfully named pages; page one carries an ``<object label>`` wrapper
  (draw.io's Edit Data serialization — the council's strongest challenge) and
  an HTML-tagged ``mxCell`` value.
* ``drawio/deploy-flow.drawio`` — the plain-XML save shape: an UNCOMPRESSED
  nested ``mxGraphModel`` ELEMENT under a ``<diagram>`` whose name is the
  auto-generated ``Page-1`` (exercising the stem-breadcrumb fallback).
* ``excalidraw/incident-runbook.excalidraw`` — the real Excalidraw v2 schema:
  bound container text (separate text element with ``containerId``), an arrow
  label, a frame ``name``, an ``isDeleted: true`` ghost whose sentinel must
  NEVER become retrievable, and an empty-string text element.

Writes ONLY with --write (QA-DEL-1: bare re-runs never clobber committed
artifacts); a bare run prints what would be written.

Run from the repository root:
    ~/.wavefoundry/venv/bin/python "docs/waves/1wl7w diagram-label-retrieval/evidence/build_fixtures_1wl7v.py" [--write]
"""

from __future__ import annotations

import argparse
import base64
import json
import urllib.parse
import zlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
DIAGRAMS = (REPO_ROOT / ".wavefoundry" / "framework" / "scripts" / "tests"
            / "fixtures" / "retrieval_golden" / "diagrams")

GHOST_SENTINEL = "GHOST_DELETED_LABEL_SENTINEL retire the legacy pager rotation"


def _compress_page(model_xml: str) -> str:
    """The canonical draw.io page compression: URL-encode -> raw deflate -> base64."""
    quoted = urllib.parse.quote(model_xml, safe="").encode("ascii")
    co = zlib.compressobj(9, zlib.DEFLATED, -15)
    raw = co.compress(quoted) + co.flush()
    return base64.b64encode(raw).decode("ascii")


def build_platform_architecture() -> str:
    page1 = (
        '<mxGraphModel dx="1400" dy="900" grid="1" gridSize="10"><root>'
        '<mxCell id="0"/><mxCell id="1" parent="0"/>'
        '<mxCell id="2" value="Ingress gateway terminates mutual TLS" '
        'style="edgeStyle=orthogonalEdgeStyle;rounded=0" edge="1" parent="1" '
        'source="3" target="4"><mxGeometry relative="1" as="geometry"/></mxCell>'
        '<mxCell id="3" value="Edge proxy fleet" style="rounded=1;whiteSpace=wrap" '
        'vertex="1" parent="1"><mxGeometry x="40" y="80" width="150" height="50" '
        'as="geometry"/></mxCell>'
        '<mxCell id="4" value="&lt;b&gt;Fraud scoring engine&lt;/b&gt;" '
        'style="rounded=1;whiteSpace=wrap;html=1" vertex="1" parent="1">'
        '<mxGeometry x="280" y="80" width="170" height="50" as="geometry"/></mxCell>'
        '<object label="Ledger reconciliation worker" ledger="general" as="">'
        '<mxCell id="5" style="shape=process;whiteSpace=wrap" vertex="1" parent="1">'
        '<mxGeometry x="280" y="200" width="190" height="50" as="geometry"/></mxCell>'
        "</object>"
        "</root></mxGraphModel>"
    )
    page2 = (
        '<mxGraphModel dx="1400" dy="900"><root>'
        '<mxCell id="0"/><mxCell id="1" parent="0"/>'
        '<mxCell id="2" value="Columnar analytics store" style="shape=cylinder3" '
        'vertex="1" parent="1"><mxGeometry x="60" y="60" width="140" height="80" '
        'as="geometry"/></mxCell>'
        '<mxCell id="3" value="replicates snapshots to the cold region" '
        'style="edgeStyle=none" edge="1" parent="1" source="2" target="4">'
        '<mxGeometry relative="1" as="geometry"/></mxCell>'
        '<mxCell id="4" value="Cold region archive" style="rounded=1" vertex="1" '
        'parent="1"><mxGeometry x="320" y="70" width="150" height="60" '
        'as="geometry"/></mxCell>'
        "</root></mxGraphModel>"
    )
    return (
        '<mxfile host="app.diagrams.net" modified="2026-08-29T00:00:00.000Z" '
        'agent="Mozilla/5.0" version="24.7.1" type="device">'
        f'<diagram id="svc-topo" name="Service topology">{_compress_page(page1)}</diagram>'
        f'<diagram id="data-plane" name="Data plane">{_compress_page(page2)}</diagram>'
        "</mxfile>\n"
    )


def build_deploy_flow() -> str:
    return (
        '<mxfile host="app.diagrams.net" modified="2026-08-29T00:00:00.000Z" '
        'version="24.7.1" type="device">'
        '<diagram id="dep-1" name="Page-1">'
        '<mxGraphModel dx="1000" dy="700"><root>'
        '<mxCell id="0"/><mxCell id="1" parent="0"/>'
        '<mxCell id="2" value="Artifact signing service" style="rounded=1" '
        'vertex="1" parent="1"><mxGeometry x="40" y="60" width="160" height="50" '
        'as="geometry"/></mxCell>'
        '<mxCell id="3" value="canary rollout gate checks error budget" '
        'style="edgeStyle=none" edge="1" parent="1" source="2" target="4">'
        '<mxGeometry relative="1" as="geometry"/></mxCell>'
        '<mxCell id="4" value="Production fleet" style="rounded=1" vertex="1" '
        'parent="1"><mxGeometry x="320" y="60" width="140" height="50" '
        'as="geometry"/></mxCell>'
        "</root></mxGraphModel>"
        "</diagram></mxfile>\n"
    )


def build_incident_runbook() -> str:
    nb = {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": [
            {"type": "rectangle", "id": "r1", "x": 120, "y": 120, "width": 220,
             "height": 70, "angle": 0, "strokeColor": "#1e1e1e",
             "backgroundColor": "transparent", "seed": 1839224,
             "isDeleted": False,
             "boundElements": [{"id": "t1", "type": "text"}]},
            {"type": "text", "id": "t1", "x": 130, "y": 140,
             "width": 200, "height": 25, "angle": 0, "seed": 552211,
             "isDeleted": False, "containerId": "r1",
             "text": "page the on-call\nresolver first",
             "originalText": "page the on-call resolver first",
             "fontSize": 20, "fontFamily": 1},
            {"type": "arrow", "id": "a1", "x": 340, "y": 150, "width": 180,
             "height": 0, "angle": 0, "seed": 90417, "isDeleted": False,
             "points": [[0, 0], [180, 0]],
             "boundElements": [{"id": "t2", "type": "text"}]},
            {"type": "text", "id": "t2", "x": 360, "y": 125,
             "width": 150, "height": 25, "seed": 66120, "isDeleted": False,
             "containerId": "a1",
             "text": "escalate to the database owner\nafter two failed probes",
             "originalText": "escalate to the database owner after two failed probes",
             "fontSize": 16, "fontFamily": 1},
            {"type": "text", "id": "t3", "x": 140, "y": 260, "width": 260,
             "height": 25, "seed": 771029, "isDeleted": False,
             "containerId": None,
             "text": "rotate the incident commander\nevery four hours",
             "originalText": "rotate the incident commander every four hours",
             "fontSize": 16, "fontFamily": 1},
            {"type": "text", "id": "ghost", "x": 400, "y": 400, "width": 100,
             "height": 25, "seed": 424242, "isDeleted": True,
             "containerId": None,
             "text": GHOST_SENTINEL, "originalText": GHOST_SENTINEL,
             "fontSize": 16, "fontFamily": 1},
            {"type": "text", "id": "empty", "x": 10, "y": 10, "width": 10,
             "height": 25, "seed": 11, "isDeleted": False, "containerId": None,
             "text": "   ", "originalText": "", "fontSize": 16, "fontFamily": 1},
            {"type": "frame", "id": "f1", "x": 100, "y": 100, "width": 480,
             "height": 220, "seed": 9917, "isDeleted": False,
             "name": "Sev1 containment steps"},
        ],
        "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
        "files": {},
    }
    return json.dumps(nb, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    out = {
        DIAGRAMS / "drawio" / "platform-architecture.drawio": build_platform_architecture(),
        DIAGRAMS / "drawio" / "deploy-flow.drawio": build_deploy_flow(),
        DIAGRAMS / "excalidraw" / "incident-runbook.excalidraw": build_incident_runbook(),
    }
    for path, content in out.items():
        print(f"{'WRITE' if args.write else 'would write'} {path} ({len(content)} bytes)")
        if args.write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
