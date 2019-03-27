class SVGPathSegList:
    def getItem(self, idx):
        pass


class SVGPathSeg:

    PATHSEG_UNKNOWN = 0
    PATHSEG_CLOSEPATH = 1
    PATHSEG_MOVETO_ABS = 2
    PATHSEG_MOVETO_REL = 3
    PATHSEG_LINETO_ABS = 4
    PATHSEG_LINETO_REL = 5
    PATHSEG_CURVETO_CUBIC_ABS = 6
    PATHSEG_CURVETO_CUBIC_REL = 7
    PATHSEG_CURVETO_QUADRATIC_ABS = 8
    PATHSEG_CURVETO_QUADRATIC_REL = 9
    PATHSEG_ARC_ABS = 10
    PATHSEG_ARC_REL = 11
    PATHSEG_LINETO_HORIZONTAL_ABS = 12
    PATHSEG_LINETO_HORIZONTAL_REL = 13
    PATHSEG_LINETO_VERTICAL_ABS = 14
    PATHSEG_LINETO_VERTICAL_REL = 15
    PATHSEG_CURVETO_CUBIC_SMOOTH_ABS = 16
    PATHSEG_CURVETO_CUBIC_SMOOTH_REL = 17
    PATHSEG_CURVETO_QUADRATIC_SMOOTH_ABS = 18
    PATHSEG_CURVETO_QUADRATIC_SMOOTH_REL = 19

    letters = [
        '', 'Z',
        'M', 'm',
        'L', 'l',
        'C', 'c',
        'Q', 'q',
        'A', 'a',
        'H', 'h',
        'V', 'v',
        'S', 's',
        'T', 't'
    ]

    def __init__(self, pathSegType):
        self.pathSegType = pathSegType

    @property
    def pathSegTypeAsLetter(self):
        return self.letters[self.pathSegType]

    def __contains__(self, item):
        return hasattr(self, item)


class SVGPathSegClosePath(SVGPathSeg):
    def __init__(self):
        super().__init__(SVGPathSeg.PATHSEG_CLOSEPATH)


class SVGPathSegMoveto(SVGPathSeg):
    def __init__(self, x, y, abs):
        if abs:
            super().__init__(SVGPathSeg.PATHSEG_MOVETO_ABS)
        else:
            super().__init__(SVGPathSeg.PATHSEG_MOVETO_REL)
        self.x = x
        self.y = y


class SVGPathSegLineto(SVGPathSeg):
    def __init__(self, x, y, abs):
        if abs:
            super().__init__(SVGPathSeg.PATHSEG_LINETO_ABS)
        else:
            super().__init__(SVGPathSeg.PATHSEG_LINETO_REL)
        self.x = x
        self.y = y


class SVGPathSegLinetoHorizontal(SVGPathSeg):
    def __init__(self, x, abs):
        if abs:
            super().__init__(SVGPathSeg.PATHSEG_LINETO_HORIZONTAL_ABS)
        else:
            super().__init__(SVGPathSeg.PATHSEG_LINETO_HORIZONTAL_REL)
        self.x = x


class SVGPathSegLinetoVertical(SVGPathSeg):
    def __init__(self, y, abs):
        if abs:
            super().__init__(SVGPathSeg.PATHSEG_LINETO_VERTICAL_ABS)
        else:
            super().__init__(SVGPathSeg.PATHSEG_LINETO_VERTICAL_REL)
        self.y = y


class SVGPathSegCurvetoCubic(SVGPathSeg):
    def __init__(self, x, y, x1, y1, x2, y2, abs):
        if abs:
            super().__init__(SVGPathSeg.PATHSEG_CURVETO_CUBIC_ABS)
        else:
            super().__init__(SVGPathSeg.PATHSEG_CURVETO_CUBIC_REL)
        self.x = x
        self.y = y
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2


class SVGPathSegCurvetoCubicSmooth(SVGPathSeg):
    def __init__(self, x, y, x2, y2, abs):
        if abs:
            super().__init__(SVGPathSeg.PATHSEG_CURVETO_CUBIC_SMOOTH_ABS)
        else:
            super().__init__(SVGPathSeg.PATHSEG_CURVETO_CUBIC_SMOOTH_REL)
        self.x = x
        self.y = y
        self.x2 = x2
        self.y2 = y2


class SVGPathSegCurvetoQuadratic(SVGPathSeg):
    def __init__(self, x, y, x1, y1, abs):
        if abs:
            super().__init__(SVGPathSeg.PATHSEG_CURVETO_QUADRATIC_ABS)
        else:
            super().__init__(SVGPathSeg.PATHSEG_CURVETO_QUADRATIC_REL)
        self.x = x
        self.y = y
        self.x1 = x1
        self.y1 = y1


class SVGPathSegCurvetoQuadraticSmooth(SVGPathSeg):
    def __init__(self, x, y, abs):
        if abs:
            super().__init__(SVGPathSeg.PATHSEG_CURVETO_QUADRATIC_SMOOTH_ABS)
        else:
            super().__init__(SVGPathSeg.PATHSEG_CURVETO_QUADRATIC_SMOOTH_REL)
        self.x = x
        self.y = y


class SVGPathSegArc(SVGPathSeg):

    def __init__(self, x, y, r1, r2, angle, largeArcFlag, sweepFlag, abs):
        if abs:
            super().__init__(SVGPathSeg.PATHSEG_ARC_ABS)
        else:
            super().__init__(SVGPathSeg.PATHSEG_ARC_REL)
        self.x = x
        self.y = y
        self.r1 = r1
        self.r2 = r2
        self.angle = angle
        self.largeArcFlag = largeArcFlag
        self.sweepFlag = sweepFlag