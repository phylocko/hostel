from django.test import Client as TestClient, TransactionTestCase

import hostel.common.models as cm
# db models
from hostel.clients.models import Client
from hostel.devices.models import Device
from hostel.nets.models import Net
from hostel.store.models import Entry
from hostel.ins.models import Incident
from datetime import datetime

c = TestClient()


class DeviceTestCase(TransactionTestCase):
    def setUp(self):

        client1 = Client.objects.create(netname='client1', clientname='ООО "Клиент 1"')
        client2 = Client.objects.create(netname='client2', clientname='ООО "Клиент 2"')
        # client3 = Client.objects.create(netname='client3', clientname='ООО "Клиент 3"')
        # client4 = Client.objects.create(netname='client3', clientname='ООО "Клиент 4"')

        client_net1 = Net.objects.create(address='10.0.0.1', netmask=32, mac='70:70:8B:39:CA:81')
        client_net2 = Net.objects.create(address='10.0.0.2', netmask=32, mac='70:70:8B:39:CA:81')
        # client_net3 = Net.objects.create(address='192.168.0.3', netmask=32)
        # client_net4 = Net.objects.create(address='192.168.0.4', netmask=32)

        client1_as1 = cm.Autonomoussystem.objects.create(asn=1234, asset='AS-1', engname='client1_as')
        client1_tech1 = cm.Tech.objects.create(type='as', client=client1, object_id=client1_as1.pk)
        client1_service1 = cm.Service.objects.create(name='wix', servicetype='global', tech=client1_tech1)
        client1_service2 = cm.Service.objects.create(name='inte2', servicetype='generic', tech=client1_tech1)

        client_net1.service = client1_service1
        client_net2.service = client1_service2

        entry1 = Entry.objects.create(type='router', vendor='juniper', serial='JUNIPER_ROUTER_SERIAL')
        entry2 = Entry.objects.create(type='switch', vendor='juniper', serial='JUNIPER_SWITCH_SERIAL')
        entry3 = Entry.objects.create(type='switch', vendor='extreme', serial='EXTREME_SWITCH_SERIAL')
        entry4 = Entry.objects.create(type='switch', vendor='cisco', serial='CISCO_SWITCH_SERIAL')

        net1 = Net.objects.create(address='192.168.0.1', netmask=32)
        net2 = Net.objects.create(address='192.168.0.2', netmask=32)
        net3 = Net.objects.create(address='192.168.0.3', netmask=32)
        net4 = Net.objects.create(address='192.168.0.4', netmask=32)

        city1 = cm.City.objects.create(name='Москва', engname='Moscow', community=4001)
        city2 = cm.City.objects.create(name='Санкт-Петербург', engname='Leningrad', community=4002)

        datacenter1 = cm.Datacenter.objects.create(name='М9',
                                                   city=city1,
                                                   organization=client1,
                                                   address='Бутлерова, 7')
        datacenter2 = cm.Datacenter.objects.create(name='БМ18',
                                                   city=city2,
                                                   organization=client2,
                                                   address='Большая Морская, 18')
        Device.objects.create(netname='router1',
                              management_net=net1,
                              type='router',
                              status='+',
                              store_entry=entry1,
                              community='public',
                              is_managed=True,
                              datacenter=datacenter1)

        Device.objects.create(netname='switch2',
                              management_net=net2,
                              type='switch',
                              status='+',
                              store_entry=entry2,
                              community='public',
                              is_managed=True,
                              datacenter=datacenter2)

        Device.objects.create(netname='switch3',
                              management_net=net3,
                              type='switch',
                              status='+',
                              store_entry=entry3,
                              community='public',
                              is_managed=True,
                              datacenter=datacenter2)

        Device.objects.create(netname='switch4',
                              management_net=net4,
                              type='switch',
                              status='+',
                              store_entry=entry4,
                              community='public',
                              is_managed=True,
                              datacenter=datacenter2)

    def test_devices_requestor_mrtg(self):
        """API gives MRTG Devices correctly"""

        response = c.get('/api/?page=devices&requestor=mrtg')
        self.assertEqual(response.status_code, 200)

        should_response = 'router1 juniperrouter public\n'
        should_response += 'switch2 juniperswitch public\n'
        should_response += 'switch3 extreme public\n'
        should_response += 'switch4 ciscoswitch public\n'

        self.assertEqual(response.content.decode('UTF-8'), should_response)

    def test_devices_requestor_dns(self):
        """API gives DNS Devices correctly"""

        reference = {
            '192.168.0.1': {'name': 'router1', 'type': 'router', 'devtype': 'juniperrouter', 'vendor': 'juniper'},
            '192.168.0.2': {'name': 'switch2', 'type': 'switch', 'devtype': 'juniperswitch', 'vendor': 'juniper'},
            '192.168.0.3': {'name': 'switch3', 'type': 'switch', 'devtype': 'extreme', 'vendor': 'extreme'},
            '192.168.0.4': {'name': 'switch4', 'type': 'switch', 'devtype': 'ciscoswitch', 'vendor': 'cisco'}
        }

        response = c.get('/api/?page=devices&requestor=dns')
        self.assertEqual(response.status_code, 200)

        json_response = response.json()
        for device in json_response['addresses']:
            address = device['address']
            for field in ['name', 'type', 'devtype', 'vendor']:
                self.assertEqual(device[field], reference[address][field])

    def test_devices_requestor_zabbix(self):
        """API gives Zabbix Devices correctly"""

        reference = {
            '192.168.0.1': {
                'name': 'router1', 'type': 'router', 'model': '', 'vendor': 'juniper', 'city': 'Москва'
            },
            '192.168.0.2': {
                'name': 'switch2', 'type': 'switch', 'model': '', 'vendor': 'juniper', 'city': 'Санкт-Петербург'
            },
            '192.168.0.3': {
                'name': 'switch3', 'type': 'switch', 'model': '', 'vendor': 'extreme', 'city': 'Санкт-Петербург'
            },
            '192.168.0.4': {
                'name': 'switch4', 'type': 'switch', 'model': '', 'vendor': 'cisco', 'city': 'Санкт-Петербург'
            },
        }

        response = c.get('/api/?page=devices&requestor=zabbix')
        self.assertEqual(response.status_code, 200)

        json_response = response.json()
        for device in json_response['addresses']:
            address = device['address']
            for field in ['name', 'type', 'type', 'model', 'vendor', 'city']:
                self.assertEqual(device[field], reference[address][field])

    def test_ins(self):
        format = '%Y-%m-%d %H:%M'
        time_start = '2019-01-02 03:44'
        time_end = '2019-01-02 06:07'

        incident = Incident.objects.create(
            pk=1,
            name='Плановые работы на сети подрядчика',
            time_start=datetime.strptime(time_start, format),
            time_end=datetime.strptime(time_end, format),
            type='work',
            provider_id=1,
            provider_tt='PROVIDER_#123',
            rt='123000')

        response = c.get('/api/ins/1/')
        self.assertEqual(response.status_code, 200)

        json_response = response.json()

        self.assertEqual(json_response.get('pk'), incident.pk)
        self.assertEqual(json_response.get('name'), incident.name)
        self.assertEqual(json_response.get('time_start'), time_start)
        self.assertEqual(json_response.get('time_end'), time_end)
        self.assertEqual(json_response.get('provider_id'), incident.provider_id)
        self.assertEqual(json_response.get('provider_tt'), incident.provider_tt)
        self.assertEqual(json_response.get('rt'), incident.rt)
