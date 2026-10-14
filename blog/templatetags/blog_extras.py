from django import template
from django.utils import timezone

from ..jalali import format_jalali, to_persian_digits

register = template.Library()


@register.filter
def jdate(value, style="long"):
    """Show a date/datetime in the Jalali calendar: {{ post.published_at|jdate }}."""
    if not value:
        return ""
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return format_jalali(value, style)


@register.filter
def fa_digits(value):
    """Turn 0-9 into Persian digits: {{ 12|fa_digits }} -> ۱۲."""
    return to_persian_digits(value)


@register.simple_tag(takes_context=True)
def page_url(context, page_number):
    """Link to another page of the current list while keeping `?q=` etc."""
    params = context["request"].GET.copy()
    params["page"] = page_number
    return "?" + params.urlencode()
