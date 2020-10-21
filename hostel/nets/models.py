from django.db import models
from django.db.models import Q
from ipaddress import IPv4Network, IPv4Address, summarize_address_range
from netaddr import IPAddress
import radix
from hostel.service.variables import validate_netmask, validate_mac
import re
import netaddr
from django.db import IntegrityError


class Nets:
    _tree = None

    def __init__(self, nets, root_net=None):
        if not self._tree:
            self._tree = radix.Radix()

        self.root_net = root_net

        self.create_tree(nets)

    def create_tree(self, nets):
        for net in nets:
            node = self._tree.add(net.network)
            node.data['margin'] = None
            node.data['hostel_net'] = net

    def _find_margins(self):
        for node in self._tree.nodes():
            node.data['margin'] = self._find_margin(node)

    def _fill_spaces(self):
        self._tree = self._find_free_nets(keep_existing=True)

    def _find_free_nets(self, keep_existing=False):

        free_ranges = []

        # ghost network for allocation space between last network in tree and the ghost
        if self.root_net:
            ghost_ipaddress = netaddr.IPAddress(self.root_net.ipaddress_to + 1)
            ghost_network = '%s/32' % ghost_ipaddress
            ghost_node = self._tree.add(ghost_network)
            ghost_node.data['hostel_net'] = Net(address=ghost_ipaddress, netmask=32)
            ghost_node.data['hostel_net'].parse_address()

        previous_node = None

        for current_node in self._tree:

            if previous_node:

                # ### Previous network address is lower:
                if previous_node.data['hostel_net'].ipaddress_from < current_node.data['hostel_net'].ipaddress_from:
                    # Dense sequence — 192.168.0.0/30 and 192.168.0.4/30 — No space available
                    if previous_node.data['hostel_net'].ipaddress_to + 1 == current_node.data[
                        'hostel_net'].ipaddress_from:
                        pass

                    # Previous net is a parent — 192.168.0.0/24 and 192.168.0.8/30 - There is space
                    elif previous_node.data['hostel_net'].ipaddress_to > current_node.data['hostel_net'].ipaddress_from:
                        if previous_node.data['hostel_net'].ipaddress_from + 1 < current_node.data[
                            'hostel_net'].ipaddress_from - 1:
                            free_ranges.append(self._generate_range(previous_node, current_node))

                    # Sparse sequence — 192.168.0.0/30 and 192.168.0.8/30 - There is space
                    elif previous_node.data['hostel_net'].ipaddress_to + 1 < current_node.data[
                        'hostel_net'].ipaddress_from:
                        free_ranges.append(self._generate_range(previous_node, current_node))

            previous_node = current_node

        if keep_existing:
            free_tree = self._tree
        else:
            free_tree = radix.Radix()

        for free_range in free_ranges:
            self._push_to_radix(free_range, free_tree, free=True)

        # don't forget to remove the ghostnet!
        if self.root_net:
            self._tree.delete(ghost_network)

        return free_tree

    def free_nodes(self):
        free_nets = self._find_free_nets()
        self._tree = free_nets
        self._find_margins()
        return [x for x in self._tree]

    def nodes(self):
        self._find_margins()
        return [x for x in self._tree]

    def filled_nodes(self):
        self._fill_spaces()
        self._find_margins()
        nodes = [x for x in self._tree]
        return nodes

    def nets(self):
        return [x.data['hostel_net'] for x in self._tree]

    def nets_filled(self):
        self._fill_spaces()
        return [x.data['hostel_net'] for x in self._tree]

    def _push_to_radix(self, nets=None, tree=None, free=None):
        if not nets:
            return

        for net in nets:
            node = tree.add(str(net.exploded))
            node.data['hostel_net'] = Net(address=net.network_address.exploded,
                                          netmask=net.prefixlen)
            node.data['hostel_net'].parse_address()
            node.data['is_free'] = True

    @staticmethod
    def _generate_range(lower_node, higher_node):

        value_from = lower_node.data['hostel_net'].ipaddress_to + 1
        value_to = higher_node.data['hostel_net'].ipaddress_from - 1

        if value_from > value_to:
            value_from = lower_node.data['hostel_net'].ipaddress_from + 1

        a = IPv4Address(address=value_from)
        b = IPv4Address(address=value_to)
        nets = summarize_address_range(a, b)

        nets = [x for x in nets]

        return nets

    @staticmethod
    def previous_net(self, net):
        try:
            net = Net.objects.filter(ipaddress_from__lte=net.ipaddress_from).order_by("-ipaddress_from").first()
        except:
            net = None

        return net

    @staticmethod
    def _find_margin(node):
        margin = 0
        if node.parent:
            margin += 1
            if node.parent.parent:
                margin += 1
                if node.parent.parent.parent:
                    margin += 1
                    if node.parent.parent.parent.parent:
                        margin += 1
                        if node.parent.parent.parent.parent.parent:
                            margin += 1
                            if node.parent.parent.parent.parent.parent.parent:
                                margin += 1
                                if node.parent.parent.parent.parent.parent.parent.parent:
                                    margin += 1
                                    if node.parent.parent.parent.parent.parent.parent.parent.parent:
                                        margin += 1
        return margin


