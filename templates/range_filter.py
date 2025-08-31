# EventHive_app/templatetags/range_filter.py
from django import template

register = template.Library()

@register.filter
def times(number):
    return range(int(number))