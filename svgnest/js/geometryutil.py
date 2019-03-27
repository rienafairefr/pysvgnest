"""
General purpose geometry functions for polygon/Bezier calculations
Copyright 2015 Jack Qiao
Licensed under the MIT license
"""
import math

from svgnest.js.geometry import Segment, Point, Arc, PolygonBound, Vector, Polygon
from svgnest.js.utils import splice, log

TOL = pow(10, -9)  # Floating point error is likely to be above 1 epsilon


def _almost_equal(a, b, tolerance=TOL):
    return abs(a - b) < tolerance


def _within_distance(p1, p2, distance):
    dx = p1.x - p2.x
    dy = p1.y - p2.y
    return (dx * dx + dy * dy) < distance * distance


def _degrees_to_radians(angle):
    return angle * math.pi / 180


def _radians_to_degrees(angle):
    return angle * 180 / math.pi


# normalize vector into a unit vector
def _normalize_vector(v):
    if _almost_equal(v.x * v.x + v.y * v.y, 1):
        return v  # given vector was already a unit vector
    len = math.sqrt(v.x * v.x + v.y * v.y)
    inverse = 1 / len

    return Point(x= v.x * inverse, y= v.y * inverse)


# returns True if p lies on the line segment defined by AB, but not at any endpoints
# may need work!
def _on_segment(A, B, p):
    # vertical line
    if _almost_equal(A.x, B.x) and _almost_equal(p.x, A.x):
        if not _almost_equal(p.y, B.y) and not _almost_equal(p.y, A.y) and max(B.y, A.y) > p.y > min(B.y, A.y):
            return True
        else:
            return False

    # horizontal line
    if _almost_equal(A.y, B.y) and _almost_equal(p.y, A.y):
        if not _almost_equal(p.x, B.x) and not _almost_equal(p.x, A.x) and max(B.x, A.x) > p.x > min(B.x, A.x):
            return True
        else:
            return False

    # range check
    if (p.x < A.x and p.x < B.x) or (p.x > A.x and p.x > B.x) or (p.y < A.y and p.y < B.y) or (p.y > A.y and p.y > B.y):
        return False

    # exclude end points
    if (_almost_equal(p.x, A.x) and _almost_equal(p.y, A.y)) or (_almost_equal(p.x, B.x) and _almost_equal(p.y, B.y)):
        return False

    cross = (p.y - A.y) * (B.x - A.x) - (p.x - A.x) * (B.y - A.y)

    if abs(cross) > TOL:
        return False

    dot = (p.x - A.x) * (B.x - A.x) + (p.y - A.y) * (B.y - A.y)

    if dot < 0 or _almost_equal(dot, 0):
        return False

    len2 = (B.x - A.x) * (B.x - A.x) + (B.y - A.y) * (B.y - A.y)

    if dot > len2 or _almost_equal(dot, len2):
        return False

    return True


# returns the intersection of AB and EF
# or None if there are no intersections or other numerical error
# if the infinite flag is set, AE and EF describe infinite lines without endpoints,
# they are finite line segments otherwise
def _line_intersect(A, B, E, F, infinite):
    a1, a2, b1, b2, c1, c2, x, y = 0, 0, 0, 0, 0, 0, 0, 0

    a1 = B.y - A.y
    b1 = A.x - B.x
    c1 = B.x * A.y - A.x * B.y
    a2 = F.y - E.y
    b2 = E.x - F.x
    c2 = F.x * E.y - E.x * F.y

    denom = a1 * b2 - a2 * b1

    x = (b1 * c2 - b2 * c1) / denom
    y = (a2 * c1 - a1 * c2) / denom

    if not math.isfinite(x) or not math.isfinite(y):
        return None

    # lines are colinear
    # var crossABE = (E.y - A.y) * (B.x - A.x) - (E.x - A.x) * (B.y - A.y)
    # var crossABF = (F.y - A.y) * (B.x - A.x) - (F.x - A.x) * (B.y - A.y)
    # if(_almostEqual(crossABE,0) and _almostEqual(crossABF,0)){
    # 	return None
    # }*/

    if not infinite:
        # coincident points do not count as intersecting
        if abs(A.x - B.x) > TOL and ((x < A.x or x > B.x) if (A.x < B.x) else (x > A.x or x < B.x)):
            return None
        if abs(A.y - B.y) > TOL and ((y < A.y or y > B.y) if (A.y < B.y) else (y > A.y or y < B.y)):
            return None

        if abs(E.x - F.x) > TOL and ((x < E.x or x > F.x) if (E.x < F.x) else (x > E.x or x < F.x)):
            return None
        if abs(E.y - F.y) > TOL and ((y < E.y or y > F.y) if (E.y < F.y) else (y > E.y or y < F.y)):
            return None

    return {'x': x, 'y': y}


class GeometryUtil:

    @staticmethod
    def almostEqual(a, b, tolerance=TOL):
        return _almost_equal(a, b, tolerance)

    @staticmethod
    def withinDistance(p1, p2, distance):
        return _within_distance(p1, p2, distance)

    @staticmethod
    def degreesToRadians(angle):
        return _degrees_to_radians(angle)

    @staticmethod
    def radiansToDegrees(angle):
        return _radians_to_degrees(angle)

    @staticmethod
    def normalizeVector(v):
        return _normalize_vector(v)


class QuadraticBezier:

    # Roger Willcocks bezier flatness criterion
    @staticmethod
    def is_flat(p1, p2, c1, tol):
        tol = 4 * tol * tol

        ux = 2 * c1.x - p1.x - p2.x
        ux *= ux

        uy = 2 * c1.y - p1.y - p2.y
        uy *= uy

        return ux + uy <= tol

    # turn Bezier into line segments via de Casteljau, returns an array of points
    @classmethod
    def linearize(cls, p1, p2, c1, tol):
        finished = [p1]  # list of points to return
        todo = [{p1: p1, p2: p2, c1: c1}]  # list of Beziers to divide

        # recursion could stack overflow, loop instead
        while len(todo) > 0:
            segment = todo[0]

            if cls.is_flat(segment.p1, segment.p2, segment.c1, tol):  # reached subdivision limit
                finished.append(Point(x=segment.p2.x, y=segment.p2.y))
                todo.shift()
            else:
                divided = cls.subdivide(segment.p1, segment.p2, segment.c1, 0.5)
                todo.splice(0, 1, divided[0], divided[1])
        return finished

    # subdivide a single Bezier
    # t is the percent along the Bezier to divide at. eg. 0.5
    @staticmethod
    def subdivide(p1, p2, c1, t):
        mid1 = Point(
            x=p1.x + (c1.x - p1.x) * t,
            y=p1.y + (c1.y - p1.y) * t
        )

        mid2 = Point(
            x=c1.x + (p2.x - c1.x) * t,
            y=c1.y + (p2.y - c1.y) * t
        )

        mid3 = Point(
            x=mid1.x + (mid2.x - mid1.x) * t,
            y=mid1.y + (mid2.y - mid1.y) * t
        )

        seg1 = Segment(p1=p1, p2=mid3, c1=mid1)
        seg2 = Segment(p1=mid3, p2=p2, c1=mid2)

        return [seg1, seg2]


