import os

from svgnest.js.svgnest import SvgNest
from svgnest.js.svgparser import child_elements, SvgParser


def progress(progress):
    # print('progress: {}', progress)
    pass


def display(nest, svglist=None, area_ratio=0, parts_ratio=0):
    if svglist:
        for i, placement in enumerate(svglist):
            print('placement={0}\narea_ratio={1}\nparts_ratio={2}'.format(placement, area_ratio, parts_ratio))
            with open(os.path.join('working{}.svg'.format(i)), 'w+') as svg_file:
                placement.writexml(svg_file)


nest = SvgNest()


def case1():
    svg_string = open('drawing.svg', 'r').read()
    svg = nest.parsesvg(svg_string)

    nest.set_bin(svg.childNodes[15])

    nest.start(progress, display)


def circlescase():
    svg_string = open('circles.svg', 'r').read()
    svg = nest.parsesvg(svg_string)

    nest.set_bin(child_elements(svg)[0])

    nest.start(progress, display)


def case2():
    svg_string = open('demo.svg', 'r').read()
    svg = nest.parsesvg(svg_string)

    nest.set_bin(child_elements(svg)[142])

    nest.start(progress, display)


if __name__ == '__main__':
    circlescase()
