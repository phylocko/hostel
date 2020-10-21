import logging

from django.core.management.base import BaseCommand
from django.db.models import Q

from hostel.common.models import Bundle
from hostel.devices.models import Device
from hostel.service.email import email_admin, MailError
from hostel.settings import ADMIN_EMAIL


class Command(BaseCommand):
    help = 'Command will set remote_device for every bundle in the database.'

    actions = []
    errors = []

    def handle(self, *args, **options):
        print("Started")
        self.unbind_old_remotes()
        self.fund_new_remotes()

        message = ''
        if self.errors:
            message += 'Errors\r\n' + '\r\n'.join(self.errors)

        if self.actions:
            message += 'Updates\r\n' + '\r\n'.join(self.actions)

        if message:
            print(message)
            try:
                email_admin(ADMIN_EMAIL, 'Remote devices', message)
            except MailError as e:
                print('Unable to send email:')
                print(e)

    def fund_new_remotes(self):
        print('searching for new remotes')

        device_list = []
        for device in Device.objects.filter(status='+', type__in=['switch', 'router']):
            device_list.append(device)

        candidate_bundles = Bundle.objects.filter(description__isnull=False)
        candidate_bundles = candidate_bundles.filter(remote_device__isnull=True)
        candidate_bundles = candidate_bundles.exclude(description__contains='.')
        candidate_bundles = candidate_bundles.exclude(description='')
        candidate_bundles = candidate_bundles.filter(Q(description__contains='-sw') |
                                                     Q(description__contains='-r'))
        for bundle in candidate_bundles:
            device = self.find_device(bundle.description, device_list)
            if device:
                print('bundle description:', bundle.description, 'found remote:', device)
                message = '{:<12} | Bundle {} ({}) is now connected to {}'.format(bundle.device.netname,
                                                                                  bundle.name,
                                                                                  bundle.description,
                                                                                  device.netname)
                self.actions.append(message)
                logging.info(message)
                bundle.remote_device = device
                bundle.save()

    def unbind_old_remotes(self):
        print('Unbinding old remotes')
        bundles_with_remotes = Bundle.objects.filter(remote_device__isnull=False)
        for bundle in bundles_with_remotes:
            if bundle.remote_device.netname not in bundle.description:
                message = '{:<12} | Bundle {} ({}) is not connected to {} anymore'.format(bundle.device.netname,
                                                                                          bundle.name,
                                                                                          bundle.description,
                                                                                          bundle.remote_device.netname)
                self.actions.append(message)
                logging.info(message)
                bundle.remote_device = None
                bundle.save()

    def find_device(self, description, device_list):
        found_device = None
        for device in device_list:
            if device.netname in description:
                if not found_device:
                    found_device = device
                    continue

                if len(device.netname) > len(found_device.netname):
                    found_device = device
        return found_device
