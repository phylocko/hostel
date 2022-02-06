from django.db import models
from hostel.service.variables import DEVICE_TYPES as TYPES
from django.db.models import Q
from hostel.common.models import Search


class Entry(models.Model):
    TYPE_CHOICES = TYPES

    id = models.AutoField(primary_key=True)
    type = models.CharField(max_length=20, blank=False, null=True, choices=TYPE_CHOICES)
    model = models.CharField(max_length=255, blank=False, null=False)
    vendor = models.CharField(max_length=50, blank=True, null=True)
    comment = models.CharField(max_length=2048, blank=True, null=True)
    serial = models.CharField(max_length=255, blank=False, null=False, default="")
    unit_height = models.IntegerField(null=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'store'

    def __str__(self):
        """
        Should return "Juniper MX80 sn: XBN78900001 [2U]" or "Juniper MX80 sn: XBN78900001"
        """

        parts = []
        if self.type:
            parts.append(self.type.upper())

        if self.vendor:
            parts.append(self.vendor)
        else:
            parts.append('<noname>')

        if self.model:
            parts.append(self.model)

        if self.unit_height:
            parts.append(f'[{self.unit_height}]')

        return ' '.join(parts)


class EntrySearch(Search):
    queryset = Entry.objects.all()
    arguments = [
        'type__icontains',
        'model__icontains',
        'vendor__icontains',
        'comment__icontains',
        'serial__icontains',
        'device__netname__icontains',
        'device__datacenter__name__icontains',
        'device__datacenter__city__name__icontains',
        'device__datacenter__address__icontains',
    ]


class Part(models.Model):
    id = models.AutoField(primary_key=True)
    type = models.CharField(max_length=20, blank=False, null=True)
    model = models.CharField(max_length=255, blank=False, null=False)
    vendor = models.CharField(max_length=50, blank=True, null=True)
    serial = models.CharField(max_length=255, blank=False, null=False, default="")
    comment = models.CharField(max_length=2048, blank=True, null=True)
    entry = models.ForeignKey(Entry, null=True, on_delete=models.SET_NULL)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'store_parts'

    def __str__(self):
        parts = []
        if self.type:
            parts.append(self.type.upper())

        if self.vendor:
            parts.append(self.vendor)
        if self.model:
            parts.append(self.model)

        parts = [x for x in parts if x]
        if parts:
            return ' '.join(parts)

        return f'Запчасть {self.pk}'


class PartSearch(Search):
    queryset = Entry.objects.all()
    arguments = [
        'type__icontains',
        'model__icontains',
        'vendor__icontains',
        'comment__icontains',
        'serial__icontains',
        'entry__device__netname__icontains',
        'entry__device__datacenter__name__icontains',
        'entry__device__datacenter__city__name__icontains',
        'entry__device__datacenter__address__icontains',
    ]
