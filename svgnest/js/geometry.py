

class Segment(object):
    def __init__(self, p1, p2, c1, c2=None):
        self.p1 = p1
        self.p2 = p2
        self.c1 = c1
        self.c2 = c2


class Point(object):
    def __init__(self, x=None, y=None):
        self.x = x
        self.y = y

    def almostEqual(self, other):
        from svgnest.js.geometryutil import GeometryUtil
        return GeometryUtil.almostEqual(self.x, other.x) and GeometryUtil.almostEqual(self.y, other.y)

class Arc:
    def __init__(self, center=None, rx=None, ry=None, theta=None, extent=None, angle=None):
        self.center = center
        self.rx = rx
        self.ry = ry
        self.theta = theta
        self.extent = extent
        self.angle = angle


class PolygonBound:
    def __init__(self, x=None, y=None, width=None, height=None):
        self.x = x
        self.y = y
        self.width = width
        self.height = height


class Vector(object):

    def __init__(self, x=None, y=None, start=None, end=None):
        self.x = x
        self.y = y
        self.start = start
        self.end = end


class Polygon(list):
    def __init__(self, l=None, source=None):
        if l is None:
            l = []
        super().__init__(l)
        self.source = source
        self.offsetx = None
        self.offsety = None
        self.children = []
        self.element_id = None
        self.width = None
        self.height = None
