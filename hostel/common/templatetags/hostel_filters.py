import json

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

from hostel import settings

register = template.Library()


@register.filter(name='spy_changes')
def spy_changes(changes):
    if not changes:
        return ""
    data = json.loads(changes)

    retval = '<ul class="list-unstyled">'
    for field, changes in data.items():
        new = changes.get('new')
        old = changes.get('old')

        if old or new:

            new = escape(new)
            old = escape(old)

            retval += '<li><b>%s</b></li><li>' % field.title()
            retval += '<ul class="list-unstyled">'
            if old:
                retval += '<li><code>%s</code> <b>></b> <code>%s</code></li>' % (
                    old, new)
            else:
                retval += '<li>%s</li>' % new
            retval += '</li></ul>'

    retval += '</ul>'

    return mark_safe(retval)


@register.filter(name='ins_type')
def ins_type(type):
    if type == "failure":
        retval = '<label class="label label-danger">Авария</label>'
    elif type == "work":
        retval = '<label class="label label-primary">Работы</label>'
    else:
        retval = '<label class="label label-default">Другое</label>'
    return mark_safe(retval)


@register.filter(name='keep_lines')
def keep_lines(text):
    if not text:
        text = ""
    retval = text.replace('\n', '<br>')
    return mark_safe(retval)


@register.filter(name='status')
def status(status):
    if status == "+":
        retval = '<span class="glyphicon glyphicon-plus text-success" aria-hidden="true"></span>'
    elif status == "-":
        retval = '<span class="glyphicon glyphicon-minus text-danger" aria-hidden="true"></span>'
    else:
        retval = '<span class="glyphicon glyphicon-question-sign text-warning" aria-hidden="true"></span>'
    return mark_safe(retval)


@register.filter(name='service_text_class')
def service_text_class(service):
    status_map = {
        'client_off': 'text-danger',
        'off': 'text-danger',
        'waiting_on': 'text-muted',
        'waiting_test': 'text-muted',
        'on': 'text-success',
        'on_test': 'text-warning',
        'off_test': 'text-danger',
    }

    return status_map.get(service.commercial_status, '?')


@register.filter(name='service_field_class')
def service_field_class(service):
    status_map = {
        'client_off': 'danger',
        'off': 'danger',
        'waiting_on': 'active',
        'waiting_test': 'active',
        'on': 'success',
        'on_test': 'warning',
        'off_test': 'danger',
    }

    return status_map.get(service.commercial_status, '?')


@register.filter(name='commercial_status')
def commercial_status(service):
    status_map = {
        'client_off': 'Клиент выкл',
        'off': 'Выключена',
        'waiting_on': 'В ожидании включения',
        'waiting_test': 'В ожидании теста',
        'on': 'Включена',
        'on_test': 'Идет тест',
        'off_test': 'Тест завершен',
    }

    return status_map.get(service.commercial_status, '?')


@register.filter(name='phone')
def phone_number(phone_field):
    if not phone_field:
        return ""

    phones = phone_field.split()

    new_phones = []
    for phone in phones:
        phone_str = ""
        for c in phone:
            if c.isdigit():
                phone_str += c

        if phone_str[0] == "8":
            phone_str = "+7%s" % phone_str[1:]

        elif phone_str[0] == "7":
            phone_str = "+7%s" % phone_str[1:]
        elif phone_str[0:1] == "+7":
            pass
        else:
            phone_str = "+7%s" % phone_str

        formatted_phone = "<a style='white-space: nowrap' href='tel:%s'>%s (%s) %s-%s-%s</a>" % (
            phone_str, phone_str[0:2], phone_str[2:5], phone_str[5:8], phone_str[8:10], phone_str[10:])
        new_phones.append(formatted_phone)

    retval = ""
    for phone in new_phones:
        retval += "%s<br>" % phone
    return mark_safe(retval)


@register.filter
def ticket(value):
    if not value:
        return ""
    else:
        url = settings.TICKET_URL_PREFIX + value + settings.TICKET_URL_SUFFIX
        return mark_safe('<a href="%s">%s</a>' % (url, value))


@register.filter(name='phone')
def phone(value):
    if not value:
        return ''

    if len(value) == 12 and value.startswith('+'):
        return '%s(%s) %s-%s' % (
            value[0:2],  # +7
            value[2:5],  # 913
            value[5:8],  # 951
            value[8:],  # 10
        )
    else:
        return value
