# Generated manually
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0021_add_is_default_to_clonedvoice'),
    ]

    operations = [
        migrations.CreateModel(
            name='CloudinarySettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cloud_name', models.CharField(blank=True, help_text='Cloudinary cloud name', max_length=255)),
                ('api_key', models.CharField(blank=True, help_text='Cloudinary API key', max_length=255)),
                ('api_secret', models.CharField(blank=True, help_text='Cloudinary API secret', max_length=255)),
                ('enabled', models.BooleanField(default=False, help_text='Enable Cloudinary uploads')),
            ],
            options={
                'verbose_name': 'Cloudinary Setting',
                'verbose_name_plural': 'Cloudinary Settings',
            },
        ),
        migrations.CreateModel(
            name='GoogleSheetsSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('spreadsheet_id', models.CharField(blank=True, help_text='Google Sheets spreadsheet ID', max_length=255)),
                ('sheet_name', models.CharField(default='Sheet1', help_text='Sheet name to write data to', max_length=255)),
                ('credentials_json', models.TextField(blank=True, help_text='Google Service Account JSON credentials')),
                ('enabled', models.BooleanField(default=False, help_text='Enable Google Sheets tracking')),
            ],
            options={
                'verbose_name': 'Google Sheets Setting',
                'verbose_name_plural': 'Google Sheets Settings',
            },
        ),
    ]