class CubicBezier:
    @classmethod
    def is_flat(cls, p1, p2, c1, c2, tol):
        tol = 16 * tol * tol

        ux = 3 * c1.x - 2 * p1.x - p2.x
        ux *= ux

        uy = 3 * c1.y - 2 * p1.y - p2.y
        uy *= uy

        vx = 3 * c2.x - 2 * p2.x - p1.x
        vx *= vx

        vy = 3 * c2.y - 2 * p2.y - p1.y
        vy *= vy

        if ux < vx:
            ux = vx
        if uy < vy:
            uy = vy

        return ux + uy <= tol

    @classmethod
    def linearize(cls, p1, p2, c1, c2, tol):
        finished = [p1]  # list of points to return
        todo = [Segment(p1=p1, p2=p2, c1=c1, c2=c2)]  # list of Beziers to divide

        # recursion could stack overflow, loop instead

        while len(todo) > 0:
            log('linearizing bezier... %s' % len(todo))
            segment = todo[0]

            if cls.is_flat(segment.p1, segment.p2, segment.c1, segment.c2, tol):  # reached subdivision limit
                finished.append(Point(x=segment.p2.x, y=segment.p2.y))
                todo.pop(0)
            else:
                divided = cls.subdivide(segment.p1, segment.p2, segment.c1, segment.c2, 0.5)
                splice(todo, 0, 1, divided[0], divided[1])
        return finished

    @classmethod
    def subdivide(cls, p1, p2, c1, c2, t):
        mid1 = Point(
            x=p1.x + (c1.x - p1.x) * t,
            y=p1.y + (c1.y - p1.y) * t
        )

        mid2 = Point(
            x=c2.x + (p2.x - c2.x) * t,
            y=c2.y + (p2.y - c2.y) * t
        )

        mid3 = Point(
            x=c1.x + (c2.x - c1.x) * t,
            y=c1.y + (c2.y - c1.y) * t
        )

        mida = Point(
            x=mid1.x + (mid3.x - mid1.x) * t,
            y=mid1.y + (mid3.y - mid1.y) * t
        )

        midb = Point(
            x=mid3.x + (mid2.x - mid3.x) * t,
            y=mid3.y + (mid2.y - mid3.y) * t
        )

        midx = Point(
            x=mida.x + (midb.x - mida.x) * t,
            y=mida.y + (midb.y - mida.y) * t
        )

        seg1 = Segment(p1=p1, p2=midx, c1=mid1, c2=mida)
        seg2 = Segment(p1=midx, p2=p2, c1=midb, c2=mid2)

        return [seg1, seg2]


class Arc:
    def linearize(self, p1, p2, rx, ry, angle, largearc, sweep, tol):

        finished = [p2]  # list of points to return

        arc = self.svgToCenter(p1, p2, rx, ry, angle, largearc, sweep)
        todo = [arc]  # list of arcs to divide

        # recursion could stack overflow, loop instead
        while len(todo) > 0:
            arc = todo[0]

            fullarc = self.center_to_svg(arc.center, arc.rx, arc.ry, arc.theta, arc.extent, arc.angle)
            subarc = self.center_to_svg(arc.center, arc.rx, arc.ry, arc.theta, 0.5 * arc.extent, arc.angle)
            arcmid = subarc.p2

            mid = Point(
                x=0.5 * (fullarc.p1.x + fullarc.p2.x),
                y=0.5 * (fullarc.p1.y + fullarc.p2.y)
            )

            # compare midpoint of line with midpoint of arc
            # this is not 100% accurate, but should be a good heuristic for flatness in most cases
            if _within_distance(mid, arcmid, tol):
                finished.unshift(fullarc.p2)
                todo.shift()
            else:
                arc1 = Arc(
                    center=arc.center,
                    rx=arc.rx,
                    ry=arc.ry,
                    theta=arc.theta,
                    extent=0.5 * arc.extent,
                    angle=arc.angle
                )
                arc2 = Arc(
                    center=arc.center,
                    rx=arc.rx,
                    ry=arc.ry,
                    theta=arc.theta + 0.5 * arc.extent,
                    extent=0.5 * arc.extent,
                    angle=arc.angle
                )
                todo.splice(0, 1, arc1, arc2)
        return finished

    # convert from center point/angle sweep definition to SVG point and flag definition of arcs
    # ported from http://commons.oreilly.com/wiki/index.php/SVG_Essentials/Paths
    def center_to_svg(self, center, rx, ry, theta1, extent, angleDegrees):

        theta2 = theta1 + extent

        theta1 = _degrees_to_radians(theta1)
        theta2 = _degrees_to_radians(theta2)
        angle = _degrees_to_radians(angleDegrees)

        cos = math.cos(angle)
        sin = math.sin(angle)

        t1cos = math.cos(theta1)
        t1sin = math.sin(theta1)

        t2cos = math.cos(theta2)
        t2sin = math.sin(theta2)

        x0 = center.x + cos * rx * t1cos + (-sin) * ry * t1sin
        y0 = center.y + sin * rx * t1cos + cos * ry * t1sin

        x1 = center.x + cos * rx * t2cos + (-sin) * ry * t2sin
        y1 = center.y + sin * rx * t2cos + cos * ry * t2sin

        largearc = 1 if extent > 180 else 0
        sweep = 1 if extent > 0 else 0

        return {
            'p1': Point(x0, y0),
            'p2': Point(x1, y1),
            'rx': rx,
            'ry': ry,
            'angle': angle,
            'largearc': largearc,
            'sweep': sweep
        }

    # convert from SVG format arc to center point arc
    @classmethod
    def svgToCenter(cls, p1, p2, rx, ry, angleDegrees, largearc, sweep):

        mid = Point(
            x=0.5 * (p1.x + p2.x),
            y=0.5 * (p1.y + p2.y)
        )

        diff = Point(
            x=0.5 * (p2.x - p1.x),
            y=0.5 * (p2.y - p1.y)
        )

        angle = _degrees_to_radians(angleDegrees % 360)

        cos = math.cos(angle)
        sin = math.sin(angle)

        x1 = cos * diff.x + sin * diff.y
        y1 = -sin * diff.x + cos * diff.y

        rx = abs(rx)
        ry = abs(ry)
        Prx = rx * rx
        Pry = ry * ry
        Px1 = x1 * x1
        Py1 = y1 * y1

        radiiCheck = Px1 / Prx + Py1 / Pry
        radiiSqrt = math.sqrt(radiiCheck)
        if radiiCheck > 1:
            rx = radiiSqrt * rx
            ry = radiiSqrt * ry
            Prx = rx * rx
            Pry = ry * ry

        sign = -1 if (largearc != sweep) else 1
        sq = ((Prx * Pry) - (Prx * Py1) - (Pry * Px1)) / ((Prx * Py1) + (Pry * Px1))

        sq = 0 if sq < 0 else sq

        coef = sign * math.sqrt(sq)
        cx1 = coef * ((rx * y1) / ry)
        cy1 = coef * -((ry * x1) / rx)

        cx = mid.x + (cos * cx1 - sin * cy1)
        cy = mid.y + (sin * cx1 + cos * cy1)

        ux = (x1 - cx1) / rx
        uy = (y1 - cy1) / ry
        vx = (-x1 - cx1) / rx
        vy = (-y1 - cy1) / ry
        n = math.sqrt((ux * ux) + (uy * uy))
        p = ux
        sign = -1 if uy < 0 else 1

        theta = sign * math.acos(p / n)
        theta = _radians_to_degrees(theta)

        n = math.sqrt((ux * ux + uy * uy) * (vx * vx + vy * vy))
        p = ux * vx + uy * vy
        sign = -1 if ((ux * vy - uy * vx) < 0) else 1
        delta = sign * math.acos(p / n)
        delta = _radians_to_degrees(delta)

        if sweep == 1 and delta > 0:
            delta -= 360
        elif sweep == 0 and delta < 0:
            delta += 360

        delta %= 360
        theta %= 360

        return Arc(
            center=Point(x=cx, y=cy),
            rx=rx,
            ry=ry,
            theta=theta,
            extent=delta,
            angle=angleDegrees
        )


