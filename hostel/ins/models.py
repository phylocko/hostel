import datetime
import math
import urllib

from django.db import models
from django.db.models import Q
from django.utils import timezone
from hostel.clients.models import Client
from hostel.common.models import Service
from hostel.service.email import email_someone, MailError


class Incident(models.Model):
    TYPES = (
        ('work', 'Работы'),
        ('failure', 'Авария'),
        ('other', 'Другое'),
    )

    id = models.AutoField(primary_key=True)

    clients = models.ManyToManyField('clients.Client')
    services = models.ManyToManyField('common.Service')
    subservices = models.ManyToManyField('common.SubService', related_name='incidents')
    leases = models.ManyToManyField('common.Lease')
    creator = models.ForeignKey('common.User', null=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=250, blank=False, null=False, default='')
    type = models.TextField(blank=False, null=False, choices=TYPES, default='other')
    closed = models.BooleanField(blank=False, default=False)
    ticket = models.CharField(max_length=20, blank=True, null=True)
    time_start = models.DateTimeField(blank=False, null=False)
    time_end = models.DateTimeField(blank=False, null=False)
    outage_period = models.IntegerField(blank=True, null=True)  # overrides calculated value
    fiber = models.CharField(max_length=1024, blank=True, null=True)
    provider = models.ForeignKey('clients.Client', null=True, blank=True, related_name="sin", on_delete=models.SET_NULL)
    provider_tt = models.CharField(max_length=100, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    report_outage = models.BooleanField(default=False)
    deleted = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'incidents'

    def __str__(self):
        return 'INS-%s' % self.pk

    @property
    def period(self) -> str:

        if self.outage_period:
            minutes = self.outage_period
        else:
            minutes = math.ceil(
                abs((self.time_end.replace(second=0) - self.time_start.replace(second=0)).total_seconds()) / 60)

        if minutes < 60:
            return str("0ч %sмин" % minutes)
        else:
            hours = math.floor(minutes / 60)
            minutes = minutes - (hours * 60)
            if minutes < 10:
                return "%sч %sмин" % (hours, minutes)
            else:
                return "%sч %sмин" % (hours, minutes)

    @property
    def progress(self) -> str:
        if self.time_start is None or self.time_end is None:
            return "unknown"

        if self.time_start < timezone.now() < self.time_end:
            return 'now'

        if self.time_start > timezone.now():
            return 'waiting'

        if self.time_end < timezone.now():
            return 'completed'

        return 'unknown'

    def warnings(self):
        warnings = []

        if self.time_start > self.time_end:
            warnings.append('Время окончания больше времени начала')

        if self.type == 'failure':
            if not self.provider:
                warnings.append('Не указан виновник')
            if not self.ticket:
                warnings.append('Не указан номер тикета')
            if not self.provider_tt:
                warnings.append('Не указан ТТ виновника')
            if not self.fiber and not self.leases.all().count():
                warnings.append('Не указаны Lease')
            if not self.services.all() and not self.comment:
                warnings.append('Не указаны услуги')
            period = self.time_end - self.time_start
            if period.seconds < 600:
                warnings.append('Короткий период простоя')

        elif self.type == 'work':

            now = datetime.datetime.now()
            notifications = self.notifications.count()

            delta_to_start = self.time_start - now
            seconds_to_start = delta_to_start.total_seconds()

            if notifications == 0:

                warnings.append('Вы еще не отправили оповещения')

                if seconds_to_start < 0:
                    warnings.append('Дата начала прошла')
                elif seconds_to_start // 60 // 60 < 72:
                    warnings.append('До начала работ менее 72 часов')

        return warnings

    def percent_progress(self):

        now = datetime.datetime.now()
        if self.time_start >= now:
            return 0

        delta = self.time_end - self.time_start
        delta = delta.total_seconds()
        percent = delta / 100

        delta_to_now = now - self.time_start
        seconds_to_now = delta_to_now.total_seconds()
        percents = int(seconds_to_now // percent)

        return percents

    @staticmethod
    def parse_intervals(text):
        if not type(text) == str:
            return None, None

        LONG_FORMAT = '%Y-%m-%d %H:%M:%S'
        SHORT_FORMAT = '%Y-%m-%d %H:%M'

        results = []
        summary_time = datetime.timedelta(0)

        def parse_dates(date_text):
            try:
                return datetime.datetime.strptime(date_text, LONG_FORMAT)
            except ValueError:
                pass

            try:
                return datetime.datetime.strptime(date_text, SHORT_FORMAT)
            except ValueError:
                pass

        for line in text.splitlines():
            if not line:
                results.append('')
                continue

            parts = line.split()
            if len(parts) < 5:
                results.append(line)
                continue

            start_text = '%s %s' % (parts[0], parts[1])
            end_text = '%s %s' % (parts[3], parts[4])

            start_date = parse_dates(start_text)
            end_date = parse_dates(end_text)

            if not start_date or not end_date:
                results.append(line)
                continue

            if start_date > end_date:
                start_date, end_date = end_date, start_date

            delta = end_date - start_date
            results.append('%s — %s [%s]' % (start_text, end_text, delta))
            summary_time += delta

        text = '\n'.join(results)

        return summary_time, text


class Notification(models.Model):
    SERVICES_TEMPLATE = '%services%'

    id = models.AutoField(primary_key=True)
    incident = models.ForeignKey(Incident, related_name='notifications', null=True, on_delete=models.SET_NULL)
    subject = models.TextField(blank=True, null=False, default='', db_column='topic')
    text = models.TextField(blank=False, null=False)
    send_list = models.TextField(blank=True, null=True)
    date_added = models.DateTimeField(auto_now_add=True)
    who_added = models.ForeignKey('common.User', related_name='sender', null=True, on_delete=models.SET_NULL)

    class Meta:
        managed = True
        db_table = 'ins_notifications'

    def save(self, *args, **kwargs):
        if not self.pk:
            if self.incident:
                self.subject = '[INS-%s] %s' % (self.incident.pk, self.incident.name)
                if self.incident.notifications.count() > 0:
                    self.subject = 'Re: %s' % self.subject
        super().save(*args, **kwargs)

    def email_all(self):

        if self.incident.clients.count() > 0:
            # send by clients
            clients = self.incident.clients.all()

        else:
            # send by services and subservices
            services = Service.objects.filter(
                Q(id__in=self.incident.services.all()) |
                Q(subservices__in=self.incident.subservices.all()))
            clients = Client.objects.filter(services__in=services).distinct()

        for client in clients:
            notification_message = NotificationMessage.objects.create(client=client, notification=self)
            try:
                notification_message.email()
            except Exception:
                pass

    def prepare_message(self, client):

        rn = ' \r\n'
        tab = ' \t'

        text = self.text

        for notification in self.incident.notifications.all().exclude(pk=self.pk).order_by('-date_added'):
            text += rn * 2 + ' - ' + rn * 2
            text += notification.date_added.strftime('%Y-%m-%d %H:%M') + rn
            text += notification.text

        if self.incident.services.all() or self.incident.subservices.all():
            services = self.incident.services.filter(client=client)
            services_text = ''
            for service in services:
                services_text += rn
                services_text += str(service)
                if service.description:
                    services_text += tab + service.description

            subservices = self.incident.subservices.filter(service__client=client)
            for subservice in subservices:
                services_text += rn
                services_text += str(subservice)
                if subservice.description:
                    services_text += tab + subservice.description

            services_text = services_text.strip()
            text = text.replace(self.SERVICES_TEMPLATE, services_text)

        return text


class NotificationMessage(models.Model):
    notification = models.ForeignKey('ins.Notification', null=False, blank=False, on_delete=models.CASCADE)
    client = models.ForeignKey('clients.Client', null=True, on_delete=models.SET_NULL)
    time = models.DateTimeField(auto_now_add=True)
    to = models.CharField(max_length=512, null=True)
    ok = models.BooleanField(default=False)
    error = models.CharField(max_length=1024)

    class Meta:
        managed = True
        db_table = 'ins_notifications_messages'

    def email(self):
        text = self.notification.prepare_message(client=self.client)
        try:
            email_someone(mail_to=self.client.email, mail_from=None,
                          message_subject=self.notification.subject,
                          message_text=text)
        except MailError as e:
            self.ok = False
            self.error = str(e)
            raise
        else:
            self.ok = True
            self.error = ''
        finally:
            self.to = self.client.email
            self.time = datetime.datetime.now()
            self.save()


class InsSearch:
    def __init__(self, queryset=None):
        self.queryset = queryset

    def search(self, search_string):

        if not search_string:
            return []

        keywords = search_string.split()
        incidents = Incident.objects.all()
        if self.queryset:
            incidents = self.queryset

        for keyword in keywords:
            incidents = incidents.filter(
                Q(pk__icontains=keyword) |
                Q(name__icontains=keyword) |
                Q(rt__icontains=keyword) |
                Q(fiber__icontains=keyword) |
                Q(provider_tt__icontains=keyword) |
                Q(comment__icontains=keyword) |
                Q(provider__netname__icontains=keyword) |
                Q(provider__clientname__icontains=keyword)
            ).order_by('-pk')

        return incidents
