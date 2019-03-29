import math

from svgnest.js.display import plot
from svgnest.js.geometry import Point, Polygon
from svgnest.js.geometryutil import rotate_polygon, polygon_area, get_polygon_bounds
from svgnest.js.utils import splice, NfpKey
from pyclipper import *


class Position:
    def __init__(self, x=None, y=None, id=None, rotation=None, nfp=None):
        self.x = x
        self.y = y
        self.id = id
        self.rotation = rotation
        self.nfp = nfp


# jsClipper uses X/Y instead of x/y...
def toClipperCoordinates(polygon):
    clone = []
    for point in polygon:
        clone.append([point.x, point.y])

    return clone


def toNestCoordinates(polygon, scale):
    clone = []
    for point in polygon:
        clone.append(Point(x=point[0]/scale, y=point[1]/scale))

    return clone


def rotate_polygon(polygon, degrees):
    rotated = Polygon()
    angle = degrees * math.pi / 180
    for point in polygon:
        x = point.x
        y = point.y
        x1 = x*math.cos(angle)-y*math.sin(angle)
        y1 = x*math.sin(angle)+y*math.cos(angle)

        rotated.append(Point(x=x1, y=y1))

    if polygon.children and len(polygon.children) > 0:
        rotated.children = [rotate_polygon(child, degrees) for child in polygon.children]

    return rotated


class PlacedPaths:
    def __init__(self, placements=None, fitness=None, paths=None, area=None):
        self.placements = placements
        self.fitness = fitness
        self.paths = paths
        self.area = area


