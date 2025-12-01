from django.db import models


class ClonedVoice(models.Model):
    name = models.CharField(max_length=100)
    file = models.FileField(upload_to='cloned_voices/')
    is_default = models.BooleanField(default=False, help_text="Default voice used for video TTS generation")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_default', '-created_at']

    def save(self, *args, **kwargs):
        # Ensure only one default voice exists
        if self.is_default:
            ClonedVoice.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

