from svgnest.js.svgnest import SvgNest

svgString = open('drawing.svg', 'r').read()

nest = SvgNest()
svg = nest.parsesvg(svgString)
t = nest.tree
nest.setbin(svg.childNodes[15])

def progress(*args, **lwargs):
    pass

def display(*args, **lwargs):
    pass

nest.start(progress, display)