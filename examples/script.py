from svgnest.js.svgnest import SvgNest

svgString = open('drawing.svg', 'r').read()

nest = SvgNest()
nest.parsesvg(svgString)
nest.start()