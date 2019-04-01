"""
 SvgNest
 Licensed under the MIT license
"""
import json
import multiprocessing
import os
import threading
import time
from pyclipper import scale_to_clipper, SimplifyPolygon, PFT_NONZERO, Area, CleanPolygon, scale_from_clipper, \
    MinkowskiSum, JT_ROUND, ET_CLOSEDPOLYGON, PyclipperOffset
from random import random, shuffle

from simplejson import JSONEncoder
from svgnest.js.display import plot
from svgnest.js.geometry import Point, Polygon
from svgnest.js.geometrybase import almost_equal
from svgnest.js.geometryutil import polygon_area, point_in_polygon, get_polygon_bounds, rotate_polygon, \
    no_fit_polygon_rectangle, no_fit_polygon, is_rectangle
from svgnest.js.placementworker import PlacementWorker
from svgnest.js.svgparser import SvgParser, child_elements
from svgnest.js.utils import splice, parseInt, parseFloat, Nfp, NfpPair, NfpKey, log


class NfpCache:
    pass


class Config:
    clipperScale = 10000000
    curveTolerance = 0.3
    spacing = 0
    rotations = 4
    populationSize = 10
    mutationRate = 10
    useHoles = False
    exploreConcave = False


def to_clipper_coordinates(polygon):
    return [[point.x, point.y] for point in polygon]


def to_nest_coordinates(polygon, scale):
    return Polygon(*(Point(x=point[0]/scale, y=point[1]/scale) for point in polygon))


CLIPPER_SCALE = 10000000


class ObjectEncoder(JSONEncoder):
    def default(self, obj):
        if hasattr(obj, "to_json"):
            return self.default(obj.to_json())
        return obj


def minkowski_difference(A, B):
    Ac = to_clipper_coordinates(A)
    Ascaled = scale_to_clipper(Ac, CLIPPER_SCALE)
    Bc = to_clipper_coordinates(B)
    Bscaled = scale_to_clipper(Bc, CLIPPER_SCALE)
    for bc in Bscaled:
        bc[0] *= -1
        bc[1] *= -1
    solution = MinkowskiSum(Ascaled, Bscaled, True)
    clipperNfp = None

    largestArea = None
    for item in solution:
        n = to_nest_coordinates(item, CLIPPER_SCALE)
        sarea = polygon_area(n)
        if largestArea is None or largestArea > sarea:
            clipperNfp = n
            largestArea = sarea

    for item in clipperNfp:
        item.x += B[0].x
        item.y += B[0].y

    return [clipperNfp]


def generate_nfp(argtuple):
    pair, searchEdges, useHoles = argtuple

    if not pair:
        return None

    A = rotate_polygon(pair.A, pair.key.Arotation)
    B = rotate_polygon(pair.B, pair.key.Brotation)

    if pair.key.inside:
        if is_rectangle(A, 0.001):
            nfp = no_fit_polygon_rectangle(A, B)
        else:
            nfp = no_fit_polygon(A, B, True, searchEdges)

        # ensure all interior NFPs have the same winding direction
        if nfp and len(nfp) > 0:
            for i in range(0, len(nfp)):
                if polygon_area(nfp[i]) > 0:
                    nfp[i].reverse()
        else:
            # warning on None inner NFP
            # this is not an error, as the part may simply be
            # larger than the bin or otherwise unplaceable due to geometry
            print('NFP Warning: ' + str(pair.key))
    else:
        if searchEdges:
            nfp = no_fit_polygon(A, B, False, searchEdges)
        else:
            nfp = minkowski_difference(A, B)

        # sanity check
        if not nfp or len(nfp) == 0:
            log('NFP Error: ' % pair.key)
            log('A: %s' % A)
            log('B: %s' % B)
            return None

        for i in range(0, len(nfp)):
            # if searchEdges is active, only the first NFP is guaranteed to pass sanity check
            if not searchEdges or i == 0:
                if abs(polygon_area(nfp[i])) < abs(polygon_area(A)):
                    log('NFP Area Error: %s %s' % (abs(polygon_area(nfp[i])), pair.key))
                    log('NFP: %s' % nfp[i])
                    log('A: %s' % A)
                    log('B: %s' % B)
                    splice(nfp, i, 1)
                    return None

        if len(nfp) == 0:
            return None

        # for outer NFPs, the first is guaranteed to be the largest.
        # Any subsequent NFPs that lie inside the first are holes
        for i in range(0, len(nfp)):
            if polygon_area(nfp[i]) > 0:
                nfp[i].reverse()

            if i > 0:
                if point_in_polygon(nfp[i][0], nfp[0]):
                    if polygon_area(nfp[i]) < 0:
                        nfp[i].reverse()

        # generate nfps for children (holes of parts) if any exist
        if useHoles and A.children and len(A.children) > 0:
            Bbounds = get_polygon_bounds(B)

            for Achild in A.children:
                Abounds = get_polygon_bounds(Achild)

                # no need to find nfp if B's bounding box is too big
                if Abounds.width > Bbounds.width and Abounds.height > Bbounds.height:

                    cnfp = no_fit_polygon(Achild, B, True, searchEdges)
                    # ensure all interior NFPs have the same winding direction
                    if cnfp and len(cnfp) > 0:
                        for j in range(0, len(cnfp)):
                            if polygon_area(cnfp[j]) < 0:
                                cnfp[j].reverse()
                            nfp.append(cnfp[j])

    return Nfp(key=pair.key, value=nfp)


