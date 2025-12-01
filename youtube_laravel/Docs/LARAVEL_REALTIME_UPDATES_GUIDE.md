# Laravel Real-Time Status Updates Implementation Guide

## 🎯 Quick Implementation for Video Processing Status

This guide shows you exactly how to implement real-time status updates for your video processing pipeline in Laravel.

---

## 🚀 Option 1: Laravel Broadcasting + Laravel Echo (Recommended)

### Step 1: Install Broadcasting

```bash
composer require pusher/pusher-php-server
# OR use Redis (simpler, no external service)
# Redis is already included in Laravel
```

### Step 2: Configure Broadcasting

**config/broadcasting.php** (already exists, just configure):
```php
'connections' => [
    'pusher' => [
        'driver' => 'pusher',
        'key' => env('PUSHER_APP_KEY'),
        'secret' => env('PUSHER_APP_SECRET'),
        'app_id' => env('PUSHER_APP_ID'),
        'options' => [
            'cluster' => env('PUSHER_APP_CLUSTER'),
            'encrypted' => true,
        ],
    ],
    
    // OR use Redis (simpler, no external service needed)
    'redis' => [
        'driver' => 'redis',
        'connection' => 'default',
    ],
],
```

**.env:**
```env
# Option 1: Pusher (external service)
BROADCAST_DRIVER=pusher
PUSHER_APP_ID=your_app_id
PUSHER_APP_KEY=your_app_key
PUSHER_APP_SECRET=your_app_secret
PUSHER_APP_CLUSTER=mt1

# Option 2: Redis (simpler, recommended for development)
BROADCAST_DRIVER=redis
```

### Step 3: Create Event

```bash
php artisan make:event VideoStatusUpdated
```

**app/Events/VideoStatusUpdated.php:**
```php
<?php

namespace App\Events;

use App\Models\VideoDownload;
use Illuminate\Broadcasting\Channel;
use Illuminate\Broadcasting\InteractsWithSockets;
use Illuminate\Contracts\Broadcasting\ShouldBroadcast;
use Illuminate\Queue\SerializesModels;

class VideoStatusUpdated implements ShouldBroadcast
{
    use InteractsWithSockets, SerializesModels;

    public function __construct(
        public VideoDownload $video
    ) {}

    public function broadcastOn(): Channel
    {
        return new Channel('video.' . $this->video->id);
    }

    public function broadcastWith(): array
    {
        return [
            'id' => $this->video->id,
            'status' => $this->video->status,
            'transcription_status' => $this->video->transcription_status,
            'ai_processing_status' => $this->video->ai_processing_status,
            'processing_v2_status' => $this->video->processing_v2_status,
            'current_step' => $this->video->processing_v2_current_step,
            'progress' => $this->calculateProgress(),
        ];
    }

    public function broadcastAs(): string
    {
        return 'status.updated';
    }

    private function calculateProgress(): int
    {
        $steps = [
            'download' => $this->video->step_download_status === 'completed' ? 1 : 0,
            'transcription' => $this->video->step_transcription_status === 'completed' ? 1 : 0,
            'ai_enhancement' => $this->video->step_ai_enhancement_status === 'completed' ? 1 : 0,
            'script_generation' => $this->video->step_script_generation_status === 'completed' ? 1 : 0,
            'tts_synthesis' => $this->video->step_tts_synthesis_status === 'completed' ? 1 : 0,
            'final_video' => $this->video->step_final_video_status === 'completed' ? 1 : 0,
        ];

        $completed = array_sum($steps);
        $total = count($steps);

        return (int) (($completed / $total) * 100);
    }
}
```

### Step 4: Update Your Job to Broadcast Events

**app/Jobs/ProcessVideoPipeline.php:**
```php
<?php

namespace App\Jobs;

use App\Events\VideoStatusUpdated;
use App\Models\VideoDownload;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;

class ProcessVideoPipeline implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public function __construct(
        public int $videoId
    ) {}

    public function handle(): void
    {
        $video = VideoDownload::findOrFail($this->videoId);

        // Step 1: Download
        $video->update(['step_download_status' => 'processing']);
        broadcast(new VideoStatusUpdated($video))->toOthers();
        $this->downloadVideo($video);
        $video->update(['step_download_status' => 'completed']);
        broadcast(new VideoStatusUpdated($video))->toOthers();

        // Step 2: Transcription
        $video->update(['step_transcription_status' => 'processing']);
        broadcast(new VideoStatusUpdated($video))->toOthers();
        $this->transcribeVideo($video);
        $video->update(['step_transcription_status' => 'completed']);
        broadcast(new VideoStatusUpdated($video))->toOthers();

        // Step 3: AI Processing
        $video->update(['step_ai_enhancement_status' => 'processing']);
        broadcast(new VideoStatusUpdated($video))->toOthers();
        $this->processAI($video);
        $video->update(['step_ai_enhancement_status' => 'completed']);
        broadcast(new VideoStatusUpdated($video))->toOthers();

        // Continue for other steps...
    }

    private function downloadVideo(VideoDownload $video): void
    {
        // Your download logic
    }

    private function transcribeVideo(VideoDownload $video): void
    {
        // Your transcription logic
    }

    private function processAI(VideoDownload $video): void
    {
        // Your AI processing logic
    }
}
```

