# Generated by Django 2.0.5 on 2022-02-06 16:21

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Part',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('type', models.CharField(max_length=20, null=True)),
                ('model', models.CharField(max_length=255)),
                ('vendor', models.CharField(blank=True, max_length=50, null=True)),
                ('serial', models.CharField(default='', max_length=255)),
                ('comment', models.CharField(blank=True, max_length=2048, null=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'store_parts',
            },
        ),
        migrations.AlterField(
            model_name='entry',
            name='vendor',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='part',
            name='entry',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='store.Entry'),
        ),
    ]
