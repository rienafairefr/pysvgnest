# matrix utility from SvgPath
# https://github.com/fontello/svgpath
import math


class Matrix:
    def __init__(self):
        self.queue = [] # list of matrixes to apply
        self.cache = None # combined matrix cache

    # combine 2 matrixes
    # m1, m2 - [a, b, c, d, e, g]
    def combine(self, m1, m2):
        return [
            m1[0] * m2[0] + m1[2] * m2[1],
            m1[1] * m2[0] + m1[3] * m2[1],
            m1[0] * m2[2] + m1[2] * m2[3],
            m1[1] * m2[2] + m1[3] * m2[3],
            m1[0] * m2[4] + m1[2] * m2[5] + m1[4],
            m1[1] * m2[4] + m1[3] * m2[5] + m1[5]
        ]

    def isIdentity(self):
        if not self.cache:
            self.cache = self.toArray()

        m = self.cache

        if m[0] == 1 and m[1] == 0 and m[2] ==  0 and m[3] ==  1 and m[4] == 0 and m[5] == 0:
            return True
        return False

    def matrix(self, m):
        if m[0] == 1 and m[1] == 0 and m[2] == 0 and m[3] == 1 and m[4] == 0 and m[5] == 0:
            return self

        self.cache = None
        self.queue.append(m)
        return self

    def translate(self, tx, ty):
        if tx != 0 or ty !=0:
            self.cache = None
            self.queue.append([1, 0, 0, 1, tx, ty])
        return self

    def scale(self, sx, sy):
        if sx != 1 or sy != 1:
            self.cache = None
            self.queue.append([sx, 0, 0, sy, 0, 0])
        return self

    def rotate(self, angle, rx, ry):
        if angle != 0:
            self.translate(rx, ry)

        rad = angle * math.pi / 180
        cos = math.cos(rad)
        sin = math.sin(rad)

        self.queue.append([cos, sin, -sin, cos, 0, 0])
        self.cache = None

        self.translate(-rx, -ry)

        return self

    def skewX(self, angle):
        if angle != 0:
            self.cache = None
            self.queue.append([1, 0, math.tan(angle * math.pi / 180), 1, 0, 0])
        return self

    def skewY(self, angle):
        if angle != 0:
            self.cache = None
            self.queue.append([1, math.tan(angle * math.pi / 180), 0, 1, 0, 0])
        return self

    # Flatten queue
    def toArray(self):
        if self.cache:
            return self.cache

        if not len(self.queue):
            self.cache = [1, 0, 0, 1, 0, 0]
            return self.cache

        self.cache = self.queue[0]

        if len(self.queue) == 1:
            return self.cache

        for i in range(0, len(self.queue)):
            self.cache = self.combine(self.cache, self.queue[i])

        return self.cache

    # Apply list of matrixes to (x,y) point.
    # If `isRelative` set, `translate` component of matrix will be skipped
    def calc(self, x, y, is_relative=None):
        # Don't change point on empty transforms queue
        if not len(self.queue):
            return [x, y]

        # Calculate final matrix, if not exists
        # NB. if you deside to apply transforms to point one-by-one,
        # they should be taken in reverse order

        if not self.cache:
            self.cache = self.toArray()

        m = self.cache

        new_x = x * m[0] + y * m[2] + (0 if is_relative else m[4])
        new_y = x * m[1] + y * m[3] + (0 if is_relative else m[5])
        # Apply matrix to point
        return [new_x, new_y]
