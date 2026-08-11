from django import template

from myapp.date_utils import format_display_date, format_display_datetime

register = template.Library()


@register.filter(name='md_date')
def md_date(value):
    return format_display_date(value)


@register.filter(name='md_datetime')
def md_datetime(value):
    return format_display_datetime(value)
