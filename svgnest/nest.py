from rectpack import float2dec as _float2dec
from rectpack import newPacker
from svgpathtools import svg2paths
from svgwrite import Drawing
from svgwrite.container import Group
from svgwrite.path import Path
from svgwrite.shapes import Rect


def nest(output, files, wbin, hbin, enclosing_rectangle=False):

    combined = Drawing(output, profile='tiny', size=('%smm' % wbin, '%smm' % hbin),
                       viewBox="0 0 %s %s" % (wbin, hbin))

    packer = newPacker()

    def float2dec(x):
        return _float2dec(x, 4)

    def bbox_paths(paths):
        bbox = None
        for p in paths:
            p_bbox = p.bbox()
            if bbox is None:
                bbox = tuple(float2dec(x) for x in p_bbox)
            else:
                bbox = (
                    min(p_bbox[0], bbox[0]),
                    max(p_bbox[1], bbox[1]),
                    min(p_bbox[2], bbox[2]),
                    max(p_bbox[3], bbox[3])
                )
        return bbox

    all_paths = {}
    for svg in files:
        paths, attributes = svg2paths(svg)
        bbox = bbox_paths(paths)
        for i in range(files[svg]):
            rid = svg + str(i)
            all_paths[rid] = paths
            packer.add_rect(bbox[1] - bbox[0],
                        bbox[3] - bbox[2], rid=rid)

    packer.add_bin(wbin, hbin)
    print('Rectangle packing...')
    packer.pack()
    rectangles = {r[5]: r for r in packer.rect_list()}

    print('packing into SVG...')
    for rid, paths in all_paths.items():
        group = Group()

        bbox = bbox_paths(paths)
        width, height = (float2dec(bbox[1] - bbox[0]), float2dec(bbox[3] - bbox[2]))
        b, x, y, w, h, rid = rectangles[rid]

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
            path.stroke(color='red', width='0.1')
            path.fill(opacity=0)
            group.add(path)

        group.translate(x + dx, y + dy)
        group.rotate(rotate)
        combined.add(group)

    if enclosing_rectangle:
        r = Rect(size=(wbin, hbin))
        r.fill(opacity=0)
        r.stroke(color='lightgray')
        combined.add(r)

    print('SVG saving...')
    combined.save(pretty=True)
