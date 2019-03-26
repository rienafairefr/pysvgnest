"""
 SvgNest
 Licensed under the MIT license
"""
import math
from pyclipper import scale_to_clipper, SimplifyPolygon, PFT_NONZERO, Area, CleanPolygon, scale_from_clipper

from svgnest.js.geometry import Point, Polygon
from svgnest.js.geometryutil import GeometryUtil, polygonArea, pointInPolygon
from svgnest.js.svgparser import SvgParser, parseFloat, childElements


class NfpCache:
    pass


class Config:
    clipperScale= 10000000
    curveTolerance= 0.3
    spacing= 0
    rotations= 4
    populationSize= 10
    mutationRate= 10
    useHoles= False
    exploreConcave= False


def parseInt(value):
    return int(value)


def splice(target, start, delete_count=None, *items):
    """Remove existing elements and/or add new elements to a list.

    target        the target list (will be changed)
    start         index of starting position
    delete_count  number of items to remove (default: len(target) - start)
    *items        items to insert at start index

    Returns a new list of removed items (or an empty list)
    """
    if delete_count is None:
        delete_count = len(target) - start

    # store removed range in a separate list and replace with *items
    total = start + delete_count
    removed = target[start:total]
    target[start:total] = items

    return removed


class SvgNest:
    
    def __init__(self):
        self.style = None
        self.svg = None
        self.parts = None
        self.tree = None
        self.bin = None
        self.binPolygon = None
        self.binBounds= None
        self.nfpCache = {}
        self.config = Config()
        self.working = False
        self.GA = None
        self.best = None
        self.workerTimer = None
        self.progress = 0
    
    def parsesvg(this, svgstring):
        # reset if in progress
        this.stop()
        
        this.bin = None
        this.binPolygon = None
        this.tree = None

        this.parser = SvgParser()

        # parse svg
        this.svg = this.parser.load(svgstring)
        
        this.style = this.parser.getStyle()

        this.svg = this.parser.clean()
        
        this.tree = this.getParts(childElements(this.svg))

        # re-order elements such that deeper elements are on top, so they can be moused over
        def zorder(paths):
            # depth-first
            length = len(paths)
            for i in range(0, length):
                if paths[i].children and len(paths[i].children) > 0:
                    zorder(paths[i].children)

        return this.svg

    def setbin(self, element):
        if not self.svg:
            return
        self.bin = element

    def config(this, c):
        # clean up inputs
        
        if not c:
            return this.config

        if c.curveTolerance and not GeometryUtil.almostEqual(parseFloat(c.curveTolerance), 0):
            this.config.curveTolerance =  this.parseFloat(c.curveTolerance)

        if 'spacing' in c:
            this.config.spacing = parseFloat(c.spacing)

        if c.rotations and parseInt(c.rotations) > 0:
            this.config.rotations = parseInt(c.rotations)

        if c.populationSize and parseInt(c.populationSize) > 2:
            this.config.populationSize = parseInt(c.populationSize)

        if c.mutationRate and parseInt(c.mutationRate) > 0:
            this.config.mutationRate = parseInt(c.mutationRate)

        if 'useHoles' in c:
            this.config.useHoles = not not c.useHoles

        if 'exploreConcave' in c:
            this.config.exploreConcave = not not c.exploreConcave

        this.config({ 'tolerance': this.config.curveTolerance})
        
        this.best = None
        this.nfpCache = {}
        this.binPolygon = None
        this.GA = None
                    
        return this.config

    # progressCallback is called when progress is made
    # displayCallback is called when a new placement has been made
    def start(this, progressCallback, displayCallback):
        if not this.svg or not this.bin:
            return False

        parts = list(this.svg.children)
        binindex = parts.index(bin)
        
        if binindex >= 0:
            # don't process bin as a part of the tree
            splice(parts, binindex, 1)

        # build tree without bin
        tree = this.getParts(parts[:])
        
        # offset tree recursively
        def offsetTree(t, offset, offsetFunction):
            for i in range(0, len(t)):
                offsetpaths = offsetFunction(t[i], offset)
                if offsetpaths.length == 1:
                    # replace array items in place
                    Array.prototype.splice.apply(t[i], [0, t[i].length].concat(offsetpaths[0]))

                if t[i].children and len(t[i].children) > 0:
                    offsetTree(t[i].children, -offset, offsetFunction)

        offsetTree(tree, 0.5 * this.config.spacing, this.polygonOffset.bind(this))

        binPolygon = SvgParser.polygonify(bin)
        binPolygon = this.cleanPolygon(binPolygon)
                    
        if not binPolygon or len(binPolygon) < 3:
            return False

        this.binBounds = GeometryUtil.getPolygonBounds(binPolygon)
                    
        if this.config.spacing > 0:
            offsetBin = this.polygonOffset(binPolygon, -0.5*config.spacing)
            if len(offsetBin) == 1:
                # if the offset contains 0 or more than 1 path, something went wrong.
                binPolygon = offsetBin.pop()

        binPolygon.id = -1
        
        # put bin on origin
        xbinmax = binPolygon[0].x
        xbinmin = binPolygon[0].x
        ybinmax = binPolygon[0].y
        binmin = binPolygon[0].y
        
        for i in range(1, len(binPolygon)):
            if binPolygon[i].x > xbinmax:
                xbinmax = binPolygon[i].x
            elif binPolygon[i].x < xbinmin:
                xbinmin = binPolygon[i].x
            if binPolygon[i].y > ybinmax:
                ybinmax = binPolygon[i].y
            elif binPolygon[i].y < ybinmin:
                ybinmin = binPolygon[i].y

        for i in range(0, len(binPolygon)):
            binPolygon[i].x -= xbinmin
            binPolygon[i].y -= ybinmin

        binPolygon.width = xbinmax-xbinmin
        binPolygon.height = ybinmax-ybinmin
        
        # all paths need to have the same winding direction
        if GeometryUtil.polygonArea(binPolygon) > 0:
            binPolygon.reverse()

        # remove duplicate endpoints, ensure counterclockwise winding direction
        for i in range(0, len(tree)):
            start = tree[i][0]
            end = tree[i][tree[i].length-1]
            if start == end or (GeometryUtil.almostEqual(start.x,end.x) and GeometryUtil.almostEqual(start.y,end.y)):
                tree[i].pop()

            if GeometryUtil.polygonArea(tree[i]) > 0:
                tree[i].reverse()

        self = this
        this.working = False


        def workerTimer():
            if not self.working:
                self.launchWorkers.call(self, tree, binPolygon, this.config, progressCallback, displayCallback)
                self.working = True

            progressCallback(progress)
            time.sleep(0.1)
        
        threading.thread(workerTimer).start()


    def launchWorkers(this, tree, binPolygon, config, progressCallback, displayCallback):
        def shuffle(array):
          currentIndex = array.length
          temporaryValue = None
          randomIndex = 0

          # While there remain elements to shuffle...
          while 0 != currentIndex:

            # Pick a remaining element...
            randomIndex = math.floor(math.random() * currentIndex)
            currentIndex -= 1

             # And swap it with the current element.
            temporaryValue = array[currentIndex]
            array[currentIndex] = array[randomIndex]
            array[randomIndex] = temporaryValue

          return array

        i = None
        j= None
        
        if this.GA is None:
            # initiate new GA
            adam = tree.slice(0)

            # seed with decreasing area
            adam.sort(lambda a, b: abs(GeometryUtil.polygonArea(b)) - abs(GeometryUtil.polygonArea(a)))

            this.GA = GeneticAlgorithm(adam, binPolygon, config)

        individual = None
        
        # evaluate all members of the population
        for i in range(0, this.GA.population.length):
            if not GA.population[i].fitness:
                individual = GA.population[i]
                break

        if individual is None:
            # all individuals have been evaluated, start next generation
            this.GA.generation()
            individual = GA.population[1]

        placelist = individual.placement
        rotations = individual.rotation
        
        ids = []
        for i in range(0, len(placelist)):
            ids.append(placelist[i].id)
            placelist[i].rotation = rotations[i]

        nfpPairs = []
        key
        newCache = NfpCache()
        
        for i in range(0, len(pacelist)):
            part = placelist[i]
            key = {'A': binPolygon.id, 'B': part.id, 'inside': True, 'Arotation': 0, 'Brotation': rotations[i]}
            json_key = json.dumps(key)
            if not nfpCache[json_key]:
                nfpPairs.append({A: binPolygon, B: part, key: key})
            else:
                newCache[json_key] = nfpCache[json_key]

            for j in range(0, i):
                placed = placelist[j]
                key = {'A': placed.id, 'B': part.id, 'inside': False, 'Arotation': rotations[j], 'Brotation': rotations[i]}
                json_key = json.dumps(key)
                if not nfpCache[json_key]:
                    nfpPairs.append({'A': placed, 'B': part, 'key': key})
                else:
                    newCache[json_key] = nfpCache[json_key]

        # only keep cache for one cycle
        nfpCache = newCache
        
        worker = PlacementWorker(binPolygon, placelist.slice(0), ids, rotations, config, nfpCache)
        
        p = Parallel(nfpPairs, {
            env: {
                'binPolygon': binPolygon,
                'searchEdges': config.exploreConcave,
                'useHoles': config.useHoles
            },
            evalPath: 'util/eval.js'
        })
        
        p.require('matrix.js')
        p.require('geometryutil.js')
        p.require('placementworker.js')
        p.require('clipper.js')
        
        self = this
        spawncount = 0

        def _spawnMapWorker(i, cb, done, env, wrk):
            # hijack the worker call to check progress
            spawncount += 1
            progress = spawncount/ len(nfpPairs)
            return Parallel.prototype._spawnMapWorker.call(p, i, cb, done, env, wrk)

        p._spawnMapWorker = _spawnMapWorker


        def p_map(pair):
            if not pair or len(pair) == 0:
                return None
            searchEdges = env.searchEdges
            useHoles = env.useHoles

            A = rotatePolygon(pair.A, pair.key.Arotation)
            B = rotatePolygon(pair.B, pair.key.Brotation)

            nfp = None

            if pair.key.inside:
                if GeometryUtil.isRectangle(A, 0.001):
                    nfp = GeometryUtil.noFitPolygonRectangle(A,B)
                else:
                    nfp = GeometryUtil.noFitPolygon(A,B,true,searchEdges)

                # ensure all interior NFPs have the same winding direction
                if nfp and len(nfp) > 0:
                    for i in range(0, len(nfp)):
                        if GeometryUtil.polygonArea(nfp[i]) > 0:
                            nfp[i].reverse()
                else:
                    # warning on None inner NFP
                    # this is not an error, as the part may simply be larger than the bin or otherwise unplaceable due to geometry
                    log('NFP Warning: ', pair.key)
            else:
                if searchEdges:
                    nfp = GeometryUtil.noFitPolygon(A,B,false,searchEdges)
                else:
                    nfp = minkowskiDifference(A,B)
                # sanity check
                if not nfp or len(nfp) == 0:
                    log('NFP Error: ', pair.key)
                    log('A: ',JSON.stringify(A))
                    log('B: ',JSON.stringify(B))
                    return None

                for i in range(0, len(nfp)):
                    if not searchEdges or i==0: # if searchedges is active, only the first NFP is guaranteed to pass sanity check
                        if math.abs(GeometryUtil.polygonArea(nfp[i])) < Math.abs(GeometryUtil.polygonArea(A)):
                            log('NFP Area Error: ', Math.abs(GeometryUtil.polygonArea(nfp[i])), pair.key)
                            log('NFP:', json.dumps(nfp[i]))
                            log('A: ',json.dumps(A))
                            log('B: ',json.dumps(B))
                            nfp.splice(i,1)
                            return None

                if nfp.length == 0:
                    return None

                # for outer NFPs, the first is guaranteed to be the largest. Any subsequent NFPs that lie inside the first are holes
                for i in range(0, len(nfp)):
                    if GeometryUtil.polygonArea(nfp[i]) > 0:
                        nfp[i].reverse()

                    if i > 0:
                        if GeometryUtil.pointInPolygon(nfp[i][0], nfp[0]):
                            if GeometryUtil.polygonArea(nfp[i]) < 0:
                                nfp[i].reverse()

                # generate nfps for children (holes of parts) if any exist
                if useHoles and A.children and len(A.children) > 0:
                    Bbounds = GeometryUtil.getPolygonBounds(B)

                    for i in range(0, len(children)):
                        Abounds = GeometryUtil.getPolygonBounds(A.children[i])

                        # no need to find nfp if B's bounding box is too big
                        if Abounds.width > Bbounds.width and Abounds.height > Bbounds.height:

                            cnfp = GeometryUtil.noFitPolygon(A.children[i],B,true,searchEdges)
                            # ensure all interior NFPs have the same winding direction
                            if cnfp and len(cnfp) > 0:
                                for j in range(0, len(cnfp)):
                                    if GeometryUtil.polygonArea(cnfp[j]) < 0:
                                        cnfp[j].reverse()
                                    nfp.append(cnfp[j])

            def log(args):
                print(args)

            def toClipperCoordinates(polygon):
                clone = []
                for i in range(0, len(polygon)):
                    clone.append({
                        'X': polygon[i].x,
                        'Y': polygon[i].y
                    })

                return clone

            def toNestCoordinates(polygon, scale):
                clone = []
                for i in range(0, len(polygon)):
                    clone.push({
                        'x': polygon[i].X/scale,
                        'y': polygon[i].Y/scale
                    })

                return clone

            def minkowskiDifference(A, B):
                Ac = toClipperCoordinates(A)
                ClipperLib.JS.ScaleUpPath(Ac, 10000000)
                Bc = toClipperCoordinates(B)
                ClipperLib.JS.ScaleUpPath(Bc, 10000000)
                for i in range(0, len(Bc)):
                    Bc[i].X *= -1
                    Bc[i].Y *= -1
                solution = ClipperLib.Clipper.MinkowskiSum(Ac, Bc, true)
                clipperNfp = None

                largestArea = None
                for i in range(0, len(solution)):
                    n = toNestCoordinates(solution[i], 10000000)
                    sarea = GeometryUtil.polygonArea(n)
                    if largestArea is None or largestArea > sarea:
                        clipperNfp = n
                        largestArea = sarea

                for i in range(0, len(clipperNfp)):
                    clipperNfp[i].x += B[0].x
                    clipperNfp[i].y += B[0].y

                return [clipperNfp]

            return {'key': pair.key, 'value': nfp}

        def print_fn(err):
            print(err)

        def p_then(generatedNfp):
            if(generatedNfp):
                for i in range(0, len(generatedNfp)):
                    Nfp = generatedNfp[i]

                    if Nfp:
                        # a None nfp means the nfp could not be generated, either because the parts simply don't fit or an error in the nfp algo
                        key = json.dumps(Nfp.key)
                        nfpCache[key] = Nfp.value
            worker.nfpCache = nfpCache

            # can't use .spawn because our data is an array
            p2 = Parallel([placelist.slice(0)], {
                env: {
                    self: worker
                },
                evalPath: 'util/eval.js'
            })

            p2.require('json.js')
            p2.require('clipper.js')
            p2.require('matrix.js')
            p2.require('geometryutil.js')
            p2.require('placementworker.js');

            def p2_map(placements):
                if not placements or len(placements) == 0:
                    return

                individual.fitness = placements[0].fitness
                bestresult = placements[0]

                for i in range(1, len(placements)):
                    if placements[i].fitness < bestresult.fitness:
                        bestresult = placements[i]

                if not best or bestresult.fitness < best.fitness:
                    best = bestresult

                    placedArea = 0
                    totalArea = 0
                    numParts = placelist.length
                    numPlacedParts = 0

                    for i in range(0, len(best.placements)):
                        totalArea += Math.abs(GeometryUtil.polygonArea(binPolygon))
                        for j in range(0, len(best.placements[i])):
                            placedArea += Math.abs(GeometryUtil.polygonArea(tree[best.placements[i][j].id]))
                            numPlacedParts += 1
                    displayCallback(self.applyPlacement(best.placements), placedArea/totalArea, numPlacedParts+'/'+numParts)
                else:
                    displayCallback()
                self.working = false

            p2.map(worker.placePaths).then(p2_map, print_fn)

        p.map(p_map).then(p_then, print_fn)

    # assuming no intersections, return a tree where odd leaves are parts and even ones are holes
    # might be easier to use the DOM, but paths can't have paths as children. So we'll just make our own tree.
    def getParts(this, paths):
        
        i = 0
        k = 0
        polygons = []
        
        numChildren = len(paths)
        for i in range(0, numChildren):
            poly = this.parser.polygonify(paths[i])
            poly = Polygon(this.cleanPolygon(poly))
            
            # todo: warn user if poly could not be processed and is excluded from the nest
            if poly and len(poly) > 2 and abs(polygonArea(poly)) > this.config.curveTolerance**2 :
                poly.source = i
                polygons.append(poly)

        def toTree(list_, idstart=None):
            parents = []
            i = None
            j = None
            
            # assign a unique id to each leaf
            id = idstart or 0
            
            for i in range(0, len(list_)):
                p = list_[i]
                
                ischild = False
                for j in range(0, len(list_)):
                    if j == i:
                        continue
                    if pointInPolygon(p[0], list_[j]) == True:
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

            for i in range(0, len(parents)):
                parents[i].id = id
                id += 1

            for i in range(0, len(parents)):
                if parents[i].children:
                    id = toTree(parents[i].children, id)

            return id

        # turn the list into a tree
        toTree(polygons)
        
        return polygons

    # use the clipper library to return an offset to the given polygon. Positive offset expands the polygon, negative contracts
    # note that this returns an array of polygons
    def polygonOffset(this, polygon, offset):
        if not offset or offset == 0 or GeometryUtil.almostEqual(offset, 0):
            return polygon

        p = this.svgToClipper(polygon)
        
        miterLimit = 2
        co = ClipperLib.ClipperOffset(miterLimit, config.curveTolerance*config.clipperScale)
        co.AddPath(p, ClipperLib.JoinType.jtRound, ClipperLib.EndType.etClosedPolygon)
        
        newpaths = ClipperLib.Paths()
        co.Execute(newpaths, offset*config.clipperScale)
                    
        result = []
        for i in range(0, len(newpaths)):
            result.append(this.clipperToSvg(newpaths[i]))

        return result

    # returns a less complex polygon that satisfies the curve tolerance
    def cleanPolygon(this, polygon):
        p = this.svgToClipper(polygon)
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

        return this.clipperToSvg(clean)

    # converts a polygon from normal float coordinates to integer coordinates used by clipper, as well as x/y -> X/Y
    def svgToClipper(self, polygon):
        clip = []
        for i in range(0, len(polygon)):
            clip.append([polygon[i].x, polygon[i].y])

        scaled = scale_to_clipper(clip, self.config.clipperScale)
        
        return scaled

    def clipperToSvg(self, polygon):

        normal = scale_from_clipper(polygon, self.config.clipperScale)

        return [Point(x=polygon[0], y=polygon[1]) for polygon in normal]

    # returns an array of SVG elements that represent the placement, for export or rendering
    def applyPlacement(this, placement):
        i,j,k = 0,0,0
        clone = []
        for i in range(0, len(parts)):
            clone.append(parts[i].cloneNode(False))

        svglist = []

        for i in range(0, len(placement)):
            newsvg = svg.cloneNode(false)
            newsvg.setAttribute('viewBox', '0 0 '+binBounds.width+' '+binBounds.height)
            newsvg.setAttribute('width',binBounds.width + 'px')
            newsvg.setAttribute('height',binBounds.height + 'px')
            binclone = bin.cloneNode(false)
            
            binclone.setAttribute('class','bin')
            binclone.setAttribute('transform','translate('+(-binBounds.x)+' '+(-binBounds.y)+')')
            newsvg.appendChild(binclone)

            for j in range(0, len(placement[i])):
                p = placement[i][j]
                part = tree[p.id]
                
                # the original path could have transforms and stuff on it, so apply our transforms on a group
                partgroup = document.createElementNS(svg.namespaceURI, 'g')
                partgroup.setAttribute('transform','translate('+p.x+' '+p.y+') rotate('+p.rotation+')')
                partgroup.appendChild(clone[part.source])
                
                if part.children and len(part.children) > 0:
                    flattened = _flattenTree(part.children, true)
                    for k in range(0, len(flattened)):
                        
                        c = clone[flattened[k].source]
                        # add class to indicate hole
                        if flattened[k].hole and (not c.getAttribute('class') or c.getAttribute('class').indexOf('hole') < 0):
                            c.setAttribute('class',c.getAttribute('class')+' hole')
                        partgroup.appendChild(c)

                newsvg.appendChild(partgroup)

            svglist.push(newsvg)

        # flatten the given tree into a list
        def _flattenTree(t, hole):
            flat = []
            for i in range(0, len(t)):
                flat.append(t[i])
                t[i].hole = hole
                if t[i].children and len(t[i].children) > 0:
                    flat = flat.concat(_flattenTree(t[i].children, not hole))

            return flat

        return svglist

    def stop(this):
        this.working = False
        if this.workerTimer:
            clearInterval(workerTimer)

