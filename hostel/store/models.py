from django.db import models
from hostel.service.variables import DEVICE_TYPES as TYPES
from hostel.service.variables import DEVICE_VENDORS as VENDORS
from django.db.models import Q
from hostel.common.models import Search


class Entry(models.Model):
    TYPE_CHOICES = TYPES
    VENDOR_CHOICES = VENDORS

    id = models.AutoField(primary_key=True)
    type = models.CharField(max_length=20, blank=False, null=True, choices=TYPE_CHOICES)
    model = models.CharField(max_length=255, blank=False, null=False)
    vendor = models.CharField(max_length=50, blank=True, null=True, choices=VENDOR_CHOICES)
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
        vendor = self.vendor or '<noname>'
        if self.vendor:
            vendor = self.vendor.title()

        if self.unit_height:
            return '%s %s sn: %s [%sU]' % (vendor, self.model, self.serial, self.unit_height)
        else:
            return '%s %s sn: %s' % (vendor, self.model, self.serial)


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
