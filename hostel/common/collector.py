import copy
import csv
import json
import logging

from hostel.common.models import Bundle, Port, BundleVlan
from hostel.devices.models import Device
from django.db.utils import IntegrityError

try:
    from hostel.settings import COLLECTOR_DATA_PATH
except ImportError:
    print("Error: name COLLECTOR_DATA_PATH not found in your settings.")
    quit()

from hostel.vlans.models import Vlan


class Collector:
    """
    Our rules:
    1. We trust the data from collector's CSV files. Please, keep them right.
    2. We're not removing Bundles of a device that it not in the collector's CSV files
    3. We're not removing BundleVlans of a device that is not in the collector's CSV files
    """

    def __init__(self, path=None):
        if not path:
            path = COLLECTOR_DATA_PATH
        self.tree = {}
        self.vlans = {}

        self.actions = []
        self.errors = []
        if not path.endswith('/'):
            path += '/'
        self.path = path
        self._build_tree()

    def _build_tree(self):
        self._build_tree_bundles()
        self._build_tree_ports()
        self._build_vlans()
        # self._import_vlans()
        # self._import_bundle_vlans()
        return

    def _build_tree_ports(self):
        # Collect ports to the tree
        ports_filename = self.path + 'ports.csv'
        with open(ports_filename, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                hostname, name, bundle, description = row.values()

                if hostname not in self.tree:
                    # bundles.csv had no bundles for the device
                    # Corrupted collector's data?
                    message = '{:<12} | Ports for are in ports.csv, but there are no bundles in bundles.csv.'.format(
                        hostname)
                    # print(message)
                    self.errors.append(message)
                    logging.error(message)
                    continue

                if bundle not in self.tree[hostname]['bundles']:
                    # Corrupted collector's data?
                    message = '{:<12} | Port {} has no it\'s bundle ({}) in bundles.csv'.format(hostname, name, bundle)
                    self.errors.append(message)
                    logging.error(message)
                    continue
                self.tree[hostname]['bundles'][bundle]['ports'][name] = {'description': description}

    def _build_tree_bundles(self):
        # Collect bundles to the tree
        bundles_filename = self.path + 'bundles.csv'
        with open(bundles_filename, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                hostname, bundle, description, is_lag = row.values()
                is_lag = True if is_lag == 'True' else False

                if hostname not in self.tree:
                    # This is the only point, where device name pushed to the tree
                    # Missing device name in the tree means the bundles.csv file
                    # has no bundles for the device
                    self.tree[hostname] = {'bundles': {}}

                if bundle in self.tree[hostname]['bundles']:
                    message = '{:<12} | Duplicated bundle %s in bundles.csv'.format(hostname, bundle)
                    logging.warning(message)
                    # print(message)
                    self.errors.append(message)

                # Push the bundle to a tree
                self.tree[hostname]['bundles'][bundle] = {'ports': {},
                                                          'description': description,
                                                          'is_lag': is_lag}

    def import_vlans_for_device(self, device):
        """
        Imports new vlans to hostel, updates BundleVlans for the device
        """

        # Vlans structure {48: Vlan}  For searcing Vlan by tag
        # It will be using later in self._import_bundle_vlans()
        self._build_vlans()

        # Collect vlans to the tree
        filename = self.path + 'vlans.csv'
        imported_vlan_ids = []
        with open(filename, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                hostname, tag, name, _ = row.values()

                # Ignoring vlan's of other devices
                if not hostname == device.netname:
                    continue

                tag = int(tag)

                if hostname not in self.tree:
                    message = '{:<12} | Device is in vlans.csv but not in hostel'.format(hostname)
                    self.errors.append(message)
                    logging.error(message)
                    continue

                if tag not in imported_vlan_ids and tag not in self.vlans:
                    try:
                        vlan = Vlan.objects.create(vlannum=tag,
                                                   vname=name,
                                                   is_local=True,
                                                   comment='Created by collector')
                    except IntegrityError:
                        message = '{:<12} | New vlan {} found, but another vlan with the same name ({}) exists!'.format(
                            tag,
                            device.netname,
                            name)
                        self.errors.append(message)
                        continue
                    else:

                        self.vlans[tag] = vlan
                        message = '{:<12} | New vlan {} [{}] found and created'.format(device.netname,
                                                                                       vlan.vname,
                                                                                       vlan.vlannum)
                        self.actions.append(message)
                        logging.info(message)
                imported_vlan_ids.append(tag)

        self._import_bundle_vlans(device)

    def _build_vlans(self):
        vlans = Vlan.objects.all().order_by('vlannum')
        for vlan in vlans:
            self.vlans[vlan.vlannum] = vlan

    def _import_bundle_vlans(self, device):
        """
        !!
        We can't follow this plan, because we'll loose
        bundle_vlans from temporary unavailable devices!
        [ Fixed: remove the BundleVlan only if the device has bunldes =) ]
        !!

        Plan:
        1. Build {(hostname, bundle_name, tag): mode} structure
           (we should have it already build during self._build_tree()
        2. For every BundleVlan of the device from Hostel:
            a. If it's in the structure:
                   update;
               else:
                   if the device has bundles in self._tree:
                       remove from Hostel
            b. Remove processed item from the structure
        Now we have only actial BundleVlans in Hostel,
        But we need to create new
        3. For every item in the structure:
            create bundle_vlan
        """

        # Checking if we have data for the device
        if not self.tree.get(device.netname):
            return

        # Generating structure {('m9-sw00', 48, 'ae0': 'tagged', ... }
        structure = {}
        filename = self.path + 'bundle_vlans.csv'
        with open(filename, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                hostname, tag, bundle_name, mode = row.values()

                # Doing only for bundle vlans of this host
                if not hostname == device.netname:
                    continue

                tag = int(tag)
                if not (hostname, tag, bundle_name) in structure:
                    structure[(hostname, tag, bundle_name)] = mode

        # Getting the current BundleVlans from Hostel
        bundle_vlans = BundleVlan.objects.filter(bundle__device=device).prefetch_related('bundle', 'vlan')
        for bundle_vlan in bundle_vlans:
            # Making a key for structure lookup
            key = (device.netname, bundle_vlan.vlan.vlannum, bundle_vlan.bundle.name)
            mode = structure.get(key)
            previous_mode = str(bundle_vlan.mode)

            if mode is None:
                # Means that the bundle_vlan it't present in a CSV file, so we gonna delete it
                bundle_vlan.delete()
                message = '{:<12} | Vlan {} [{}] {} removed from bundle {}'.format(
                    device.netname,
                    bundle_vlan.vlan.vname,
                    bundle_vlan.vlan.vlannum,
                    previous_mode,
                    bundle_vlan.bundle.name
                )
                self.actions.append(message)
                continue

            if mode:
                if not mode == bundle_vlan.mode:
                    # Update only BundleVlans that are changed. Mode is the only parameter that can change
                    bundle_vlan.mode = mode
                    bundle_vlan.save()
                    message = '{:<12} | Vlan {} [{}] changed it\'s mode on bundle {}: {} -> {}'.format(
                        device.netname,
                        bundle_vlan.vlan.vname,
                        bundle_vlan.vlan.vlannum,
                        bundle_vlan.bundle.name,
                        previous_mode,
                        bundle_vlan.mode
                    )
                    self.actions.append(message)
                del structure[key]

        for bundle_vlan_data, mode in structure.items():
            _, vlan_id, bundle_name = bundle_vlan_data

            try:
                bundle = Bundle.objects.get(device=device, name=bundle_name)
            except Bundle.DoesNotExist:
                message = '{:<12} | Bundle {} found in collector CSV file, but is not in Hostel'.format(
                    device.netname,
                    bundle_name)
                self.errors.append(message)
                continue

            try:
                vlan = Vlan.objects.get(vlannum=vlan_id)
            except Vlan.DoesNotExist:
                message = '{:<12} | Vlan {} found in collector CSV file, but is not in Hostel'.format(
                    device.netname,
                    vlan_id)
                self.errors.append(message)
                continue

            bundle_vlan = BundleVlan.objects.create(bundle=bundle, vlan=vlan, mode=mode)
            message = '{:<12} | Vlan {} [{}] added {} to bundle {} ({})'.format(
                device.netname,
                vlan.vlannum,
                vlan.vname,
                bundle_vlan.mode,
                bundle.name,
                bundle.description)
            self.actions.append(message)

    def import_bundles_for_device(self, device):
        collector_device = self.tree.get(device.netname)
        if not collector_device:
            # Device IS in Hostel, but IS NOT in collector's CSV
            message = '{:<12} | Device is in Hostel, but is not in collector\'s CSV files.'.format(device.netname)
            self.errors.append(message)
            logging.warning(message)
            return

        if not collector_device.get('bundles'):
            # Device is not updated for a while
            message = '{:<12} | Device has no bundles in collector\'s CSV'.format(device.netname)
            self.errors.append(message)
            logging.warning(message)
            return

        # Now we're sure that the device DO has some bundles in bundles.csv,
        # so we may delete hostel bundles than\t are not in

        self._update_bundles(device)
        self._update_ports(device)

    def _update_ports(self, device):
        # Ports are updating independently, not in update_bundles() cycle

        processed_ports = []  # for duplicate control

        # Building a {port: {descriptions: '', 'bundle: ''}} structure
        collector_ports = {}
        for bundle_name, bundle_data in self.tree[device.netname]['bundles'].items():
            for port_name, port_data in bundle_data['ports'].items():
                collector_ports[port_name] = {'description': port_data['description'],
                                              'bundle_name': bundle_name}

        ports = Port.objects.filter(bundle__device=device).prefetch_related('bundle')
        ports = ports.order_by('iface_index', '-created')

        for port in ports:

            # Delete duplicates
            if port.name in processed_ports:
                port.delete()
                # Once it is processed, it's already deleted from collector_ports
                message = '{:<12} | Port {} deleted as it\'s duplicated'.format(device.netname,
                                                                                port.name)
                logging.warning(message)
                continue

            # Append to list for duplicate control
            processed_ports.append(port.name)

            if port.name in collector_ports:
                port_data = collector_ports[port.name]
                if not self._ports_equals(port, port_data):
                    self._update_port(device, port, port_data)
                del collector_ports[port.name]
                del port_data

            else:
                port.delete()
                message = '{:<12} | Port {} ({}) deleted'.format(device.netname,
                                                                 port.name,
                                                                 port.description)
                self.actions.append(message)
                logging.info(message)

        # Now we have only new created ports in collector_ports
        for port_name, port_data in collector_ports.items():
            self._create_port(device, port_name, port_data)

    def _update_bundles(self, device):
        collector_device = copy.deepcopy(self.tree.get(device.netname))
        bundles = device.bundles.all().order_by('iface_index').prefetch_related('ports')

        for bundle in bundles:
            self._process_bundle(bundle)
            try:
                del collector_device['bundles'][bundle.name]
            except KeyError:
                # KeyError means the bundle not in collector data [i.e. deleted]
                # No actions needed because we have it already deleted in update_bundle()
                pass

        # After updating bundles there must be only new bundles in collector_device
        for bundle_name, bundle_data in collector_device['bundles'].items():
            self._create_bundle(device, bundle_name, bundle_data)

    def import_vlans_for_devices(self):
        # Gets all devices, and does import_vlans_for_device for each one
        devices = Device.objects.filter(type__in=['router', 'switch'], status='+')
        devices = devices.order_by('netname')
        for device in devices:
            self.import_vlans_for_device(device)

    def import_bundles_for_devices(self):
        devices = Device.objects.filter(type__in=['router', 'switch'], status='+', is_managed=True)
        devices = devices.order_by('netname')
        for device in devices:
            self.import_bundles_for_device(device)

    @staticmethod
    def _ports_equals(port, data):
        if port.description == data['description'] and port.bundle.name == data['bundle_name']:
            return True
        return False

    @staticmethod
    def _bundles_equals(bundle, data):

        if not bundle.description == data['description']:
            return False

        if not bundle.is_lag == data['is_lag']:
            return False

        return True

    def _update_port(self, device, port, port_data):
        changes = []
        previous_bundle_name = port.bundle.name
        if not previous_bundle_name == port_data['bundle_name']:
            # Port got membership in another bundle
            try:
                bundle = Bundle.objects.get(name=port_data['bundle_name'], device=device)
            except Bundle.DoesNotExist:
                message = '%s: bundle for port %s not found.' % (device.netname, port.name)
                self.errors.append(message)
                logging.error(message)
                return
            port.bundle = bundle
            changes.append('bundle {} -> {}'.format(previous_bundle_name, bundle.name))

        previous_description = port.description
        if not port_data['description'] == previous_description:
            port.description = port_data['description']
            changes.append('description: {} -> {}'.format(previous_description, port_data['description']))

        try:
            port.save()
        except Exception as e:
            message = '{:<12} | Critical blocking error: port {}: {}'.format(device.netname,
                                                                             port.name,
                                                                             str(e))
            self.errors.append(message)
            return

        changes_string = ', '.join(changes)
        message = '{:<12} | Port {} {} updated: {}'.format(device.netname, port.name, port.description, changes_string)
        self.actions.append(message)
        logging.info(message)

    def _update_bundle(self, bundle, bundle_data):
        changes = []

        previous_description = bundle.description
        if not previous_description == bundle_data['description']:
            changes.append('description: {} -> {}'.format(
                previous_description or '""',
                bundle_data['description'] or '""'))
            bundle.description = bundle_data['description']

        previous_is_lag = bundle.is_lag
        if not previous_is_lag == bundle_data['is_lag']:
            changes.append('LAG member: {} -> {}'.format(previous_is_lag, bundle_data['description']))
            bundle.is_lag = bundle_data['is_lag']

        bundle.save()

        changes_string = ', '.join(changes)
        message = '{:<12} | Bundle {} ({}) updated: {}'.format(bundle.device.netname,
                                                               bundle.name,
                                                               bundle.description,
                                                               changes_string)
        self.actions.append(message)
        logging.info(message)

    def _process_bundle(self, bundle):

        # Collector bundles to be updated
        collector_device = self.tree.get(bundle.device.netname)

        # Gone bundles
        if bundle.name not in collector_device['bundles']:
            # We checked earlier that we have collector_device['bundles'],
            # so we're sure that the bundle is gone
            bundle.delete()
            message = '{:<12} | Bundle {} ({}) deleted'.format(bundle.device.netname, bundle.name, bundle.description)
            self.actions.append(message)
            logging.info(message)
            return

        if not self._bundles_equals(bundle, collector_device['bundles'][bundle.name]):
            self._update_bundle(bundle, collector_device['bundles'][bundle.name])

        # We can't operate with bundle's ports here,
        # because ports could move to other bundles
        # Ports will be updated outside of this function

        return

    def _create_bundle(self, device, bundle_name, bundle_data):
        bundle = Bundle(device=device,
                        name=bundle_name,
                        description=bundle_data['description'],
                        is_lag=bundle_data['is_lag'])
        bundle.save()
        message = '{:<12} | Bundle {} ({}) created'.format(device.netname, bundle.name, bundle.description)
        self.actions.append(message)
        logging.info(message)

    def _create_port(self, device, port_name, port_data):
        try:
            bundle = Bundle.objects.get(device=device, name=port_data['bundle_name'])
        except Bundle.DoesNotExist:
            message = '%s: unable to fund bundle for port %s' % (device, port_name)
            self.errors.append(message)
            logging.warning(message)
            return

        port = Port(bundle=bundle,
                    name=port_name,
                    description=port_data['description'])
        port.save()
        message = '{:<12} | Port {} ({}) under bundle {} ({}) created'.format(device.netname,
                                                                              port.name,
                                                                              port.description,
                                                                              bundle.name,
                                                                              bundle.description)
        self.actions.append(message)
        logging.info(message)

    @staticmethod
    def print_tree(tree):
        print(json.dumps(tree, indent=2, sort_keys=True))
