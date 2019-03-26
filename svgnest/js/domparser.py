from xml.dom.minidom import parse, parseString


class DOMParser:
    def parseFromString(self, markup, type):
        return parseString(markup)
