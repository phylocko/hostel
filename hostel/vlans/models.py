import datetime
from django.db import models
from django.db.models import Q
from hostel.service.variables import validate_vlan_name
from hostel.service.variables import validate_vlan_id


class VlanHelper():
    def __init__(self, vlan):
        self.vlan = vlan

    def can_be_saved(self):
        if self.vlan.pk is None:
            return self.can_be_created()

        if Vlan.objects.filter(vlannum=self.vlan.vlannum).exclude(
                pk=self.vlan.pk).count() == 0:
            return True
        return False

    def can_be_created(self):
        if Vlan.objects.filter(vlannum=self.vlan.vlannum).count() == 0:
            return True

        return False


class Vlan(models.Model):
    vlanid = models.AutoField(db_column='vlanID',
                              primary_key=True)  # Field name made lowercase.
    service = models.ForeignKey('common.Service',
                                related_name="vlan",
                                on_delete=models.SET_NULL,
                                null=True)
    vlannum = models.IntegerField(blank=False, null=False, unique=True, validators=[validate_vlan_id])
    vname = models.CharField(max_length=20, blank=False, null=False, unique=True, validators=[validate_vlan_name])
    status = models.CharField(max_length=20, blank=True, null=True)
    ticket = models.CharField(max_length=20, blank=True, null=True)
    comment = models.CharField(max_length=2048, blank=True, null=True)

    # Deprecated at 2018-06-08:
    multivlan = models.BooleanField(default=False)

    is_management = models.BooleanField(default=False)
    is_local = models.BooleanField(default=True)  # provisioned on our network

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    isFreeRange = False
    freeUpTo = 0

    def is_updated_today(self):
        few_hours = datetime.timedelta(hours=12)
        return datetime.datetime.now() - self.updated < few_hours

    def is_gone(self):
        three_days = datetime.timedelta(days=3)
        return datetime.datetime.now() - self.updated > three_days

    class Meta:
        managed = True
        db_table = "vlans"

    def __str__(self):
        return '%s [%s]' % (self.vlannum, self.vname)


class Vlanaggregator():
    initial_vlans = ''

    def aggregate(self):
        vlans = Vlan.objects.all().order_by('vlannum')
        self.initial_vlans = [x for x in vlans]
        return self.initial_vlans

    def aggregate_with_freevlans(self):
        if not self.initial_vlans:
            self.aggregate()

        i = 1
        aggregated_vlans = []

        vlan_count = len(self.initial_vlans)

        while i < vlan_count - 1:
            aggregated_vlans.append(self.initial_vlans[i])
            if self.initial_vlans[i].vlannum + 1 < self.initial_vlans[
                i + 1].vlannum:
                vlan = Vlan()
                vlan.isFreeRange = True
                vlan.vname = 'Свободен'
                vlan.vlannum = self.initial_vlans[i].vlannum + 1
                vlan.freeUpTo = self.initial_vlans[i + 1].vlannum - 1
                aggregated_vlans.append(vlan)
            i += 1
            pass

        return aggregated_vlans

    def freevlans(self):
        if not self.initial_vlans:
            self.aggregate()

        aggregated_vlans = self.aggregate_with_freevlans()

        free_vlans = []
        for vlan in aggregated_vlans:
            if vlan.isFreeRange:
                free_vlans.append(vlan)

        return free_vlans


class VlanSearch:
    def __init__(self, queryset=None):
        self.queryset = Vlan.objects.all()
        if queryset:
            self.queryset = queryset

    def search(self, search_string):

        if not search_string:
            return Vlan.objects.none()

        search_string = search_string.strip()

        if search_string.isdigit():
            vlans = self.queryset.filter(vlannum__istartswith=search_string)
        else:
            keywords = search_string.split()
            vlans = self.queryset
            for keyword in keywords:
                vlans = vlans.filter(Q(vname__icontains=keyword) |
                                     Q(vlannum__icontains=keyword) |
                                     Q(comment__icontains=keyword))
        return vlans.order_by('vlannum')
