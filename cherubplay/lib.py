# -*- coding: utf-8 -*-

import re

colour_validator = re.compile("^[A-Fa-f0-9]{6}$")
username_validator = re.compile("^[-a-z0-9_]+$")

reserved_usernames = ()

symbols = (u"●", u"🌀")

