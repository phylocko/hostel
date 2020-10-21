# Generated by Django 2.1.5 on 2020-10-17 21:32

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('vlans', '0001_initial'),
        ('clients', '0002_auto_20201017_2132'),
        ('docs', '0001_initial'),
        ('common', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='subservice',
            name='vlans',
            field=models.ManyToManyField(related_name='subservices', to='vlans.Vlan'),
        ),
        migrations.AddField(
            model_name='service',
            name='application',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='services', to='docs.Application'),
        ),
        migrations.AddField(
            model_name='service',
            name='asn',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='services', to='common.Autonomoussystem'),
        ),
        migrations.AddField(
            model_name='service',
            name='cities',
            field=models.ManyToManyField(related_name='services', to='common.City'),
        ),
        migrations.AddField(
            model_name='service',
            name='client',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='services', to='clients.Client'),
        ),
        migrations.AddField(
            model_name='service',
            name='lease',
            field=models.ManyToManyField(related_name='services', to='common.Lease'),
        ),
        migrations.AddField(
            model_name='rack',
            name='datacenter',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='common.Datacenter'),
        ),
        migrations.AddField(
            model_name='port',
            name='bundle',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='ports', to='common.Bundle'),
        ),
        migrations.AddField(
            model_name='phone',
            name='client',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='clients.Client'),
        ),
        migrations.AddField(
            model_name='lease',
            name='application',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='leases', to='docs.Application'),
        ),
        migrations.AddField(
            model_name='lease',
            name='cities',
            field=models.ManyToManyField(related_name='leases', to='common.City'),
        ),
        migrations.AddField(
            model_name='lease',
            name='group',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='leases', to='common.LeaseGroup'),
        ),
        migrations.AddField(
            model_name='lease',
            name='organization',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='clients.Client'),
        ),
        migrations.AddField(
            model_name='datacenter',
            name='city',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='common.City'),
        ),
        migrations.AddField(
            model_name='datacenter',
            name='organization',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='clients.Client'),
        ),
        migrations.AddField(
            model_name='call',
            name='phone',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='common.Phone'),
        ),
        migrations.AddField(
            model_name='burstset',
            name='bundles',
            field=models.ManyToManyField(related_name='bursts_member', to='common.Bundle'),
        ),
        migrations.AddField(
            model_name='burstset',
            name='client',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='clients.Client'),
        ),
        migrations.AddField(
            model_name='burstset',
            name='extract_bundles',
            field=models.ManyToManyField(related_name='bursts_negative', to='common.Bundle'),
        ),
        migrations.AddField(
            model_name='bundlevlan',
            name='bundle',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='common.Bundle'),
        ),
        migrations.AddField(
            model_name='bundlevlan',
            name='services',
            field=models.ManyToManyField(related_name='bundle_vlans', to='common.Service'),
        ),
        migrations.AddField(
            model_name='bundlevlan',
            name='subservices',
            field=models.ManyToManyField(related_name='bundle_vlans', to='common.SubService'),
        ),
        migrations.AddField(
            model_name='bundlevlan',
            name='vlan',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vlans.Vlan'),
        ),
    ]
