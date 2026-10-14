"""Markdown -> HTML (with syntax highlighting and a table of contents)."""
from typing import NamedTuple

import markdown
from django.utils.safestring import mark_safe
from markdown.extensions.toc import slugify_unicode

_EXTENSIONS = [
    "fenced_code",
    "codehilite",
    "tables",
    "toc",
    "sane_lists",
    "attr_list",
]

_EXTENSION_CONFIGS = {
    "codehilite": {"guess_lang": False, "css_class": "codehilite"},
    "toc": {
        "toc_depth": "2-3",
        "slugify": slugify_unicode,  # keeps Persian letters in heading ids
        "permalink": "#",
        "permalink_class": "headerlink",
        "permalink_title": "پیوند به این بخش",
    },
}


class Rendered(NamedTuple):
    html: str
    toc: str


def render_markdown(text: str) -> Rendered:
    """
    Render trusted Markdown (only the site owner writes posts, so raw HTML
    inside the text is intentionally allowed).
    """
    md = markdown.Markdown(
        extensions=_EXTENSIONS,
        extension_configs=_EXTENSION_CONFIGS,
        output_format="html",
    )
    html = md.convert(text or "")
    toc = md.toc if md.toc_tokens else ""
    return Rendered(mark_safe(html), mark_safe(toc))