class Placement(list):
    def __init__(self, poly):
        super().__init__(poly)
        self._poly = poly


class SvgNest:

    def __init__(self):
        self.style = None
        self.svg = None
        self.parts = None
        self.tree = None
        self.bin = None
        self.binPolygon = None
        self.binBounds = None
        self.nfpCache = {}
        self.config = Config()
        self.working = False
        self.GA = None
        self.best = None
        self.workerTimer = None
        self.progress = 0
        self.parser = None
        self.binindex = None
        self.individual = None

    def parsesvg(self, svgstring):
        log('parse SVG...')
        # reset if in progress
        self.stop()

        self.bin = None
        self.binPolygon = None
        self.tree = None

        self.parser = SvgParser()

        # parse svg
        self.svg = self.parser.load(svgstring)

        self.style = self.parser.getStyle()

        self.svg = self.parser.clean()

        self.tree = self.get_parts(child_elements(self.svg))

        # re-order elements such that deeper elements are on top, so they can be moused over
        def zorder(paths):
            # depth-first
            length = len(paths)
            for i in range(0, length):
                if paths[i].children and len(paths[i].children) > 0:
                    zorder(paths[i].children)

        return self.svg

    def set_bin(self, element):
        if not self.svg:
            return
        self.bin = element

    def config(self, c):
        # clean up inputs

        if not c:
            return self.config

        if c.curveTolerance and not almost_equal(parseFloat(c.curveTolerance), 0):
            self.config.curveTolerance = parseFloat(c.curveTolerance)

        if 'spacing' in c:
            self.config.spacing = parseFloat(c.spacing)

        if c.rotations and parseInt(c.rotations) > 0:
            self.config.rotations = parseInt(c.rotations)

        if c.populationSize and parseInt(c.populationSize) > 2:
            self.config.populationSize = parseInt(c.populationSize)

        if c.mutationRate and parseInt(c.mutationRate) > 0:
            self.config.mutationRate = parseInt(c.mutationRate)

        if 'useHoles' in c:
            self.config.useHoles = not not c.useHoles

        if 'exploreConcave' in c:
            self.config.exploreConcave = not not c.exploreConcave

        # self.config(Config(tolerance=self.config.curveTolerance))

        self.best = None
        self.nfpCache = {}
        self.binPolygon = None
        self.GA = None

        return self.config

    # progressCallback is called when progress is made
    # displayCallback is called when a new placement has been made
    def start(self, progressCallback, displayCallback):
        if not self.svg or not self.bin:
            return False

        self.parts = child_elements(self.svg)
        self.binindex = self.parts.index(self.bin)

        if self.binindex >= 0:
            # don't process bin as a part of the tree
            splice(self.parts, self.binindex, 1)

        # build tree without bin
        tree = self.get_parts(self.parts[:])

        # offset tree recursively
        def offsetTree(t, offset, offsetFunction):
            for i in range(0, len(t)):
                offsetpaths = offsetFunction(t[i], offset)
                if len(offsetpaths) == 1:
                    # replace array items in place
                    to_add = [0, t[i].length]
                    to_add.extend(offsetpaths[0])
                    splice(t[i], to_add)

                if t[i].children and len(t[i].children) > 0:
                    offsetTree(t[i].children, -offset, offsetFunction)

        offsetTree(tree, 0.5 * self.config.spacing, self.polygon_offset)

        binPolygon = self.parser.polygonify(self.bin)
        binPolygon = self.clean_polygon(binPolygon)

        if not binPolygon or len(binPolygon) < 3:
            return False

        self.binBounds = get_polygon_bounds(binPolygon)

        if self.config.spacing > 0:
            offsetBin = self.polygon_offset(binPolygon, -0.5 * self.config.spacing)
            if len(offsetBin) == 1:
                # if the offset contains 0 or more than 1 path, something went wrong.
                binPolygon = offsetBin.pop()

        binPolygon.id = -1

        # put bin on origin
        xbinmax = binPolygon[0].x
        xbinmin = binPolygon[0].x
        ybinmax = binPolygon[0].y
        ybinmin = binPolygon[0].y

        for item in binPolygon:
            if item.x > xbinmax:
                xbinmax = item.x
            elif item.x < xbinmin:
                xbinmin = item.x
            if item.y > ybinmax:
                ybinmax = item.y
            elif item.y < ybinmin:
                ybinmin = item.y

        for i in range(0, len(binPolygon)):
            binPolygon[i].x -= xbinmin
            binPolygon[i].y -= ybinmin

        binPolygon.width = xbinmax - xbinmin
        binPolygon.height = ybinmax - ybinmin

        # all paths need to have the same winding direction
        if polygon_area(binPolygon) > 0:
            binPolygon.reverse()

        self.binPolygon = binPolygon

        # remove duplicate endpoints, ensure counterclockwise winding direction
        for i in range(0, len(tree)):
            start = tree[i][0]
            end = tree[i][-1]
            if start == end or start.almost_equal(end):
                tree[i].pop()

            if polygon_area(tree[i]) > 0:
                tree[i].reverse()

        self.working = False

        def worker_fn():
            self.launch_workers(tree, binPolygon, self.config, displayCallback)
            self.working = False

        while True:
            if not self.working:
                self.working = True
                worker = threading.Thread(target=worker_fn)
                worker.start()

            progressCallback(self.progress)
            time.sleep(0.1)

    def launch_workers(self, tree, binPolygon, config, displayCallback):
        print('launch_workers')
        if self.GA is None:
            # initiate new GA
            adam = tree[:]

            # seed with decreasing area
            adam.sort(key=lambda a: abs(polygon_area(a)))

            self.GA = GeneticAlgorithm(adam, binPolygon, config)

        self.individual = None

        # evaluate all members of the population
        for member in self.GA.population:
            if not member.fitness:
                self.individual = member
                break

        if self.individual is None:
            # all individuals have been evaluated, start next generation
            self.GA.generation()
            self.individual = self.GA.population[1]

        placelist = self.individual.placement
        rotations = self.individual.rotation

        ids = []
        for i, place in enumerate(placelist):
            ids.append(place.id)
            place.rotation = rotations[i]

        nfpPairs = []
        newCache = {}

        for i, part in enumerate(placelist):
            key = NfpKey(A=binPolygon.id, B=part.id, inside=True,
                         Arotation=0, Brotation=rotations[i])
            if not self.nfpCache.get(key):
                nfpPairs.append(NfpPair(A=binPolygon, B=part, key=key))
            else:
                newCache[key] = self.nfpCache[key]

            for j in range(0, i):
                placed = placelist[j]
                key = NfpKey(A=placed.id, B=part.id, inside=False,
                             Arotation=rotations[j], Brotation=rotations[i])
                if not self.nfpCache.get(key):
                    nfpPairs.append(NfpPair(A=placed, B=part, key=key))
                else:
                    newCache[key] = self.nfpCache[key]

        # only keep cache for one cycle
        nfpCache = newCache

        searchEdges = self.config.exploreConcave
        useHoles = self.config.useHoles

        worker = PlacementWorker(binPolygon, placelist[:], ids, rotations, config, nfpCache)
        """
        p = Parallel(nfpPairs, {
            env: {
                'binPolygon': binPolygon,
                'searchEdges': config.exploreConcave,
                'useHoles': config.useHoles
            },
            evalPath: 'util/eval.js'
        })
        
        self = this
        spawncount = 0

        def _spawnMapWorker(i, cb, done, env, wrk):
            # hijack the worker call to check progress
            spawncount += 1
            progress = spawncount/ len(nfpPairs)
            return Parallel.prototype._spawnMapWorker.call(p, i, cb, done, env, wrk)

        p._spawnMapWorker = _spawnMapWorker
        """

        pool = multiprocessing.Pool()

        try:
            generatedNfp = pool.map(generate_nfp, ((p, searchEdges, useHoles) for p in nfpPairs))
            with open(os.path.join('raw', 'generated_nfp.json'), 'w+') as raw:
                raw_data = [
                    {'A': nfpPairs[i].A.x_y, 'B': nfpPairs[i].B.x_y, 'nfp': [item.x_y for item in p.value]} for i, p in enumerate(generatedNfp) if p is not None
                ]
                json.dump(raw_data, raw, indent=True)
            self.p_then(displayCallback, placelist, worker, generatedNfp)
            self.progress += 1
        finally:
            pool.close()

    def p_then(self, displayCallback, placelist, worker, generatedNfp):
        if generatedNfp:
            for Nfp in generatedNfp:
                if Nfp:
                    # a None nfp means the nfp could not be generated,
                    # either because the parts simply don't fit or an error in the nfp algo
                    self.nfpCache[Nfp.key] = Nfp.value
        worker.nfpCache = self.nfpCache

        pool2 = multiprocessing.Pool()

        try:
            placements = pool2.map(worker.place_paths, [Placement(placelist)])
            self.treat_placements(worker, placelist, displayCallback, placements)
        finally:
            pool2.close()

    def treat_placements(self, worker, placelist, displayCallback, placements):
        if not placements or len(placements) == 0:
            return

        self.individual.fitness = placements[0].fitness
        bestresult = placements[0]

        for i in range(1, len(placements)):
            if placements[i].fitness < bestresult.fitness:
                bestresult = placements[i]

        if not self.best or bestresult.fitness < self.best.fitness:
            self.best = bestresult

            placed_area = 0
            total_area = 0
            num_parts = len(placelist)
            num_placed_parts = 0

            for best_placement in self.best.placements:
                total_area += abs(polygon_area(self.binPolygon))
                for best_placement_item in best_placement:
                    placed_area += abs(polygon_area(self.tree[best_placement_item.id]))
                    num_placed_parts += 1
            if total_area != 0:
                displayCallback(self, self.apply_placement(self.best.placements), placed_area / total_area,
                                '{0}/{1}'.format(num_placed_parts, num_parts))
                print('displayed')
        worker.working = False

    # assuming no intersections, return a tree where odd leaves are parts and even ones are holes
    # might be easier to use the DOM, but paths can't have paths as children. So we'll just make our own tree.
    def get_parts(self, paths):

        polygons = []

        num_children = len(paths)
        for i in range(0, num_children):
            poly = self.parser.polygonify(paths[i])
            poly = self.clean_polygon(poly)

            # todo: warn user if poly could not be processed and is excluded from the nest
            if poly and len(poly) > 2 and abs(polygon_area(poly)) > self.config.curveTolerance ** 2:
                poly.source = i
                polygons.append(poly)

        def to_tree(list_, idstart=None):
            parents = []
            i = 0

            # assign a unique id to each leaf
            id = idstart or 0

            for i in range(0, len(list_)):
                p = list_[i]

                ischild = False
                for j in range(0, len(list_)):
                    if j == i:
                        continue
                    if point_in_polygon(p[0], list_[j]):
                        list_[j].children.append(p)
                        p.parent = list_[j]
                        ischild = True
                        break

                if not ischild:
                    parents.append(p)
            # for(i=0; i<list.length; i++){
            #     if(parents.indexOf(list[i]) < 0){
            #         list.splice(i, 1);
            #         i--;
            #     }
            # }
            while i < len(list_):
                if list_[i] not in parents:
                    splice(list_, i, 1)
                    i -= 1

                i += 1

            for parent in parents:
                parent.id = id
                id += 1

            for parent in parents:
                if parent.children:
                    id = to_tree(parent.children, id)

            return id

        # turn the list into a tree
        to_tree(polygons)

        return polygons

    # use the clipper library to return an offset to the given polygon.
    # Positive offset expands the polygon, negative contracts
    # note that this returns an array of polygons
    def polygon_offset(self, polygon, offset):
        if not offset or offset == 0 or almost_equal(offset, 0):
            return polygon

        p = self.svg_to_clipper(polygon)

        miterLimit = 2
        co = PyclipperOffset(miterLimit, self.config.curveTolerance * self.config.clipperScale)
        co.AddPath(p, JT_ROUND, ET_CLOSEDPOLYGON)

        newpaths = co.Execute(offset * self.config.clipperScale)

        result = []
        for newpath in newpaths:
            result.append(self.clipper_to_svg(newpath))

        return result

    # returns a less complex polygon that satisfies the curve tolerance
    def clean_polygon(this, polygon):
        p = this.svg_to_clipper(polygon)
        # remove self-intersections and find the biggest polygon that's left
        simple = SimplifyPolygon(p, PFT_NONZERO)

        if not simple or len(simple) == 0:
            return None

        biggest = simple[0]
        biggestarea = abs(Area(biggest))
        for i in range(1, len(simple)):
            area = abs(Area(simple[i]))
            if area > biggestarea:
                biggest = simple[i]
                biggestarea = area

        # clean up singularities, coincident points and edges
        clean = CleanPolygon(biggest, this.config.curveTolerance * this.config.clipperScale)

        if not clean or len(clean) == 0:
            return None

        return this.clipper_to_svg(clean)

    # converts a polygon from normal float coordinates to integer coordinates used by clipper, as well as x/y -> X/Y
    def svg_to_clipper(self, polygon):
        clip = [[point.x, point.y] for point in polygon]

        return scale_to_clipper(clip, self.config.clipperScale)

    def clipper_to_svg(self, polygon):

        normal = scale_from_clipper(polygon, self.config.clipperScale)

        return Polygon(*(Point(x=polygon[0], y=polygon[1]) for polygon in normal))

    # returns an array of SVG elements that represent the placement, for export or rendering
    def apply_placement(self, placement):
        clone = [part.cloneNode(False) for part in self.parts]

        # flatten the given tree into a list
        def _flattenTree(t, hole):
            flat = []
            for item_t in t:
                flat.append(item_t)
                item_t.hole = hole
                if item_t.children and len(item_t.children) > 0:
                    flat.extend(_flattenTree(item_t.children, not hole))

            return flat

        svglist = []

        for item in placement:
            newsvg = self.svg.cloneNode(False)
            document = self.svg.ownerDocument
            newsvg.setAttribute('viewBox', '0 0 {0} {1}'.format(self.binBounds.width, self.binBounds.height))
            newsvg.setAttribute('width', str(self.binBounds.width) + 'px')
            newsvg.setAttribute('height', str(self.binBounds.height) + 'px')
            binclone = self.bin.cloneNode(False)

            binclone.setAttribute('class', 'bin')
            binclone.setAttribute('transform',
                                  'translate({0} {1})'.format(-self.binBounds.x, -self.binBounds.y))
            newsvg.appendChild(binclone)

            for p in item:
                if p.id == self.binindex:
                    continue
                part = self.tree[p.id]

                # the original path could have transforms and stuff on it, so apply our transforms on a group
                partgroup = document.createElementNS(self.svg.namespaceURI, 'g')
                partgroup.setAttribute('transform',
                                       'translate({0} {1}) rotate({2})'.format(p.x, p.y, p.rotation))
                partgroup.appendChild(clone[part.source])

                if part.children and len(part.children) > 0:
                    print('part has children')
                    flattened = _flattenTree(part.children, True)
                    for flattened_item in flattened:
                        try:
                            c = clone[flattened_item.source].cloneNode(False)
                        except IndexError:
                            continue
                        # add class to indicate hole
                        if flattened_item.hole and (
                                not c.getAttribute('class') or 'hole' not in c.getAttribute('class') < 0):
                            c.setAttribute('class', c.getAttribute('class') + ' hole')
                        partgroup.appendChild(c)

                newsvg.appendChild(partgroup)
            svglist.append(newsvg)

        return svglist

    def stop(self):
        self.working = False
        if self.workerTimer:
            # clearInterval(workerTimer)
            pass


