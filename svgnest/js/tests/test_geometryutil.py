import pytest
from svgnest.js.display import plot

from svgnest.js.geometry import Point, Polygon, Vector
from svgnest.js.geometryutil import rotate_polygon, normalize_vector, point_in_polygon, polygon_area, intersect, \
    no_fit_polygon, no_fit_polygon_rectangle, is_rectangle, search_start_point


@pytest.mark.parametrize(
    ['input', 'expected'],
    (
            (Polygon(Point(0, 0), Point(2, 0), Point(2, 1), Point(0, 0)),
             Polygon(Point(0, 0), Point(0, 2), Point(-1, 2), Point(0, 0))),
            (Polygon(Point(0, 0), Point(2, 0), Point(2, 1)),
             Polygon(Point(0, 0), Point(0, 2), Point(-1, 2))),
    ))
def test_rotate_polygon(input, expected):
    rotated = rotate_polygon(input, 90)
    assert rotated.almost_equal(expected)


def test_normalize_vector():
    _SQRT2 = 0.70710678118
    assert normalize_vector(Vector(1, 0)).almost_equal(Vector(1, 0))
    assert normalize_vector(Vector(5, 0)).almost_equal(Vector(1, 0))
    assert normalize_vector(Vector(1, 1)).almost_equal(Vector(_SQRT2, _SQRT2))
    assert normalize_vector(Vector(1, -1)).almost_equal(Vector(_SQRT2, -_SQRT2))


SQUARE2x2 = Polygon(Point(0, 0), Point(2, 0), Point(2, 2), Point(0, 2), Point(0, 0))
RECT4x2 = Polygon(Point(0, 0), Point(0, 2), Point(4, 2), Point(4, 0), Point(0, 0))


@pytest.mark.parametrize(
    ['point', 'polygon', 'expected'],
    (
            (Point(1, 1), SQUARE2x2, True),
            (Point(3, 1), SQUARE2x2, False),
            (Point(2, 1), SQUARE2x2, None),
    ))
def test_point_in_polygon(point, polygon, expected):
    pip = point_in_polygon(point, polygon)
    assert pip == expected


def test_polygon_area():
    assert polygon_area(SQUARE2x2) == -4
    assert polygon_area(RECT4x2) == 8


def test_intersect():
    assert intersect(SQUARE2x2, RECT4x2)
    assert intersect(SQUARE2x2, SQUARE2x2)