# returns the rectangular bounding box of the given polygon
def get_polygon_bounds(polygon):
    if not polygon or len(polygon) < 3:
        return None

    xmin = polygon[0].x
    xmax = polygon[0].x
    ymin = polygon[0].y
    ymax = polygon[0].y

    for point in polygon:
        if point.x > xmax:
            xmax = point.x
        elif point.x < xmin:
            xmin = point.x

        if point.y > ymax:
            ymax = point.y
        elif point.y < ymin:
            ymin = point.y

    return PolygonBound(
        x=xmin,
        y=ymin,
        width=xmax - xmin,
        height=ymax - ymin
    )


# return True if point is in the polygon, False if outside, and None if exactly on a point or edge
def point_in_polygon(point, polygon):
    if not polygon or len(polygon) < 3:
        return None

    inside = False
    offsetx = polygon.offsetx or 0
    offsety = polygon.offsety or 0

    i = 0
    j = len(polygon) - 1
    while True:
        if i >= len(polygon):
            break

        xi = polygon[i].x + offsetx
        yi = polygon[i].y + offsety
        xj = polygon[j].x + offsetx
        yj = polygon[j].y + offsety

        if _almost_equal(xi, point.x) and _almost_equal(yi, point.y):
            return None  # no result

        if _on_segment(Point(xi, yi), Point(xj, yj), point):
            return None  # exactly on the segment

        if _almost_equal(xi, xj) and _almost_equal(yi, yj):  # ignore very small lines
            i += 1
            j = i
            continue

        if ((yi > point.y) != (yj > point.y)) and (point.x < (xj - xi) * (point.y - yi) / (yj - yi) + xi):
            inside = not inside

        i += 1
        j = i

    return inside


# returns the area of the polygon, assuming no self-intersections
# a negative area indicates counter-clockwise winding direction
def polygon_area(polygon):
    area = 0
    i = 0
    j = len(polygon) - 1
    while True:
        if i >= len(polygon):
            break
        area += (polygon[j].x + polygon[i].x) * (polygon[j].y - polygon[i].y)
        i += 1
        j = i

    return 0.5 * area

    # todo: swap this for a more efficient sweep-line implementation
    # returnEdges: if set, return all edges on A that have intersections


def intersect(A, B):
    Aoffsetx = A.offsetx or 0
    Aoffsety = A.offsety or 0

    Boffsetx = B.offsetx or 0
    Boffsety = B.offsety or 0

    A = A[:]
    B = B[:]

    for i in range(0, len(A) - 1):
        for j in range(0, len(B) - 1):
            a1 = Point(A[i].x + Aoffsetx, A[i].y + Aoffsety)
            a2 = Point(A[i + 1].x + Aoffsetx, A[i + 1].y + Aoffsety)
            b1 = Point(B[j].x + Boffsetx, B[j].y + Boffsety)
            b2 = Point(B[j + 1].x + Boffsetx, B[j + 1].y + Boffsety)

            prevbindex = len(B) - 1 if j == 0 else j - 1
            prevaindex = len(A) - 1 if i == 0 else i - 1
            nextbindex = 0 if (j + 1 == len(B) - 1) else j + 2
            nextaindex = 0 if (i + 1 == len(A) - 1) else i + 2

            # go even further back if we happen to hit on a loop end point
            if B[prevbindex] == B[j] or (
                    _almost_equal(B[prevbindex].x, B[j].x) and _almost_equal(B[prevbindex].y, B[j].y)):
                prevbindex = B.length - 1 if (prevbindex == 0) else prevbindex - 1

            if A[prevaindex] == A[i] or (
                    _almost_equal(A[prevaindex].x, A[i].x) and _almost_equal(A[prevaindex].y, A[i].y)):
                prevaindex = A.length - 1 if (prevaindex == 0) else prevaindex - 1

            # go even further forward if we happen to hit on a loop end point
            if B[nextbindex] == B[j + 1] or (
                    _almost_equal(B[nextbindex].x, B[j + 1].x) and _almost_equal(B[nextbindex].y, B[j + 1].y)):
                nextbindex = 0 if (nextbindex == B.length - 1) else nextbindex + 1

            if A[nextaindex] == A[i + 1] or (
                    _almost_equal(A[nextaindex].x, A[i + 1].x) and _almost_equal(A[nextaindex].y, A[i + 1].y)):
                nextaindex = 0 if (nextaindex == A.length - 1) else nextaindex + 1

            a0 = Point(A[prevaindex].x + Aoffsetx, A[prevaindex].y + Aoffsety)
            b0 = Point(B[prevbindex].x + Boffsetx, B[prevbindex].y + Boffsety)

            a3 = Point(A[nextaindex].x + Aoffsetx, A[nextaindex].y + Aoffsety)
            b3 = Point(B[nextbindex].x + Boffsetx, B[nextbindex].y + Boffsety)

            if _on_segment(a1, a2, b1) or (_almost_equal(a1.x, b1.x) and _almost_equal(a1.y, b1.y)):
                # if a point is on a segment, it could intersect or it could not. Check via the neighboring points
                b0in = point_in_polygon(b0, A)
                b2in = point_in_polygon(b2, A)
                if (b0in and not b2in) or (not b0in and b2in):
                    return True
                else:
                    continue

            if _on_segment(a1, a2, b2) or (_almost_equal(a2.x, b2.x) and _almost_equal(a2.y, b2.y)):
                # if a point is on a segment, it could intersect or it could not. Check via the neighboring points
                b1in = point_in_polygon(b1, A)
                b3in = point_in_polygon(b3, A)

                if (b1in  and not b3in ) or (not b1in and b3in):
                    return True
                else:
                    continue

            if _on_segment(b1, b2, a1) or (_almost_equal(a1.x, b2.x) and _almost_equal(a1.y, b2.y)):
                # if a point is on a segment, it could intersect or it could not. Check via the neighboring points
                a0in = point_in_polygon(a0, B)
                a2in = point_in_polygon(a2, B)

                if (a0in and not a2in) or (not a0in and a2in):
                    return True
            else:
                continue

            if _on_segment(b1, b2, a2) or (_almost_equal(a2.x, b1.x) and _almost_equal(a2.y, b1.y)):
                # if a point is on a segment, it could intersect or it could not. Check via the neighboring points
                a1in = point_in_polygon(a1, B)
                a3in = point_in_polygon(a3, B)

                if (a1in and not a3in ) or (not a1in and a3in):
                    return True
                else:
                    continue

            p = _line_intersect(b1, b2, a1, a2)

            if p is not None:
                return True

    return False