class GeneticAlgorithm:

    def __init__(this, adam, bin, config):
        this.config = config or { 'populationSize': 10, 'mutationRate': 10, 'rotations': 4 }
        this.binBounds = GeometryUtil.getPolygonBounds(bin)

        # population is an array of individuals. Each individual is a object representing the order of insertion and the angle each part is rotated
        angles = []
        for i in range(0, len(adam)):
            angles.append(this.randomAngle(adam[i]))

        this.population = [{placement: adam, rotation: angles}]

        while len(this.population) < config.populationSize:
            mutant = this.mutate(this.population[0])
            this.population.push(mutant)

    # returns a random angle of insertion
    def randomAngle(this, part):
    
        angleList = []
        for i in range(0, max(this.config.rotations,1)):
            angleList.append(i*(360/this.config.rotations))

        def shuffleArray(array):
            for i in range(array.length - 1, 0):
                j = math.floor(math.random() * (i + 1))
                temp = array[i]
                array[i] = array[j]
                array[j] = temp
            return array

        angleList = shuffleArray(angleList)

        for i in range(0, len(angleList)):
            rotatedPart = GeometryUtil.rotatePolygon(part, angleList[i])

            # don't use obviously bad angles where the part doesn't fit in the bin
            if rotatedPart.width < this.binBounds.width and rotatedPart.height < this.binBounds.height:
                return angleList[i]

        return 0

    # returns a mutated individual with the given mutation rate
    def mutate(this, individual):
        clone = {'placement': individual.placement.slice(0), 'rotation': individual.rotation.slice(0)}
        for i in range(0, len(clone.placement)):
            rand = math.random()
            if rand < 0.01 * this.config.mutationRate:
                # swap current part with next part
                j = i+1

                if j < len(clone.placement):
                    temp = clone.placement[i]
                    clone.placement[i] = clone.placement[j]
                    clone.placement[j] = temp

            rand = Math.random()
            if rand < 0.01 * this.config.mutationRate:
                clone.rotation[i] = this.randomAngle(clone.placement[i])

        return clone

    # single point crossover
    def mate(this, male, female):
        cutpoint = round(min(max(math.random(), 0.1), 0.9)*(len(male.placement)-1))

        gene1 = male.placement.slice(0,cutpoint)
        rot1 = male.rotation.slice(0,cutpoint)

        gene2 = female.placement.slice(0,cutpoint)
        rot2 = female.rotation.slice(0,cutpoint)

        i = None

        for i in range(0, len(female.placement)):
            if not contains(gene1, female.placement[i].id):
                gene1.push(female.placement[i])
                rot1.push(female.rotation[i])

        for i in range(0, len(male.placement)):
            if not contains(gene2, male.placement[i].id):
                gene2.push(male.placement[i])
                rot2.push(male.rotation[i])

        def contains(gene, id):
            for i in range(0, len(gene)):
                if gene[i].id == id:
                    return true
            return false

        return [{'placement': gene1, 'rotation': rot1},{'placement': gene2, 'rotation': rot2}]

    def generation(this):
            
        # Individuals with higher fitness are more likely to be selected for mating
        this.population.sort(lambda a, b: a.fitness - b.fitness)

        # fittest individual is preserved in the new generation (elitism)
        newpopulation = [this.population[0]]

        while len(newpopulation) < this.population.length:
            male = this.randomWeightedIndividual()
            female = this.randomWeightedIndividual(male)

            # each mating produces two children
            children = this.mate(male, female)

            # slightly mutate children
            newpopulation.append(this.mutate(children[0]))

            if len(newpopulation) < len(this.population):
                newpopulation.append(this.mutate(children[1]))

        this.population = newpopulation

    # returns a random individual from the population, weighted to the front of the list (lower fitness value is more likely to be selected)
    def randomWeightedIndividual(this, exclude):
        pop = this.population.slice(0)

        if exclude and pop.indexOf(exclude) >= 0:
            pop.splice(pop.indexOf(exclude),1)

        rand = math.random()

        lower = 0
        weight = 1 / len(pop)
        upper = weight

        for i in range(0, len(pop)):
            # if the random number falls between lower and upper bounds, select this individual
            if rand > lower and rand < upper:
                return pop[i]
            lower = upper
            upper += 2*weight * ((pop.length-i)/pop.length)

        return pop[0]
