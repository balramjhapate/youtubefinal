# Generated manually for review status fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0019_add_transcript_without_timestamps'),
    ]

    operations = [
        migrations.AddField(
            model_name='videodownload',
            name='review_status',
            field=models.CharField(
                choices=[
                    ('pending_review', 'Pending Review'),
                    ('approved', 'Approved'),
                    ('needs_revision', 'Needs Revision'),
                    ('rejected', 'Rejected'),
                ],
                default='pending_review',
                help_text='Review status of final processed video',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='review_notes',
            field=models.TextField(blank=True, help_text='Review notes or feedback'),
        ),
        migrations.AddField(
            model_name='videodownload',
            name='reviewed_at',
            field=models.DateTimeField(blank=True, help_text='When video was reviewed', null=True),
        ),
    ]

