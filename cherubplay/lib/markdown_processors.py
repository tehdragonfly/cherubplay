import re

from markdown import util
from markdown.treeprocessors import Treeprocessor


# Custom autolink regex because the standard one requires angle brackets.
# Also we only autolink HTTPS links.
AUTOLINK_RE = r"((?:[Ff]|[Hh][Tt])[Tt][Pp][Ss]://[^\s]+)"


class HeaderLevelProcessor(Treeprocessor):
    """
    Shift headings down two levels.

    h1 and h2 are already used by the layout, so we only want h3+ in messages.
    """

    def __init__(self, md):
        self.md = md

    def run(self, tree, ancestors=None):
        for element in tree.iter():
            if element.tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                level = int(element.tag[1])
                element.tag = "h" + str(min(level + 2, 6))
        return tree


class LinkRelProcessor(Treeprocessor):
    """
    Tree processor to add rel="noopener" to links.
    """

    def __init__(self, md):
        self.md = md

    def run(self, tree, ancestors=None):
        for element in tree.iter():
            if element.tag == "a":
                element.set("target", "_blank")
                element.set("rel", "noopener")
                href = element.get("href")
                if not href.startswith("http://") and not href.startswith("https://"):
                    element.set("href", "")
                if element.text == href and href.endswith(")") and not "(" in href:
                    element.text = element.text[:-1]
                    element.set("href", href[:-1])
                    element.tail = ")" + (element.tail or "")
        return tree
