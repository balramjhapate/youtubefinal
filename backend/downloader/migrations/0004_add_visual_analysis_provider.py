# Generated migration for visual analysis provider setting

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('downloader', '0003_add_analysis_provider_settings'),
    ]

    operations = [
        migrations.AddField(
            model_name='aiprovidersettings',
            name='visual_analysis_provider',
            field=models.CharField(
                default='openai',
                help_text='AI provider for visual analysis (OpenAI GPT-4o-mini or Gemini Vision)',
                max_length=50,
                choices=[('gemini', 'Google Gemini'), ('openai', 'OpenAI'), ('anthropic', 'Anthropic (Claude)')]
            ),
        ),
    ]