class NetManager(models.Manager):
    def parents_of(self, net):
        parents = Net.objects.filter(
            ipaddress_from__lte=net.ipaddress_from,
            ipaddress_to__gte=net.ipaddress_to,
            netmask__lt=net.netmask).order_by('-netmask')
        return parents

    def children_of(self, net):
        children = Net.objects.filter(
            ipaddress_from__gte=net.ipaddress_from,
            ipaddress_to__lte=net.ipaddress_to,
            netmask__gt=net.netmask).order_by('ipaddress_from', 'netmask')
        return children


class Net(models.Model):
    STATUSES = (
        ('+', '+'),
        ('-', '—'),
    )
    ALLOCATED_FOR = (
        ('', ''),
        ('service', 'Выдан клиенту под услугу'),
        ('internal', 'Управление/наши ресурсы'),
        ('info', 'Простой аллокейшн, информационный'),
        ('service_range', 'Диапазон выдачи под услугу'),
    )

    free = False

    id = models.AutoField(primary_key=True)

    service = models.ForeignKey('common.Service',
                                related_name='net',
                                blank=True, null=True,
                                on_delete=models.SET_NULL)

    subservice = models.ForeignKey('common.SubService',
                                   related_name='nets',
                                   blank=True, null=True,
                                   on_delete=models.SET_NULL)

    device = models.ForeignKey('devices.Device',
                               related_name='net',
                               blank=True,
                               null=True,
                               on_delete=models.SET_NULL)

    vlan = models.ForeignKey('vlans.Vlan', null=True,
                             blank=True,
                             related_name='nets',
                             on_delete=models.SET_NULL)

    # deprecated
    management_vlan = models.OneToOneField("vlans.VLAN",
                                           null=True,
                                           blank=True,
                                           related_name="management_net",
                                           on_delete=models.SET_NULL)

    city = models.ForeignKey('common.City',
                             related_name="nets",
                             blank=True,
                             null=True,
                             on_delete=models.SET_NULL)

    # Сеть обозначает диапазон услуги
    allocating_service = models.OneToOneField('common.Ourservice',
                                              on_delete=models.SET_NULL,
                                              related_name='allocated_net',
                                              null=True)

    address = models.GenericIPAddressField(db_column='ipaddress',
                                           blank=False,
                                           null=False,
                                           default="",
                                           max_length=19)

    ipaddress_from = models.BigIntegerField(blank=False, null=False)
    ipaddress_to = models.BigIntegerField(blank=False, null=False)
    netmask = models.IntegerField(blank=False, null=False, default=32, validators=[validate_netmask])
    description = models.CharField(max_length=50, blank=True, null=False)
    status = models.CharField(max_length=20,
                              blank=True,
                              null=False,
                              choices=STATUSES, default=STATUSES[0][0])
    mac = models.CharField(max_length=17, blank=True, null=True, validators=[validate_mac])

    comment = models.CharField(max_length=2048, blank=True, null=False)
    ptr = models.CharField(max_length=255, blank=True, null=True)
    ticket = models.CharField(max_length=20, blank=False, null=True)
    protected = models.BooleanField(default=False)
    is_allocation = models.BooleanField(default=False)
    allocated_for = models.CharField(max_length=15,
                                     blank=True,
                                     choices=ALLOCATED_FOR)  # internal | service | client | info

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    objects = NetManager()

    class Meta:
        managed = True
        db_table = 'nets'
        unique_together = ('ipaddress_from', 'ipaddress_to')

    @property
    def last_octet(self):
        return self.address.split('.')[-1]

    @property
    def penultimate_octet(self):
        return self.address.split('.')[-2]

    @property
    def network(self):
        return '%s/%s' % (self.address, self.netmask)

    @property
    def address6(self):

        if not self.service:
            return

        if self.service.name == 'inet2':
            prefix = "2a00:1b30:8888::"
        elif self.service.name == 'wix':
            prefix = '2a00:1b30::'
        else:
            return

        address6 = prefix
        if self.penultimate_octet in ["123", "113"]:
            address6 += 'a'
        address6 += self.last_octet
        return address6

    def parse_address(self):
        netaddr_network = netaddr.IPNetwork('%s/%s' % (self.address, self.netmask))

        self.ipaddress_from = int(netaddr_network.network)

        if self.netmask == 32:
            self.ipaddress_to = int(netaddr_network.network)
        elif self.netmask == 31:
            self.ipaddress_to = int(netaddr_network.network) + 1
        else:
            self.ipaddress_to = int(netaddr_network.broadcast)

    def parse_mac(self):
        try:
            correct_mac = str(netaddr.EUI(self.mac)).replace('-', ':')
        except TypeError:
            return

        if not self.mac == correct_mac:
            self.mac = correct_mac

    def save(self, *args, **kwargs):
        if self.protected:
            raise ValueError('This network is protected and can\'t be changed')

        # Filling data
        self.parse_address()

        netaddr_network = netaddr.IPNetwork('%s/%s' % (self.address, self.netmask))

        # Do we have host bits in network address?
        if not self.address == str(netaddr_network.network):
            raise ValueError('Invalid IP address/mask pair')

        self.parse_mac()

        # Do we already have the same network?
        try:
            super(Net, self).save(*args, **kwargs)
        except IntegrityError:
            raise ValueError('Network already exists')

    def protect(self, *args, **kwargs):
        self.protected = True
        super(Net, self).save(*args, **kwargs)

    def unprotect(self, *args, **kwargs):
        self.protected = False
        super(Net, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        super(Net, self).delete(*args, **kwargs)

    def __str__(self):
        return self.address if self.netmask == 32 else '%s/%s' % (self.address, self.netmask)


class NetHelper:
    net = Net
    supernet = Net

    def __init__(self, net):
        self.net = net

    def get_supernet(self):
        supernet = Net.objects.filter(
            ipaddress_from__lte=self.net.ipaddress_from,
            ipaddress_to__gte=self.net.ipaddress_to,
            netmask__lt=self.net.netmask).order_by('-netmask', '-ipaddress_from').first()

        self.supernet = supernet or None
        return self.supernet


class Netaggregator:
    nets = []
    rtree = None
    initial_nets = ''

    def __init__(self, net):
        self.net = net

    def aggregate(self):
        self.initial_nets = Net.objects.filter(
            ipaddress_from__gte=self.net.ipaddress_from,
            ipaddress_to__lte=self.net.ipaddress_to).order_by('ipaddress_from', 'netmask')

        self.rtree = radix.Radix()

        for net in self.initial_nets:
            rnode = self.rtree.add(net.network)
            rnode.data['net'] = net

        self.nets = [x.data['net'] for x in self.addMargins(self.rtree)]

        return self.nets

    def aggregate_with_freenets(self):
        if not self.initial_nets:
            self.aggregate()

        net_count = len(self.initial_nets)

        if self.initial_nets[0].ipaddress_from + 1 < self.initial_nets[1].ipaddress_from:
            free_nets = self._allocate_free_nets(self.initial_nets[0].ipaddress_from + 1,
                                                 self.initial_nets[1].ipaddress_from - 1)
            self.push_to_rtree(free_nets)

        i = 0
        while i < net_count:
            if i < net_count - 1:
                if self.initial_nets[i].ipaddress_to + 1 < self.initial_nets[i + 1].ipaddress_from:
                    free_nets = self._allocate_free_nets(
                        self.initial_nets[i].ipaddress_to + 1,
                        self.initial_nets[i + 1].ipaddress_from - 1)
                    self.push_to_rtree(free_nets)
            else:
                if self.initial_nets[i].ipaddress_to + 1 < self.initial_nets[0].ipaddress_to - 1:
                    free_nets = self._allocate_free_nets(
                        self.initial_nets[i].ipaddress_to + 1,
                        self.initial_nets[0].ipaddress_to - 1)
                    self.push_to_rtree(free_nets)

            i += 1

        self.nets = [x.data['net'] for x in self.addMargins(self.rtree)]
        return self.nets

    def freenets(self, longest_netmask=32, shortest_netmask=0):
        """
        Здесь есть ошибка: алгоритм разбивает сеть на свободные с максимльно
        возможными масками, а потом выбирает из них те, что shortest_mask.
        Следовательно, если shortest = 32, сети /27 даже не отобразятся, что плохо!
        """
        self.aggregate_with_freenets()

        for net in self.nets:
            if not net.free:
                self.rtree.delete(net.network)
            elif net.netmask > longest_netmask or net.netmask < shortest_netmask:
                self.rtree.delete(net.network)

        self.nets = [x.data['net'] for x in self.addMargins(self.rtree)]
        return self.nets

    def push_to_rtree(self, free_nets):
        for n in free_nets:
            rnode = self.rtree.add(n.exploded)
            rnode.data['net'] = Net(address=n.network_address.exploded,
                                    netmask=n.prefixlen)
            rnode.data['net'].parse_address()
            rnode.data['net'].free = True

    def _allocate_free_nets(self, ipaddress_from, ipaddress_to):
        a = IPv4Address(address=ipaddress_from)
        b = IPv4Address(address=ipaddress_to)
        range = summarize_address_range(a, b)
        return range

    def addMargins(self, radix_nets):
        for net in radix_nets:
            if net.parent:
                net.data['net'].margin = 1

                if net.parent.parent:
                    net.data['net'].margin = 2

                    if net.parent.parent.parent:
                        net.data['net'].margin = 3

                        if net.parent.parent.parent.parent:
                            net.data['net'].margin = 4

                            if net.parent.parent.parent.parent.parent:
                                net.data['net'].margin = 5

                                if net.parent.parent.parent.parent.parent.parent:
                                    net.data['net'].margin = 6

        return radix_nets


class NetSearch:
    def search(self, original_search_string):
        if not original_search_string:
            return []

        if original_search_string is None:
            return []

        original_search_string = original_search_string.strip()

        chars = re.compile("[A-zА-я#,/%$]")

        if chars.findall(original_search_string):
            nets = Net.objects.filter(
                Q(description__icontains=original_search_string) |
                Q(comment__icontains=original_search_string) |
                Q(mac__icontains=original_search_string) |
                Q(ptr__icontains=original_search_string)).order_by('ipaddress_from', 'netmask')
        else:
            nets = Net.objects.filter(
                address__icontains=original_search_string).order_by('ipaddress_from', 'netmask')

        if len(nets) == 0:
            network_regexp = re.compile("^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}/[0-9]{1,2}$")
            ipaddress_regexp = re.compile("^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$")

            if network_regexp.search(original_search_string):
                try:
                    network = IPv4Network(original_search_string)
                except Net.DoesNotExist:
                    return []

                nets = Net.objects.filter(
                    ipaddress_from__lte=network.broadcast_address,
                    ipaddress_to__gte=network.broadcast_address,
                    netmask=network.prefixlen).order_by("-netmask")

                if len(nets) == 0:
                    nets = Net.objects.filter(
                        ipaddress_from__gte=network.network_address,
                        ipaddress_to__lte=network.broadcast_address,
                        netmask__gte=network.prefixlen).order_by("ipaddress_from", "-netmask")

            if ipaddress_regexp.search(original_search_string):
                try:
                    address = IPv4Address(original_search_string)
                except:
                    return []

                nets = Net.objects.filter(ipaddress_from__lte=address,
                                          ipaddress_to__gte=address).order_by("-netmask")[0:1]
        return nets
