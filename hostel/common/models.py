import datetime
import json

import netaddr
from django.contrib.auth.models import AbstractBaseUser, UserManager, PermissionsMixin
from django.contrib.auth.validators import *
from django.db import models
from django.db.models import Q

from hostel.nets.models import Net, Netaggregator
from hostel.service.variables import lease_types, service_params, validate_mail_list, validate_netname
from hostel.settings import MEDIA_ROOT, STUPID_SHORTS
from hostel.vlans.models import Vlan
from hostel.vlans.models import Vlanaggregator


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom Hostel user
    """

    REQUIRED_FIELDS = ['email']

    THEMES = (
        ('bs3', 'BS3'),
    )
    GENDERS = (('male', 'Мужчина'), ('female', 'Женщина'))
    USER_KINDS = (
        ('tech', 'Технический персонал'),
        ('buh', 'Бухгалтерия'),
        ('manager', 'Менеджер'),
        ('project', 'Проект-менеджер')
    )

    username_validator = UnicodeUsernameValidator()

    username = models.CharField(max_length=40, unique=True, null=False, blank=False, validators=[username_validator])
    first_name = models.CharField(max_length=30, null=True, blank=True)
    last_name = models.CharField(max_length=30, null=True, blank=True)
    mid_name = models.CharField(max_length=30, null=True, blank=True)

    email = models.EmailField(null=True, blank=True, unique=True)
    phone = models.CharField(max_length=30, blank=True, null=True)
    ext_phone = models.CharField(max_length=30, blank=True, null=True)

    birthday = models.DateTimeField(blank=True, null=True, default=None)
    position = models.CharField(max_length=255, blank=True, null=True)

    kind = models.CharField(max_length=20, choices=USER_KINDS, null=False)
    gender = models.CharField(choices=GENDERS, max_length=20)
    theme = models.CharField(max_length=20, choices=THEMES, default=THEMES[0][0])
    pagination_count = models.PositiveIntegerField(blank=False, null=False, default=50)

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)

    photo = models.ImageField(null=True, upload_to='user_photos')

    last_login = models.DateTimeField(null=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'username'

    class Meta:
        ordering = ['id']
        db_table = 'users'
        swappable = 'AUTH_USER_MODEL'

    def get_full_name(self):
        values = []
        if self.first_name:
            values.append(self.first_name)

        if self.mid_name:
            values.append(self.mid_name)

        if self.last_name:
            values.append(self.last_name)

        if values:
            return ' '.join(values)
        return ''


class City(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, blank=False, null=False, unique=True)
    map_url = models.URLField(blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'cities'

    def __str__(self):
        return self.name


class Search:
    queryset = None
    arguments = []
    local_search_arguments = []

    def __init__(self, queryset=None):
        if queryset:
            self.queryset = queryset

    def search(self, search_string):
        return self._search(self.arguments, search_string)

    def local_search(self, search_string):
        return self._search(self.local_search_arguments, search_string)

    def _search(self, arguments, search_string):
        listing = self.queryset

        for word in search_string.split():
            or_expression = Q()
            for argument in arguments:
                arg_dict = {argument: word}
                or_expression |= Q(**arg_dict)
            listing = listing.filter(or_expression)
        return listing


class CitySearch(Search):
    queryset = City.objects.all().order_by('name')
    arguments = [
        'name__icontains',
        'engname__icontains',
        'community__icontains',
    ]


class Port(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, blank=False, null=False, unique=False)
    iface_index = models.IntegerField(null=True)
    # Don't forget to remove null and blank
    bundle = models.ForeignKey('common.Bundle', related_name='ports',
                               null=True, blank=True,
                               on_delete=models.CASCADE)
    description = models.CharField(max_length=100, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.iface_index = self._iface_index()
        super(Port, self).save(*args, *kwargs)

    def _iface_index(self):
        prefix = '100'

        if 'FastEthernet' in self.name:
            prefix = '110'

        if 'fe' in self.name:
            prefix = '110'

        if 'GigabitEthernet' in self.name:
            prefix = '120'

        if 'ge' in self.name:
            prefix = '120'

        if 'xe' in self.name:
            prefix = '140'

        if 'et' in self.name:
            prefix = '150'

        if 'ae' in self.name:
            prefix = '160'

        if 'po' in self.name:
            prefix = '160'

        name_normalized = self.name
        if '.' in self.name:
            parts = self.name.split('.')
            name_normalized = parts[0]
        iface_index = int(prefix + ''.join([x for x in list(name_normalized) if x.isdigit()]))
        return iface_index

    class Meta:
        managed = True
        db_table = 'ports'
        ordering = ['iface_index']
        unique_together = ('bundle', 'name')

    def __str__(self):
        return "%s (%s)" % (self.name, self.description)

    def is_updated_today(self):
        few_hours = datetime.timedelta(hours=12)
        return datetime.datetime.now() - self.updated < few_hours

    def is_gone(self):
        three_days = datetime.timedelta(days=3)
        return datetime.datetime.now() - self.updated > three_days

    def mrtg_name(self):
        return self.name


class BundleVlan(models.Model):
    MODES = (
        ("tagged", "Tagged"),
        ("untagged", "Untagged"),
    )
    services = models.ManyToManyField('common.Service', related_name='bundle_vlans')
    subservices = models.ManyToManyField('common.SubService', related_name='bundle_vlans')
    vlan = models.ForeignKey('vlans.Vlan', null=False, blank=False, on_delete=models.CASCADE)
    bundle = models.ForeignKey('common.Bundle', null=False, blank=False, on_delete=models.CASCADE)
    mode = models.CharField(max_length=20, blank=False, null=False, choices=MODES)
    comment = models.TextField(max_length=2048, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = u'bundle_vlan'
        unique_together = ('bundle', 'vlan')

    def is_updated_today(self):
        few_hours = datetime.timedelta(hours=12)
        return datetime.datetime.now() - self.updated < few_hours

    def is_gone(self):
        three_days = datetime.timedelta(days=3)
        return datetime.datetime.now() - self.updated > three_days

    def __str__(self):
        return '%s:%s : %s [%s] %s' % (
            self.bundle.device.netname, self.bundle.name, self.vlan.vname, self.vlan.vlannum, self.mode[0].upper())


class Bundle(models.Model):
    name = models.CharField(max_length=50, null=False, blank=False)
    description = models.CharField(max_length=50, null=True, blank=True)
    iface_index = models.IntegerField(null=True)

    is_lag = models.BooleanField(default=False)
    device = models.ForeignKey('devices.Device', related_name='bundles',
                               null=False, blank=False,
                               on_delete=models.CASCADE)
    remote_device = models.ForeignKey('devices.Device', related_name='remote_bundles',
                                      null=True, blank=True,
                                      on_delete=models.SET_NULL)
    vlans = models.ManyToManyField('vlans.Vlan', related_name='bundles',

                                   through='common.BundleVlan')
    comment = models.TextField(max_length=2048, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bundles'
        ordering = ['iface_index']
        unique_together = ('device', 'name')

    def save(self, *args, **kwargs):
        self.iface_index = self._iface_index()
        super(Bundle, self).save(*args, *kwargs)

    def _iface_index(self):
        prefix = '100'

        if 'FastEthernet' in self.name:
            prefix = '110'

        if 'fe' in self.name:
            prefix = '110'

        if 'GigabitEthernet' in self.name:
            prefix = '120'

        if 'ge' in self.name:
            prefix = '120'

        if 'xe' in self.name:
            prefix = '140'

        if 'et' in self.name:
            prefix = '150'

        if 'ae' in self.name:
            prefix = '160'

        if 'po' in self.name:
            prefix = '160'

        name_normalized = self.name
        if '.' in self.name:
            parts = self.name.split('.')
            name_normalized = parts[0]

        iface_index = int(prefix + ''.join([x for x in list(name_normalized) if x.isdigit()]))

        return iface_index

    def mrtg_name(self):
        return self.name

    def traffic_ports(self):
        """
        Represents all ports to count traffic.
        If this is a Juniper ae* interface, will return the ae.
        Else will return it's members
        """
        if not self.device.store_entry:
            return []

        if self.device.store_entry.vendor == 'juniper':
            return [self]

        return self.ports.all()

    def is_updated_today(self):
        few_hours = datetime.timedelta(hours=12)
        return datetime.datetime.now() - self.updated < few_hours

    def is_gone(self):
        three_days = datetime.timedelta(days=3)
        return datetime.datetime.now() - self.updated > three_days

    def __str__(self):
        if self.description:
            return '%s (%s)' % (self.name, self.description)
        return self.name


class Lease(models.Model):
    id = models.AutoField(primary_key=True)

    ticket = models.CharField(max_length=20, blank=False, null=True)
    type = models.CharField(max_length=50, blank=False, null=False, choices=lease_types)
    organization = models.ForeignKey('clients.Client', blank=True, null=True, on_delete=models.SET_NULL)
    cities = models.ManyToManyField('common.City', related_name='leases')
    group = models.ForeignKey('common.LeaseGroup', related_name='leases',
                              blank=True, null=True, on_delete=models.PROTECT)
    application = models.ForeignKey('docs.Application', related_name='leases', on_delete=models.SET_NULL, null=True)
    identity = models.CharField(max_length=128, blank=False, null=False)
    addresses = models.CharField(max_length=256, blank=True, null=True)
    agreement = models.CharField(max_length=128, blank=True, null=True)
    support_email = models.CharField(max_length=255, blank=True, null=True, validators=[validate_mail_list])

    google_map_url = models.URLField(null=True, blank=True)

    comment = models.TextField(max_length=2048, blank=True, null=True)

    contacts = models.TextField(max_length=2048, blank=True, null=True)
    is_ours = models.BooleanField(default=False)

    # It is for fibers only. False means fiber is rented
    is_bought = models.BooleanField(default=False)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    # deprecated
    description = models.CharField(max_length=50, blank=True, null=True, )

    class Meta:
        managed = True
        db_table = 'leases'

    def get_support_email(self):
        if self.support_email:
            return self.support_email

        if self.organization:
            if self.organization.support_email:
                return self.organization.support_email

    def get_title(self):
        return '%s %s' % (self.type.upper(), self.identity)

    # save lease
    def save(self, *args, **kwargs):
        if self.addresses:
            for match in STUPID_SHORTS:
                self.addresses = self.addresses.replace(match, '')

        super().save()

    def __str__(self):
        if not self.type:
            self.type = 'other'

        if self.organization:
            return '%s via %s' % (self.type.upper(), self.organization.netname)
        else:
            return self.type.upper()


class LeaseGroup(models.Model):
    ticket = models.CharField(max_length=20, blank=False, null=True)
    description = models.CharField(max_length=128, null=False, blank=False)
    comment = models.TextField(max_length=2048, blank=True, null=True)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'lease_groups'

    def __str__(self):
        if self.rt:
            return 'RT#%s: %s' % (self.rt, self.description)
        return self.description


class LeaseSearch(Search):
    queryset = Lease.objects.all()
    arguments = [
        'type__icontains',
        'identity__icontains',
        'addresses__icontains',
        'agreement__icontains',
        'description__icontains',
        'organization__netname__icontains',
        'organization__clientname__icontains',
    ]


class BurstSet(models.Model):
    client = models.ForeignKey('clients.Client', blank=False, null=False, on_delete=models.CASCADE)
    bundles = models.ManyToManyField('common.Bundle', related_name='bursts_member')
    extract_bundles = models.ManyToManyField('common.Bundle', related_name='bursts_negative')
    limit = models.IntegerField(blank=True, null=True, default=None)
    name = models.CharField(max_length=255, blank=False, null=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    price = models.FloatField(null=False, default=0)
    subscription_fee = models.IntegerField(null=False, default=0)
    with_tax = models.BooleanField(default=False)
    DIRECTIONS = (
        ('max', 'Превалирующий'),
        ('in', 'Входящий'),
        ('out', 'Исходящий')
    )
    direction = models.CharField(choices=DIRECTIONS, max_length=20, default=DIRECTIONS[0][0])

    class Meta:
        managed = True
        db_table = 'burst_sets'

    def traffic_ports(self):
        ports = []
        for bundle in self.bundles.all():
            if bundle.device.store_entry.vendor == 'juniper':
                ports.append(bundle)
            else:
                for port in bundle.ports.all():
                    ports.append(port)
        return ports

    def substract_ports(self):
        ports = []
        for bundle in self.extract_bundles.all():
            if not bundle.ports.all():
                ports.append(bundle)
            else:
                for port in bundle.ports.all():
                    ports.append(port)
        return ports

    def __str__(self):
        return self.name


class UserSearch(Search):
    queryset = User.objects.all().order_by('username')
    arguments = [
        'username__icontains',
        'last_name__icontains',
        'first_name__icontains',
        'mid_name__icontains',
        'position__icontains',
        'email__icontains',
    ]


class Rack(models.Model):
    FRONT_SIDE = 'front'
    BACK_SIDE = 'back'

    location = models.CharField(max_length=64, null=True, blank=True)
    height = models.IntegerField(default=42)
    datacenter = models.ForeignKey('common.Datacenter', null=True, on_delete=models.SET_NULL)
    comment = models.TextField(null=True)

    class Meta:
        managed = True
        db_table = 'racks'

    def __str__(self):
        if self.datacenter:
            display_name = self.datacenter.name + ', ' + self.location
        else:
            display_name = self.location or 'Rack'
        display_name += ' [%sU]' % self.height
        return display_name

    def can_accommodate(self, start_unit, end_unit, side=None, device=None, need_whole_depth=False):
        """
        Checks if a device can be placed in the rack

        start_unit: numerically lower unit of the device (including)
        end_unit: numerically higher unit of the device (including)
        side: which side of rack is placed ('front', 'back')
        device: device we need to accommodate. For excluding from occupied units list
        """

        free_units = self.get_free_units(excluded_device=device, side=side, need_whole_depth=need_whole_depth)
        device_units = [x for x in range(start_unit, end_unit + 1)]

        for unit in device_units:
            if unit not in free_units:
                return False

        return True

    def get_free_units(self, side, excluded_device=None, need_whole_depth=False):
        free_units = {x for x in range(1, self.height + 1)}

        rack_devices = self.device_set.filter(
            store_entry__isnull=False,
            store_entry__unit_height__isnull=False,
            start_unit__isnull=False,
        )

        for device in rack_devices:

            if device == excluded_device:
                continue

            device_on_my_side = device.rack_placement == side

            if device_on_my_side or device.whole_rack_depth or need_whole_depth:

                device_range = range(
                    device.start_unit,
                    device.start_unit + device.store_entry.unit_height
                )
                for unit in device_range:
                    free_units.remove(unit)

        return free_units

    def facades(self, excluded_device=None):
        """
        Generate a following structure:
        [
            {'type': 'empty', 'number': 42},  # A FREE unit
            {'type': 'empty', 'number': 41},  # A FREE unit
            {'type': 'device', 'number': 40, 'device': Device,},  # A unit occupied by Device (start)
            {'type': 'skip', 'number': 39, 'device': Device,},    # A unit occupied by Device (continued)
            {'type': 'empty', 'number': 38},  # A FREE unit
            ...
            {'type': 'empty',  'number': 1},  # A FREE unit
        ]
        """

        REVERSE = True

        TYPE_EMPTY = 'EMPTY'
        TYPE_DEVICE = 'DEVICE'
        TYPE_OTHER_DEVICE_BLOCKING = 'OTHER_DEVICE_BLOCKING'
        TYPE_OTHER_DEVICE_INFO = 'OTHER_DEVICE_INFO'
        TYPE_SKIP = 'SKIP'

        front_schema = [
            {'type': TYPE_EMPTY, 'number': x}
            for x in range(0, self.height + 1)
        ]

        back_schema = [
            {'type': TYPE_EMPTY, 'number': x}
            for x in range(0, self.height + 1)
        ]

        devices = self.device_set.filter(
            start_unit__isnull=False,
            store_entry__isnull=False
        ).order_by('start_unit')

        for device in devices:
            if device == excluded_device:
                continue

            device_range = range(device.start_unit, device.start_unit + device.store_entry.unit_height)
            for unit in device_range:

                front_unit = front_schema[unit]
                back_unit = back_schema[unit]

                my_unit, other_unit = front_unit, back_unit
                if device.rack_placement == self.FRONT_SIDE:
                    device_here = device.rack_placement = self.FRONT_SIDE
                else:
                    device_here = device.rack_placement = not self.FRONT_SIDE

                if device_here:
                    my_unit['type'] = TYPE_DEVICE
                    my_unit['device'] = device
                    if other_unit['type'] != TYPE_DEVICE:
                        other_unit['device'] = device
                        other_unit['type'] = TYPE_OTHER_DEVICE_INFO
                        if device.whole_rack_depth:
                            other_unit['type'] = TYPE_OTHER_DEVICE_BLOCKING
                else:
                    other_unit['type'] = TYPE_DEVICE
                    other_unit['device'] = device
                    if my_unit['type'] != TYPE_DEVICE:
                        my_unit['device'] = device
                        my_unit['type'] = TYPE_OTHER_DEVICE_INFO
                        if device.whole_rack_depth:
                            my_unit['type'] = TYPE_OTHER_DEVICE_BLOCKING

        front_schema = front_schema[1:]
        back_schema = back_schema[1:]

        for schema in [front_schema, back_schema]:
            if REVERSE:
                schema.reverse()

            current_device = None
            for unit in schema:
                if unit['type'] == TYPE_DEVICE:
                    if unit['device'] == current_device:
                        unit['type'] = TYPE_SKIP
                    else:
                        current_device = unit['device']

        for u in front_schema:
            print(u)
        return front_schema, back_schema


class Datacenter(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, blank=False, null=True)
    city = models.ForeignKey(City, blank=False, null=True, on_delete=models.SET_NULL)
    address = models.CharField(max_length=255, blank=False, null=False)
    comment = models.CharField(max_length=2048, blank=True, null=True)
    contacts = models.CharField(max_length=2048, blank=True, null=True)
    organization = models.ForeignKey('clients.Client', blank=True, null=True, on_delete=models.SET_NULL)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'datacentres'

    def __str__(self):

        city = '<No city>'
        if self.city:
            city = self.city.name

        address = '<No address>'
        if self.address:
            address = self.address

        return '%s, %s [%s]' % (city, address, self.name)

    def save(self, *args, **kwargs):
        if self.address:
            for match in STUPID_SHORTS:
                self.address = self.address.replace(match, '')
        super().save()


class DatacenterSearch(Search):
    queryset = Datacenter.objects.all()
    arguments = [
        'name__icontains',
        'address__icontains',
        'comment__icontains',
        'organization__netname__icontains',
        'organization__clientname__icontains',
        'city__name__icontains',
        'contacts__icontains',
    ]


class Autonomoussystem(models.Model):
    id = models.AutoField(primary_key=True)
    asn = models.IntegerField(null=False, blank=False)
    asset = models.CharField(max_length=25, null=False, blank=True)
    aslist = models.CharField(max_length=255, null=False, blank=True)
    engname = models.CharField(max_length=255, null=False, blank=False, validators=[validate_netname],
                               default="undefined")

    client = models.ForeignKey(
        'clients.Client',
        on_delete=models.CASCADE,
        related_name='asns',
        null=False
    )

    comment = models.TextField(max_length=2048, blank=True, null=True)
    asset6 = models.CharField(max_length=25, blank=True, null=True)
    ticket = models.CharField(max_length=20, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'autonomousSystems'

    def is_white(self):
        return self.asn < 64512 or self.asn > 66000

    def __str__(self):
        if self.engname:
            return 'AS%s [%s]' % (self.asn, self.engname)
        return 'AS%s' % self.asn


class ASIndependantService:
    freenets = []
    service_name = str
    defaults = dict()
    freevlans = []

    def __init__(self):
        self.ourservice = Ourservice.objects.get(name=self.service_name)
        if self.defaults['require_vlan']:
            self.vlan_aggregator = Vlanaggregator()

        if self.defaults['require_net']:
            self.netaggregator = Netaggregator(Net.objects.get(pk=self.ourservice.root_net))

    def get_free_nets(self):
        if not self.freenets:
            self.freenets = self.netaggregator.freenets(longest_netmask=self.defaults['longest_netmask'],
                                                        shortest_netmask=self.defaults['shortest_netmask'])
        return self.freenets

    def suggest_address(self):
        if not self.freenets:
            self.netaggregator.freenets(longest_netmask=self.defaults['longest_netmask'],
                                        shortest_netmask=self.defaults['shortest_netmask'])

        if len(self.freenets) > 0:
            self.defaults['address'] = self.freenets[0].address

        return {'address': self.defaults['address'], 'netmask': self.defaults['longest_netmask']}

    def __str__(self):
        return "Service %s" % self.service_name.upper()


class ASRequiredService:
    freenets = []
    service_name = str
    defaults = dict()
    freevlans = []

    def __init__(self):
        self.ourservice = Ourservice.objects.get(name=self.service_name)

        if self.defaults['require_vlan']:
            self.vlan_aggregator = Vlanaggregator()

        if self.defaults['require_net']:
            self.netaggregator = Netaggregator(Net.objects.get(pk=self.ourservice.root_net))

    def get_free_nets(self):
        if not self.freenets:
            self.freenets = self.netaggregator.freenets(longest_netmask=self.defaults['longest_netmask'],
                                                        shortest_netmask=self.defaults['shortest_netmask'])
        return self.freenets

    def suggest_address(self):
        if not self.freenets:
            self.netaggregator.freenets(longest_netmask=self.defaults['longest_netmask'],
                                        shortest_netmask=self.defaults['shortest_netmask'])

        if len(self.freenets) > 0:
            self.defaults['address'] = self.freenets[0].address

        return {'address': self.defaults['address'], 'netmask': self.defaults['longest_netmask']}

    def __str__(self):
        return "Service %s" % self.service_name.upper()


class service_inet2(ASRequiredService):
    service_name = 'inet2'

    TYPES = (
        ('generic', 'Generic'),
        ('peer', 'Peer'),
        ('dg', 'With DoS guard'),
        ('rkn', 'With RKN filter'),
    )

    defaults = {
        'status': '?',
        'servicetype': 'generic',
        'require_vlan': False,
        'multiple_vlans': False,
        'require_net': True,
        'longest_netmask': 32,
        'shortest_netmask': 24,
        'require_port': True,
    }


class service_telia(ASRequiredService):
    service_name = 'telia'

    TYPES = (
        ('generic', 'Generic'),
    )

    defaults = {
        'status': '?',
        'servicetype': 'generic',
        'require_vlan': True,
        'require_net': False,
        'longest_netmask': 32,
        'shortest_netmask': 24,
        'require_port': True,
    }


class service_homeix(ASRequiredService):
    service_name = 'homeix'

    TYPES = (
        ('generic', 'Generic'),
    )

    defaults = {
        'status': '?',
        'servicetype': 'global',
        'require_vlan': False,
        'require_net': True,
        'longest_netmask': 32,
        'shortest_netmask': 32,
        'require_port': True,
    }


class service_wix(ASRequiredService):
    service_name = 'wix'

    TYPES = (
        ('global', 'Global'),
        ('ru', 'RU'),
        ('msk', 'MSK'),
        ('mskplus', 'MSK+'),
        ('customers', 'Customers'),
        ('peer', 'Peer'),
    )

    defaults = {
        'status': '?',
        'servicetype': 'global',
        'require_vlan': False,
        'multiple_vlans': False,
        'require_net': True,
        'address': '',
        'longest_netmask': 32,
        'shortest_netmask': 23,
        'require_port': True,
    }


class service_bgpinet(ASRequiredService):
    service_name = "bgpinet"

    TYPES = (
        ('generic', 'Generic'),
        ('peer', 'Peer'),
    )

    defaults = {
        'status': '+',
        'servicetype': 'generic',
        'require_vlan': True,
        'multiple_vlans': False,
        'require_net': True,
        'address': '',
        'longest_netmask': 30,
        'shortest_netmask': 24,
        'require_port': True,
    }


class service_l3inet(ASIndependantService):
    service_name = "l3inet"

    TYPES = (
        ('generic', 'Generic'),
    )

    defaults = {
        'status': '+',
        'servicetype': 'generic',
        'require_vlan': True,
        'multiple_vlans': False,
        'require_net': True,
        'longest_netmask': 30,
        'shortest_netmask': 24,
        'require_port': True,
    }


class service_l3vpn(ASIndependantService):
    service_name = "l3vpn"

    TYPES = (
        ('generic', 'Generic'),
    )

    defaults = {
        'status': '+',
        'servicetype': 'generic',
        'require_vlan': True,
        'multiple_vlans': True,
        'require_net': True,
        'longest_netmask': 30,
        'shortest_netmask': 24,
        'require_port': True,
    }


class service_l2(ASIndependantService):
    service_name = "l2"

    TYPES = (
        ('vlan', 'Vlan'),
        ('vpls', 'VPLS'),
        ('qinq', '802.1ad Q-in-Q'),
    )

    defaults = {'status': '+',
                'servicetype': 'generic',
                'require_vlan': True,
                'multiple_vlans': False,
                'require_net': False,
                'require_port': True,
                }


class service_l1(ASIndependantService):
    service_name = "l1"

    TYPES = (
        ('dwdm', 'Лямбда *WDM'),
        ('fiber', 'Волокно'),
        ("crossconnect", "СЛ (Кроссировка на площадке)"),
    )

    defaults = {'status': '+',
                'servicetype': 'dwdm',
                'require_vlan': False,
                'require_net': False,
                'require_port': False,
                }


class service_24htv(ASIndependantService):
    """
    Deprecated on 2018-12-04
    """
    service_name = "24htv"

    TYPES = (
        ('generic', 'Generic'),
    )

    defaults = {'status': '+',
                'servicetype': 'generic',
                'require_vlan': True,
                'multiple_vlans': False,
                'require_net': False,
                'require_port': True,
                }


class service_telephony(ASIndependantService):
    service_name = "telephony"

    TYPES = (
        ('generic', 'Generic'),
    )

    defaults = {
        'status': '+',
        'servicetype': 'generic',
        'require_vlan': False,
        'require_net': False,
        'require_port': False,
    }


class service_colocation():
    service_name = "colocation"
    TYPES = (
        ('generic', 'Generic'),
    )

    defaults = {'status': '+',
                'servicetype': 'generic',
                'require_vlan': False,
                'require_net': False,
                'require_port': False,
                }


class service_hosting():
    service_name = "hosting"

    TYPES = (
        ('generic', 'Generic'),
        ('vps', 'VPS'),
    )

    defaults = {'status': '+',
                'servicetype': 'generic',
                'require_net': False,
                'require_vlan': False,
                'require_port': False,
                }


class ArchivedService(models.Model):
    ticket = models.CharField(max_length=20, blank=False, null=True)
    name = models.CharField(db_column='service', max_length=10, blank=False, null=False)
    params = models.TextField(blank=True, null=True)
    client = models.ForeignKey(
        'clients.Client',
        on_delete=models.CASCADE,
        related_name='archived_services',
        null=False
    )

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __init__(self, *args, **kwargs):
        service = None
        if 'service' in kwargs:
            service = kwargs.pop('service')
        super(ArchivedService, self).__init__(*args, **kwargs)

        if service:
            self.pk = service.pk
            self.rt = service.rt
            self.name = service.name
            self.client = service.client
            self.created = datetime.datetime.now()
            self.params = service.serialize()

    def __str__(self):
        if self.pk:
            return "%s-%s" % (self.name.upper()[:3], self.pk)
        else:
            return 'Archived service'

    def params_dict(self):
        return json.loads(self.params)


class SubService(models.Model):
    SID_RE = r'^\S{2,3}-\d{1,4}-\S{1,20}$'

    STATUSES = (
        ('on', 'Включена постоянно'),
        ('test', 'Тест'),
        ('off', 'Выключена'),
    )
    sub_id = models.CharField(max_length=20, blank=False, null=False)
    service = models.ForeignKey(
        'common.Service',
        null=False,
        related_name='subservices',
        on_delete=models.CASCADE)

    vlans = models.ManyToManyField('vlans.Vlan', related_name='subservices')
    cities = models.ManyToManyField('common.City', related_name='subservices')
    leases = models.ManyToManyField('common.Lease', related_name="subservices")

    ticket = models.CharField(max_length=20, blank=False, null=True)
    status = models.CharField(max_length=20, blank=False, null=False, choices=STATUSES)
    comment = models.CharField(max_length=2048, blank=True, null=True)
    description = models.CharField(max_length=512, blank=True, null=True)  # Description for client. Do not swear!

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'subservices'
        ordering = ['-pk']
        unique_together = ('sub_id', 'service')

    def __str__(self):
        if self.sub_id:
            return '%s-%s' % (self.service.__str__(), self.sub_id)
        if self.pk and self.service:
            return self.service.__str__() + '-?'
        return '<New subservice>'

    def delete(self, delete_nets=False, delete_vlans=False, *args, **kwargs):
        # archived_subservice = ArchivedSubService(service=self)
        # archived_subservice.save()

        if delete_nets:
            self.nets.all().delete()
        if delete_vlans:
            self.vlans.all().delete()

        super().delete(*args, *kwargs)


class Service(models.Model):
    STATUSES = (
        ('on', 'Включена постоянно'),
        ('test', 'Тест'),
        ('off', 'Выключена'),
    )
    ticket = models.CharField(max_length=20, blank=False, null=True)
    name = models.CharField(db_column='service', max_length=10, blank=False, null=False)

    client = models.ForeignKey(
        'clients.Client',
        on_delete=models.CASCADE,
        related_name='services',
        null=False
    )

    asn = models.ForeignKey(
        'common.Autonomoussystem',
        on_delete=models.CASCADE,
        related_name='services',
        null=True
    )
    application = models.ForeignKey('docs.Application', related_name='services', on_delete=models.SET_NULL, null=True)

    # FIXME: lease -> leases
    lease = models.ManyToManyField(Lease, related_name="services")
    status = models.CharField(max_length=20, blank=False, null=False, choices=STATUSES)
    cities = models.ManyToManyField('common.City', related_name='services')
    comment = models.CharField(max_length=2048, blank=True, null=True)
    servicetype = models.CharField(max_length=25, blank=False, null=False)
    description = models.CharField(max_length=512, blank=True, null=True)  # Description for client. Do not swear!
    provider_id = models.CharField(max_length=2048, blank=True, null=True)
    commited_bandwidth = models.IntegerField(null=True, blank=True, default=None)
    maximum_bandwidth = models.IntegerField(null=True, blank=True, default=None)
    start_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'services'
        ordering = ['-pk']

    def serialize(self):
        data = {
            'status': self.status,
            'commercial_status': self.commercial_status,
            'comment': self.comment or '',
            'servicetype': self.servicetype,
            'description': self.description or '',
            'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'end_time': self.end_time.strftime('%Y-%m-%d %H:%M:%S'),
            'created': self.created.strftime('%Y-%m-%d %H:%M:%S'),
            'updated': self.updated.strftime('%Y-%m-%d %H:%M:%S'),
        }

        if self.asn:
            data['asn'] = str(self.asn)

        data['leases'] = ['%s | %s | %s | %s' % (x.organization,
                                                 x.type,
                                                 x.agreement,
                                                 x.identity)
                          for x in self.lease.all()]
        data['cities'] = [str(x) for x in self.cities.all()]
        data['nets'] = [str(x) for x in self.net.all()]
        data['vlans'] = [str(x) for x in self.vlan.all()]
        data['bundle_vlans'] = [str(x) for x in self.bundle_vlans.all()]

        return json.dumps(data)

    def params(self):
        if not self.name:
            return {}
        return service_params.get(self.name, {})

    @property
    def commercial_status(self):

        if not self.client.enabled:
            return 'client_off'

        if self.status == 'off':
            return 'off'

        if self.start_time > datetime.datetime.now():
            if self.status == 'on':
                return 'waiting_on'
            else:
                return 'waiting_test'

        if self.status == 'on':
            return 'on'

        if self.status == 'test':
            if self.end_time > datetime.datetime.now():
                return 'on_test'
            return 'off_test'

    def suggested_nets(self):
        params = self.params()
        service_model = Ourservice.objects.get(name=self.name)
        service_net = Net.objects.get(pk=service_model.root_net)
        aggregator = Netaggregator(service_net)
        free_nets = aggregator.freenets(longest_netmask=params['max_mask'],
                                        shortest_netmask=params['min_mask'])
        return free_nets

    def suggested_hosts(self):

        our_service = Ourservice.objects.get(name=self.name)
        service_net = Net.objects.get(pk=our_service.root_net)
        occupied_nets = Net.objects.filter(ipaddress_from__gte=service_net.ipaddress_from,
                                           ipaddress_to__lte=service_net.ipaddress_to,
                                           netmask__gt=service_net.netmask)
        netaddr_network = netaddr.IPNetwork(service_net.network)
        entire_range = [x for x in netaddr_network.iter_hosts()]

        for net in occupied_nets:
            for n in netaddr.IPNetwork(net.network).iter_hosts():
                entire_range.remove(n)

        return entire_range

    def get_free_vlans(self):
        aggregator = Vlanaggregator()
        return aggregator.freevlans()

    def __str__(self):
        if not self.pk:
            if self.name:
                return 'New %s service' % self.name
            else:
                return 'New service'
        return "%s-%s" % (self.name.upper()[:3], self.pk)

    @property
    def warnings(self):
        warnings = []
        params = self.params()

        if params.get('require_net') and self.net.count() == 0:
            warnings.append('Не привязана сеть')

        if params.get('require_vlan') and self.vlan.count() == 0:
            warnings.append('Не привязан vlan')

        if params.get('require_as') and not self.asn:
            warnings.append('Не задана AS')

        return warnings

    def delete(self, delete_nets=False, delete_vlans=False, *args, **kwargs):
        archived_service = ArchivedService(service=self)
        archived_service.save()

        if delete_nets:
            self.net.all().delete()
        if delete_vlans:
            self.vlan.all().delete()

        super(Service, self).delete(*args, *kwargs)

    def save(self, *args, **kwargs):
        if self.description:
            for match in STUPID_SHORTS:
                self.description = self.description.replace(match, '')
        super().save()


class Phone(models.Model):
    number = models.CharField(max_length=20, null=False, unique=True)
    client = models.ForeignKey('clients.Client', null=True, on_delete=models.SET_NULL)
    description = models.CharField(max_length=256, null=True)
    count = models.IntegerField(default=0)
    blacklisted = models.BooleanField(default=False)
    spam = models.BooleanField(default=False)

    class Meta:
        managed = True
        db_table = 'phones'

    def as_dict(self):
        return {
            'id': self.pk,
            'number': self.number,
            'netname': None if not self.client else self.client.netname,
            'description': self.description,
            'blacklisted': self.blacklisted,
            'spam': self.spam,
            'count': self.count,
        }

    def show_phone(self):
        if self.number.startswith('+'):
            return self.number
        return '+7' + self.number


class Call(models.Model):
    phone = models.ForeignKey('common.Phone', null=False, on_delete=models.CASCADE)
    time = models.DateTimeField(auto_now_add=True)
    bot_message_id = models.BigIntegerField(null=True)

    class Meta:
        managed = True
        db_table = 'calls'

    def as_dict(self):
        return {
            'id': self.pk,
            'phone_id': None if not self.phone else self.phone.pk,
            'bot_message_id': self.bot_message_id,
            'time': self.time.strftime('%Y-%m-%d %H:%M:%s')
        }


class Ourservice(models.Model):
    # Этот класс представляет из себя услугу для выведения в списке возможных услуг.
    id = models.AutoField(primary_key=True)  # Field name made lowercase.
    name = models.CharField(max_length=20, blank=True, null=True, unique=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    comment = models.CharField(max_length=255, blank=True, null=True)

    # deprecated on 2018-12-04
    visible = models.BooleanField(default=True)

    # deprecated on 2018-12-04
    tech_type = models.CharField(max_length=10, blank=True, null=True)

    # deprecated on 2018-12-04
    # UPD: can't be deprecated. It's using by api/rs/peers/ for query nets of a service
    root_net = models.IntegerField(null=True)

    class Meta:
        managed = True
        db_table = 'our_services'

    def __str__(self):
        return self.name


class Photo(models.Model):
    id = models.AutoField(primary_key=True)
    src = models.ImageField(upload_to='photos')
    name = models.CharField(max_length=20, blank=True, null=True, unique=True)
    comment = models.CharField(max_length=255, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'photos'


class ServiceSearch:
    def __init__(self, queryset=None):
        self.queryset = Service.objects.all()
        if queryset:
            self.queryset = queryset

    def search(self, search_string):

        if not search_string:
            return None

        search_string = search_string.strip()

        sid_re = re.compile("^[A-Za-z0-9]{2,3}-[0-9]{1,8}$")
        rs_re = re.compile("^peer_(112|113|122|123)[0-9]{1,3}$")

        if rs_re.search(search_string):

            address_part = search_string[5:]
            penultimate_octet = address_part[:3]
            last_octet = address_part[3:]

            if penultimate_octet in ['112', '113']:
                service_address = "193.106.%s.%s" % (penultimate_octet, last_octet)
            elif penultimate_octet in ['122', '123']:
                service_address = "85.112.%s.%s" % (penultimate_octet, last_octet)
            else:
                return Service.objects.none()

            try:
                service_net = Net.objects.get(address=service_address, netmask=32)
            except Net.DoesNotExist:
                return Service.objects.none()

            if service_net.service:
                return [service_net.service]
            else:
                return Service.objects.none()

        if sid_re.search(search_string):
            parts = search_string.split('-')
            name, pk = parts[0], parts[1]
            try:
                service = Service.objects.get(pk=pk, name__icontains=name)
            except Service.DoesNotExist:
                return Service.objects.none()
            return [service]

        services = self.queryset

        keywords = search_string.split()
        for keyword in keywords:
            services = services.filter(Q(cities__name__icontains=keyword) |
                                       Q(client__netname__icontains=keyword) |
                                       Q(client__clientname__icontains=keyword) |
                                       Q(name__icontains=keyword) |
                                       Q(servicetype__icontains=keyword) |
                                       Q(comment__icontains=keyword) |
                                       Q(description__icontains=keyword)).order_by("pk")

        return services.distinct()


class SubServiceSearch:

    def __init__(self, queryset=None):
        self.queryset = SubService.objects.all()
        if queryset:
            self.queryset = queryset

    def search(self, search_string):

        if not search_string:
            return None

        search_string = search_string.strip()

        subservice_re = re.compile(SubService.SID_RE)
        if subservice_re.match(search_string):
            parts = search_string.split('-')
            subservices = self.queryset.filter(service_id=parts[1], sub_id=parts[2])
            if subservices.count() > 0:
                return subservices

        subservices = self.queryset

        keywords = search_string.split()
        for keyword in keywords:
            subservices = subservices.filter(
                Q(sub_id__icontains=keyword) |
                Q(cities__name__icontains=keyword) |
                Q(service__client__netname__icontains=keyword) |
                Q(service__client__clientname__icontains=keyword) |
                Q(service__name__icontains=keyword) |
                Q(service__servicetype__icontains=keyword) |
                Q(comment__icontains=keyword) |
                Q(description__icontains=keyword)
            ).order_by("pk")

        return subservices.distinct()


class PortSearch(Search):
    queryset = Port.objects.all().order_by('bundle__device__netname')
    arguments = [
        'name__icontains',
        'description__icontains',
        'bundle__device__netname__icontains',
        'bundle__device__datacenter__address__icontains',
    ]


class BundleSearch(Search):
    queryset = Bundle.objects.all().order_by('device__netname', 'iface_index')
    arguments = [
        'name__icontains',
        'description__icontains',
        'device__datacenter__name__icontains',
        'device__netname__icontains',
        'device__datacenter__address__icontains',
        'device__datacenter__city__name__icontains',
    ]
    local_search_arguments = [
        'name__icontains',
        'description__icontains',
    ]


class BurstSetSearch(Search):
    queryset = BurstSet.objects.all().order_by('client__netname')
    arguments = [
        'name__icontains',
        'client__netname__icontains',
        'client__clientname__icontains',
    ]


class AutonomousSystemSearch(Search):
    queryset = Autonomoussystem.objects.all()

    def search(self, search_string):
        search_string = search_string.strip()
        if search_string.startswith('as'):
            asn = [x for x in search_string if x.isdigit()]
            if len(search_string) - len(asn) <= 3:
                asn = ''.join(asn)
                asns = Autonomoussystem.objects.filter(asn__contains=asn)
                if asns:
                    return asns

        autonomous_systems = Autonomoussystem.objects.filter(
            Q(asn__icontains=search_string) |
            Q(asset__icontains=search_string) |
            Q(engname__icontains=search_string) |
            Q(comment__icontains=search_string)).order_by('asn')
        return autonomous_systems


class PhoneSearch(Search):
    queryset = Phone.objects.all().order_by('count')
    arguments = [
        'number__icontains',
        'description__icontains',
        'client__netname__icontains',
        'client__clientname__icontains',
    ]


class CallSearch(Search):
    queryset = Call.objects.all().order_by('-time')
    arguments = [
        'phone__number__icontains',
        'phone__description__icontains',
        'phone__client__netname__icontains',
        'phone__client__clientname__icontains',
    ]