### Step 5: Install Laravel Echo (Frontend)

```bash
npm install laravel-echo pusher-js
# OR for Redis
npm install laravel-echo @pusher/pusher-js
```

**resources/js/bootstrap.js:**
```javascript
import Echo from 'laravel-echo';
import Pusher from 'pusher-js';

window.Pusher = Pusher;

window.Echo = new Echo({
    broadcaster: 'pusher',
    key: import.meta.env.VITE_PUSHER_APP_KEY,
    cluster: import.meta.env.VITE_PUSHER_APP_CLUSTER,
    forceTLS: true
});

// OR for Redis (using Laravel WebSockets or Soketi)
window.Echo = new Echo({
    broadcaster: 'pusher',
    key: import.meta.env.VITE_PUSHER_APP_KEY,
    wsHost: window.location.hostname,
    wsPort: 6001,
    forceTLS: false,
    enabledTransports: ['ws', 'wss'],
});
```

**.env (Frontend):**
```env
VITE_PUSHER_APP_KEY="${PUSHER_APP_KEY}"
VITE_PUSHER_APP_CLUSTER="${PUSHER_APP_CLUSTER}"
```

### Step 6: Use in React Component

**resources/js/Pages/Videos/Show.jsx:**
```jsx
import { useEffect, useState } from 'react';
import { Head, usePage } from '@inertiajs/react';

export default function Show({ video: initialVideo }) {
    const [video, setVideo] = useState(initialVideo);
    const { echo } = usePage().props;

    useEffect(() => {
        // Listen for status updates
        const channel = window.Echo.channel(`video.${video.id}`)
            .listen('.status.updated', (e) => {
                setVideo(prev => ({
                    ...prev,
                    status: e.status,
                    transcription_status: e.transcription_status,
                    ai_processing_status: e.ai_processing_status,
                    processing_v2_status: e.processing_v2_status,
                    current_step: e.current_step,
                    progress: e.progress,
                }));
            });

        return () => {
            window.Echo.leaveChannel(`video.${video.id}`);
        };
    }, [video.id]);

    return (
        <>
            <Head title={video.title || 'Video Details'} />
            
            <div className="container mx-auto px-4 py-8">
                <h1 className="text-3xl font-bold mb-4">{video.title}</h1>
                
                {/* Progress Bar */}
                <div className="mb-6">
                    <div className="flex justify-between mb-2">
                        <span className="text-sm font-medium">Processing Progress</span>
                        <span className="text-sm font-medium">{video.progress || 0}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2.5">
                        <div
                            className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
                            style={{ width: `${video.progress || 0}%` }}
                        ></div>
                    </div>
                </div>

                {/* Current Step */}
                {video.current_step && (
                    <div className="mb-4 p-4 bg-blue-50 rounded">
                        <p className="text-sm text-blue-800">
                            Current Step: <strong>{video.current_step}</strong>
                        </p>
                    </div>
                )}

                {/* Status Cards */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                    <div className="p-4 border rounded">
                        <h3 className="font-bold mb-2">Download</h3>
                        <p className={`text-sm ${
                            video.step_download_status === 'completed' ? 'text-green-600' :
                            video.step_download_status === 'processing' ? 'text-blue-600' :
                            'text-gray-600'
                        }`}>
                            {video.step_download_status}
                        </p>
                    </div>

                    <div className="p-4 border rounded">
                        <h3 className="font-bold mb-2">Transcription</h3>
                        <p className={`text-sm ${
                            video.step_transcription_status === 'completed' ? 'text-green-600' :
                            video.step_transcription_status === 'processing' ? 'text-blue-600' :
                            'text-gray-600'
                        }`}>
                            {video.step_transcription_status}
                        </p>
                    </div>

                    <div className="p-4 border rounded">
                        <h3 className="font-bold mb-2">AI Processing</h3>
                        <p className={`text-sm ${
                            video.step_ai_enhancement_status === 'completed' ? 'text-green-600' :
                            video.step_ai_enhancement_status === 'processing' ? 'text-blue-600' :
                            'text-gray-600'
                        }`}>
                            {video.step_ai_enhancement_status}
                        </p>
                    </div>
                </div>

                {/* Video Content */}
                {/* ... rest of your component */}
            </div>
        </>
    );
}
```