class Individual:
    def __init__(self, placement=None, rotation=None):
        self.placement = placement
        self.rotation = rotation
        self.fitness = 0


class GeneticAlgorithm:

    def __init__(self, adam, bin, config):
        self.config = config or {'populationSize': 10, 'mutationRate': 10, 'rotations': 4}
        self.binBounds = get_polygon_bounds(bin)

        # population is an array of individuals. Each individual is a object representing the order
        # of insertion and the angle each part is rotated
        angles = []
        for part in adam:
            angles.append(self.random_angle(part))

        self.population = [Individual(placement=adam, rotation=angles)]

        while len(self.population) < config.populationSize:
            mutant = self.mutate(self.population[0])
            self.population.append(mutant)

    # returns a random angle of insertion
    def random_angle(self, part):

        angleList = []
        for i in range(0, max(self.config.rotations, 1)):
            angleList.append(i * (360 / self.config.rotations))

        shuffle(angleList)

        for angle in angleList:
            rotatedPart = rotate_polygon(part, angle)

            # don't use obviously bad angles where the part doesn't fit in the bin
            if rotatedPart.width < self.binBounds.width and rotatedPart.height < self.binBounds.height:
                return angle

        return 0

    # returns a mutated individual with the given mutation rate
    def mutate(self, individual):
        clone = Individual(placement=individual.placement, rotation=individual.rotation)
        for i, clone_placement in enumerate(clone.placement):
            rand = random()
            if rand < 0.01 * self.config.mutationRate:
                # swap current part with next part
                j = i + 1

                if j < len(clone.placement):
                    temp = clone_placement
                    clone.placement[i] = clone.placement[j]
                    clone.placement[j] = temp

            rand = random()
            if rand < 0.01 * self.config.mutationRate:
                clone.rotation[i] = self.random_angle(clone_placement)

        return clone

    # single point crossover
    def mate(self, male, female):
        cutpoint = round(min(max(random(), 0.1), 0.9) * (len(male.placement) - 1))

        gene1 = male.placement[:cutpoint]
        rot1 = male.rotation[:cutpoint]

        gene2 = female.placement[:cutpoint]
        rot2 = female.rotation[:cutpoint]

        def contains(gene, id):
            for item in gene:
                if item.id == id:
                    return True
            return False

        for i, item in enumerate(female.placement):
            if not contains(gene1, item.id):
                gene1.append(item)
                rot1.append(female.rotation[i])

        for i, item in enumerate(male.placement):
            if not contains(gene2, item.id):
                gene2.append(item)
                rot2.append(male.rotation[i])

        return [Individual(placement=gene1, rotation=rot1), Individual(placement=gene2, rotation=rot2)]

    def generation(self):

        # Individuals with higher fitness are more likely to be selected for mating
        self.population.sort(key=lambda a: a.fitness)

        # fittest individual is preserved in the new generation (elitism)
        newpopulation = [self.population[0]]

        while len(newpopulation) < len(self.population):
            male = self.randomWeightedIndividual()
            female = self.randomWeightedIndividual(male)

            # each mating produces two children
            children = self.mate(male, female)

            # slightly mutate children
            newpopulation.append(self.mutate(children[0]))

            if len(newpopulation) < len(self.population):
                newpopulation.append(self.mutate(children[1]))

        self.population = newpopulation

    # returns a random individual from the population,
    # weighted to the front of the list (lower fitness value is more likely to be selected)
    def randomWeightedIndividual(self, exclude=None):
        pop = self.population[:]

        if exclude and exclude in pop:
            splice(pop, pop.index(exclude), 1)

        rand = random()

        lower = 0
        weight = 1 / len(pop)
        upper = weight

        for i, item in enumerate(pop):
            # if the random number falls between lower and upper bounds, select this individual
            if lower < rand < upper:
                return item
            lower = upper
            upper += 2 * weight * (len(pop) - i) / len(pop)

        return pop[0]
