import re
from difflib import SequenceMatcher

from django.db import models
from django.db.models import Q
from transliterate import translit

import hostel.common.models as common_models
from hostel.common.models import Autonomoussystem, Service
from hostel.nets.models import Net, NetSearch
from hostel.service.variables import validate_netname, validate_mail_list


class Client(models.Model):

    service_list = None
    id = models.AutoField(primary_key=True)
    manager = models.ForeignKey('common.User', null=True, blank=True, on_delete=models.SET_NULL)
    city = models.ForeignKey('common.City', null=True, blank=True, on_delete=models.SET_NULL)
    netname = models.CharField(max_length=255, blank=False, null=True, unique=True, validators=[validate_netname])

    # This field is a client name for w-ix website only
    clientname = models.CharField(max_length=255, blank=True, null=True, unique=False)

    engname = models.CharField(max_length=255, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    contacts = models.TextField(blank=True, null=True)
    support_contacts = models.TextField(blank=True, null=True)
    enabled = models.BooleanField(default=True, null=False)
    comment = models.CharField(max_length=2048, blank=True, null=True)
    email = models.CharField(max_length=255, blank=True, null=True, validators=[validate_mail_list])
    support_email = models.CharField(max_length=255, blank=True, null=True, validators=[validate_mail_list])
    url = models.URLField(max_length=255, blank=True, null=True)
    ticket = models.CharField(max_length=20, blank=True, null=True)
    is_consumer = models.BooleanField(default=True)
    is_provider = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    ratio = 0.0

    class Meta:
        managed = True
        db_table = 'clients'

    def __str__(self):
        return self.netname

    def bundles(self):
        return common_models.Bundle.objects.filter(bundlevlan__services__client=self).distinct()


class ClientSearch:
    def __init__(self, queryset=None):
        self.queryset = queryset

    def search(self, search_string):

        # search_string = str(search_string)
        search_string.strip()

        if search_string:
            clients = self.queryset or Client.objects.all()
            keywords = search_string.split()
            for keyword in keywords:
                clients = clients.filter(Q(netname__icontains=keyword) |
                                         Q(engname__icontains=keyword) |
                                         Q(clientname__icontains=keyword) |
                                         Q(comment__icontains=keyword) |
                                         Q(contacts__icontains=keyword) |
                                         Q(support_contacts__icontains=keyword) |
                                         Q(url__icontains=keyword) |
                                         Q(email__icontains=keyword) |
                                         Q(support_email__icontains=keyword))
            return clients

        return Client.objects.none()

    def api_search(self, original_search_string):
        if not original_search_string:
            return []

        if original_search_string is None:
            return []

        clid_pattern = re.compile("^[0-9]{1,7}$")
        email_pattern = re.compile("[a-z0-9\.]{1,20}@.{1,30}\.[a-z]{1,10}")
        rt_pattern = re.compile("^rt[0-9]{5,6}$")
        asn_pattern = re.compile("^as[0-9]{3,7}$")
        peer_pattern = re.compile("^peer_[0-9]{3}[0-9]{1,3}$")
        service_pattern = re.compile("^[A-z0-9]{2,3}-[0-9]{1,7}$")
        ip_address_pattern = re.compile("^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$")

        original_search_string = original_search_string.lower().strip()

        g = clid_pattern.search(original_search_string)
        if g:
            return self.search_by_clid(original_search_string)

        g = email_pattern.search(original_search_string)
        if g:
            return self.search_by_email(original_search_string)

        g = asn_pattern.search(original_search_string)
        if g:
            return self.search_by_asn(original_search_string[2:])

        g = rt_pattern.search(original_search_string)
        if g:
            return self.search_by_rt(original_search_string[2:])

        g = peer_pattern.search(original_search_string)
        if g:
            return self.search_by_peer(original_search_string)

        g = service_pattern.search(original_search_string)
        if g:
            return self.search_by_service(original_search_string)

        g = ip_address_pattern.search(original_search_string)
        if g:
            return self.search_by_ipaddress(original_search_string)

        clientlist = []
        if original_search_string:
            search_string = self.normalize(original_search_string)

            p = re.compile("\".+\"")

            if search_string is not None:

                try:
                    exact_client = Client.objects.get(netname=original_search_string)
                except:
                    exact_client = None

                if exact_client:
                    return [exact_client]

                clients = Client.objects.all()

                s = SequenceMatcher()
                s.set_seq1(search_string)

                for client in clients:

                    g = p.search(client.clientname)
                    if g:
                        clear_data = g.group().lower()[1:-1]
                        clear_data = self.normalize(clear_data)
                    else:
                        clear_data = self.normalize(client.clientname)

                    s.set_seq2(clear_data)
                    if s.ratio() > 0.5:
                        client.ratio = s.ratio()
                        clientlist.append(client)

                    s.set_seq2(client.netname)
                    if s.ratio() > 0.5:
                        if s.ratio() > client.ratio:
                            client.ratio = s.ratio()
                            clientlist.append(client)

                    s.set_seq2(translit(client.netname, "ru"))
                    if s.ratio() > 0.5:
                        if s.ratio() > client.ratio:
                            client.ratio = s.ratio()
                            clientlist.append(client)

                    if client.netname[0:3] == search_string[0:3]:
                        client.ratio += 0.45

                clients = []

                for client in clientlist:
                    if client.ratio >= 1:
                        clients.append(client)

                if len(clients) == 0:

                    while len(clientlist) > 0:
                        min = 2
                        for c in clientlist:
                            if c.ratio < min:
                                min = c.ratio

                        for c in clientlist:
                            if c.ratio == min:
                                # c.netname += " " + str(c.ratio)
                                clients.append(c)
                                clientlist.remove(c)
                    clients.reverse()

                clients = list(set(clients))

                if len(clients) == 0:
                    clients = Client.objects.filter(clientname__icontains=search_string)

                return clients

    @staticmethod
    def search_by_clid(clid):
        return Client.objects.filter(pk=clid)

    def search_by_asn(self, asn):
        as_list = Autonomoussystem.objects.filter(asn=asn)
        clientlist = []

        for autonomous_system in as_list:
            client = Client.objects.get(pk=autonomous_system.related_client_id)
            if client not in clientlist:
                clientlist.append(client)

        return clientlist

    def search_by_service(self, service):
        sid = service.split("-")[1]

        try:
            service = Service.objects.get(pk=sid)
        except:
            return []

        try:
            client = service.client

        except:
            return []

        return [client]

    def search_by_email(self, email):
        clients = Client.objects.filter(email__icontains=email)

        if clients.count() == 0:
            clients = Client.objects.filter(maillist__icontains=email)

        if clients.count() == 0:
            clients = Client.objects.filter(contacts__icontains=email)

        if clients.count() == 0:
            email_parts = email.split("@")
            domain = email_parts[1]

            COMMON_MAILS = [
                'mail.ru',
                'list.ru',
                'gmail.com',
                'yandex.ru',
                'ya.ru',
                'bk.ru',
                'inbox.ru',
                'rambler.ru',
            ]

            if domain not in COMMON_MAILS:
                clients = Client.objects.filter(Q(email__icontains='@%s' % domain) |
                                                Q(maillist__icontains='@%s' % domain) |
                                                Q(contacts__icontains='@%s' % domain) |
                                                Q(url__icontains='.%s' % domain))

        return clients

    def search_by_rt(self, rt_number):
        client_list = []
        services = Service.objects.filter(rt=rt_number)
        for service in services:
            if service.client not in client_list:
                client_list.append(service.client)

        clients = Client.objects.filter(rt=rt_number)
        for client in clients:
            if client not in client_list:
                client_list.append(client)

        return client_list

    def search_by_peer(self, peer):

        clientlist = []
        penultimate = peer[5:8]
        last_octet = peer[8:]

        if penultimate == "122" or penultimate == "123":
            ipaddress = "85.112.%s.%s" % (penultimate, last_octet)

        elif penultimate == "112" or penultimate == "113":
            ipaddress = "193.106.%s.%s" % (penultimate, last_octet)

        else:
            return []

        nets = Net.objects.filter(address=ipaddress, netmask=32)
        if nets.count() > 0:
            for net in nets:
                try:
                    client = net.service.client
                except:
                    continue
                if client not in clientlist:
                    clientlist.append(client)
        return clientlist

    def search_by_ipaddress(self, ipaddress):
        clientlist = []
        nets = NetSearch().search(ipaddress)
        for net in nets:
            if net.address == ipaddress:
                try:
                    client = net.service.client
                except:
                    client = None

                if client:
                    clientlist.append(client)
        return clientlist

    def normalize(self, name):
        name = name.lower()
        name = name.replace("ооо", "")
        name = name.replace("зао", "")
        name = name.replace("пао", "")
        name = name.replace("ао", "")
        name = name.replace("\"", "")
        name = name.replace(" телеком", "")
        name = name.replace("-телеком", "")
        return name.strip()
