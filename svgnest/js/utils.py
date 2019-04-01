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


class Nfp(namedtuple('Nfp', ['key', 'value'])):
    def to_json(self):
        return {'key': self.key, 'value': self.value}


class NfpPair(namedtuple('NfpPair', ['A', 'B', 'key'])):
    def to_json(self):
        return {'A': self.A, 'B': self.B, 'key': self.key}


class NfpKey(namedtuple('NfpKey', ['A', 'B', 'inside', 'Arotation', 'Brotation'])):
    def to_json(self):
        return {'A': self.A, 'B': self.B, 'inside': self.inside, 'Arotation': self.Arotation, 'Brotration:': self.Brotation}


DEBUG = True


logger = logging.getLogger('pysvgnest')
logger.setLevel(logging.INFO)
logging.basicConfig()


def log(msg, level=logging.DEBUG):
    logger.log(level, msg)
