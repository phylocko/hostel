from django.core.management.base import BaseCommand
from pyzabbix import ZabbixAPI

from hostel.devices.models import Device
from hostel.service.email import email_admin, MailError
from hostel.settings import ADMIN_EMAIL


class Command(BaseCommand):
    help = 'Import device\'s firware versions from Zabbix'

    def handle(self, *args, **options):
        try:
            from hostel.settings import ZABBIX_DATA
        except ImportError:
            print('Cannot import ZABBIX_DATA from settings file')
            quit(1)

        z = ZabbixAPI(ZABBIX_DATA['url'],
                      user=ZABBIX_DATA['login'],
                      password=ZABBIX_DATA['password'])

        devices = Device.objects.filter(is_managed=True,
                                        type__in=['router', 'switch'],
                                        status='+').order_by('netname')

        report_text = ''

        for device in devices:
            data = z.item.get(host=device.netname,
                              search={'name': 'Firmware'},
                              output=['lastvalue'])

            if not data:
                continue

            firmware = data[0].get('lastvalue')
            if not firmware:
                continue

            if device.version == firmware:
                continue

            message_string = '%s: Firmware changed from "%s" to "%s"' % (device.netname,
                                                                         device.version,
                                                                         firmware)
            device.version = firmware
            device.save()

            report_text += message_string + '\n'
            print(message_string)

        if report_text:
            try:
                email_admin(ADMIN_EMAIL, 'Firmware upgrades', report_text)
            except MailError:
                pass
