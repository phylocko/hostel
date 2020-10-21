from django.core.management.base import BaseCommand
from hostel.clients.models import Client
from hostel.companies.models import Company


class Command(BaseCommand):
    help = 'Creates companies from clients that have agreements and clientnames'

    def handle(self, *args, **options):
        print('Making companies from clients...')

        companies = Company.objects.all()
        if companies.count() > 0:
            self.stdout.write(self.style.ERROR('Companies already created. This script should be run once.'))
            quit()

        for client in Client.objects.filter(clientname__isnull=False).distinct():
            if not client.clientname:
                continue

            if not client.docs.all():
                continue

            company = Company()
            company.name = client.clientname
            company.is_active = True if client.status == '+' else False
            company.client = client
            company.comment = client.comment
            company.rt = client.ticket
            print(company)
            print(' - client:', company.client.netname)
            print(' - comment:', company.comment)
            print(' - is active:', company.is_active)
            print('=' * 30)
            company.save()

            for agreement in client.docs.all():
                agreement.company = company
                print(' - - ', agreement)
                agreement.save()
