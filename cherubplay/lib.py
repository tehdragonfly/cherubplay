# -*- coding: utf-8 -*-

import paginate, re

from collections import OrderedDict
from hashlib import sha256


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


deduplicate_regex = re.compile("[\W_]+")


def prompt_hash(text):
    return sha256(deduplicate_regex.sub("", text.lower()).encode()).hexdigest()


class OnlineUserStore(object):
    def __init__(self, redis):
        self.redis = redis

    def connect(self, chat, chat_user, socket_id):
        # TODO fire online/offline messages from here too?
        self.redis.hset("online:" + str(chat.id), socket_id, chat_user.handle)

    def disconnect(self, chat, socket_id):
        self.redis.hdel("online:" + str(chat.id), socket_id)

    def rename(self, chat, old_handle, new_handle):
        for socket_id, current_handle in self.redis.hgetall("online:" + str(chat.id)).items():
            if current_handle.decode() == old_handle:
                self.redis.hset("online:" + str(chat.id), socket_id, new_handle)

    def online_handles(self, chat):
        return set(_.decode("utf-8") for _ in self.redis.hvals("online:" + str(chat.id)))

