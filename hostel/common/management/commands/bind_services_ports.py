from collections import namedtuple

from django.core.management.base import BaseCommand

from hostel.common.models import Service, BundleVlan
from hostel.service.email import email_admin
from hostel.settings import ADMIN_EMAIL

Change = namedtuple('Change', 'changed_entity client bundle_vlan sign')


def process_service(service=None, subservice=None, changes=None):

    assert service or subservice

    if service:
        entity = service
        client = service.client
        vlans = service.vlan.all()
    else:
        entity = subservice
        client = subservice.service.client
        vlans = subservice.vlans.all()

    found_bundle_vlans = BundleVlan.objects.filter(
        bundle__remote_device__isnull=True,
        vlan__in=vlans
    )
    current_bundle_vlans = entity.bundle_vlans.all()
    lost_bundle_vlans = [x for x in entity.bundle_vlans.all() if x not in found_bundle_vlans]
    new_bundle_vlans = [x for x in found_bundle_vlans if x not in current_bundle_vlans]

    for bundle_vlan in lost_bundle_vlans:
        change = Change(changed_entity=entity, client=client, bundle_vlan=bundle_vlan, sign='-')
        changes.append(change)
        entity.bundle_vlans.remove(bundle_vlan)

    for bundle_vlan in new_bundle_vlans:
        change = Change(changed_entity=entity, client=client, bundle_vlan=bundle_vlan, sign='+')
        changes.append(change)
        entity.bundle_vlans.add(bundle_vlan)


class Command(BaseCommand):
    help = 'Binds BundleVlans to services and subservices'
    service_names = ['l2', 'bgpinet', 'l3inet', 'l3vpn', 'telia']

    def handle(self, *args, **options):
        print('Bind BundleVlans to services')

        changes = []
        services = Service.objects.filter(name__in=self.service_names, status__in=['on', 'test'])

        for service in services:
            process_service(service=service, changes=changes)

            for subservice in service.subservices.all():
                process_service(subservice=subservice, changes=changes)

        if not changes:
            print('No changes')
            return

        report_text = ''
        for change in changes:
            row = '%s %s %s %s %s\n' % (
                change.sign,
                change.changed_entity,
                change.client,
                change.bundle_vlan,
                'added' if change.sign == '+' else 'removed'
            )
            report_text += row

        print('Sending an email to admins')
        email_admin(ADMIN_EMAIL, 'Port bindings', report_text)
        print(report_text)
