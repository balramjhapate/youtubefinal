"""
Management command to check for and reset stuck transcriptions.

Usage:
    python manage.py check_stuck_transcriptions
    python manage.py check_stuck_transcriptions --reset
    python manage.py check_stuck_transcriptions --timeout 30
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from downloader.models import VideoDownload


class Command(BaseCommand):
    help = 'Check for and optionally reset stuck transcriptions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset stuck transcriptions to not_transcribed status',
        )
        parser.add_argument(
            '--timeout',
            type=int,
            default=30,
            help='Timeout in minutes (default: 30)',
        )

    def handle(self, *args, **options):
        timeout_minutes = options['timeout']
        reset = options['reset']
        
        # Find stuck transcriptions
        stuck_videos = VideoDownload.objects.filter(
            transcription_status='transcribing',
            transcript_started_at__isnull=False
        )
        
        stuck_count = 0
        for video in stuck_videos:
            elapsed_minutes = (timezone.now() - video.transcript_started_at).total_seconds() / 60
            if elapsed_minutes > timeout_minutes:
                stuck_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"Found stuck transcription: Video ID {video.id} "
                        f"({video.title[:50]}...) - stuck for {elapsed_minutes:.1f} minutes"
                    )
                )
                
                if reset:
                    video.transcription_status = 'not_transcribed'
                    video.transcript_error_message = (
                        f"Transcription was stuck for {elapsed_minutes:.1f} minutes and was reset. "
                        "Please try transcribing again."
                    )
                    video.transcript_started_at = None
                    video.save()
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ Reset video ID {video.id}")
                    )
        
        if stuck_count == 0:
            self.stdout.write(
                self.style.SUCCESS('No stuck transcriptions found.')
            )
        elif not reset:
            self.stdout.write(
                self.style.WARNING(
                    f'\nFound {stuck_count} stuck transcription(s). '
                    'Run with --reset to reset them.'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\n✓ Reset {stuck_count} stuck transcription(s).')
            )

