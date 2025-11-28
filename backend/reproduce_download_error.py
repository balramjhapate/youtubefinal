import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rednote_project.settings')
django.setup()

from downloader.models import VideoDownload
from downloader.utils import download_file
from django.core.files.base import ContentFile

def reproduce():
    try:
        video_id = 23
        print(f"Attempting to fetch VideoDownload with id={video_id}")
        try:
            video = VideoDownload.objects.get(id=video_id)
        except VideoDownload.DoesNotExist:
             print(f"Video with id={video_id} not found. Listing all videos:")
             for v in VideoDownload.objects.all():
                 print(f"ID: {v.id}, Title: {v.title}")
             return

        print(f"Found video: {video.title}")
        print(f"Video URL: {video.video_url}")
        
        if not video.video_url:
            print("Error: No video URL found")
            return

        print("Attempting download_file...")
        # We need to mock requests or just let it run. utils.py prints errors.
        # But utils.py uses print(), so we should see it.
        
        file_content = download_file(video.video_url)
        
        if file_content:
            print(f"Download successful. Content size: {file_content.size}")
            print("Attempting to save to local file...")
            filename = f"{video.video_id or 'video'}_{video.pk}.mp4"
            try:
                video.local_file.save(filename, file_content, save=True)
                print("Save successful.")
            except Exception as e:
                print(f"Save failed: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("download_file returned None. Check logs for 'Download error:'.")
            
    except Exception as e:
        print(f"Exception caught: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    reproduce()
