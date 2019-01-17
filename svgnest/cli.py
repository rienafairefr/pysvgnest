import argparse

from svgnest import nest


def width_height(wxh):
    width_height = wxh.split('x')
    if len(width_height) != 2:
        raise argparse.ArgumentError('Should be in the form WxH')
    width, height = tuple(width_height)
    try:
        width = int(width)
    except ValueError:
        raise argparse.ArgumentError('Width should be an integer')
    try:
        height = int(height)
    except ValueError:
        raise argparse.ArgumentError('Height should be an integer')
    return width, height


def file_num(filenum):
    s = filenum.split(':')
    if len(s) == 2:
        try:
            s[1] = int(s[1])
        except ValueError:
            raise argparse.ArgumentError('The number of times to'
                                         'include a SVG should be an integer')
    elif len(s) == 1:
        s.append(1)
    else:
        raise argparse.ArgumentError('The files should be'
                                     'passed through the format -f FILE[:NUM]')

    return s


def parse_args(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--enclose', action='store_true')
    parser.add_argument('-f', dest='files', type=file_num,
                        metavar='FILE[:NUM]', help='Nesting files',
                        action='append', required=True)
    parser.add_argument('-s', dest='size', required=True, type=width_height,
                        help='Plate size in the form WxH (mm)')
    parser.add_argument('-o', dest='output', help='Output file', required=True)
    ns = parser.parse_args(args)

    width, height = ns.size

    files = {f[0]: f[1] for f in ns.files}
    return (ns.output, files, width, height, ns.enclose)


def main():
    nest(*parse_args())


if __name__ == '__main__':
    main()
