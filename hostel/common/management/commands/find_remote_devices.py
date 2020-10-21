from django.core.management.base import BaseCommand
import hostel.common.models as common_models
from hostel.devices.models import Device
import re


class Command(BaseCommand):
    help = 'Command will set remote_device for every bundle in the database.'

    def handle(self, *args, **options):
        devices = {}
        for device in Device.objects.filter(status='+', type__in=['switch', 'router']):
            devices[device.netname] = device.pk

        print('Finding remote devices for bundles')

        for bundle in common_models.Bundle.objects.filter(description__isnull=False):
            if '.' not in bundle.name:
                remote_id = self.remote_device_id(bundle.description, devices)
                if remote_id:
                    remote_device = Device.objects.get(pk=remote_id)
                    bundle.remote_device = remote_device
                    bundle.save()

    def remote_device_id(self, description, devices):
        if description:
            for netname, pk in devices.items():
                p = '%s(\D|$)' % netname
                pattern = re.compile(p)
                if pattern.match(description):
                    return pk
