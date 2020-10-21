from hostel.clients.models import ClientSearch
from hostel.companies.models import CompanySearch
from hostel.nets.models import NetSearch
from hostel.devices.models import DeviceSearch
from hostel.ins.models import InsSearch
from hostel.vlans.models import VlanSearch
from hostel.store.models import EntrySearch
from hostel.docs.models import AgreementSearch
from hostel.common.models import (
    LeaseSearch, ServiceSearch, SubServiceSearch, AutonomousSystemSearch,
    BundleSearch, DatacenterSearch, UserSearch
)


class SearchAll:
    @staticmethod
    def search(search_string):

        search_results = dict(clients=[],
                              services=[],
                              subservices=[],
                              nets=[],
                              devices=[],
                              store_items=[],
                              incidents=[],
                              vlans=[],
                              autonomous_systems=[],
                              leases=[],
                              docs=[],
                              bundles=[],
                              datacenters=[],
                              companies=[])

        if not search_string:
            return dict(count=0, search_results=search_results)

        search_string = search_string.strip()

        search_results['clients'] = ClientSearch().search(search_string)
        search_results['companies'] = CompanySearch().search(search_string)
        search_results['services'] = ServiceSearch().search(search_string)
        search_results['subservices'] = SubServiceSearch().search(search_string)
        search_results['nets'] = NetSearch().search(search_string)
        search_results['devices'] = DeviceSearch().search(search_string)
        search_results['store_items'] = EntrySearch().search(search_string)
        search_results['vlans'] = VlanSearch().search(search_string)
        search_results['autonomous_systems'] = AutonomousSystemSearch().search(search_string)
        search_results['leases'] = LeaseSearch().search(search_string)
        search_results['docs'] = AgreementSearch().search(search_string)
        search_results['bundles'] = BundleSearch().search(search_string)
        search_results['datacenters'] = DatacenterSearch().search(search_string)
        search_results['staff'] = UserSearch().search(search_string)

        count = 0
        for group in search_results.values():
            count += len(group)

        return dict(search_results=search_results, count=count)
