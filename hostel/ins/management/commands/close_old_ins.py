from django.core.management.base import BaseCommand
from hostel.ins.models import Incident
import datetime


class Command(BaseCommand):
    help = 'Will remove all Bundles where is_gone == True'

    def handle(self, *args, **options):
        diff = datetime.datetime.now() - datetime.timedelta(days=3)

        old_incidents = Incident.objects.filter(type='work', closed=False,
                                                deleted=False, time_end__lte=diff)
        for ins in old_incidents:
            ins.closed = True
            ins.save()
