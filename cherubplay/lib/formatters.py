import re

from markdown import Markdown, Extension
from markdown.inlinepatterns import AutolinkInlineProcessor
from markupsafe import escape, Markup

from cherubplay.lib.markdown_processors import AUTOLINK_RE, HeaderLevelProcessor, LinkRelProcessor
from cherubplay.models.enums import MessageFormat


linebreak_regex = re.compile(r"[\r\n]+")
paragraph = Markup("<p>%s</p>")


class ProcessorExtension(Extension):
    def extendMarkdown(self, md):
        """
        Remove processors allowing raw HTML, images and some formatting we
        don't have CSS for.
        """
        for key in ["html_block", "reference"]:
            del md.preprocessors[key]
        for key in [
            "backtick", "reference", "image_link", "image_reference",
            "short_reference", "autolink", "automail", "html", "entity",
        ]:
            del md.inlinePatterns[key]
        md.inlinePatterns.register(AutolinkInlineProcessor(AUTOLINK_RE, md), "autolink", 120)
        for key in ["code", "quote"]:
            del md.parser.blockprocessors[key]
        md.treeprocessors.register(HeaderLevelProcessor(md), "header_level", 10)
        md.treeprocessors.register(LinkRelProcessor(md), "link_rel", 10)


md = Markdown(extensions=[ProcessorExtension()])


plain_text_formatters = {
    MessageFormat.raw: lambda value: value,
    MessageFormat.markdown: lambda value: value,
}

html_formatters = {
    MessageFormat.raw: lambda value: Markup("\n").join(
        paragraph % escape(line)
        for line in linebreak_regex.split(value)
    ),
    MessageFormat.markdown: lambda value: Markup(md.reset().convert(value)),
}


def raw_trimmer(value: str, length: int) -> (bool, str):
    """
    Trim `value` to a maximum of `length`.

    Returns a tuple with a boolean indicating whether the string needed to be
    trimmed followed by the trimmed or whole string.
    """
    if len(value) <= length:
        return False, html_formatters[MessageFormat.raw](value)
    return True, html_formatters[MessageFormat.raw](value[:length - 3] + "...")


def markdown_trimmer(value: str, length: int) -> (bool, str):
    # TODO make sure this doesn't cut markdown syntax in half
    if len(value) <= length:
        return False, html_formatters[MessageFormat.markdown](value)
    return True, html_formatters[MessageFormat.markdown](value[:length - 3] + "...")


trimmers = {
    MessageFormat.raw: raw_trimmer,
    MessageFormat.markdown: markdown_trimmer,
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

    def update(self, format: MessageFormat, text: str):
        setattr(self._obj, self._format_attr, format)
        setattr(self._obj, self._text_attr,   text)

    def trim_html(self, length: int):
        # For list pages.
        return trimmers[getattr(self._obj, self._format_attr)](getattr(self._obj, self._text_attr), length)


class FormattedField:
    def __init__(self, format_attr, text_attr):
        self._format_attr = format_attr
        self._text_attr = text_attr

    def __get__(self, instance, owner):
        if not instance:
            raise ValueError("can only be accessed from an instance")
        return FormattedValue(instance, self._format_attr, self._text_attr)

    def __set__(self, instance, value):
        if not instance:
            raise ValueError("can only be set from an instance")
        setattr(instance, self._text_attr, value)
