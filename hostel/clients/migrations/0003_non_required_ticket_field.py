# Generated by Django 2.0.5 on 2021-01-18 22:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0002_auto_20201017_2132'),
    ]

    operations = [
        migrations.AlterField(
            model_name='client',
            name='ticket',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
    ]