class PlacementWorker:
    # return a placement for the paths/rotations given
    # happens inside a worker

    def __init__(self, binPolygon, paths, ids, rotations, config, nfpCache=None):
        self.binPolygon = binPolygon
        self.paths = paths
        self.ids = ids
        self.rotations = rotations
        self.config = config
        self.nfpCache = nfpCache or {}
        self.working = True

    def place_paths(self, paths):

        if not self.binPolygon:
            return None

        # rotate paths by given rotation
        rotated = []
        for path in paths:
            r = rotate_polygon(path, path.rotation)
            r.rotation = path.rotation
            r.source = path.source
            r.id = path.id
            rotated.append(r)

        paths = rotated

        allplacements = []
        fitness = 0
        binarea = abs(polygon_area(self.binPolygon))

        while len(paths) > 0:

            placed = []
            placements = []
            fitness += 1  # add 1 for each new bin opened (lower fitness is better)
            minwidth = None

            for i, path in enumerate(paths):

                # inner NFP
                key = NfpKey(
                    A=-1,
                    B=path.id,
                    inside=True,
                    Arotation=0,
                    Brotation=path.rotation
                )
                binNfp = self.nfpCache.get(key)

                # part unplaceable, skip
                if not binNfp or len(binNfp) == 0:
                    continue

                # ensure all necessary NFPs exist
                error = False
                for placed_path in placed:
                    key = NfpKey(
                        A=placed_path.id,
                        B=path.id,
                        inside=False,
                        Arotation=placed_path.rotation,
                        Brotation=path.rotation
                    )
                    nfp = self.nfpCache.get(key)

                    if not nfp:
                        error = True
                        break

                # part unplaceable, skip
                if error:
                    continue

                position = None
                if len(placed) == 0:
                    # first placement, put it on the left
                    for item_j in binNfp:
                        for item_k in item_j:
                            if position is None or item_k.x-path[0].x < position.x:
                                position = Position(
                                    x=item_k.x-path[0].x,
                                    y=item_k.y-path[0].y,
                                    id=path.id,
                                    rotation=path.rotation
                                )

                    placements.append(position)
                    placed.append(path)

                    continue

                clipperBinNfp = [toClipperCoordinates(bin_nfp_item) for bin_nfp_item in binNfp]

                clipperBinNfp = scale_to_clipper(clipperBinNfp, self.config.clipperScale)

                clipper = Pyclipper()

                for j in range(0, len(placed)):
                    key = NfpKey(
                        A=placed[j].id,
                        B=path.id,
                        inside=False,
                        Arotation=placed[j].rotation,
                        Brotation=path.rotation
                    )
                    nfp = self.nfpCache[key]

                    if not nfp:
                        continue

                    for k in range(0, len(nfp)):
                        clone = toClipperCoordinates(nfp[k])
                        for clone_item in clone:
                            clone_item[0] += placements[j].x
                            clone_item[1] += placements[j].y

                        clone = scale_to_clipper(clone, self.config.clipperScale)
                        CleanPolygon(clone, 0.0001 * self.config.clipperScale)
                        area = abs(Area(clone))
                        if len(clone) > 2 and area > 0.1*self.config.clipperScale*self.config.clipperScale:
                            clipper.AddPath(clone, PT_SUBJECT, True)

                try:
                    combinedNfp = clipper.Execute(CT_UNION, PFT_NONZERO, PFT_NONZERO)
                except ClipperException as e:
                    continue

                # difference with bin polygon
                clipper = Pyclipper()

                clipper.AddPaths(combinedNfp, PT_CLIP, True)
                clipper.AddPaths(clipperBinNfp, PT_SUBJECT, True)
                try:
                    finalNfp = clipper.Execute(CT_DIFFERENCE, PFT_NONZERO, PFT_NONZERO)
                except ClipperException as e:
                    continue

                finalNfp = CleanPolygons(finalNfp, 0.0001 * self.config.clipperScale)

                j = 0
                while j < len(finalNfp):
                    area = abs(Area(finalNfp[j]))
                    if len(finalNfp[j]) < 3 or area < 0.1*self.config.clipperScale*self.config.clipperScale:
                        splice(finalNfp, j, 1)
                        j -= 1
                    j += 1

                if not finalNfp or len(finalNfp) == 0:
                    continue

                f = []
                for nfp in finalNfp:
                    # back to normal scale
                    f.append(toNestCoordinates(nfp, self.config.clipperScale))
                finalNfp = f

                # choose placement that results in the smallest bounding box
                # could use convex hull instead, but it can create oddly
                # shaped nests (triangles or long slivers) which are not optimal for real-world use
                # todo: generalize gravity direction
                minwidth = None
                minarea = None
                minx = None
                nf = None
                area = None
                shiftvector = None

                for nf in finalNfp:
                    if abs(polygon_area(nf)) < 2:
                        continue

                    for item_nf in nf:
                        allpoints = Polygon()
                        for m in range(0, len(placed)):
                            for n in range(0, len(placed[m])):
                                allpoints.append(Point(x= placed[m][n].x+placements[m].x, y= placed[m][n].y+placements[m].y))

                        shiftvector = Position(
                            x=item_nf.x-path[0].x,
                            y=item_nf.y-path[0].y,
                            id=path.id,
                            rotation=path.rotation,
                            nfp=combinedNfp
                        )

                        for m in range(0, len(path)):
                            allpoints.append(Point(x=path[m].x+shiftvector.x, y=path[m].y+shiftvector.y))

                        rectbounds = get_polygon_bounds(allpoints)

                        # weigh width more, to help compress in direction of gravity
                        area = rectbounds.width*2 + rectbounds.height

                        if minarea is None or area < minarea or (almost_equal(minarea, area) and (minx is None or shiftvector.x < minx)):
                            minarea = area
                            minwidth = rectbounds.width
                            position = shiftvector
                            minx = shiftvector.x
                if position:
                    placed.append(path)
                    placements.append(position)

            if minwidth:
                fitness += minwidth / binarea

            for placed_path in placed:
                index = paths.index(placed_path)
                if index >= 0:
                    splice(paths, index, 1)

            if placements and len(placements) > 0:
                allplacements.append(placements)
            else:
                break # something went wrong

        # there were parts that couldn't be placed
        fitness += 2*len(paths)

        return PlacedPaths(placements=allplacements, fitness=fitness, paths=paths, area= binarea)
