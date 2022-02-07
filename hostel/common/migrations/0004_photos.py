# Generated by Django 2.0.5 on 2021-10-05 00:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0003_auto_20201017_2132'),
    ]

    operations = [
        migrations.CreateModel(
            name='Photo',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('src', models.ImageField(upload_to='photos')),
                ('name', models.CharField(blank=True, max_length=20, null=True, unique=True)),
                ('comment', models.CharField(blank=True, max_length=255, null=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'photos',
                'managed': True,
            },
        ),
    ]