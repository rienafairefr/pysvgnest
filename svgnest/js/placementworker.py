import json
import math

from svgnest.js.geometry import Point
from svgnest.js.geometryutil import rotatePolygon, GeometryUtil, polygonArea
from svgnest.js.utils import splice


class Position:
    def __init__(self, x=None, y=None, id=None, rotation=None):
        self.x = x
        self.y = y
        self.id = id
        self.rotation = rotation


# jsClipper uses X/Y instead of x/y...
def toClipperCoordinates(polygon):
    clone = []
    for i in range(0, len(polygon)):
        clone.append([polygon[i].x, polygon[i].y])

    return clone


def toNestCoordinates(polygon, scale):
    clone = []
    for i in range(0, len(polygon)):
        clone.append([
             polygon[i].X/scale,
            polygon[i].Y/scale
        ])

    return clone


def rotatePolygon(polygon, degrees):
    rotated = []
    angle = degrees * math.pi / 180
    for i, point in enumerate(polygon):
        x = point.x
        y = point.y
        x1 = x*math.cos(angle)-y*math.sin(angle)
        y1 = x*math.sin(angle)+y*math.cos(angle)

        rotated.append(Point(x=x1, y=y1))

    if polygon.children and polygon.children.length > 0:
        rotated.children = []
        for j in range(0, len(polygon.children)):
            rotated.children.append(rotatePolygon(polygon.children[j], degrees))

    return rotated