# placement algos as outlined in [1] http://www.cs.stir.ac.uk/~goc/papers/EffectiveHueristic2DAOR2013.pdf

# returns a continuous polyline representing the normal-most edge of the given polygon
# eg. a normal vector of [-1, 0] will return the left-most edge of the polygon
# this is essentially algo 8 in [1], generalized for any vector direction
def polygon_edge(polygon, normal):
    if not polygon or len(polygon) < 3:
        return None

    normal = _normalize_vector(normal)

    direction = Point(
        x=-normal.y,
        y=normal.x
    )

    # find the max and min points, they will be the endpoints of our edge
    min = None
    max = None

    dotproduct = []

    for point in polygon:
        dot = point.x * direction.x + point.y * direction.y
        dotproduct.append(dot)
        if min is None or dot < min:
            min = dot
        if max is None or dot > max:
            max = dot

    # there may be multiple vertices with min/max values.
    # in which case we choose the one that is normal-most (eg. left most)
    indexmin = 0
    indexmax = 0

    normalmin = None
    normalmax = None

    for i, point in enumerate(polygon):
        if _almost_equal(dotproduct[i], min):
            dot = polygon[i].x * normal.x + point.y * normal.y
            if (normalmin is None or dot > normalmin):
                normalmin = dot
                indexmin = i
        elif _almost_equal(dotproduct[i], max):
            dot = polygon[i].x * normal.x + point.y * normal.y
            if (normalmax is None or dot > normalmax):
                normalmax = dot
                indexmax = i

    # now we have two edges bound by min and max points, figure out which edge faces our direction vector

    indexleft = indexmin - 1
    indexright = indexmin + 1

    if indexleft < 0:
        indexleft = len(polygon) - 1
    if indexright >= polygon.length:
        indexright = 0

    minvertex = polygon[indexmin]
    left = polygon[indexleft]
    right = polygon[indexright]

    leftvector = Vector(
        x=left.x - minvertex.x,
        y=left.y - minvertex.y
    )

    rightvector = Vector(
        x=right.x - minvertex.x,
        y=right.y - minvertex.y
    )

    dotleft = leftvector.x * direction.x + leftvector.y * direction.y
    dotright = rightvector.x * direction.x + rightvector.y * direction.y

    # -1 = left, 1 = right
    scandirection = -1

    if _almost_equal(dotleft, 0):
        scandirection = 1
    elif _almost_equal(dotright, 0):
        scandirection = -1
    else:
        normaldotleft = None
        normaldotright = None

        if _almost_equal(dotleft, dotright):
            # the points line up exactly along the normal vector
            normaldotleft = leftvector.x * normal.x + leftvector.y * normal.y
            normaldotright = rightvector.x * normal.x + rightvector.y * normal.y
        elif dotleft < dotright:
            # normalize right vertex so normal projection can be directly compared
            normaldotleft = leftvector.x * normal.x + leftvector.y * normal.y
            normaldotright = (rightvector.x * normal.x + rightvector.y * normal.y) * (dotleft / dotright)
        else:
            # normalize left vertex so normal projection can be directly compared
            normaldotleft = leftvector.x * normal.x + leftvector.y * normal.y * (dotright / dotleft)
            normaldotright = rightvector.x * normal.x + rightvector.y * normal.y

        if normaldotleft > normaldotright:
            scandirection = -1
        else:
            # technically they could be equal, (ie. the segments bound by left and right points are incident)
            # in which case we'll have to climb up the chain until lines are no longer incident
            # for now we'll just not handle it and assume people aren't giving us garbage input..
            scandirection = 1

    # connect all points between indexmin and indexmax along the scan direction
    edge = []
    count = 0
    i = indexmin
    while count < len(polygon):
        if i >= len(polygon):
            i = 0
        elif i < 0:
            i = len(polygon) - 1

        edge.append(polygon[i])

        if i == indexmax:
            break
        i += scandirection
        count += 1

    return edge


# returns the normal distance from p to a line segment defined by s1 s2
# this is basically algo 9 in [1], generalized for any vector direction
# eg. normal of [-1, 0] returns the horizontal distance between the point and the line segment
# sxinclusive: if True, include endpoints instead of excluding them
def point_line_distance(p, s1, s2, normal, s1inclusive, s2inclusive):
    normal = _normalize_vector(normal)

    dir = Vector(
        x=normal.y,
        y=-normal.x
    )

    pdot = p.x * dir.x + p.y * dir.y
    s1dot = s1.x * dir.x + s1.y * dir.y
    s2dot = s2.x * dir.x + s2.y * dir.y

    pdotnorm = p.x * normal.x + p.y * normal.y
    s1dotnorm = s1.x * normal.x + s1.y * normal.y
    s2dotnorm = s2.x * normal.x + s2.y * normal.y

    # point is exactly along the edge in the normal direction
    if _almost_equal(pdot, s1dot) and _almost_equal(pdot, s2dot):
        # point lies on an endpoint
        if _almost_equal(pdotnorm, s1dotnorm):
            return None

        if _almost_equal(pdotnorm, s2dotnorm):
            return None

        # point is outside both endpoints
        if pdotnorm > s1dotnorm and pdotnorm > s2dotnorm:
            return min(pdotnorm - s1dotnorm, pdotnorm - s2dotnorm)
        if pdotnorm < s1dotnorm and pdotnorm < s2dotnorm:
            return -min(s1dotnorm - pdotnorm, s2dotnorm - pdotnorm)

        # point lies between endpoints
        diff1 = pdotnorm - s1dotnorm
        diff2 = pdotnorm - s2dotnorm
        if diff1 > 0:
            return diff1
        else:
            return diff2
    # point
    elif _almost_equal(pdot, s1dot):
        if s1inclusive:
            return pdotnorm - s1dotnorm
        else:
            return None
    elif _almost_equal(pdot, s2dot):
        if s2inclusive:
            return pdotnorm - s2dotnorm
        else:
            return None
    elif (pdot < s1dot and pdot < s2dot) or (pdot > s1dot and pdot > s2dot):
        return None  # point doesn't collide with segment

    return pdotnorm - s1dotnorm + (s1dotnorm - s2dotnorm) * (s1dot - pdot) / (s1dot - s2dot)


