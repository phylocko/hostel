from hostel.nets.models import Net


for net in Net.objects.all():
    if net.management_vlan:
        net.vlan = net.management_vlan
        net.save()

