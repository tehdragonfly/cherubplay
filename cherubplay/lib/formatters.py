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


class FormattedValue:
    def __init__(self, obj, format_attr, text_attr):
        self._obj = obj
        self._format_attr = format_attr
        self._text_attr = text_attr

    def as_plain_text(self) -> str:
        # For notifications etc.
        return getattr(self._obj, self._text_attr)

    def as_html(self) -> Markup:
        # For chat pages.
        raise NotImplementedError


class FormattedField:
    def __init__(self, format_attr, text_attr):
        self._format_attr = format_attr
        self._text_attr = text_attr

    def __get__(self, instance, owner):
        if not instance:
            raise ValueError("can only be accessed from an instance")
        return FormattedValue(instance, self._format_attr, self._text_attr)
