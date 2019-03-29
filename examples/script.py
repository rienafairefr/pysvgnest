import os

from svgnest.js.svgnest import SvgNest
from svgnest.js.svgparser import child_elements


def progress(progress):
    print('progress: %s', progress)


def display(placement=None, area_ratio=0, parts_ratio=0):
    if placement:
        print('placement={0}\narea_ratio={1}\nparts_ratio={2}'.format(placement, area_ratio, parts_ratio))
        with open(os.path.join('working.svg'), 'w+') as svg_file:
            placement.writexml(svg_file)


nest = SvgNest()


def case1():
    svgString = open('drawing.svg', 'r').read()
    svg = nest.parsesvg(svgString)

    nest.set_bin(svg.childNodes[15])

    nest.start(progress, display)


def case2():
    svgString = open('demo.svg', 'r').read()
    svg = nest.parsesvg(svgString)

    nest.set_bin(child_elements(svg)[142])

    nest.start(progress, display)

if __name__ == '__main__':
    case1()