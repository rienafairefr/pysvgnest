import os

from rectpack import float2dec as _float2dec
from rectpack import newPacker
from svgpathtools import svg2paths
from svgwrite import Drawing
from svgwrite.container import Group
from svgwrite.path import Path
from svgwrite.shapes import Rect


def nest(output, files, wbin, hbin, enclosing_rectangle=False):

    packer = newPacker()

    def float2dec(x):
        return _float2dec(x, 4)

    def bbox_paths(paths):
        bbox = None
        for p in paths:
            p_bbox = p.bbox()
            if bbox is None:
                bbox = p_bbox
            else:
                bbox = (
                    min(p_bbox[0], bbox[0]),
                    max(p_bbox[1], bbox[1]),
                    min(p_bbox[2], bbox[2]),
                    max(p_bbox[3], bbox[3])
                )
        return tuple(float2dec(x) for x in bbox)

    all_paths = {}
    for svg\
            in files:
        paths, attributes = svg2paths(svg)
        bbox = bbox_paths(paths)
        for i in range(files[svg]):
            rid = svg + str(i)
            all_paths[rid] = {
                'paths': paths,
                'bbox': bbox
            }
            print(rid)
            packer.add_rect(bbox[1] - bbox[0],
                            bbox[3] - bbox[2], rid=rid)

    print('Rectangle packing...')
    while True:
        packer.add_bin(wbin, hbin)
        packer.pack()
        rectangles = {r[5]: r for r in packer.rect_list()}
        if len(rectangles) == len(all_paths):
            break
        else:
            print('not enough space in the bin, adding ')

    combineds = {}

    print('packing into SVGs...')
    for rid, obj in all_paths.items():
        paths = obj['paths']
        bbox = obj['bbox']
        group = Group()

        width, height = (float2dec(bbox[1] - bbox[0]),
                         float2dec(bbox[3] - bbox[2]))
        bin, x, y, w, h, _ = rectangles[rid]
        if bin not in combineds:
            svg_file = output
            if bin != 0:
                splitext = os.path.splitext(svg_file)
                svg_file = splitext[0] + '.%s' % bin + splitext[1]
            dwg = Drawing(svg_file, profile='tiny',
                          size=('%smm' % wbin, '%smm' % hbin),
                          viewBox="0 0 %s %s" % (wbin, hbin))
            combineds[bin] = dwg

        combined = combineds[bin]

        if (width > height and w > h) or \
                (width < height and w < h) or \
                (width == height and w == h):
            rotate = 0
            dx = -bbox[0]
            dy = -bbox[2]
        else:
            rotate = 90
            dx = -bbox[2]
            dy = -bbox[0]

        for p in paths:
            path = Path(d=p.d())
            path.stroke(color='red', width='1')
            path.fill(opacity=0)
            group.add(path)

        group.translate(x + dx, y + dy)
        group.rotate(rotate)
        combined.add(group)

    for combined in combineds.values():
        if enclosing_rectangle:
            r = Rect(size=(wbin, hbin))
            r.fill(opacity=0)
            r.stroke(color='lightgray')
            combined.add(r)

        print('SVG saving...')
        combined.save(pretty=True)
