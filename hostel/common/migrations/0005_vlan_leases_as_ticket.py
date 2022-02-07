# Generated by Django 2.0.5 on 2022-02-04 16:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vlans', '0002_auto_20220203_1744'),
        ('common', '0004_photos'),
    ]

    operations = [
        migrations.AddField(
            model_name='lease',
            name='vlans',
            field=models.ManyToManyField(related_name='leases', to='vlans.Vlan'),
        ),
        migrations.AlterField(
            model_name='autonomoussystem',
            name='ticket',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
    ]