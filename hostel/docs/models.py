import os
from django.db import models
from hostel.settings import MEDIA_ROOT
from django.core.files.storage import FileSystemStorage
from django.db.models import Q


class Agreement(models.Model):
    PARTNER_TYPES = (
        ("client", "Клиент"),
        ("provider", "Поставщик"),
    )

    FILE_FOLDER = "agreements"

    id = models.AutoField(primary_key=True)

    # Deprecated at 2019-01-24
    client = models.ForeignKey('clients.Client', related_name='docs', blank=True, default="", null=True,
                               on_delete=models.SET_NULL)

    company = models.ForeignKey('companies.Company', related_name='agreements', blank=True, default="", null=True,
                                on_delete=models.SET_NULL)
    agreement_number = models.CharField(blank=False, null=False, default="", max_length=100)
    name = models.CharField(max_length=255, blank=True, null=True)
    filename = models.CharField(max_length=255, blank=False, null=True)
    comment = models.TextField(blank=True, null=True)
    partner_type = models.CharField(max_length=15, blank=False, null=False, default="client", choices=PARTNER_TYPES)
    agreement_date = models.DateField(blank=True, null=True)
    is_terminated = models.BooleanField(default=False)
    creator = models.ForeignKey('common.User', null=True, blank=True, on_delete=models.SET_NULL)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'agreements'
        ordering = ['-created']

    def handle_file(self, file):
        prefix = 'Договор с неизвестным клиентом. '
        if self.company:
            prefix = 'Договор с %s. ' % self.company.name

        filename = prefix + file.name.lower().capitalize()

        fs = FileSystemStorage(location="%s/docs/%s" % (MEDIA_ROOT, self.FILE_FOLDER),
                               file_permissions_mode=0o644)
        filename = fs.get_available_name(filename)
        try:
            filename = fs.save(filename, file)
        except Exception:
            return False

        self.filename = filename
        self.save()
        return filename

    def delete_file(self):
        path = "%s/docs/%s/%s" % (MEDIA_ROOT, self.FILE_FOLDER, self.filename)
        if os.path.isfile(path):
            os.remove(path)
        self.filename = None
        self.save()

    def __str__(self):
        name = self.agreement_number
        if self.name or self.filename:
            name = "%s — %s" % (self.agreement_number, self.name or self.filename)
        return name or "Не указан"

    def delete(self, *args, **kwargs):
        Application.objects.filter(agreement=self).delete()
        self.delete_file()
        super(Agreement, self).delete(*args, **kwargs)


class Application(models.Model):
    FILE_FOLDER = "applications"
    APP_TYPE_ORDER = 'order'
    APP_TYPE_AKT = 'akt'
    APP_TYPE_OTHER = 'other'
    APP_TYPE_APPLICATION = 'application'

    RU_NAMES = {
        APP_TYPE_ORDER: 'Заказ',
        APP_TYPE_AKT: 'Акт к заказу/приложению',
        APP_TYPE_APPLICATION: 'Приложение',
    }

    APPLICATION_TYPES = (
        (APP_TYPE_ORDER, '1. Заказ'),
        (APP_TYPE_AKT, '2. Акт к заказу/приложению'),
        (APP_TYPE_APPLICATION, '3. Приложение'),
        (APP_TYPE_OTHER, '0. Другое'),
    )

    id = models.AutoField(primary_key=True)
    agreement = models.ForeignKey(Agreement, related_name='applications', default="", null=False, blank=True,
                                  on_delete=models.SET_DEFAULT)
    name = models.CharField(max_length=255, blank=True, null=True)

    application_type = models.CharField(max_length=25,
                                        choices=APPLICATION_TYPES,
                                        null=False,
                                        blank=False,
                                        default=APP_TYPE_OTHER)

    # represents self number for order, and order number for akt
    order_number = models.IntegerField(null=True, blank=True)
    date = models.DateField(blank=True, null=True)
    filename = models.CharField(max_length=255, blank=False, null=True)
    comment = models.TextField(blank=True, null=True)
    creator = models.ForeignKey('common.User', null=True, blank=True, on_delete=models.SET_NULL)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'docs'

    def handle_file(self, file):
        filename = "%s" % file.name.lower().capitalize()

        fs = FileSystemStorage(location="%s/docs/%s" % (MEDIA_ROOT, self.FILE_FOLDER),
                               file_permissions_mode=0o644)
        filename = fs.get_available_name(filename)
        try:
            filename = fs.save(filename, file)
        except:
            return False

        self.filename = filename
        self.save()
        return filename

    def delete_file(self):
        path = "%s/docs/%s/%s" % (MEDIA_ROOT, self.FILE_FOLDER, self.filename)
        if os.path.isfile(path):
            os.remove(path)
        self.filename = None
        self.save()

    def __str__(self):
        if self.application_type in [self.APP_TYPE_APPLICATION,
                                     self.APP_TYPE_ORDER,
                                     self.APP_TYPE_AKT]:
            title = self.RU_NAMES.get(self.application_type)
            title += ' №' + str(self.order_number) if self.order_number else ""
        else:
            title = self.name
        return '%s' % title

    def delete(self, *args, **kwargs):
        self.delete_file()
        super(Application, self).delete(*args, **kwargs)


class AgreementSearch:
    def __init__(self, queryset=None):
        self.queryset = Agreement.objects.all()
        if queryset:
            self.queryset = queryset

    def search(self, search_string):

        if not search_string:
            return self.queryset.none()

        search_string = search_string.strip()
        keywords = search_string.split()
        agreements = self.queryset
        for keyword in keywords:
            agreements = agreements.filter(
                Q(agreement_number__icontains=keyword) |
                Q(comment__icontains=keyword) |
                Q(name__icontains=keyword) |
                Q(filename__icontains=keyword) |
                Q(company__name__icontains=keyword) |
                Q(company__comment__icontains=keyword) |
                Q(company__client__netname__icontains=keyword) |
                Q(applications__name__icontains=keyword) |
                Q(applications__comment__icontains=keyword)
            )
        agreements = agreements.distinct()
        return agreements


class ApplicationSearch:
    def __init__(self, queryset=None):
        self.queryset = queryset

    def search(self, search_string):
        if not search_string:
            return []

        search_string = search_string.strip()
        keywords = search_string.split()
        if self.queryset:
            applications = self.queryset
        else:
            applications = Application.objects.all()
        for keyword in keywords:
            applications = applications.filter(
                Q(agreement__name__icontains=keywords) |
                Q(name__icontains=keyword) |
                Q(filename__icontains=keyword)
            )

        return applications
