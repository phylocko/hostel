from datetime import datetime, timedelta

from django.core.management.base import BaseCommand

import hostel.common.models as common_models
from hostel.service.email import email_admin, MailError
from hostel.settings import ADMIN_EMAIL


class Command(BaseCommand):
    help = 'Notifying us about expirating service tests'

    def handle(self, *args, **options):
        one_day = timedelta(hours=24)
        today_midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + one_day
        tomorrow_midnight = today_midnight + one_day
        exp_services = common_models.Service.objects.filter(end_time__gte=today_midnight,
                                                            end_time__lt=tomorrow_midnight,
                                                            status='?').order_by('client__manager')

        if not exp_services:
            return None

        for s in exp_services:
            subject = 'Тест %s для %s (%s) заканчивается %s' % (
                s.name,
                s.client.clientname,
                s.client.city.name,
                s.end_time.strftime('%d.%m в %H:%M')
            )
            text = 'Тест услуги %s %s [%s] ' % (s.name.upper(), s.servicetype.upper(), s)
            text += 'завершится %s\n' % s.end_time.strftime('%d.%m.%Y в %H:%M')
            emails = s.client.manager.profile.email + ', %s' % ADMIN_EMAIL
            try:
                email_admin(emails, subject, text)
            except MailError:
                pass

    def report_text(self, services, manager=None):

        if manager:
            selected_services = services.filter(client__manager=manager)
        else:
            selected_services = services

        if not selected_services:
            return None

        report = 'Привет! Завтра завершается тест по следующим услугам:\n'
        report += '%s | %s | %s | %s' % ('Услуга ',
                                         'Организация          '
                                         '', 'Менеджер    ',
                                         'Дата окончания теста\n')

        for s in selected_services:
            report += '%s | %s | %s | %s\n' % (s,
                                               s.client.clientname.ljust(20),
                                               s.client.manager.username.ljust(12),
                                               s.end_time.strftime('%Y-%m-%d %H:%M'))
        return report
