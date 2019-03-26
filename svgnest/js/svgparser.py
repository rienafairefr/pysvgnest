import math
import re

from svgpathtools import QuadraticBezier

from svgnest.js.domparser import DOMParser
from svgnest.js.geometry import Point, Arc
from svgnest.js.geometryutil import GeometryUtil, CubicBezier
from svgnest.js.matrix import Matrix


class Config:
    tolerance = 2  # max bound for bezier->line segment conversion, in native SVG units
    toleranceSvg = 0.005  # fudge factor for browser inaccuracy in SVG unit handling


def parseFloat(f):
    return float(f)


class SvgParser:
    def __init__(self):
        # the SVG document
        self.svg = None

        # the top level SVG element of the SVG document
        self.svgRoot = None

        self.allowedElements = ['svg', 'circle', 'ellipse', 'path', 'polygon', 'polyline', 'rect']
        self.conf = Config()

    def config(self, config):
        self.conf.tolerance = config.tolerance

    def load(this, svgString):
        parser = DOMParser()
        svg = parser.parseFromString(svgString, "image/svg+xml")

        if svg:
            this.svg = svg
            this.svgRoot = svg.firstElementChild

        return this.svgRoot

    # use the utility functions in this class to prepare the svg for CAD-CAM/nest related operations
    def cleanInput(this):
        # apply any transformations, so that all path positions etc will be in the same coordinate space
        this.applyTransform(this.svgRoot)

        # remove any g elements and bring all elements to the top level
        this.flatten(this.svgRoot)

        # remove any non-contour elements like text
        this.filter(this.allowedElements)

        # split any compound paths into individual path elements
        this.recurse(this.svgRoot, this.splitPath)

        return this.svgRoot

    # return style node, if any
    def getStyle(this):
        if not this.svgRoot:
            return False

        for i in range(0, this.svgRoot.children.length):
            el = this.svgRoot.children[i]
            if el.tagName == 'style':
                return el

        return False

    # set the given path as absolute coords (capital commands)
    # from http://stackoverflow.com/a/9677915/433888
    def pathToAbsolute(this, path):
        if not path or path.tagName != 'path':
            raise Exception('invalid path')

        seglist = path.pathSegList
        x, y, x0, y0, x1, y1, x2, y2 = 0, 0, 0, 0, 0, 0, 0, 0

        for i in range(0, seglist.numberOfItems):
            command = seglist.getItem(i).pathSegTypeAsLetter
            s = seglist.getItem(i)

            if re.match('[MLHVCSQTA]', command, re.IGNORECASE):
                if 'x' in s: x=s.x
                if 'y' in s: y=s.y
            else:
                if 'x1' in s: x1=x+s.x1
                if 'x2' in s: x2=x+s.x2
                if 'y1' in s: y1=y+s.y1
                if 'y2' in s: y2=y+s.y2
                if 'x'  in s: x+=s.x
                if 'y'  in s: y+=s.y

                if command == 'm': seglist.replaceItem(path.createSVGPathSegMovetoAbs(x,y),i)
                elif command == 'l': seglist.replaceItem(path.createSVGPathSegLinetoAbs(x,y),i)
                elif command == 'h': seglist.replaceItem(path.createSVGPathSegLinetoHorizontalAbs(x),i)
                elif command == 'v': seglist.replaceItem(path.createSVGPathSegLinetoVerticalAbs(y),i)
                elif command == 'c': seglist.replaceItem(path.createSVGPathSegCurvetoCubicAbs(x,y,x1,y1,x2,y2),i)
                elif command == 's': seglist.replaceItem(path.createSVGPathSegCurvetoCubicSmoothAbs(x,y,x2,y2),i)
                elif command == 'q': seglist.replaceItem(path.createSVGPathSegCurvetoQuadraticAbs(x,y,x1,y1),i)
                elif command == 't': seglist.replaceItem(path.createSVGPathSegCurvetoQuadraticSmoothAbs(x,y),i)
                elif command == 'a': seglist.replaceItem(path.createSVGPathSegArcAbs(x,y,s.r1,s.r2,s.angle,s.largeArcFlag,s.sweepFlag),i)
                elif command == 'z' or command == 'Z': x=x0; y=y0;
            # Record the start of a subpath
            if command=='M' or command=='m':
                x0, y0 =x, y

    # takes an SVG transform string and returns corresponding SVGMatrix
    # from https://github.com/fontello/svgpath
    def transformParse(this, transformString):

        class Operations:
            def __init__(self):
                self.matrix = True
                self.scale = True
                self.rotate = True
                self.translate = True
                self.skewX = True
                self.skew = True

        operations = Operations()

        CMD_SPLIT_RE    = re.compile('\s*(matrix|translate|scale|rotate|skewX|skewY)\s*\(\s*(.+?)\s*\)[\s,]*')
        PARAMS_SPLIT_RE = re.compile('[\s,]+')

        matrix = Matrix()
        cmd = None
        params = None

        # Split value into ['', 'translate', '10 50', '', 'scale', '2', '', 'rotate',  '-45', '']
        items = transformString.split(CMD_SPLIT_RE)

        for item in items:

            # Skip empty elements
            if not len(item): continue

            # remember operation
            if operations[item] is not None:
                cmd = item
                continue

            # extract params & att operation to matrix
            params = item.split(PARAMS_SPLIT_RE).map(lambda i: +i or 0)

            # If params count is not correct - ignore command
            if cmd == 'matrix':
                if (params.length == 6):
                    matrix.matrix(params)
                continue

            elif cmd == 'scale':
                if (params.length == 1):
                    matrix.scale(params[0], params[0])
                elif (params.length == 2):
                    matrix.scale(params[0], params[1])
                continue

            elif cmd == 'rotate':
                if (params.length == 1):
                    matrix.rotate(params[0], 0, 0)
                elif (params.length == 3):
                    matrix.rotate(params[0], params[1], params[2])
                continue

            elif cmd == 'translate':
                if (params.length == 1):
                    matrix.translate(params[0], 0)
                elif (params.length == 2):
                    matrix.translate(params[0], params[1])
                continue

            elif cmd == 'skewX':
                if (params.length == 1):
                    matrix.skewX(params[0])
                continue

            elif cmd == 'skewY':
                if (params.length == 1):
                    matrix.skewY(params[0])
                continue

        return matrix

    # recursively apply the transform property to the given element
    def applyTransform(this, element, globalTransform):

        globalTransform = globalTransform or ''
        transformString = element.getAttribute('transform') or ''
        transformString = globalTransform + transformString

        transform = None
        scale = None
        rotate = None

        if transformString and transformString.length > 0:
            transform = this.transformParse(transformString)

        if not transform:
            transform = Matrix()

        tarray = transform.toArray()

        # decompose affine matrix to rotate, scale components (translate is just the 3rd column)
        rotate = math.atan2(tarray[1], tarray[3])*180/math.pi
        scale = math.sqrt(tarray[0]*tarray[0]+tarray[2]*tarray[2])

        if element.tagName == 'g' or element.tagName == 'svg':
            del element.transform
            children = list(element.children)
            for i in range(0, len(children)):
                this.applyTransform(children[i], transformString)
        elif transform and not transform.isIdentity():
            if element.tagName == 'ellipse':
                # the goal is to remove the transform property, but an ellipse without a transform will have no rotation
                # for the sake of simplicity, we will replace the ellipse with a path, and apply the transform to that path
                path = this.svg.createElementNS(element.namespaceURI, 'path')
                move = path.createSVGPathSegMovetoAbs(parseFloat(element.getAttribute('cx')) - parseFloat(element.getAttribute('rx')), element.getAttribute('cy'))
                arc1 = path.createSVGPathSegArcAbs(parseFloat(element.getAttribute('cx')) + parseFloat(element.getAttribute('rx')), element.getAttribute('cy'), element.getAttribute('rx'), element.getAttribute('ry'), 0, 1, 0)
                arc2 = path.createSVGPathSegArcAbs(parseFloat(element.getAttribute('cx')) - parseFloat(element.getAttribute('rx')), element.getAttribute('cy'), element.getAttribute('rx'), element.getAttribute('ry'), 0, 1, 0)

                path.pathSegList.appendItem(move)
                path.pathSegList.appendItem(arc1)
                path.pathSegList.appendItem(arc2)
                path.pathSegList.appendItem(path.createSVGPathSegClosePath())

                transformProperty = element.getAttribute('transform')
                if transformProperty:
                    path.setAttribute('transform', transformProperty)

                element.parentElement.replaceChild(path, element)

                element = path

            if element.tagName == 'path':
                this.pathToAbsolute(element)
                seglist = element.pathSegList
                prevx = 0
                prevy = 0

                for i in range(0, len(seglist.numberOfItems)):
                    s = seglist.getItem(i)
                    command = s.pathSegTypeAsLetter

                    if command == 'H':
                        seglist.replaceItem(element.createSVGPathSegLinetoAbs(s.x,prevy),i)
                        s = seglist.getItem(i)

                    elif command == 'V':
                        seglist.replaceItem(element.createSVGPathSegLinetoAbs(prevx,s.y),i)
                        s = seglist.getItem(i)

                    # currently only works for uniform scale, no skew
                    # todo: fully support arbitrary affine transforms...
                    elif command == 'A':
                        seglist.replaceItem(element.createSVGPathSegArcAbs(s.x,s.y,s.r1*scale,s.r2*scale,s.angle+rotate,s.largeArcFlag,s.sweepFlag),i)
                        s = seglist.getItem(i)

                    if 'x' in s and 'y' in s:
                        transformed = transform.calc(s.x, s.y)
                        prevx = s.x
                        prevy = s.y

                        s.x = transformed[0]
                        s.y = transformed[1]

                    if 'x1' in s and 'y1' in s:
                        transformed = transform.calc(s.x1, s.y1)
                        s.x1 = transformed[0]
                        s.y1 = transformed[1]

                    if 'x2' in s and 'y2' in s:
                        transformed = transform.calc(s.x2, s.y2)
                        s.x2 = transformed[0]
                        s.y2 = transformed[1]

                element.removeAttribute('transform')
            elif element.tagName == 'circle':
                transformed = transform.calc(element.getAttribute('cx'), element.getAttribute('cy'))
                element.setAttribute('cx', transformed[0])
                element.setAttribute('cy', transformed[1])

                # skew not supported
                element.setAttribute('r', element.getAttribute('r')*scale)

            if element.tagName == 'rect':
                # similar to the ellipse, we'll replace rect with polygon
                polygon = this.svg.createElementNS(element.namespaceURI, 'polygon')


                p1 = this.svgRoot.createSVGPoint()
                p2 = this.svgRoot.createSVGPoint()
                p3 = this.svgRoot.createSVGPoint()
                p4 = this.svgRoot.createSVGPoint()

                p1.x = parseFloat(element.getAttribute('x')) or 0
                p1.y = parseFloat(element.getAttribute('y')) or 0

                p2.x = p1.x + parseFloat(element.getAttribute('width'))
                p2.y = p1.y

                p3.x = p2.x
                p3.y = p1.y + parseFloat(element.getAttribute('height'))

                p4.x = p1.x
                p4.y = p3.y

                polygon.points.appendItem(p1)
                polygon.points.appendItem(p2)
                polygon.points.appendItem(p3)
                polygon.points.appendItem(p4)

                transformProperty = element.getAttribute('transform')
                if transformProperty:
                    polygon.setAttribute('transform', transformProperty)

                element.parentElement.replaceChild(polygon, element)
                element = polygon

            if element.tagName == 'polygon' or element.tagName == 'polyline':
                for i in range(0, len(element.points)):
                    point = element.points[i]
                    ransformed = transform.calc(point.x, point.y)
                    point.x = transformed[0]
                    point.y = transformed[1]

                del element.transform

    # bring all child elements to the top level
    def flatten(this, element):
        for i in range(0, len(element.children)):
            this.flatten(element.children[i])

        if element.tagName != 'svg':
            while len(element.children) > 0:
                element.parentElement.appendChild(element.children[0])

    # remove all elements with tag name not in the whitelist
    # use this to remove <text>, <g> etc that don't represent shapes
    def filter(this, whitelist, element):
        if not whitelist or len(whitelist) == 0:
            raise Exception('invalid whitelist')

        element = element or this.svgRoot

        for i in range(0, len(element.children)):
            this.filter(whitelist, element.children[i])

        if len(element.children) == 0 and whitelist.indexOf(element.tagName) < 0:
            element.parentElement.removeChild(element)

    # split a compound path (paths with M, m commands) into an array of paths
    def splitPath(this, path):
        if not path or path.tagName != 'path' or not path.parentElement:
            return False

        seglist = path.pathSegList
        x, y, x0, y0=0,0,0,0
        paths = []

        p = None

        lastM = 0
        for i in range(seglist.numberOfItems-1, 0):
            if i > 0 and seglist.getItem(i).pathSegTypeAsLetter == 'M' or seglist.getItem(i).pathSegTypeAsLetter == 'm':
                lastM = i
                break

        if lastM == 0:
            return False # only 1 M command, no need to split

        for i in range(0, i<seglist.numberOfItems):
            s = seglist.getItem(i)
            command = s.pathSegTypeAsLetter

            if command == 'M' or command == 'm':
                p = path.cloneNode()
                p.setAttribute('d','')
                paths.push(p)

            if re.match('[MLHVCSQTA]', command):
                if 'x' in s: x=s.x
                if 'y' in s: y=s.y

                p.pathSegList.appendItem(s)
            else:
                if 'x'  in s: x+=s.x
                if 'y'  in s: y+=s.y
                if command == 'm':
                    p.pathSegList.appendItem(path.createSVGPathSegMovetoAbs(x,y))
                else:
                    if command == 'Z' or command == 'z':
                        x = x0
                        y = y0
                    p.pathSegList.appendItem(s)
            #  Record the start of a subpath
            if command=='M' or command=='m':
                x0=x, y0=y

        addedPaths = []
        for i in range(0, len(paths)):
            # don't add trivial paths from sequential M commands
            if paths[i].pathSegList.numberOfItems > 1:
                path.parentElement.insertBefore(paths[i], path)
                addedPaths.append(paths[i])

        path.remove()

        return addedPaths

    # recursively run the given function on the given element
    def recurse(this, element, func):
        # only operate on original DOM tree, ignore any children that are added. Avoid infinite loops
        children = list(element.children)
        for i in range(0, len(children)):
            this.recurse(children[i], func)

        func(element)

    # return a polygon from the given SVG element in the form of an array of points
    def polygonify(this, element):
        poly = []
        i = 0

        if element.tagName == 'polygon' or element.tagName ==  'polyline':
            for i in range(0, len(element.points)):
                poly.append(Point(
                    x= element.points[i].x,
                    y= element.points[i].y
                ))
        if element.tagName == 'rect':
            p1 = Point()
            p2 = Point()
            p3 = Point()
            p4 = Point()

            p1.x = parseFloat(element.getAttribute('x')) or 0
            p1.y = parseFloat(element.getAttribute('y')) or 0

            p2.x = p1.x + parseFloat(element.getAttribute('width'))
            p2.y = p1.y

            p3.x = p2.x
            p3.y = p1.y + parseFloat(element.getAttribute('height'))

            p4.x = p1.x
            p4.y = p3.y

            poly.append(p1)
            poly.append(p2)
            poly.append(p3)
            poly.append(p4)
        elif element.tagName == 'circle':
            radius = parseFloat(element.getAttribute('r'))
            cx = parseFloat(element.getAttribute('cx'))
            cy = parseFloat(element.getAttribute('cy'))

            # num is the smallest number of segments required to approximate the circle to the given tolerance
            num = math.ceil((2*math.pi)/math.acos(1 - (this.conf.tolerance/radius)))

            if num < 3:
                num = 3

            for i in range(0, num):
                theta = i * ( (2*math.pi) / num)
                point = {}
                point.x = radius*math.cos(theta) + cx
                point.y = radius*math.sin(theta) + cy

                poly.append(point)
        elif element.tagName == 'ellipse':
            # same as circle case. There is probably a way to reduce points but for convenience we will just flatten the equivalent circular polygon
            rx = parseFloat(element.getAttribute('rx'))
            ry = parseFloat(element.getAttribute('ry'))
            maxradius = math.max(rx, ry)

            cx = parseFloat(element.getAttribute('cx'))
            cy = parseFloat(element.getAttribute('cy'))

            num = math.ceil((2*math.pi)/math.acos(1 - (this.conf.tolerance/maxradius)))

            if num < 3:
                num = 3

            for i in range(0, num):
                theta = i * ( (2*math.pi) / num)
                point = {}
                point.x = rx*math.cos(theta) + cx
                point.y = ry*math.sin(theta) + cy

                poly.append(point)
        elif element.tagName == 'path':
            # we'll assume that splitpath has already been run on this path, and it only has one M/m command
            seglist = element.pathSegList

            firstCommand = seglist.getItem(0)
            astCommand = seglist.getItem(seglist.numberOfItems-1)

            x,y,x0,y0,x1,y1,x2,y2,prevx,prevy,prevx1,prevy1,prevx2,prevy2=0,0,0,0,0,0,0,0,0,0,0,0,0,0

            for i in range(0, seglist.numberOfItems):
                s = seglist.getItem(i)
                command = s.pathSegTypeAsLetter

                prevx = x
                prevy = y

                prevx1 = x1
                prevy1 = y1

                prevx2 = x2
                prevy2 = y2

                if re.match('[MLHVCSQTA]', command):
                    if ('x1' in s): x1=s.x1
                    if ('x2' in s): x2=s.x2
                    if ('y1' in s): y1=s.y1
                    if ('y2' in s): y2=s.y2
                    if ('x' in s): x=s.x
                    if ('y' in s): y=s.y
                else:
                    if ('x1' in s): x1=x+s.x1
                    if ('x2' in s): x2=x+s.x2
                    if ('y1' in s): y1=y+s.y1
                    if ('y2' in s): y2=y+s.y2;
                    if ('x'  in s): x+=s.x
                    if ('y'  in s): y+=s.y
                # linear line types
                if command == 'm' or command == 'M' or  command == 'l' or  command == 'L'\
                or command == 'h' or command == 'H' or command == 'v' or command == 'V':
                    point = Point(x, y)
                    point.x = x
                    point.y = y
                    poly.push(point)
                # Quadratic Beziers
                elif command == 't' or command == 'T':
                    # implicit control point
                    if i > 0 and re.match('[QqTt]', seglist.getItem(i-1).pathSegTypeAsLetter):
                        x1 = prevx + (prevx-prevx1)
                        y1 = prevy + (prevy-prevy1)
                    else:
                        x1 = prevx
                        y1 = prevy
                elif command == 'q' or command == 'Q':
                    pointlist = QuadraticBezier.linearize(Point(x= prevx, y= prevy), Point(x= x, y= y), Point(x= x1, y= y1), this.conf.tolerance)
                    pointlist.shift() # firstpoint would already be in the poly
                    for j in range(0, len(pointlist)):
                        point = Point(pointlist[j].x, pointlist[j].y)
                        poly.append(point)
                elif command == 's' or command == 'S':
                    if i > 0 and re.match('[CcSs]', seglist.getItem(i-1).pathSegTypeAsLetter):
                        x1 = prevx + (prevx-prevx2)
                        y1 = prevy + (prevy-prevy2)
                    else:
                        x1 = prevx
                        y1 = prevy
                elif command == 'c' or command == 'C':
                    pointlist = CubicBezier.linearize({x: prevx, y: prevy}, Point(x=x, y= y), Point(x= x1, y= y1), {x: x2, y: y2}, this.conf.tolerance)
                    pointlist.shift()  # firstpoint would already be in the poly
                    for j in range(0, len(pointlist)):
                        point = Point(pointlist[j].x, pointlist[j].y)
                        poly.append(point)
                elif command == 'a' or command == 'A':
                    pointlist = Arc.linearize(Point(x= prevx, y= prevy), Point(x= x, y= y), s.r1, s.r2, s.angle, s.largeArcFlag,s.sweepFlag, this.conf.tolerance)
                    pointlist.shift()

                    for j in range(0, len(pointlist)):
                        point = Point(pointlist[j].x, pointlist[j].y)
                        poly.append(point)
                elif command == 'z' or command == 'Z':
                    x=x0; y=y0;

                # Record the start of a subpath
                if command=='M' or command=='m':
                    x0=x
                    y0=y

        # do not include last point if coincident with starting point
        while poly.length > 0 and GeometryUtil.almostEqual(poly[0].x, poly[poly.length - 1].x, this.conf.toleranceSvg) and GeometryUtil.almostEqual(poly[0].y, poly[poly.length - 1].y, this.conf.toleranceSvg):
            poly.pop()

        return poly
