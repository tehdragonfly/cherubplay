import re

from markupsafe import escape, Markup

from cherubplay.models.enums import MessageFormat


linebreak_regex = re.compile(r"[\r\n]+")
paragraph = Markup("<p>%s</p>")


plain_text_formatters = {
    MessageFormat.raw: lambda value: value,
}

html_formatters = {
    MessageFormat.raw: lambda value: Markup("\n").join(
        paragraph % escape(line)
        for line in linebreak_regex.split(value)
    ),
}


class FormattedValue:
    def __init__(self, obj, format_attr, text_attr):
        self._obj = obj
        self._format_attr = format_attr
        self._text_attr = text_attr

    def __bool__(self):
        return bool(getattr(self._obj, self._text_attr))

    @property
    def format(self) -> str:
        return getattr(self._obj, self._format_attr)

    @property
    def raw(self) -> str:
        return getattr(self._obj, self._text_attr)

    def as_plain_text(self) -> str:
        # For notifications etc.
        return plain_text_formatters[getattr(self._obj, self._format_attr)](getattr(self._obj, self._text_attr))

    def as_html(self) -> Markup:
        # For chat pages.
        return html_formatters[getattr(self._obj, self._format_attr)](getattr(self._obj, self._text_attr))

    def __json__(self, request=None):
        return {
            "format": self.format,
            "raw": self.raw,
            "as_plain_text": self.as_plain_text(),
            "as_html": self.as_html(),
        }


class FormattedField:
    def __init__(self, format_attr, text_attr):
        self._format_attr = format_attr
        self._text_attr = text_attr

    def __get__(self, instance, owner):
        if not instance:
            raise ValueError("can only be accessed from an instance")
        return FormattedValue(instance, self._format_attr, self._text_attr)
