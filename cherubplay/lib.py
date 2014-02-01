# -*- coding: utf-8 -*-

import re

colour_validator = re.compile("^[A-Fa-f0-9]{6}$")
username_validator = re.compile("^[-a-z0-9_]+$")

reserved_usernames = ()

symbols = (u"●", u"🌀")

preset_colours = [
    ("000000", "Preset colours..."),
    ("000000", "Basic black"),
    ("FFFFFF", "Omniscient asshole white"),
    ("0715CD", "John/Tavrisprite blue"),
    ("B536DA", "Rose/Fefetasprite purple"),
    ("E00707", "Dave/Dirquiusprite red"),
    ("4AC925", "Jade/Erisolsprite green"),
    ("00D5F2", "Jane/Nannasprite blue"),
    ("FF6FF2", "Roxy pink"),
    ("F141EF", "Jaspersprite pink"),
    ("F2A400", "Dirk/Davesprite orange"),
    ("1F9400", "Jake/Jadesprite green"),
    ("FF0000", "Candy red"),
    ("A10000", "Aries red"),
    ("A15000", "Taurus brown"),
    ("A1A100", "Gemini yellow"),
    ("626262", "Cancer grey"),
    ("416600", "Leo green"),
    ("008141", "Virgo green"),
    ("008282", "Libra blue"),
    ("005682", "Scorpio blue"),
    ("000056", "Sagittarius blue"),
    ("2B0057", "Capricorn purple"),
    ("6A006A", "Aquarius purple"),
    ("77003C", "Pisces pink"),
    ("929292", "Calliope grey"),
    ("323232", "Caliborn grey"),
    ("2ED73A", "Hideous dead sister green"),
]

