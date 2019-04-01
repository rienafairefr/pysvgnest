from svgnest.js.display import plot
from svgnest.js.geometry import Polygon
from svgnest.js.svgnest import minkowski_difference


def test_minkowski():
    A = Polygon.from_list_dict([{"x": -109, "y": 126}, {"x": -109, "y": 119},
                                {"x": -98, "y": 119}, {"x": -98, "y": 126}])
    B = Polygon.from_list_dict([{"x": 75, "y": 105}, {"x": 62, "y": 113}, {"x": 53, "y": 107},
                                {"x": 59, "y": 98}])

    expected = [Polygon.from_list_dict([{"x": -109, "y": 126}, {"x": -109, "y": 119},
                                        {"x": -96, "y": 111}, {"x": -85, "y": 111},
                                        {"x": -76, "y": 117}, {"x": -76, "y": 124},
                                        {"x": -82, "y": 133},
                                        {"x": -93, "y": 133}])]

    value = minkowski_difference(A, B)

    plot([A, B, expected[0]])

    assert expected == value
