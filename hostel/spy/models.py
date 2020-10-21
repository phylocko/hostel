from django.db import models
from django.utils import timezone
import json


class Spy(models.Model):
    CREATE = 'create'
    CHANGE = 'change'
    DELETE = 'delete'

    ACTION_CHOICES = (
        (CREATE, 'CREATE'),
        (CHANGE, 'CHANGE'),
        (DELETE, 'DELETE'),
    )

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey('common.User', null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=25, choices=ACTION_CHOICES)
    object_name = models.CharField(max_length=100, blank=True, null=True)
    object_id = models.IntegerField(null=True)
    object_str = models.CharField(max_length=255, null=True, blank=True)
    changes = models.TextField(blank=True, null=True)
    client = models.ForeignKey('clients.Client', null=True, blank=True, default=None, on_delete=models.SET_NULL)
    time = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'spy_log'

    def changed(self, instance=None, old_instance=None, form=None, request=None):
        try:
            user = request.user
        except AttributeError:
            user = None

        self.log(object=instance,
                 old_object=old_instance,
                 form=form,
                 user=user,
                 action=Spy.CHANGE)

    def created(self, instance=None, form=None, request=None, client=None):
        try:
            user = request.user
        except AttributeError:
            user = None

        self.log(object=instance, form=form, action=Spy.CREATE, user=user, client=client)

    def deleted(self, instance=None, request=None, client=None):
        self.log(object=instance, user=request.user, client=client, action=Spy.DELETE)

    def log(self, object=None, old_object=None, form=None, user=None, action=None, client=None):

        changes = {}

        if form:
            for field_name in form.changed_data:
                changes[field_name] = {'new': str(form.cleaned_data[field_name])}
                if old_object is not None:
                    changes[field_name]['old'] = str(getattr(old_object, field_name))

        if client:
            client_id = client.pk
        elif hasattr(object, 'related_client_id'):
            client_id = getattr(object, 'related_client_id')
        else:
            client_id = None

        # Заполняем все поля
        self.object_name = object.__class__.__name__
        self.object_str = str(object)
        self.object_id = object.pk
        self.user = user
        self.action = action
        if len(changes) > 0:
            self.changes = json.dumps(changes, ensure_ascii=False)
        self.client_id = client_id

        self.time = timezone.now()
        self.save()

    def json_changes(self):
        if self.changes:
            return self.changes.replace("\\\"", '\\\\"')
        else:
            return None
