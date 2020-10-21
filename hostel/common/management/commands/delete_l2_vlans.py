from django.core.management.base import BaseCommand
import hostel.common.models as common_models
from telneter import Account, Executor
from collections import defaultdict
from time import sleep
from threading import Thread


class Command(BaseCommand):
    help = 'Command will delete service vlan from service devices'

    account = None

    def add_arguments(self, parser):
        parser.add_argument('service_id', type=int, help='Service ID')
        parser.add_argument('login', type=str, help='Username on the devices')

    def handle(self, *args, **options):
        service_id = options.get('service_id')
        try:
            service = common_models.Service.objects.get(pk=service_id)
        except common_models.Service.DoesNotExist:
            self.stdout.write(self.style.ERROR('Service with ID %s does not exist' % service_id))
            return

        login = options.get('login')
        if login:
            self.account = Account(username=login)
        else:
            self.account = Account()

        devices_bundles = defaultdict(list)
        for vlan in service.vlan.all():
            for bundle_vlan in vlan.bundlevlan_set.all():
                devices_bundles[bundle_vlan.bundle.device].append(bundle_vlan)

        warnings = []

        devices_commands = {}
        for device, bundle_vlans in devices_bundles.items():
            command_list = self.get_device_commands(device, bundle_vlans)
            if device.type == 'switch':
                devices_commands[device] = command_list
            else:
                warnings.append(
                    'Delete manually %s (%s)' % (device.netname, ', '.join([x.bundle.name for x in bundle_vlans])))

        threads = []
        for device, commands in devices_commands.items():
            thread = Thread(target=self.execute_commands, args=[device.netname, commands])
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        if warnings:
            self.stdout.write(self.style.WARNING('\r\nWARNINGS:'))
            for warning in warnings:
                self.stdout.write(self.style.WARNING(' -> ' + warning))

    @staticmethod
    def get_device_commands(device, bundle_vlans):
        commands = []
        if device.vendor == 'juniper':
            commands.append('cli')
            commands.append('configure')

            for bundle_vlan in bundle_vlans:
                cmd_template = 'delete interfaces %s.0 family ethernet-switching vlan members %s'
                commands.append(cmd_template % (bundle_vlan.bundle.name, bundle_vlan.vlan.vname))
            commands.append('commit and-quit')

        elif device.vendor == 'extreme':
            for bundle_vlan in bundle_vlans:
                command = 'delete vlan %s' % bundle_vlan.vlan.vname
                if command not in commands:
                    commands.append(command)
        return commands

    def execute_commands(self, device_name, command_list):
        try:
            e = Executor(account=self.account, hostname=device_name)
        except ValueError as e:
            self.stdout.write(self.style.ERROR(device_name + ': ' + str(e)))
            return

        for command in command_list:
            self.stdout.write(self.style.SUCCESS('%s: %s' % (device_name, command)))
            result = e.cmd(command)
            self.stdout.write(result)
            sleep(1)
        e.close()
