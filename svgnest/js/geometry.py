from svgnest.js.geometrybase import almost_equal


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
        self.marked = None

    def __repr__(self):
        return 'Point<%s,%s>' % (self.x, self.y)

    def almost_equal(self, other):
        return almost_equal(self.x, other.x) and almost_equal(self.y, other.y)

    @property
    def xy(self):
        return self.x, self.y


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

    def almost_equal(self, other):
        return almost_equal(self.x, other.x) and \
               almost_equal(self.y, other.y) and \
               almost_equal(self.start, other.start) and \
               almost_equal(self.end, other.end)


class Polygon(list):
    def __init__(self, *input_list, source=None):
        super().__init__(list(input_list))
        self.source = source
        self.offsetx = None
        self.offsety = None
        self.children = []
        self.element_id = None
        self.width = None
        self.height = None

    def almost_equal(self, other):
        if len(other) != len(self):
            return False
        for i, op in enumerate(other):
            if not self[i].almost_equal(op):
                return False
        return True

    def clone(self):
        return Polygon(*self[:], source=self.source)

    @property
    def length(self):
        return len(self)

    @property
    def xy(self):
        return [point.x for point in self], [point.y for point in self]

    @property
    def x_y(self):
        return [(point.x, point.y) for point in self]
