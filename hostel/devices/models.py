from django.db import models
from django.db.models import Q

from hostel.service.variables import DEVICE_TYPES as TYPES
from hostel.service.variables import validate_netname
from hostel.common import models as common_models


class Device(models.Model):
    STATUSES = (
        ('+', '+'),
        ('-', '—'),
    )

    RACK_PLACEMENT_CHOICES = (
        (common_models.Rack.FRONT_SIDE, 'С передней стороны стойки'),
        (common_models.Rack.BACK_SIDE, 'С задней стороны стойки'),
    )

    id = models.AutoField(primary_key=True)

    # Это поле убирать нельзя, оно нужно для генерации A-записи в DNS
    management_net = models.OneToOneField(
        'nets.Net',
        related_name='managed_device',
        blank=True,
        null=True,
        on_delete=models.SET_NULL)

    datacenter = models.ForeignKey(
        'common.Datacenter',
        related_name="device",
        blank=True,
        null=True,
        on_delete=models.SET_NULL)

    netname = models.CharField(
        max_length=255,
        blank=False,
        null=False,
        unique=True,
        validators=[validate_netname])

    rack = models.ForeignKey('common.Rack', null=True, on_delete=models.SET_NULL)
    start_unit = models.IntegerField(null=True)
    rack_placement = models.CharField(
        max_length=20,
        choices=RACK_PLACEMENT_CHOICES,
        default=RACK_PLACEMENT_CHOICES[0][0], null=False
    )
    whole_rack_depth = models.BooleanField(default=True, null=False)

    # deprecated, use "hardware" instead
    store_entry = models.OneToOneField(
        'store.Entry',
        related_name='device',
        blank=True,
        null=True,
        on_delete=models.SET_NULL)

    type = models.CharField(max_length=20, blank=False, null=True, choices=TYPES)  # deprecated

    photos = models.ManyToManyField('common.Photo')

    status = models.CharField(max_length=20, blank=True, null=True, choices=STATUSES, default=STATUSES[0][0])
    comment = models.CharField(max_length=2048, blank=True, null=True)
    community = models.CharField(max_length=40, blank=True, null=True)
    version = models.CharField(max_length=512, blank=True, null=True)
    is_managed = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'devices'

    def __str__(self):
        return self.netname

    @property
    def vendor(self):
        if self.store_entry:
            return self.store_entry.vendor or None

        return None


class DeviceSearch:
    def search(self, search_string):
        if not search_string:
            return []

        search_string = search_string.strip()
        keywords = search_string.split()

        devices = Device.objects.all()

        for keyword in keywords:
            devices = devices.filter(
                Q(netname__icontains=keyword) |
                Q(type__icontains=keyword) |
                Q(store_entry__model__icontains=keyword) |
                Q(store_entry__vendor__icontains=keyword) |
                Q(comment__icontains=keyword) |

                Q(datacenter__name__icontains=keyword) |
                Q(datacenter__address__icontains=keyword) |
                Q(datacenter__city__name__icontains=keyword)
            ).order_by("netname")

        return devices
