# -*- coding: utf-8 -*-

import re

colour_validator = re.compile("^E00707$|^F2A400$|^416600$", re.I)
username_validator = re.compile("^[-a-z0-9_]+$")

reserved_usernames = ()

symbols = (u"🌟", u"👓")

preset_colours = [
    ("E00707", "preset colors"),
    ("E00707", "awesome coolkid red"),
    ("F2A400", "alt timeline coolkid orange"),
]

