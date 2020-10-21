from django.core.management.base import BaseCommand

from hostel.common.collector import Collector
from hostel.devices.models import Device
from hostel.service.email import email_admin
from hostel.settings import ADMIN_EMAIL


class Command(BaseCommand):
    help = 'Binds BundleVlans to services'

    def add_arguments(self, parser):
        parser.add_argument('netname',
                            type=str,
                            help='Netname to update or "all"')

    def handle(self, *args, **options):
        try:
            collector = Collector()

            if options['netname'] == 'all':
                collector.import_bundles_for_devices()
                collector.import_vlans_for_devices()

            else:
                try:
                    device = Device.objects.get(netname=options['netname'], is_managed=True)
                except Device.DoesNotExist:
                    message = '%s not found in Hostel or "is_managed" isn\'t checked' % options['netname']
                    self.stdout.write(self.style.ERROR(message))
                    return
                else:
                    collector.import_bundles_for_device(device)
                    collector.import_vlans_for_device(device)

            for error in collector.errors:
                self.stdout.write(self.style.ERROR(error))

            for action in collector.actions:
                self.stdout.write(action)

            message = ''
            if collector.errors:
                message += 'Errors:\r\n'
                for error in collector.errors:
                    message += error
                    message += '\r\n'

            if collector.actions:
                message += '\r\nUpdates:\r\n'
                for action in collector.actions:
                    message += action
                    message += '\r\n'

            if message:
                email_admin(ADMIN_EMAIL, 'Collector', message)

        except Exception as e:
            email_admin(ADMIN_EMAIL, 'Collector Exception', str(e))