---

## 🔄 Option 2: Smart Polling with Inertia.js (Simpler, Good Enough)

If you don't want to set up WebSockets, Inertia.js makes polling very efficient:

**resources/js/Pages/Videos/Show.jsx:**
```jsx
import { useEffect, useState } from 'react';
import { Head, router } from '@inertiajs/react';

export default function Show({ video: initialVideo }) {
    const [video, setVideo] = useState(initialVideo);

    useEffect(() => {
        // Only poll if video is processing
        if (
            video.processing_v2_status === 'running' ||
            video.transcription_status === 'transcribing' ||
            video.ai_processing_status === 'processing'
        ) {
            const interval = setInterval(() => {
                router.reload({
                    only: ['video'],
                    preserveState: true,
                    preserveScroll: true,
                });
            }, 2000); // Poll every 2 seconds

            return () => clearInterval(interval);
        }
    }, [
        video.processing_v2_status,
        video.transcription_status,
        video.ai_processing_status,
    ]);

    // Update video when props change
    useEffect(() => {
        setVideo(initialVideo);
    }, [initialVideo]);

    return (
        <>
            <Head title={video.title || 'Video Details'} />
            {/* ... rest of component */}
        </>
    );
}
```

**Pros:**
- ✅ No WebSocket setup needed
- ✅ Works immediately
- ✅ Inertia.js handles it efficiently
- ✅ Simple to implement

**Cons:**
- ⚠️ Slight delay (2 seconds)
- ⚠️ More server requests

---

## 📊 Option 3: Server-Sent Events (SSE) - One-Way Updates

For one-way status updates (server → client):

**app/Http/Controllers/VideoController.php:**
```php
public function streamStatus(VideoDownload $video)
{
    return response()->stream(function () use ($video) {
        $lastStatus = null;
        
        while (true) {
            $video->refresh();
            
            // Only send if status changed
            if ($video->processing_v2_status !== $lastStatus) {
                echo "data: " . json_encode([
                    'status' => $video->processing_v2_status,
                    'current_step' => $video->processing_v2_current_step,
                    'progress' => $this->calculateProgress($video),
                ]) . "\n\n";
                
                $lastStatus = $video->processing_v2_status;
                
                ob_flush();
                flush();
            }
            
            // Break if processing complete
            if (in_array($video->processing_v2_status, ['completed', 'failed'])) {
                break;
            }
            
            sleep(1);
        }
    }, 200, [
        'Content-Type' => 'text/event-stream',
        'Cache-Control' => 'no-cache',
        'Connection' => 'keep-alive',
    ]);
}
```

**Frontend:**
```jsx
useEffect(() => {
    const eventSource = new EventSource(`/videos/${video.id}/stream-status`);
    
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        setVideo(prev => ({ ...prev, ...data }));
    };
    
    return () => eventSource.close();
}, [video.id]);
```

---

## 🎯 Recommendation

**For your video processing app:**

1. **Start with Option 2 (Smart Polling)** - Get it working quickly
2. **Upgrade to Option 1 (Broadcasting)** - When you need true real-time
3. **Use Redis** - Simpler than Pusher, no external service needed

**Why this order:**
- ✅ Get features working fast
- ✅ Upgrade when needed
- ✅ Less complexity initially
- ✅ Better user experience later

---

## 🚀 Quick Setup Commands

```bash
# 1. Install broadcasting (if using Pusher)
composer require pusher/pusher-php-server

# 2. Create event
php artisan make:event VideoStatusUpdated

# 3. Install frontend
npm install laravel-echo pusher-js

# 4. Configure .env
# Set BROADCAST_DRIVER=redis or pusher

# 5. Start queue worker (for jobs)
php artisan queue:work

# 6. Start Laravel WebSockets (if using Redis)
# Install: composer require beyondcode/laravel-websockets
php artisan websockets:serve
```

---

**Choose the option that fits your needs!** 🎯

