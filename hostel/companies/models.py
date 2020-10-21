from django.db import models
from django.db.models import Q


class Company(models.Model):
    """
    This model represents an organization, while clients.Client is a technical entity
    """
    ticket = models.CharField(max_length=20, blank=False, null=True)
    name = models.CharField(max_length=255, blank=False, null=False, unique=False)
    city = models.ForeignKey('common.City', null=True, blank=True, on_delete=models.SET_NULL)
    contacts = models.TextField(blank=True, null=True)
    comment = models.CharField(max_length=2048, blank=True, null=True)
    client = models.ForeignKey('clients.Client', blank=True, null=True, related_name='companies',
                               on_delete=models.SET_NULL)
    # Electronic document_management
    edm = models.BooleanField(default=False)
    is_active = models.BooleanField(default=1)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    creator = models.ForeignKey('common.User', null=True, on_delete=models.SET_NULL)

    class Meta:
        managed = True
        db_table = 'companies'
        unique_together = ('name', 'client')

    def __str__(self):
        return self.name


class CompanySearch:
    def search(self, search_string):
        if not search_string:
            return []

        search_string = search_string.strip()
        words = search_string.split()

        companies = Company.objects.all()

        for word in words:
            companies = companies.filter(Q(name__icontains=word) |
                                         Q(client__netname__icontains=word) |
                                         Q(client__clientname__icontains=word) |
                                         Q(comment__icontains=word))

        return companies
