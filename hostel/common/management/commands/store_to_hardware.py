from django.core.management.base import BaseCommand
from hostel.store.models import Entry
from hostel.devices.models import Device, Hardware, DeviceType, DeviceVendor


class Command(BaseCommand):
    help = 'Create Hardware, DeviceType, DeviceVendor and so from StoreEntry'

    def handle(self, *args, **options):

        DeviceVendor.objects.all().delete()
        DeviceType.objects.all().delete()
        Hardware.objects.all().delete()
        for d in Device.objects.all():
            d.hardware = None
            d.save()

        device_vendors = {}
        device_types = {}

        for entry in Entry.objects.all():

            if entry.vendor:
                if entry.vendor not in device_vendors:
                    device_vendors[entry.vendor] = DeviceVendor.objects.create(title=entry.vendor)

            if entry.type:
                if entry.type not in device_types:
                    device_types[entry.type] = DeviceType.objects.create(title=entry.type)

            if entry.type and entry.vendor:
                device_types[entry.type].vendors.add(device_vendors[entry.vendor])

            hardware = Hardware(model=entry.model, serial=entry.serial, comment=entry.comment)
            if entry.type:
                hardware.device_type = device_types[entry.type]
            if entry.vendor:
                hardware.vendor = device_vendors[entry.vendor]

            hardware.save()

            for device in Device.objects.filter(store_entry=entry):
                device.hardware = hardware
                if entry.type:
                    device.device_type = device_types[entry.type]
                device.save()
