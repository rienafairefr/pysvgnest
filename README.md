[![Build Status](https://travis-ci.org/rienafairefr/pysvgnest.svg?branch=master)](https://travis-ci.org/rienafairefr/pysvgnest)s

Small utility to nest multiple SVGs files into a single one, trying to minimize the empty wasted space. This is usually useful for lasercutting projects.

For now, the nesting is ultra basic:

- Rectangle packing using the `rectpack` library, considering the bounding box of the paths
- files with a single path in it seem fine.
- files that contain multiple paths might  
- units are assumed to be mm 
- Nesting on multiplate plates|bins is not yet supported
- All paths are brutally styled: removing the fill and putting the stroke to red with 0.1 width
  - This was done because I was nesting `.svg` files exported by OpenSCAD 

The API to call from Python is minimal:

```
from svgnest import nest
files = {
  'part1.svg': 1,
  'part2.svg': 2
}
// nest in a 600x300 mm plate, saving to combined.svg 
nest('combined.svg', files, 600, 300)
```

each file can be added once or multiple times to the plate by specifying in the 
`files` input dictionary. 

Dependencies:

[rectpack](https://pypi.org/project/rectpack/)
[svgwrite](https://pypi.org/project/svgwrite/) 
[svgpathtools](https://pypi.org/project/svgpathtools/)  
