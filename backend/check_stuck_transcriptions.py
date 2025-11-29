"""
Script to check for and reset stuck transcriptions.

Usage:
    python check_stuck_transcriptions.py
    python check_stuck_transcriptions.py --reset
    python check_stuck_transcriptions.py --timeout 30
"""
import argparse
from datetime import datetime, timedelta
from app.models import SessionLocal, VideoDownload


def check_stuck_transcriptions(reset=False, timeout_minutes=30):
    """Check for and optionally reset stuck transcriptions"""
    db = SessionLocal()
    
    try:
        # Find stuck transcriptions
        stuck_videos = db.query(VideoDownload).filter(
            VideoDownload.transcription_status == 'transcribing',
            VideoDownload.transcript_started_at.isnot(None)
        ).all()
        
        stuck_count = 0
        now = datetime.utcnow()
        
        for video in stuck_videos:
            if video.transcript_started_at:
                elapsed_minutes = (now - video.transcript_started_at).total_seconds() / 60
                
                if elapsed_minutes > timeout_minutes:
                    stuck_count += 1
                    title_preview = video.title[:50] if video.title else "No title"
                    print(f"⚠️  Found stuck transcription: Video ID {video.id} "
                          f"({title_preview}...) - stuck for {elapsed_minutes:.1f} minutes")
                    
                    if reset:
                        video.transcription_status = 'not_transcribed'
                        video.transcript_error_message = (
                            f"Transcription was stuck for {elapsed_minutes:.1f} minutes and was reset. "
                            "Please try transcribing again."
                        )
                        video.transcript_started_at = None
                        db.commit()
                        print(f"✓ Reset video ID {video.id}")
        
        if stuck_count == 0:
            print("✓ No stuck transcriptions found.")
        elif not reset:
            print(f"\n⚠️  Found {stuck_count} stuck transcription(s). "
                  "Run with --reset to reset them.")
        else:
            print(f"\n✓ Reset {stuck_count} stuck transcription(s).")
            
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Check for and optionally reset stuck transcriptions')
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
    
    args = parser.parse_args()
    check_stuck_transcriptions(reset=args.reset, timeout_minutes=args.timeout)

