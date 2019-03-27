import logging
from collections import namedtuple


def splice(target, start, delete_count=None, *items):
    """Remove existing elements and/or add new elements to a list.

    target        the target list (will be changed)
    start         index of starting position
    delete_count  number of items to remove (default: len(target) - start)
    *items        items to insert at start index

    Returns a new list of removed items (or an empty list)
    """
    if delete_count is None:
        delete_count = len(target) - start

    # store removed range in a separate list and replace with *items
    total = start + delete_count
    removed = target[start:total]
    target[start:total] = items

    return removed


def parseInt(value):
    try:
        return int(value)
    except ValueError:
        return None


def parseFloat(f):
    try:
        return float(f)
    except ValueError:
        return None


Nfp = namedtuple('Nfp', ['key', 'value'])
NfpPair = namedtuple('NfpPair', ['A', 'B', 'key'])
NfpKey = namedtuple('NfpKey', ['A', 'B', 'inside', 'Arotation', 'Brotation'])
DEBUG = True


logger = logging.getLogger('pysvgnest')
logger.setLevel(logging.INFO)
logging.basicConfig()


def log(msg, level=logging.DEBUG):
    logger.log(level, msg)