data = [[[{'x': 34, 'y': 24}, {'x': 54, 'y': 22}, {'x': 95, 'y': 74}, {'x': 80, 'y': 10}, {'x': 20, 'y': 55},
          {'x': 48, 'y': 31}, {'x': 36, 'y': 84}, {'x': 94, 'y': 80}, {'x': 20, 'y': 38}, {'x': 10, 'y': 1},
          {'x': 13, 'y': 68}], 1626.5],
        [[{'x': 8, 'y': 54}, {'x': 40, 'y': 29}, {'x': 67, 'y': 61}, {'x': 26, 'y': 93}], -1937], [
            [{'x': 82, 'y': 74}, {'x': 78, 'y': 71}, {'x': 97, 'y': 13}, {'x': 37, 'y': 36}, {'x': 45, 'y': 33},
             {'x': 34, 'y': 9}, {'x': 85, 'y': 30}, {'x': 10, 'y': 31}, {'x': 84, 'y': 92}], 2175], [
            [{'x': 94, 'y': 25}, {'x': 34, 'y': 67}, {'x': 4, 'y': 7}, {'x': 26, 'y': 45}, {'x': 38, 'y': 0},
             {'x': 13, 'y': 31}, {'x': 49, 'y': 52}, {'x': 6, 'y': 49}, {'x': 24, 'y': 34}], -1281], [
            [{'x': 64, 'y': 52}, {'x': 65, 'y': 12}, {'x': 46, 'y': 85}, {'x': 97, 'y': 94}, {'x': 4, 'y': 17},
             {'x': 19, 'y': 71}, {'x': 58, 'y': 86}, {'x': 96, 'y': 51}, {'x': 90, 'y': 18}, {'x': 94, 'y': 83},
             {'x': 94, 'y': 65}, {'x': 44, 'y': 59}], 2843],
        [[{'x': 79, 'y': 97}, {'x': 50, 'y': 54}, {'x': 49, 'y': 52}, {'x': 0, 'y': 81}], 1530], [
            [{'x': 87, 'y': 97}, {'x': 73, 'y': 22}, {'x': 82, 'y': 65}, {'x': 59, 'y': 25}, {'x': 73, 'y': 61},
             {'x': 48, 'y': 19}, {'x': 68, 'y': 3}, {'x': 3, 'y': 73}, {'x': 47, 'y': 85}, {'x': 84, 'y': 81}], 2689.5],
        [[{'x': 23, 'y': 18}, {'x': 64, 'y': 70}, {'x': 38, 'y': 61}, {'x': 39, 'y': 11}, {'x': 90, 'y': 49},
          {'x': 68, 'y': 87}], -2191.5], [
            [{'x': 25, 'y': 95}, {'x': 51, 'y': 28}, {'x': 12, 'y': 57}, {'x': 41, 'y': 99}, {'x': 46, 'y': 63},
             {'x': 69, 'y': 88}, {'x': 59, 'y': 1}, {'x': 40, 'y': 73}, {'x': 93, 'y': 87}, {'x': 8, 'y': 33},
             {'x': 71, 'y': 90}, {'x': 57, 'y': 10}, {'x': 73, 'y': 83}], 1983.5],
        [[{'x': 66, 'y': 8}, {'x': 83, 'y': 33}, {'x': 50, 'y': 74}, {'x': 92, 'y': 42}, {'x': 48, 'y': 75}], -808],
        [[{'x': 32, 'y': 3}, {'x': 54, 'y': 9}, {'x': 56, 'y': 98}, {'x': 37, 'y': 50}, {'x': 34, 'y': 18}], -1290],
        [[{'x': 48, 'y': 56}, {'x': 32, 'y': 2}, {'x': 76, 'y': 21}, {'x': 35, 'y': 82}], -1172.5],
        [[{'x': 92, 'y': 25}, {'x': 40, 'y': 66}, {'x': 93, 'y': 17}, {'x': 86, 'y': 23}, {'x': 38, 'y': 63},
          {'x': 68, 'y': 91}, {'x': 23, 'y': 28}], -909.5],
        [[{'x': 58, 'y': 61}, {'x': 73, 'y': 58}, {'x': 4, 'y': 96}, {'x': 37, 'y': 74}, {'x': 99, 'y': 74},
          {'x': 50, 'y': 27}, {'x': 70, 'y': 79}, {'x': 25, 'y': 58}, {'x': 71, 'y': 35}, {'x': 20, 'y': 0},
          {'x': 45, 'y': 30}], 688.5], [
            [{'x': 86, 'y': 66}, {'x': 8, 'y': 30}, {'x': 33, 'y': 46}, {'x': 64, 'y': 75}, {'x': 33, 'y': 23},
             {'x': 4, 'y': 7}, {'x': 29, 'y': 67}], 1843],
        [[{'x': 91, 'y': 12}, {'x': 47, 'y': 70}, {'x': 21, 'y': 14}, {'x': 23, 'y': 73}, {'x': 87, 'y': 90}], 2611],
        [[{'x': 42, 'y': 32}, {'x': 54, 'y': 7}, {'x': 51, 'y': 42}, {'x': 14, 'y': 80}, {'x': 84, 'y': 24},
          {'x': 84, 'y': 51}, {'x': 82, 'y': 91}], -1058.5],
        [[{'x': 48, 'y': 48}, {'x': 49, 'y': 49}, {'x': 15, 'y': 22}, {'x': 84, 'y': 39}, {'x': 81, 'y': 33}], -498.5],
        [[{'x': 56, 'y': 64}, {'x': 83, 'y': 21}, {'x': 21, 'y': 58}, {'x': 33, 'y': 44}, {'x': 42, 'y': 24},
          {'x': 92, 'y': 36}], -683.5],
        [[{'x': 60, 'y': 50}, {'x': 33, 'y': 30}, {'x': 80, 'y': 10}, {'x': 44, 'y': 65}, {'x': 56, 'y': 99},
          {'x': 51, 'y': 57}, {'x': 84, 'y': 61}, {'x': 72, 'y': 30}, {'x': 95, 'y': 1}, {'x': 16, 'y': 38},
          {'x': 10, 'y': 7}, {'x': 25, 'y': 50}, {'x': 47, 'y': 2}, {'x': 84, 'y': 96}, {'x': 31, 'y': 81}], -792.5],
        [[{'x': 52, 'y': 47}, {'x': 99, 'y': 7}, {'x': 36, 'y': 58}, {'x': 57, 'y': 46}], 81],
        [[{'x': 60, 'y': 31}, {'x': 19, 'y': 3}, {'x': 4, 'y': 6}, {'x': 19, 'y': 52}], 1372],
        [[{'x': 91, 'y': 51}, {'x': 14, 'y': 4}, {'x': 58, 'y': 22}, {'x': 97, 'y': 38}], -642.5],
        [[{'x': 83, 'y': 58}, {'x': 14, 'y': 24}, {'x': 11, 'y': 12}, {'x': 12, 'y': 47}], 874],
        [[{'x': 97, 'y': 70}, {'x': 85, 'y': 72}, {'x': 90, 'y': 41}, {'x': 79, 'y': 61}], 48.5],
        [[{'x': 21, 'y': 37}, {'x': 61, 'y': 23}, {'x': 47, 'y': 57}, {'x': 56, 'y': 80}], -791],
        [[{'x': 45, 'y': 94}, {'x': 93, 'y': 35}, {'x': 79, 'y': 20}, {'x': 29, 'y': 87}], 1484],
        [[{'x': 13, 'y': 2}, {'x': 49, 'y': 77}, {'x': 30, 'y': 89}, {'x': 37, 'y': 95}], -675],
        [[{'x': 19, 'y': 47}, {'x': 86, 'y': 3}, {'x': 62, 'y': 70}, {'x': 74, 'y': 72}], -1621.5],
        [[{'x': 67, 'y': 15}, {'x': 35, 'y': 39}, {'x': 23, 'y': 14}, {'x': 39, 'y': 59}], 438],
        [[{'x': 61, 'y': 84}, {'x': 52, 'y': 50}, {'x': 18, 'y': 33}, {'x': 64, 'y': 82}], 382],
        [[{'x': 37, 'y': 15}, {'x': 33, 'y': 54}, {'x': 92, 'y': 62}, {'x': 95, 'y': 33}], 2034.5],
        [[{'x': 65, 'y': 4}, {'x': 29, 'y': 92}, {'x': 82, 'y': 49}, {'x': 37, 'y': 10}], 877],
        [[{'x': 41, 'y': 68}, {'x': 69, 'y': 84}, {'x': 89, 'y': 83}, {'x': 1, 'y': 13}], 1194],
        [[{'x': 68, 'y': 23}, {'x': 53, 'y': 66}, {'x': 26, 'y': 86}, {'x': 63, 'y': 92}], 861],
        [[{'x': 90, 'y': 56}, {'x': 31, 'y': 72}, {'x': 57, 'y': 78}, {'x': 29, 'y': 62}], -187],
        [[{'x': 41, 'y': 36}, {'x': 38, 'y': 21}, {'x': 33, 'y': 96}, {'x': 59, 'y': 79}], 862],
        [[{'x': 69, 'y': 31}, {'x': 36, 'y': 71}, {'x': 21, 'y': 36}, {'x': 63, 'y': 1}], -1612.5],
        [[{'x': 75, 'y': 13}, {'x': 57, 'y': 84}, {'x': 10, 'y': 18}, {'x': 82, 'y': 8}], -2407.5],
        [[{'x': 14, 'y': 27}, {'x': 10, 'y': 69}, {'x': 27, 'y': 32}, {'x': 11, 'y': 78}], -56]]


