import json
import random
from glob import glob

from svgnest.js.display import plot
from svgnest.js.geometry import Polygon, Point

# files = glob('nfp*.json')
# raw_path = random.choice(files)

raw_path = 'generated_nfp.json'


def from_x_y(l):
    p = Polygon(*(Point(x, y) for x, y in l))
    if p[-1] != p[0]:
        p.append(p[0])
    return p


with open(raw_path, 'r') as raw_file:
    data = json.load(raw_file)

    polys = [from_x_y(el['B']) for el in data]
    nfps = [from_x_y(p) for el in data for p in el['nfp']]
    bin = from_x_y(data[0]['A'])

    plot([*polys, *nfps])


