import math

TOL = pow(10, -9)  # Floating point error is likely to be above 1 epsilon


def almost_equal(a, b, tolerance=TOL):
    if a is None and b is None: return True
    return abs(a - b) < tolerance


def within_distance(p1, p2, distance):
    dx = p1.x - p2.x
    dy = p1.y - p2.y
    return (dx * dx + dy * dy) < distance * distance


def degrees_to_radians(angle):
    return angle * math.pi / 180


def radians_to_degrees(angle):
    return angle * 180 / math.pi


def on_segment(A, B, p):
    # vertical line
    if almost_equal(A.x, B.x) and almost_equal(p.x, A.x):
        if not almost_equal(p.y, B.y) and not almost_equal(p.y, A.y) and max(B.y, A.y) > p.y > min(B.y, A.y):
            return True
        else:
            return False

    # horizontal line
    if almost_equal(A.y, B.y) and almost_equal(p.y, A.y):
        if not almost_equal(p.x, B.x) and not almost_equal(p.x, A.x) and max(B.x, A.x) > p.x > min(B.x, A.x):
            return True
        else:
            return False

    # range check
    if (p.x < A.x and p.x < B.x) or (p.x > A.x and p.x > B.x) or (p.y < A.y and p.y < B.y) or (p.y > A.y and p.y > B.y):
        return False

    # exclude end points
    if (almost_equal(p.x, A.x) and almost_equal(p.y, A.y)) or (almost_equal(p.x, B.x) and almost_equal(p.y, B.y)):
        return False

    cross = (p.y - A.y) * (B.x - A.x) - (p.x - A.x) * (B.y - A.y)

    if abs(cross) > TOL:
        return False

    dot = (p.x - A.x) * (B.x - A.x) + (p.y - A.y) * (B.y - A.y)

    if dot < 0 or almost_equal(dot, 0):
        return False

    len2 = (B.x - A.x) * (B.x - A.x) + (B.y - A.y) * (B.y - A.y)

    if dot > len2 or almost_equal(dot, len2):
        return False

    return True
