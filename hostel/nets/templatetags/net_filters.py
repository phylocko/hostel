from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name='margin')
def phone_number(margin):
    if not margin:
        margin = 0
    retval = "&nbsp;&nbsp;" * margin
    return mark_safe(retval)

@register.filter(name='parent_id')
def parent_id(parent):
    if not parent:
        return ""
    parent = parent.replace(".", "_")
    parent = parent.replace("/", "-")
    return mark_safe(parent)