def point_distance(p, s1, s2, normal, infinite=None):
    normal = _normalize_vector(normal)

    dir = Vector(
        x=normal.y,
        y=-normal.x
    )

    pdot = p.x * dir.x + p.y * dir.y
    s1dot = s1.x * dir.x + s1.y * dir.y
    s2dot = s2.x * dir.x + s2.y * dir.y

    pdotnorm = p.x * normal.x + p.y * normal.y
    s1dotnorm = s1.x * normal.x + s1.y * normal.y
    s2dotnorm = s2.x * normal.x + s2.y * normal.y

    if not infinite:
        if ((pdot < s1dot or _almost_equal(pdot, s1dot)) and (pdot < s2dot or _almost_equal(pdot, s2dot))) or (
                (pdot > s1dot or _almost_equal(pdot, s1dot)) and (pdot > s2dot or _almost_equal(pdot, s2dot))):
            return None  # dot doesn't collide with segment, or lies directly on the vertex
        if (_almost_equal(pdot, s1dot) and _almost_equal(pdot, s2dot)) and (
                pdotnorm > s1dotnorm and pdotnorm > s2dotnorm):
            return min(pdotnorm - s1dotnorm, pdotnorm - s2dotnorm)
        if (_almost_equal(pdot, s1dot) and _almost_equal(pdot, s2dot)) and (
                pdotnorm < s1dotnorm and pdotnorm < s2dotnorm):
            return -min(s1dotnorm - pdotnorm, s2dotnorm - pdotnorm)

    return -(pdotnorm - s1dotnorm + (s1dotnorm - s2dotnorm) * (s1dot - pdot) / (s1dot - s2dot))


def segment_distance(A, B, E, F, direction):
    normal = Vector(
        x=direction.y,
        y=-direction.x
    )

    reverse = Vector(
        x=-direction.x,
        y=-direction.y
    )

    dotA = A.x * normal.x + A.y * normal.y
    dotB = B.x * normal.x + B.y * normal.y
    dotE = E.x * normal.x + E.y * normal.y
    dotF = F.x * normal.x + F.y * normal.y

    crossA = A.x * direction.x + A.y * direction.y
    crossB = B.x * direction.x + B.y * direction.y
    crossE = E.x * direction.x + E.y * direction.y
    crossF = F.x * direction.x + F.y * direction.y

    ABmin = min(dotA, dotB)
    ABmax = max(dotA, dotB)

    EFmax = max(dotE, dotF)
    EFmin = min(dotE, dotF)

    # segments that will merely touch at one point
    if _almost_equal(ABmax, EFmin, TOL) or _almost_equal(ABmin, EFmax, TOL):
        return None
    # segments miss eachother completely
    if ABmax < EFmin or ABmin > EFmax:
        return None

    if (ABmax > EFmax and ABmin < EFmin) or (EFmax > ABmax and EFmin < ABmin):
        overlap = 1
    else:
        minMax = min(ABmax, EFmax)
        maxMin = max(ABmin, EFmin)

        maxMax = max(ABmax, EFmax)
        minMin = min(ABmin, EFmin)

        overlap = (minMax - maxMin) / (maxMax - minMin)

    crossABE = (E.y - A.y) * (B.x - A.x) - (E.x - A.x) * (B.y - A.y)
    crossABF = (F.y - A.y) * (B.x - A.x) - (F.x - A.x) * (B.y - A.y)

    # lines are colinear
    if _almost_equal(crossABE, 0) and _almost_equal(crossABF, 0):

        ABnorm = Vector(B.y - A.y, A.x - B.x)
        EFnorm = Vector(F.y - E.y, E.x - F.x)

        ABnormlength = math.sqrt(ABnorm.x * ABnorm.x + ABnorm.y * ABnorm.y)
        ABnorm.x /= ABnormlength
        ABnorm.y /= ABnormlength

        EFnormlength = math.sqrt(EFnorm.x * EFnorm.x + EFnorm.y * EFnorm.y)
        EFnorm.x /= EFnormlength
        EFnorm.y /= EFnormlength

        # segment normals must point in opposite directions
        if abs(ABnorm.y * EFnorm.x - ABnorm.x * EFnorm.y) < TOL and ABnorm.y * EFnorm.y + ABnorm.x * EFnorm.x < 0:
            # normal of AB segment must point in same direction as given direction vector
            normdot = ABnorm.y * direction.y + ABnorm.x * direction.x
            # the segments merely slide along eachother
            if _almost_equal(normdot, 0, TOL):
                return None
            if normdot < 0:
                return 0
        return None

    distances = []

    # coincident points
    if _almost_equal(dotA, dotE):
        distances.push(crossA - crossE)
    elif _almost_equal(dotA, dotF):
        distances.push(crossA - crossF)
    elif EFmin < dotA < EFmax:
        d = point_distance(A, E, F, reverse)
        # A currently touches EF, but AB is moving away from EF
        if d is not None and GeometryUtil.almostEqual(d, 0):
            dB = point_distance(B, E, F, reverse, True)
            if dB < 0 or _almost_equal(dB * overlap, 0):
                d = None
        if d is not None:
            distances.append(d)

    if _almost_equal(dotB, dotE):
        distances.append(crossB - crossE)
    elif _almost_equal(dotB, dotF):
        distances.append(crossB - crossF)
    elif EFmin < dotB < EFmax:
        d = point_distance(B, E, F, reverse)

        # crossA>crossB A currently touches EF, but AB is moving away from EF
        if d is not None and _almost_equal(d, 0):
            dA = point_distance(A, E, F, reverse, True)
            if dA < 0 or _almost_equal(dA * overlap, 0):
                d = None
        if d is not None:
            distances.append(d)

    if ABmin < dotE < ABmax:
        d = point_distance(E, A, B, direction)
        # crossF<crossE A currently touches EF, but AB is moving away from EF
        if d is not None and _almost_equal(d, 0):
            dF = point_distance(F, A, B, direction, True)
            if dF < 0 or _almost_equal(dF * overlap, 0):
                d = None
        if d is not None:
            distances.append(d)

    if ABmin < dotF < ABmax:
        d = point_distance(F, A, B, direction)
        # and crossE<crossF A currently touches EF, but AB is moving away from EF
        if d is not None and _almost_equal(d,0):
            dE = point_distance(E, A, B, direction, True)
            if dE < 0 or _almost_equal(dE * overlap, 0):
                d = None
        if d is not None:
            distances.append(d)

    if len(distances) == 0:
        return None

    return min(distances)


def polygon_slide_distance(A, B, direction, ignoreNegative):
    Aoffsetx = A.offsetx or 0
    Aoffsety = A.offsety or 0

    Boffsetx = B.offsetx or 0
    Boffsety = B.offsety or 0

    A = A.slice(0)
    B = B.slice(0)

    # close the loop for polygons
    if A[0] != A[A.length - 1]:
        A.append(A[0])

    if B[0] != B[B.length - 1]:
        B.append(B[0])

    edgeA = A
    edgeB = B

    distance = None

    dir = _normalize_vector(direction)

    normal = Vector(
        x=dir.y,
        y=-dir.x
    )

    reverse = Vector(
        x=-dir.x,
        y=-dir.y,
    )

    for i in range(0, len(edgeB)):
        mind = None
        for j in range(0, len(edgeA) - 1):
            A1 = Point(edgeA[j].x + Aoffsetx, edgeA[j].y + Aoffsety)
            A2 = Point(edgeA[j + 1].x + Aoffsetx, edgeA[j + 1].y + Aoffsety)
            B1 = Point(edgeB[i].x + Boffsetx, edgeB[i].y + Boffsety)
            B2 = Point(edgeB[i + 1].x + Boffsetx, edgeB[i + 1].y + Boffsety)

            if (_almost_equal(A1.x, A2.x) and _almost_equal(A1.y, A2.y)) or (
                    _almost_equal(B1.x, B2.x) and _almost_equal(B1.y, B2.y)):
                continue  # ignore extremely small lines

            d = segment_distance(A1, A2, B1, B2, dir)

            if d is not None and (distance is None or d < distance):
                if not ignoreNegative or d > 0 or _almost_equal(d, 0):
                    distance = d
    return distance


