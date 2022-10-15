import json
from pathlib import Path


def test_anchor_points() -> None:
    from genshinmap.models import Anchor, XYPoint

    with open(Path(__file__).parent / "anchors.json", encoding="utf-8") as f:
        anchor = Anchor.parse_obj(json.load(f)["list"][0])
    assert anchor.get_children_all_left_point() == [
        XYPoint(-5897, 4570),
        XYPoint(-6461, 4482),
    ]
    assert anchor.get_children_all_right_point() == [
        XYPoint(-5617, 4750),
        XYPoint(-6081, 4848),
    ]
