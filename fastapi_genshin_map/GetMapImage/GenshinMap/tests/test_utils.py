import json
from pathlib import Path

DIR = Path(__file__).parent


def test_get_points_by_id() -> None:
    from genshinmap.models import Point, XYPoint
    from genshinmap.utils import get_points_by_id

    with open(DIR / "points.json") as f:
        points = [Point.parse_obj(i) for i in json.load(f)["point_list"]]
    assert get_points_by_id(298, points) == [
        XYPoint(114, 514),
        XYPoint(1919, 810),
    ]


def test_convert_pos() -> None:
    from genshinmap.models import XYPoint
    from genshinmap.utils import convert_pos

    points = [XYPoint(1200, 5000), XYPoint(-4200, 1800)]
    origin = [4844, 4335]
    assert convert_pos(points, origin) == [
        XYPoint(x=6044, y=9335),
        XYPoint(x=644, y=6135),
    ]


def test_convert_pos_crop() -> None:
    from genshinmap.models import XYPoint
    from genshinmap.utils import convert_pos_crop

    points = [XYPoint(0, 0), XYPoint(20, 20)]
    assert convert_pos_crop(0, points) == points
    assert convert_pos_crop(1, points) == [
        XYPoint(-4096, 0),
        XYPoint(-4076, 20),
    ]
    assert convert_pos_crop(4, points) == [
        XYPoint(0, -4096),
        XYPoint(20, -4076),
    ]
    assert convert_pos_crop(5, points) == [
        XYPoint(-4096, -4096),
        XYPoint(-4076, -4076),
    ]


def test_internal_generate_matrix() -> None:
    from genshinmap.utils import _generate_matrix

    assert _generate_matrix(0, 3, 8) == list(range(12))
    assert _generate_matrix(0, 1, 4) == [0, 1, 4, 5]
    assert _generate_matrix(0, 2, 4) == [0, 1, 2, 4, 5, 6]
    assert _generate_matrix(0, 0, 4) == [0, 4]
    assert _generate_matrix(0, 0, 8) == [0, 4, 8]
    assert _generate_matrix(0, 2, 0) == [0, 1, 2]
    assert _generate_matrix(0, 2, 8) == [0, 1, 2, 4, 5, 6, 8, 9, 10]
    assert _generate_matrix(1, 3, 5) == [1, 2, 3, 5, 6, 7]


def test_internal_pos_to_index() -> None:
    from genshinmap.utils import _pos_to_index

    assert _pos_to_index(0, 0) == 0
    assert _pos_to_index(4096, 0) == 1
    assert _pos_to_index(0, 4096) == 4
    assert _pos_to_index(4096, 4096) == 5


def test_crop_image_and_points() -> None:
    from genshinmap.models import XYPoint
    from genshinmap.utils import crop_image_and_points

    assert crop_image_and_points(
        [XYPoint(x=4200, y=8000), XYPoint(x=4150, y=10240)]
    ) == ([5, 9], 0, [XYPoint(x=104, y=3904), XYPoint(x=54, y=6144)])
    points = [
        XYPoint(x=0, y=0),
        XYPoint(x=20, y=20),
        XYPoint(x=4096, y=0),
        XYPoint(x=4116, y=20),
        XYPoint(x=0, y=4096),
        XYPoint(x=20, y=4116),
        XYPoint(x=4096, y=4096),
        XYPoint(x=4116, y=4116),
    ]
    assert crop_image_and_points(points) == (
        [0, 1, 4, 5],
        1,
        points,
    )