# project each point of B onto A in the given direction, and return the
def polygon_projection_distance(A, B, direction):
    Boffsetx = B.offsetx or 0
    Boffsety = B.offsety or 0

    Aoffsetx = A.offsetx or 0
    Aoffsety = A.offsety or 0

    A = A[:]
    B = B[:]

    # close the loop for polygons
    if A[0] != A[-1]:
        A.append(A[0])

    if B[0] != B[-1]:
        B.append(B[0])

    edgeA = A
    edgeB = B

    distance = None
    p, d, s1, s2 = None, None, None, None

    for i in range(0, len(edgeB)-1):
        # the shortest/most negative projection of B onto A
        minprojection = None
        for j in range(0, len(edgeA)-1):
            p = Point(edgeB[i].x + Boffsetx, edgeB[i].y + Boffsety)
            s1 = Point(edgeA[j].x + Aoffsetx, edgeB[i].y + Aoffsety)
            s2 = Point(edgeA[j + 1].x + Aoffsetx, edgeA[j + 1].y + Aoffsety)

            if abs((s2.y - s1.y) * direction.x - (s2.x - s1.x) * direction.y) < TOL:
                continue

            # project point, ignore edge boundaries
            d = point_distance(p, s1, s2, direction)

            if d is not None and (minprojection is None or d < minprojection):
                minprojection = d
        if minprojection is not None and (distance is None or minprojection > distance):
            distance = minprojection

    return distance


# searches for an arrangement of A and B such that they do not overlap
# if an NFP is given, only search for startpoints that have not already been traversed in the given NFP
def search_start_point(A, B, inside, NFP=None):
    # clone arrays
    A = Polygon(A[:])
    B = Polygon(B[:])

    # close the loop for polygons
    if A[0] != A[-1]:
        A.append(A[0])

    if B[0] != B[-1]:
        B.append(B[0])

    # returns True if point already exists in the given nfp
    def inNfp(p, nfp):
        if not nfp or len(nfp) == 0:
            return False

        for i in range(0, len(nfp)):
            for j in range(0, len(nfp[i])):
                if _almost_equal(p.x, nfp[i][j].x) and _almost_equal(p.y, nfp[i][j].y):
                    return True

        return False

    for i, a in enumerate(A):
        if not a.marked:
            a.marked = True
            for j in range(0, len(B)):
                B.offsetx = a.x - B[j].x
                B.offsety = a.y - B[j].y

                Binside = None
                for b in B:
                    inpoly = point_in_polygon(Point(b.x + B.offsetx, b.y + B.offsety), A)
                    if inpoly is not None:
                        Binside = inpoly
                        break

                if Binside is None:  # A and B are the same
                    return None

                startPoint = Point(B.offsetx, B.offsety)
                if ((Binside and inside) or (not Binside and not inside)) \
                        and not intersect(A, B) and not inNfp(startPoint, NFP):
                    return startPoint

                # slide B along vector
                vx = A[i + 1].x - a.x
                vy = A[i + 1].y - a.y

                d1 = polygon_projection_distance(A, B, Point(x=vx, y=vy))
                d2 = polygon_projection_distance(B, A, Point(x=-vx, y=-vy))

                d = None

                # todo: clean this up
                if d1 is None and d2 is None:
                    # nothin
                    pass
                elif d1 is None:
                    d = d2
                elif d2 is None:
                    d = d1
                else:
                    d = min(d1, d2)

                # only slide until no longer negative
                # todo: clean this up
                if d is not None and not _almost_equal(d, 0) and d > 0:
                    pass
                else:
                    continue

                vd2 = vx * vx + vy * vy

                if d * d < vd2 and not _almost_equal(d * d, vd2):
                    vd = math.sqrt(vx * vx + vy * vy)
                    vx *= d / vd
                    vy *= d / vd

                B.offsetx += vx
                B.offsety += vy

                for k in range(0, len(B)):
                    inpoly = point_in_polygon(Point(B[k].x + B.offsetx, B[k].y + B.offsety), A)
                    if inpoly is not None:
                        Binside = inpoly
                        break
                startPoint = Point(B.offsetx, B.offsety)
                if ((Binside and inside) or (not Binside and not inside)) \
                        and not intersect(A, B) and not inNfp(startPoint, NFP):
                    return startPoint

    return None


def is_rectangle(poly, tolerance=None):
    bb = get_polygon_bounds(poly)
    tolerance = tolerance or TOL

    for i in range(0, len(poly)):
        if not _almost_equal(poly[i].x, bb.x, tolerance=tolerance) and not _almost_equal(poly[i].x, bb.x + bb.width,
                                                                                         tolerance=tolerance):
            return False
        if not _almost_equal(poly[i].y, bb.y, tolerance=tolerance) and not _almost_equal(poly[i].y, bb.y + bb.height,
                                                                                         tolerance=tolerance):
            return False

    return True


# returns an interior NFP for the special case where A is a rectangle
def no_fit_polygon_rectangle(A, B):
    minAx = A[0].x
    minAy = A[0].y
    maxAx = A[0].x
    maxAy = A[0].y

    for i in range(1, len(A)):
        if A[i].x < minAx:
            minAx = A[i].x
        if A[i].y < minAy:
            minAy = A[i].y
        if A[i].x > maxAx:
            maxAx = A[i].x
        if A[i].y > maxAy:
            maxAy = A[i].y

    minBx = B[0].x
    minBy = B[0].y
    maxBx = B[0].x
    maxBy = B[0].y
    for i in range(1, len(B)):
        if B[i].x < minBx:
            minBx = B[i].x
        if B[i].y < minBy:
            minBy = B[i].y
        if B[i].x > maxBx:
            maxBx = B[i].x
        if B[i].y > maxBy:
            maxBy = B[i].y

    if maxBx - minBx > maxAx - minAx:
        return None
    if maxBy - minBy > maxAy - minAy:
        return None

    return [[
        Point(minAx - minBx + B[0].x, minAy - minBy + B[0].y),
        Point(maxAx - maxBx + B[0].x, minAy - minBy + B[0].y),
        Point(maxAx - maxBx + B[0].x, maxAy - maxBy + B[0].y),
        Point(minAx - minBx + B[0].x, maxAy - maxBy + B[0].y)
    ]]