class PlacementWorker:
    # return a placement for the paths/rotations given
    # happens inside a worker

    def __init__(this, binPolygon, paths, ids, rotations, config, nfpCache=None):
        this.binPolygon = binPolygon
        this.paths = paths
        this.ids = ids
        this.rotations = rotations
        this.config = config
        this.nfpCache = nfpCache or {}

    def placePaths(this, paths):

        if not this.binPolygon:
            return None

        # rotate paths by given rotation
        rotated = []
        for i in range(0, len(paths)):
            r = rotatePolygon(paths[i], paths[i].rotation)
            r.rotation = paths[i].rotation
            r.source = paths[i].source
            r.id = paths[i].id
            rotated.append(r)

        paths = rotated

        allplacements = []
        fitness = 0
        binarea = abs(polygonArea(this.binPolygon))
        key = None
        nfp = None

        while paths.length > 0:

            placed = []
            placements = []
            fitness += 1  # add 1 for each new bin opened (lower fitness is better)
            minwidth = None

            for i, path in enumerate(paths):

                # inner NFP
                key = json.dumps({'A':-1, 'B': path.id, 'inside': True, 'Arotation': 0, 'Brotation': path.rotation})
                binNfp = this.nfpCache.get(key)

                # part unplaceable, skip
                if not binNfp or len(binNfp) == 0:
                    continue

                # ensure all necessary NFPs exist
                error = False
                for j in range(0, len(placed)):
                    key = json.dumps({'A': placed[j].id, 'B': path.id, 'inside': False, 'Arotation': placed[j].rotation, 'Brotation': path.rotation})
                    nfp = this.nfpCache.get(key)

                    if not nfp:
                        error = True
                        break

                # part unplaceable, skip
                if error:
                    continue

                position = None
                if len(placed) == 0:
                    # first placement, put it on the left
                    for j in range(0, len(binNfp)):
                        for k in range(0, len(binNfp[k])):
                            if position is None or binNfp[j][k].x-path[0].x < position.x:
                                position = Position(
                                    x= binNfp[j][k].x-path[0].x,
                                    y= binNfp[j][k].y-path[0].y,
                                    id= path.id,
                                    rotation= path.rotation
                                )

                    placements.append(position)
                    placed.append(path)

                    continue

                clipperBinNfp = []
                for j in range(0, len(binNfp)):
                    clipperBinNfp.append(toClipperCoordinates(binNfp[j]))

                scale_to_clipper(clipperBinNfp, self.config.clipperScale)

                clipper = pyclipper.PyClipper()
                combinedNfp = pyclipper.Paths()


                for j in range(0, len(placed)):
                    key = json.dumps({'A': placed[j].id, 'B': path.id, 'inside': false, 'Arotation': placed[j].rotation, 'Brotation': path.rotation})
                    nfp = self.nfpCache[key]

                    if not nfp:
                        continue

                    for k in range(0, len(nfp)):
                        clone = self.toClipperCoordinates(nfp[k])
                        for m in range(0, len(mClone)):
                            clone[m].X += placements[j].x
                            clone[m].Y += placements[j].y

                        scale_to_clipper(clone, self.config.clipperScale)
                        clone = ClipperLib.Clipper.CleanPolygon(clone, 0.0001*self.config.clipperScale)
                        area = Math.abs(ClipperLib.Clipper.Area(clone))
                        if clone.length > 2 and area > 0.1*self.config.clipperScale*self.config.clipperScale:
                            clipper.AddPath(clone, ClipperLib.PolyType.ptSubject, True)

                if not clipper.Execute(ClipperLib.ClipType.ctUnion, combinedNfp, ClipperLib.PolyFillType.pftNonZero, ClipperLib.PolyFillType.pftNonZero):
                    continue

                # difference with bin polygon
                finalNfp = ClipperLib.Paths()
                clipper = ClipperLib.Clipper()

                clipper.AddPaths(combinedNfp, ClipperLib.PolyType.ptClip, true)
                clipper.AddPaths(clipperBinNfp, ClipperLib.PolyType.ptSubject, true)
                if not clipper.Execute(ClipperLib.ClipType.ctDifference, finalNfp, ClipperLib.PolyFillType.pftNonZero, ClipperLib.PolyFillType.pftNonZero):
                    continue

                finalNfp = ClipperLib.Clipper.CleanPolygons(finalNfp, 0.0001*self.config.clipperScale)

                j = 0
                while j<len(finalNfp):
                    area = abs(ClipperLib.Clipper.Area(finalNfp[j]))
                    if finalNfp[j].length < 3 or area < 0.1*self.config.clipperScale*self.config.clipperScale:
                        finalNfp.splice(j,1)
                        j -= 1
                    j += 1

                if not finalNfp or len(finalNfp) == 0:
                    continue

                f = []
                for j in range(0, len(finalNfp)):
                    # back to normal scale
                    f.append(toNestCoordinates(finalNfp[j], self.config.clipperScale))
                finalNfp = f

                # choose placement that results in the smallest bounding box
                # could use convex hull instead, but it can create oddly shaped nests (triangles or long slivers) which are not optimal for real-world use
                # todo: generalize gravity direction
                minwidth = None
                minarea = None
                minx = None
                nf = None
                area = None
                shiftvector = None

                for j in range(0, len(finalNfp)):
                    nf = finalNfp[j]
                    if abs(polygonArea(nf)) < 2:
                        continue

                    for k in range(0, len(nf)):
                        allpoints = []
                        for m in range(0, len(placed)):
                            for n in range(0, len(placed[m])):
                                allpoints.append(Point(x= placed[m][n].x+placements[m].x, y= placed[m][n].y+placements[m].y))

                        shiftvector = Position(
                            x= nf[k].x-path[0].x,
                            y= nf[k].y-path[0].y,
                            id= path.id,
                            rotation= path.rotation,
                            nfp= combinedNfp
                        )

                        for m in range(0, len(path)):
                            allpoints.append(Point(x= path[m].x+shiftvector.x, y=path[m].y+shiftvector.y))

                        rectbounds = getPolygonBounds(allpoints)

                        # weigh width more, to help compress in direction of gravity
                        area = rectbounds.width*2 + rectbounds.height

                        if minarea is None or area < minarea or (GeometryUtil.almostEqual(minarea, area) and (minx is None or shiftvector.x < minx)):
                            minarea = area
                            minwidth = rectbounds.width
                            position = shiftvector
                            minx = shiftvector.x
                if position:
                    placed.append(path)
                    placements.append(position)

            if minwidth:
                fitness += minwidth / binarea

            for i in range(0, len(placed)):
                index = paths.index(placed[i])
                if index >= 0:
                    splice(paths, index,1)

            if placements and len(placements) > 0:
                allplacements.append(placements)
            else:
                break; # something went wrong

        # there were parts that couldn't be placed
        fitness += 2*len(paths)

        return {'placements': allplacements, 'fitness': fitness, 'paths': paths, 'area': binarea }
