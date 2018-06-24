import re

from markupsafe import escape, Markup

from cherubplay.models.enums import MessageFormat


class Formatter:
    def __init__(self, message):
        self._message = message

    def as_plain_text(self) -> str:
        # For notifications etc.
        raise NotImplementedError

    def as_html(self) -> Markup:
        # For chat pages.
        raise NotImplementedError


linebreak_regex = re.compile(r"[\r\n]+")
paragraph = Markup("<p>%s</p>")


class RawFormatter(Formatter):
    def as_plain_text(self) -> str:
        return self._message.text

    def as_html(self) -> Markup:
        return Markup("\n").join(
            paragraph % escape(line)
            for line in linebreak_regex.split(self._message.text)
        )


message_formatters = {
    MessageFormat.raw: RawFormatter,
}