# given a static polygon A and a movable polygon B, compute a no fit polygon by orbiting B about A
# if the inside flag is set, B is orbited inside of A rather than outside
# if the searchEdges flag is set, all edges of A are explored for NFPs - multiple
def no_fit_polygon(A, B, inside, searchEdges):
    if not A or len(A) < 3 or not B or len(B) < 3:
        return None

    A.offsetx = 0
    A.offsety = 0

    i = None
    j = None

    minA = A[0].y
    minAindex = 0

    maxB = B[0].y
    maxBindex = 0

    for i in range(1, len(A)):
        A[i].marked = False
        if A[i].y < minA:
            minA = A[i].y
            minAindex = i

    for i in range(1, len(B)):
        B[i].marked = False
        if B[i].y > maxB:
            maxB = B[i].y
            maxBindex = i

    if not inside:
        # shift B such that the bottom-most point of B is at the top-most point of A. This guarantees an initial placement with no intersections
        startpoint = Point(
            A[minAindex].x - B[maxBindex].x,
            A[minAindex].y - B[maxBindex].y
        )
    else:
        # no reliable heuristic for inside
        startpoint = search_start_point(A, B, True)

    NFPlist = Polygon()

    while startpoint is not None:

        B.offsetx = startpoint.x
        B.offsety = startpoint.y

        # maintain a list of touching points/edges
        touching = []

        prevvector = None  # keep track of previous vector
        NFP = [Point(
            B[0].x + B.offsetx,
            B[0].y + B.offsety
        )]

        referencex = B[0].x + B.offsetx
        referencey = B[0].y + B.offsety
        startx = referencex
        starty = referencey
        counter = 0

        while counter < 10 * (A.length + B.length):  # sanity check, prevent infinite loop
            touching = []
            # find touching vertices/edges
            for i in range(0, len(A)):
                nexti = 0 if (i == A.length - 1) else i + 1
                for j in range(0, len(B)):
                    nextj = 0 if (j == B.length - 1) else j + 1
                    if _almost_equal(A[i].x, B[j].x + B.offsetx) and _almost_equal(A[i].y, B[j].y + B.offsety):
                        touching.append({type: 0, A: i, B: j})
                    elif _on_segment(A[i], A[nexti], Point(x=B[j].x + B.offsetx, y=B[j].y + B.offsety)):
                        touching.append({type: 1, A: nexti, B: j})
                    elif _on_segment(Point(x=B[j].x + B.offsetx, y=B[j].y + B.offsety),
                                     Point(x=B[nextj].x + B.offsetx, y=B[nextj].y + B.offsety), A[i]):
                        touching.append({type: 2, A: i, B: nextj})

            # generate translation vectors from touching vertices/edges
            vectors = []
            for i in range(0, len(touching)):
                vertexA = A[touching[i].A]
                vertexA.marked = True

                # adjacent A vertices
                prevAindex = touching[i].A - 1
                nextAindex = touching[i].A + 1

                prevAindex = A.length - 1 if (prevAindex < 0) else prevAindex  # loop
                nextAindex = 0 if (nextAindex >= A.length) else nextAindex  # loop

                prevA = A[prevAindex]
                nextA = A[nextAindex]

                # adjacent B vertices
                vertexB = B[touching[i].B]

                prevBindex = touching[i].B - 1
                nextBindex = touching[i].B + 1

                prevBindex = B.length - 1 if (prevBindex < 0) else prevBindex  # loop
                nextBindex = 0 if (nextBindex >= B.length) else nextBindex  # loop

                prevB = B[prevBindex]
                nextB = B[nextBindex]

                if touching[i].type == 0:

                    vA1 = Vector(
                        x=prevA.x - vertexA.x,
                        y=prevA.y - vertexA.y,
                        start=vertexA,
                        end=prevA
                    )

                    vA2 = Vector(
                        x=nextA.x - vertexA.x,
                        y=nextA.y - vertexA.y,
                        start=vertexA,
                        end=nextA
                    )

                    # B vectors need to be inverted
                    vB1 = Vector(
                        x=vertexB.x - prevB.x,
                        y=vertexB.y - prevB.y,
                        start=prevB,
                        end=vertexB
                    )

                    vB2 = Vector(
                        x=vertexB.x - nextB.x,
                        y=vertexB.y - nextB.y,
                        start=nextB,
                        end=vertexB
                    )

                    vectors.append(vA1)
                    vectors.append(vA2)
                    vectors.append(vB1)
                    vectors.append(vB2)
                elif touching[i].type == 1:
                    vectors.append(Vector(
                        x=vertexA.x - (vertexB.x + B.offsetx),
                        y=vertexA.y - (vertexB.y + B.offsety),
                        start=prevA,
                        end=vertexA
                    ))

                    vectors.append(Vector(
                        x=prevA.x - (vertexB.x + B.offsetx),
                        y=prevA.y - (vertexB.y + B.offsety),
                        start=vertexA,
                        end=prevA
                    ))
                elif touching[i].type == 2:
                    vectors.append(Vector(
                        x=vertexA.x - (vertexB.x + B.offsetx),
                        y=vertexA.y - (vertexB.y + B.offsety),
                        start=prevB,
                        end=vertexB
                    ))

                    vectors.append(Vector(
                        x=vertexA.x - (prevB.x + B.offsetx),
                        y=vertexA.y - (prevB.y + B.offsety),
                        start=vertexB,
                        end=prevB
                    ))

            # todo: there should be a faster way to reject vectors
            #  that will cause immediate intersection. For now just check them all

            translate = None
            maxd = 0

            for i in range(0, len(vectors)):
                if vectors[i].x == 0 and vectors[i].y == 0:
                    continue

                # if this vector points us back to where we came from, ignore it.
                # ie cross product = 0, dot product < 0
                if prevvector and vectors[i].y * prevvector.y + vectors[i].x * prevvector.x < 0:

                    # compare magnitude with unit vectors
                    vectorlength = math.sqrt(vectors[i].x * vectors[i].x + vectors[i].y * vectors[i].y)
                    unitv = Vector(x=vectors[i].x / vectorlength, y=vectors[i].y / vectorlength)

                    prevlength = math.sqrt(prevvector.x * prevvector.x + prevvector.y * prevvector.y)
                    prevunit = Vector(x=prevvector.x / prevlength, y=prevvector.y / prevlength)

                    # we need to scale down to unit vectors to normalize vector length. Could also just do a tan here
                    if abs(unitv.y * prevunit.x - unitv.x * prevunit.y) < 0.0001:
                        continue

                d = polygon_slide_distance(A, B, vectors[i], True)
                vecd2 = vectors[i].x * vectors[i].x + vectors[i].y * vectors[i].y

                if d is None or d * d > vecd2:
                    vecd = math.sqrt(vectors[i].x * vectors[i].x + vectors[i].y * vectors[i].y)
                    d = vecd

                if d is not None and d > maxd:
                    maxd = d
                    translate = vectors[i]

            if translate is None or _almost_equal(maxd, 0):
                # didn't close the loop, something went wrong here
                NFP = None
                break

            translate.start.marked = True
            translate.end.marked = True

            prevvector = translate

            # trim
            vlength2 = translate.x * translate.x + translate.y * translate.y
            if maxd * maxd < vlength2 and not _almost_equal(maxd * maxd, vlength2):
                scale = math.sqrt((maxd * maxd) / vlength2)
                translate.x *= scale
                translate.y *= scale

            referencex += translate.x
            referencey += translate.y

            if _almost_equal(referencex, startx) and _almost_equal(referencey, starty):
                # we've made a full loop
                break

            # if A and B start on a touching horizontal line, the end point may not be the start point
            looped = False
            if len(NFP) > 0:
                for i in range(0, len(NFP)):
                    if _almost_equal(referencex, NFP[i].x) and _almost_equal(referencey, NFP[i].y):
                        looped = True

            if looped:
                # we've made a full loop
                break

            NFP.append(Point(
                x=referencex,
                y=referencey
            ))

            B.offsetx += translate.x
            B.offsety += translate.y

            counter += 1

        if NFP and len(NFP) > 0:
            NFPlist.append(NFP)

        if not searchEdges:
            # only get outer NFP or first inner NFP
            break

        startpoint = search_start_point(A, B, inside, NFPlist)

    return NFPlist


