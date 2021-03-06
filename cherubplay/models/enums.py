from enum import Enum


class ChatMode(Enum):
    one_on_one = "one_on_one"
    group      = "group"


class ChatSource(Enum):
    front_page      = "front_page"
    directory       = "directory"
    user_connection = "user_connection"
    admin           = "admin"


class ChatUserStatus(Enum):
    active  = "active"
    deleted = "deleted"


class MessageType(Enum):
    ic     = "ic"
    ooc    = "ooc"
    system = "system"


class MessageFormat(Enum):
    raw      = "raw"
    markdown = "markdown"


class TagType(Enum):
    maturity         = "maturity"
    warning          = "warning"
    type             = "type"
    fandom           = "fandom"
    fandom_wanted    = "fandom_wanted"
    character        = "character"
    character_wanted = "character_wanted"
    gender           = "gender"
    gender_wanted    = "gender_wanted"
    misc             = "misc"

    @property
    def playing(self):
        if self in TagType.playing_types:
            return self
        elif self in TagType.wanted_types:
            return TagType(self.value.replace("_wanted", ""))

    @property
    def wanted(self):
        if self in TagType.playing_types:
            return TagType(self.value + "_wanted")
        elif self in TagType.wanted_types:
            return self

    @property
    def pair(self):
        if self in TagType.playing_types or self in TagType.wanted_types:
            return self.playing, self.wanted
        return self,

    @property
    def ui_value(self):
        return self.value.replace("_", " ")


TagType.playing_types = {TagType.fandom,        TagType.character,        TagType.gender}
TagType.wanted_types  = {TagType.fandom_wanted, TagType.character_wanted, TagType.gender_wanted}

