import pytest

from svgnest.js.display import plot
from svgnest.js.geometry import Point, Polygon, Vector
from svgnest.js.geometryutil import rotate_polygon, normalize_vector, point_in_polygon, polygon_area, intersect, \
    no_fit_polygon, no_fit_polygon_rectangle, is_rectangle


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


def test_is_rectangle():
    assert is_rectangle(RECT4x2, 0.001)
    assert is_rectangle(SQUARE2x2, 0.001)
