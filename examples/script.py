import os

from svgnest.js.svgnest import SvgNest
from svgnest.js.svgparser import child_elements

svgString = open('demo.svg', 'r').read()

nest = SvgNest()
svg = nest.parsesvg(svgString)
t = nest.tree

# nest.setbin(svg.childNodes[15])   #drawing.svg

elements = child_elements(svg)
widths = [el.getAttribute("width") for el in elements]
nest.setbin(elements[142])   # demo.svg


def progress(progress):
    print('progress: %s', progress)


def display(placement=None, area_ratio=0, parts_ratio=0):
    if placement:
        print('placement={0}\narea_ratio={1}\nparts_ratio={2}'.format(placement, area_ratio, parts_ratio))
        with open(os.path.join('working.svg'), 'w+') as svg_file:
            placement.writexml(svg_file)


nest.start(progress, display)