# given two polygons that touch at at least one point, but do not intersect.
# Return the outer perimeter of both polygons as a single continuous polygon
# A and B must have the same winding direction
def polygon_hull(A, B):
    if not A or len(A) < 3 or not B or len(B) < 3:
        return None

    i = None
    j = None

    Aoffsetx = A.offsetx or 0
    Aoffsety = A.offsety or 0
    Boffsetx = B.offsetx or 0
    Boffsety = B.offsety or 0

    # start at an extreme point that is guaranteed to be on the final polygon
    miny = A[0].y
    startPolygon = A
    startIndex = 0

    for i in range(0, len(A)):
        if A[i].y + Aoffsety < miny:
            miny = A[i].y + Aoffsety
            startPolygon = A
            startIndex = i

    for i in range(0, len(B)):
        if B[i].y + Boffsety < miny:
            miny = B[i].y + Boffsety
            startPolygon = B
            startIndex = i

    # for simplicity we'll define polygon A as the starting polygon
    if startPolygon == B:
        B = A
        A = startPolygon
        Aoffsetx = A.offsetx or 0
        Aoffsety = A.offsety or 0
        Boffsetx = B.offsetx or 0
        Boffsety = B.offsety or 0

    A = A.slice(0)
    B = B.slice(0)

    C = []
    current = startIndex
    intercept1 = None
    intercept2 = None

    # scan forward from the starting point
    for i in range(0, len(A) + 1):
        current = 0 if (current == A.length) else current
        next = 0 if (current == A.length - 1) else current + 1
        touching = False
        for j in range(0, len(B)):
            nextj = 0 if (j == B.length - 1) else j + 1
            if _almost_equal(A[current].x + Aoffsetx, B[j].x + Boffsetx) and _almost_equal(A[current].y + Aoffsety,
                                                                                         B[j].y + Boffsety):
                C.append(Point(x=A[current].x + Aoffsetx, y=A[current].y + Aoffsety))
                intercept1 = j
                touching = True
                break
            elif _on_segment(Point(x=A[current].x + Aoffsetx, y=A[current].y + Aoffsety),
                             Point(x=A[next].x + Aoffsetx, y=A[next].y + Aoffsety),
                             Point(x=B[j].x + Boffsetx, y=B[j].y + Boffsety)):
                C.append(Point(x=A[current].x + Aoffsetx, y=A[current].y + Aoffsety))
                C.append(Point(x=B[j].x + Boffsetx, y=B[j].y + Boffsety))
                intercept1 = j
                touching = True
                break
            elif _on_segment(Point(x=B[j].x + Boffsetx, y=B[j].y + Boffsety),
                             Point(x=B[nextj].x + Boffsetx, y=B[nextj].y + Boffsety),
                             Point(x=A[current].x + Aoffsetx, y=A[current].y + Aoffsety)):
                C.append(Point(x=A[current].x + Aoffsetx, y=A[current].y + Aoffsety))
                C.append(Point(x=B[nextj].x + Boffsetx, y=B[nextj].y + Boffsety))
                intercept1 = nextj
                touching = True
                break

        if touching:
            break

        C.append(Point(x=A[current].x + Aoffsetx, y=A[current].y + Aoffsety))

        current += 1

    # scan backward from the starting point
    current = startIndex - 1
    for i in range(0, len(A)):
        current = len(A) - 1 if current < 0 else current
        next = len(A) - 1 if current == 0 else current - 1
        touching = False
        for j in range(0, len(B)):
            nextj = 0 if (j == B.length - 1) else j + 1
            if _almost_equal(A[current].x + Aoffsetx, B[j].x + Boffsetx) and _almost_equal(A[current].y,
                                                                                         B[j].y + Boffsety):
                C.insert(0, Point(x=A[current].x + Aoffsetx, y=A[current].y + Aoffsety))
                intercept2 = j
                touching = True
                break
            elif _on_segment(Point(x=A[current].x + Aoffsetx, y=A[current].y + Aoffsety),
                             Point(x=A[next].x + Aoffsetx, y=A[next].y + Aoffsety),
                             Point(x=B[j].x + Boffsetx, y=B[j].y + Boffsety)):
                C.insert(0, Point(x=A[current].x + Aoffsetx, y=A[current].y + Aoffsety))
                C.insert(0, Point(x=B[j].x + Boffsetx, y=B[j].y + Boffsety))
                intercept2 = j
                touching = True
                break
            elif _on_segment(Point(x=B[j].x + Boffsetx, y=B[j].y + Boffsety),
                             Point(x=B[nextj].x + Boffsetx, y=B[nextj].y + Boffsety),
                             Point(x=A[current].x + Aoffsetx, y=A[current].y + Aoffsety)):
                C.insert(0, Point(x=A[current].x + Aoffsetx, y=A[current].y + Aoffsety))
                intercept2 = j
                touching = True
                break

        if touching:
            break

        C.insert(0, Point(x=A[current].x + Aoffsetx, y=A[current].y + Aoffsety))

        current -= 1

    if intercept1 is None or intercept2 is None:
        # polygons not touching?
        return None

    # the relevant points on B now lie between intercept1 and intercept2
    current = intercept1 + 1
    for i in range(0, len(B)):
        current = 0 if (current == len(B)) else current
        C.append(Point(x=B[current].x + Boffsetx, y=B[current].y + Boffsety))

        if current == intercept2:
            break

        current += 1

    # dedupe
    for i in range(0, len(C)):
        next = 0 if (i == len(C) - 1) else i + 1
        if _almost_equal(C[i].x, C[next].x) and _almost_equal(C[i].y, C[next].y):
            splice(C, i, 1)
            i -= 1

    return C


def rotate_polygon(polygon, angle):
    rotated = Polygon()
    angle = angle * math.pi / 180
    for point in polygon:
        x = point.x
        y = point.y
        x1 = x * math.cos(angle) - y * math.sin(angle)
        y1 = x * math.sin(angle) + y * math.cos(angle)

        rotated.append(Point(x=x1, y=y1))
    # reset bounding box
    bounds = get_polygon_bounds(rotated)
    rotated.x = bounds.x
    rotated.y = bounds.y
    rotated.width = bounds.width
    rotated.height = bounds.height

    return rotated
