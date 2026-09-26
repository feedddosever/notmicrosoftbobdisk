"""Assert that rater.ORDER equals build/graph.json topo_order."""

import json
import pathlib

from service.sheetshift_ho3.rater import ORDER


def test_order_matches_topo_order():
    graph = json.loads(
        (pathlib.Path(__file__).parent.parent / "build" / "graph.json").read_text(encoding="utf-8")
    )
    topo_order = tuple(graph["topo_order"])
    assert ORDER == topo_order, (
        f"ORDER length {len(ORDER)} vs topo_order length {len(topo_order)}; "
        f"first diff: {next((i, o, t) for i,(o,t) in enumerate(zip(ORDER,topo_order)) if o!=t) if ORDER != topo_order else 'lengths differ'}"
    )
