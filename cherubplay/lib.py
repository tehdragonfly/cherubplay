# -*- coding: utf-8 -*-

import paginate, re

from collections import OrderedDict


def make_paginator(request, item_count, current_page, items_per_page=25):
    return paginate.Page(
        [],
        page=current_page,
        items_per_page=items_per_page,
        item_count=item_count,
        url_maker=lambda page: request.current_route_path(_query={"page": page}),
    )


colour_validator = re.compile("^[A-Fa-f0-9]{6}$")
username_validator = re.compile("^[-a-z0-9_]+$")
email_validator = re.compile("^.+@.+\..+$")

reserved_usernames = ()

symbols = (u"●", u"🌀", u"♠", u"♣", u"♦", u"♥", u"▲", u"■", u"⬟", u"★")

preset_colours = [
    ("000000", "Preset colours..."),
    ("000000", "Basic black"),
    ("FFFFFF", "Omniscient asshole white"),
    ("0715CD", "John/Tavrisprite blue"),
    ("B536DA", "Rose/Fefetasprite purple"),
    ("E00707", "Dave/ARquiusprite red"),
    ("4AC925", "Jade/Erisolsprite green"),
    ("00D5F2", "Jane/Nannasprite blue"),
    ("FF6FF2", "Roxy pink"),
    ("F141EF", "Jaspersprite pink"),
    ("F2A400", "Dirk/Davesprite orange"),
    ("1F9400", "Jake/Jadesprite green"),
    ("4B4B4B", "Dad grey"),
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
    ("FF00EE", "Obnoxious fantroll pink"),
]

prompt_categories = OrderedDict([
    ("homestuck", "Homestuck"),
    ("crossover", "Homestuck crossover"),
    ("not-homestuck", "Not Homestuck"),
])

prompt_starters = OrderedDict([
    ("starter", "Starter"),
    ("no-starter", "No starter"),
])

prompt_levels = OrderedDict([
    ("sfw", "Safe for work"),
    ("nsfw", "Not safe for work"),
    ("nsfw-extreme", "NSFW extreme"),
])
