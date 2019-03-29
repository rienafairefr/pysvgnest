# display methods, for dev
from math import sqrt, floor, ceil

from matplotlib import pyplot

GM = (sqrt(5) - 1.0) / 2.0
W = 8.0
H = W * GM
SIZE = (W, H)


def set_limits(ax, x0, xN, y0, yN):
    ax.set_xlim(x0, xN)
    ax.set_ylim(y0, yN)
    ax.set_aspect("equal")


def plot(polygons=None, points=None):
    if polygons is None: polygons = []
    if points is None: points = []
    fig = pyplot.figure(1, figsize=SIZE, dpi=90)

    # 1: valid ring
    ax = fig.add_subplot(121)

    xmin = min(min(point.x for polygon in polygons for point in polygon) if polygons else float('inf'),
               min(point.x for point in points) if points else float('inf'))
    xmax = max(max(point.x for polygon in polygons for point in polygon) if polygons else float('-inf'),
               max(point.x for point in points) if points else float('-inf'))
    ymin = min(min(point.y for polygon in polygons for point in polygon) if polygons else float('inf'),
               min(point.y for point in points) if points else float('inf'))
    ymax = max(max(point.y for polygon in polygons for point in polygon) if polygons else float('-inf'),
               max(point.y for point in points) if points else float('-inf'))

    for polygon in polygons:
        ax.plot(*polygon.xy, '-')

    for point in points:
        ax.plot(*point.xy, 'o')

    set_limits(ax, xmin - 0.2 * (xmax - xmin), xmax + 0.2 * (xmax - xmin), ymin - 0.2 * (ymax - ymin),
               ymax + 0.2 * (ymax - ymin))

    pyplot.show()