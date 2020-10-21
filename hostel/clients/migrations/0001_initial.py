# Generated by Django 2.1.5 on 2020-10-17 21:32

from django.db import migrations, models
import hostel.service.variables


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Client',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('netname', models.CharField(max_length=255, null=True, unique=True, validators=[hostel.service.variables.validate_netname])),
                ('clientname', models.CharField(blank=True, max_length=255, null=True)),
                ('engname', models.CharField(blank=True, max_length=255, null=True)),
                ('address', models.CharField(blank=True, max_length=255, null=True)),
                ('contacts', models.TextField(blank=True, null=True)),
                ('support_contacts', models.TextField(blank=True, null=True)),
                ('enabled', models.BooleanField(default=True)),
                ('comment', models.CharField(blank=True, max_length=2048, null=True)),
                ('email', models.CharField(blank=True, max_length=255, null=True, validators=[hostel.service.variables.validate_mail_list])),
                ('support_email', models.CharField(blank=True, max_length=255, null=True, validators=[hostel.service.variables.validate_mail_list])),
                ('url', models.URLField(blank=True, max_length=255, null=True)),
                ('ticket', models.CharField(max_length=20, null=True)),
                ('is_consumer', models.BooleanField(default=True)),
                ('is_provider', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'clients',
                'managed': True,
            },
        ),
    ]