@pytest.mark.parametrize(['polygon', 'expected'], data)
def test_polygon_area_rnd(polygon, expected):
    poly = Polygon(*(Point(p['x'], p['y']) for p in polygon))
    value = polygon_area(poly)

    assert expected == value


def test_nfp():
    B = Polygon(Point(0, 0), Point(1, 0), Point(0.5, 0.5), Point(0, 0))
    nfp = no_fit_polygon(SQUARE2x2, B, False, True)

    assert len(nfp) == 1
    assert nfp[0].almost_equal(
        Polygon(Point(-0.5, -0.5), Point(1.5, -0.5), Point(2.0, 0.0), Point(2.0, 2.0), Point(0.0, 2.0),
                Point(-1.0, 2.0), Point(-1.0, 0.0)))

    nfp2 = no_fit_polygon_rectangle(RECT4x2, B)
    assert len(nfp2) == 1
    assert nfp2[0].almost_equal(Polygon(Point(0, 0), Point(3, 0), Point(3, 1.5), Point(0, 1.5)))
    # plot([RECT4x2, *nfp2, B], [])


def test_nfp_2():
    A = Polygon.from_list_dict([{"x": 106, "y": 125}, {"x": 0.0, "y": 125}, {"x": 0.0, "y": 0.0}, {"x": 106, "y": 0.0}])
    B = Polygon.from_list_dict([{"x": -117, "y": 106}, {"x": -117, "y": 87}, {"x": -99, "y": 87}, {"x": -99, "y": 106}])

    nfp = no_fit_polygon(A, B, True, True)

    expected = [
        Polygon.from_list_dict([{"x": 88, "y": 125}, {"x": 88, "y": 19}, {"x": 0, "y": 19}, {"x": 0, "y": 125}])]

    # plot([A, B, expected[0]])

    assert nfp == expected


def test_search_start_point():
    A = Polygon.from_list_dict([{"x": 106, "y": 125}, {"x": 0.0, "y": 125}, {"x": 0.0, "y": 0.0}, {"x": 106, "y": 0.0}])
    B = Polygon.from_list_dict([{"x": -117, "y": 106}, {"x": -117, "y": 87}, {"x": -99, "y": 87}, {"x": -99, "y": 106}])

    start_point = search_start_point(A, B, True)

    expected = Point(205.0, 19.0)

    assert expected == start_point


def test_intersect():
    A = Polygon.from_list_dict([{"x": 106, "y": 125}, {"x": 0.0, "y": 125}, {"x": 0.0, "y": 0.0}, {"x": 106, "y": 0.0}])
    B = Polygon.from_list_dict([{"x": -117, "y": 106}, {"x": -117, "y": 87}, {"x": -99, "y": 87}, {"x": -99, "y": 106}])
    B.offsetx = 205
    B.offsety = 19

    intersect_A_B = intersect(A, B)

    expected = False

    assert expected == intersect_A_B


def test_is_rectangle():
    assert is_rectangle(RECT4x2, 0.001)
    assert is_rectangle(SQUARE2x2, 0.001)


