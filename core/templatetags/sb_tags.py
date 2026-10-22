from datetime import timedelta

from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    """Return the current query string with the given parameters replaced.

    Changing any filter resets pagination unless `page` is passed explicitly.
    """
    query = context["request"].GET.copy()
    if "page" not in kwargs:
        query.pop("page", None)
    for key, value in kwargs.items():
        if value in (None, ""):
            query.pop(key, None)
        else:
            query[key] = value
    encoded = query.urlencode()
    return f"?{encoded}" if encoded else "?"


@register.filter
def hours_display(value):
    """Format a number of hours in a friendly way."""
    if value in (None, ""):
        return "—"
    hours = float(value)
    if hours < 1:
        return f"{max(1, round(hours * 60))} min"
    if hours < 48:
        return f"{hours:.1f} h"
    return f"{hours / 24:.1f} days"


@register.filter
def duration_display(value):
    if not isinstance(value, timedelta):
        return "—"
    return hours_display(value.total_seconds() / 3600)


@register.filter
def percent_of(value, total):
    try:
        total = float(total)
        return 0 if total <= 0 else round(float(value) * 100 / total)
    except (TypeError, ValueError):
        return 0
