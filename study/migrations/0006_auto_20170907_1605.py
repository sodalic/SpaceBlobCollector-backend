# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2017-09-07 16:05
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models
import study.validators


class Migration(migrations.Migration):

    dependencies = [
        ('study', '0005_auto_20170907_1404'),
    ]

    operations = [
        migrations.AlterField(
            model_name='researcher',
            name='access_key_id',
            field=models.CharField(max_length=64, null=True, validators=[django.core.validators.RegexValidator(b'^[0-9a-zA-Z+/]+$')]),
        ),
        migrations.AlterField(
            model_name='researcher',
            name='access_key_secret',
            field=models.CharField(max_length=44, null=True, validators=[django.core.validators.RegexValidator(b'^[0-9a-zA-Z_\\-]+$')]),
        ),
        migrations.AlterField(
            model_name='researcher',
            name='access_key_secret_salt',
            field=models.CharField(max_length=24, null=True, validators=[django.core.validators.RegexValidator(b'^[0-9a-zA-Z_\\-]+$')]),
        ),
        migrations.AlterField(
            model_name='study',
            name='encryption_key',
            field=models.CharField(help_text='Key used for encrypting the study data', max_length=32, validators=[study.validators.LengthValidator(32, message=b'Invalid encryption key')]),
        ),
        migrations.AlterField(
            model_name='study',
            name='name',
            field=models.TextField(help_text='Name of the study; can be of any length', unique=True),
        ),
    ]
