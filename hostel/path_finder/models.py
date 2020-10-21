import networkx as nx
from networkx.exception import NetworkXNoPath

import hostel.common.models as common_models
from hostel.devices.models import Device


class PathNotFound(Exception):
    pass


class PathFinder:
    @staticmethod
    def suggest_paths(source_id, target_id, exclude_netnames):

        try:
            source_bundle = common_models.Bundle.objects.get(pk=source_id)
        except common_models.Bundle.DoesNotExist:
            return {'error': 'Bundle %s doesn\'t exist' % source_id}

        try:
            target_bundle = common_models.Bundle.objects.get(pk=target_id)
        except common_models.Bundle.DoesNotExist:
            return {'error': 'Bundle %s doesn\'t exist' % target_id}

        selected_devices = Device.objects.filter(type__in=['router', 'switch'], status='+') \
            .exclude(netname__in=exclude_netnames) \
            .order_by('netname')

        # creating graph
        G = nx.Graph()
        G.add_nodes_from(selected_devices)

        # creating edges
        for device in selected_devices:
            for bundle in device.bundles.filter(remote_device__isnull=False).exclude(
                    remote_device__netname__in=exclude_netnames):
                remote_device = bundle.remote_device
                if remote_device.bundles.filter(remote_device=device):

                    if remote_device.type == 'router' and device.type == 'switch':
                        G.add_edge(device, remote_device, weight=1.0)

                    elif remote_device.type == 'switch' and device.type == 'router':
                        G.add_edge(device, remote_device, weight=1.0)

                    else:
                        G.add_edge(device, remote_device, weight=2.0)

        # fake edges among routers
        routers = selected_devices.filter(type='router')
        for source in routers:
            for target in routers:
                if not G.has_edge(source, target):
                    G.add_edge(source, target, weight=1)

        try:
            # paths = [x for x in nx.all_shortest_paths(G, source_bundle.device, target_bundle.device, weight=True)]
            paths = [nx.dijkstra_path(G, source_bundle.device, target_bundle.device)]
        except NetworkXNoPath:
            return {'error': 'No paths found'}

        paths = [[device.netname for device in path] for path in paths]

        # generating data
        data = {
            'source': '{device} port {name} [{description}]'.format(device=source_bundle.device.netname,
                                                                    name=source_bundle.name,
                                                                    description=source_bundle.description),
            'target': '{device} port {name} [{description}]'.format(device=target_bundle.device.netname,
                                                                    name=target_bundle.name,
                                                                    description=target_bundle.description),
            'paths': paths
        }

        return data

    def full_path(self, source_id, target_id, requested_path):
        device_path = []
        for netname in requested_path:  # can't get in in one query due to disability to keep order
            device = Device.objects.get(netname=netname)
            device_path.append(device)

        computed_path = []
        i = 0
        while i < len(device_path):
            try:
                data = self.find_params(i, device_path, source_id, target_id)
            except PathNotFound:
                raise PathNotFound

            computed_path.append(data)
            i += 1

        data = {'source': source_id,
                'target': target_id,
                'requested_path': requested_path,
                'computed_path': computed_path}
        return data

    @staticmethod
    def find_params(i, device_path, source_id, target_id):
        source_bundle = common_models.Bundle.objects.get(pk=source_id)
        target_bundle = common_models.Bundle.objects.get(pk=target_id)
        current_device = device_path[i]

        if i == 0:
            prev_bundle = source_bundle
            next_device = device_path[i + 1]
            next_bundle = current_device.bundles.filter(remote_device=next_device).first()
        elif i == len(device_path) - 1:
            next_bundle = target_bundle
            prev_device = device_path[i - 1]
            prev_bundle = current_device.bundles.filter(remote_device=prev_device).first()
        else:
            prev_device = device_path[i - 1]
            next_device = device_path[i + 1]
            prev_bundle = current_device.bundles.filter(remote_device=prev_device).first()
            next_bundle = current_device.bundles.filter(remote_device=next_device).first()

        data = {'device': current_device.netname, 'type': current_device.type}
        if current_device.store_entry:
            data['vendor'] = current_device.store_entry.vendor

        if current_device.type == 'switch':
            if not prev_bundle or not next_bundle:
                raise PathNotFound
            data['ports'] = [prev_bundle.name, next_bundle.name]

        elif current_device.type == 'router':
            ccc_params = {}
            if prev_device.type == 'router':
                ccc_params['remote_address'] = prev_device.management_net.address
                ccc_params['interface'] = next_bundle.name

            elif next_device.type == 'router':
                ccc_params['remote_address'] = next_device.management_net.address
                ccc_params['interface'] = prev_bundle.name
            data['ccc_params'] = ccc_params

        return data
