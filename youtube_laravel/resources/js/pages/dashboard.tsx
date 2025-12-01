import AddVideoModal from '@/components/add-video-modal';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import AppLayout from '@/layouts/app-layout';
import { Head, Link, router } from '@inertiajs/react';
import {
    Brain,
    CheckCircle2,
    Download,
    Eye,
    FileText,
    MessageSquare,
    RefreshCw,
    Settings,
    Trash2,
    Video,
    Volume2,
    XCircle,
} from 'lucide-react';
import { useState } from 'react';

interface Stats {
    total_videos: number;
    successful_videos: number;
    failed_videos: number;
    pending_videos: number;
    downloaded_videos?: number;
    transcribed_videos: number;
    transcribing_videos: number;
    ai_processed_videos: number;
    ai_processing_videos: number;
    prompts_generated?: number;
    tts_completed_videos: number;
    final_processed_videos: number;
    recent_videos: Array<{
        id: number;
        title: string | null;
        cover_url: string | null;
        status: string;
        transcription_status: string;
        ai_processing_status: string;
        is_downloaded: boolean;
        audio_prompt_status: string | null;
        step_tts_synthesis_status: string | null;
        step_script_generation_status: string | null;
        created_at: string;
    }>;
}

export default function Dashboard({ stats }: { stats: Stats }) {
    const [selectedVideos, setSelectedVideos] = useState<number[]>([]);
    const [isAddVideoModalOpen, setIsAddVideoModalOpen] = useState(false);

    const handleSelectAll = () => {
        if (selectedVideos.length === stats.recent_videos.length) {
            setSelectedVideos([]);
        } else {
            setSelectedVideos(stats.recent_videos.map((v) => v.id));
        }
    };

    const handleReprocess = (videoId: number) => {
        router.post(`/videos/${videoId}/reprocess`, {}, {
            preserveScroll: true,
        });
    };

    const handleDelete = (videoId: number) => {
        if (confirm('Are you sure you want to delete this video?')) {
            router.delete(`/videos/${videoId}`, {
                preserveScroll: true,
            });
        }
    };

    return (
        <AppLayout>
            <Head title="Dashboard" />

            <div className="container mx-auto px-4 py-8">
                <div className="mb-8 flex items-center justify-between">
                    <div>
                        <h1 className="mb-2 text-4xl font-bold">Dashboard</h1>
                        <p className="text-muted-foreground">
                            Overview of your RedNote video collection
                        </p>
                    </div>
                    <div className="flex items-center gap-3">
                        <Link href="/app-settings">
                            <Button variant="outline" size="icon">
                                <Settings className="size-4" />
                            </Button>
                        </Link>
                        <Button
                            size="lg"
                            className="gap-2 bg-red-600 hover:bg-red-700 text-white"
                            onClick={() => setIsAddVideoModalOpen(true)}
                        >
                            <Video className="size-4" />
                            + Add Video
                        </Button>
                    </div>
                </div>

                <AddVideoModal
                    isOpen={isAddVideoModalOpen}
                    onClose={() => setIsAddVideoModalOpen(false)}
                />

                {/* Dashboard Statistics */}
                <div className="mb-8">
                    <h2 className="mb-4 text-xl font-bold">Dashboard Statistics</h2>
                    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
                        {/* Total Videos */}
                        <div className="rounded-lg border bg-card p-6 shadow-sm">
                            <div className="mb-2 flex items-center gap-2">
                                <Video className="size-5 text-red-600 dark:text-red-500" />
                            </div>
                            <p className="text-3xl font-bold">
                                {stats.total_videos}
                            </p>
                            <p className="text-sm text-muted-foreground">Total Videos</p>
                        </div>

                        {/* Successful */}
                        <div className="rounded-lg border bg-card p-6 shadow-sm">
                            <div className="mb-2 flex items-center gap-2">
                                <CheckCircle2 className="size-5 text-green-600 dark:text-green-500" />
                            </div>
                            <p className="text-3xl font-bold text-green-600 dark:text-green-500">
                                {stats.successful_videos}
                            </p>
                            <p className="text-sm text-muted-foreground">Successful</p>
                        </div>

                        {/* Downloaded */}
                        <div className="rounded-lg border bg-card p-6 shadow-sm">
                            <div className="mb-2 flex items-center gap-2">
                                <Download className="size-5 text-blue-600 dark:text-blue-500" />
                            </div>
                            <p className="text-3xl font-bold text-blue-600 dark:text-blue-500">
                                {stats.downloaded_videos || 0}
                            </p>
                            <p className="text-sm text-muted-foreground">Downloaded</p>
                        </div>

                        {/* AI Processed */}
                        <div className="rounded-lg border bg-card p-6 shadow-sm">
                            <div className="mb-2 flex items-center gap-2">
                                <Brain className="size-5 text-orange-600 dark:text-orange-500" />
                            </div>
                            <p className="text-3xl font-bold text-orange-600 dark:text-orange-500">
                                {stats.ai_processed_videos}
                            </p>
                            <p className="text-sm text-muted-foreground">AI Processed</p>
                        </div>

                        {/* Prompts Generated */}
                        <div className="rounded-lg border bg-card p-6 shadow-sm">
                            <div className="mb-2 flex items-center gap-2">
                                <MessageSquare className="size-5 text-purple-600 dark:text-purple-500" />
                            </div>
                            <p className="text-3xl font-bold text-purple-600 dark:text-purple-500">
                                {stats.prompts_generated || 0}
                            </p>
                            <p className="text-sm text-muted-foreground">Prompts Generated</p>
                        </div>

                        {/* Synthesized */}
                        <div className="rounded-lg border bg-card p-6 shadow-sm">
                            <div className="mb-2 flex items-center gap-2">
                                <Volume2 className="size-5 text-green-600 dark:text-green-500" />
                            </div>
                            <p className="text-3xl font-bold text-green-600 dark:text-green-500">
                                {stats.tts_completed_videos}
                            </p>
                            <p className="text-sm text-muted-foreground">Synthesized</p>
                        </div>

                        {/* Transcribed */}
                        <div className="rounded-lg border bg-card p-6 shadow-sm">
                            <div className="mb-2 flex items-center gap-2">
                                <FileText className="size-5 text-purple-600 dark:text-purple-500" />
                            </div>
                            <p className="text-3xl font-bold text-purple-600 dark:text-purple-500">
                                {stats.transcribed_videos}
                            </p>
                            <p className="text-sm text-muted-foreground">Transcribed</p>
                        </div>

                        {/* Failed */}
                        <div className="rounded-lg border bg-card p-6 shadow-sm">
                            <div className="mb-2 flex items-center gap-2">
                                <XCircle className="size-5 text-red-600 dark:text-red-500" />
                            </div>
                            <p className="text-3xl font-bold text-red-600 dark:text-red-500">
                                {stats.failed_videos}
                            </p>
                            <p className="text-sm text-muted-foreground">Failed</p>
                        </div>
                    </div>
                </div>

                {/* Recent Videos */}
                <div className="rounded-lg border bg-card p-6 shadow-sm">
                    <div className="mb-4 flex items-center justify-between">
                        <h2 className="text-xl font-bold">
                            Recent Videos <span className="text-sm font-normal text-muted-foreground">({stats.recent_videos.length} videos)</span>
                        </h2>
                    </div>
                    {stats.recent_videos.length > 0 ? (
                        <>
                            <div className="mb-4 flex items-center gap-2">
                                <input
                                    type="checkbox"
                                    checked={selectedVideos.length === stats.recent_videos.length && stats.recent_videos.length > 0}
                                    onChange={handleSelectAll}
                                    className="rounded"
                                />
                                <label className="text-sm text-muted-foreground">
                                    Select All ({stats.recent_videos.length} videos)
                                </label>
                            </div>
                            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                                {stats.recent_videos.map((video) => {
                                    const isSelected = selectedVideos.includes(video.id);
                                    const statusBadges = [];
                                    
                                    if (video.status === 'success') {
                                        statusBadges.push({ label: 'Success', variant: 'default' as const, color: 'bg-green-500' });
                                    }
                                    if (video.transcription_status === 'transcribed') {
                                        statusBadges.push({ label: 'Transcribed', variant: 'default' as const, color: 'bg-blue-500' });
                                    }
                                    if (video.ai_processing_status === 'processed') {
                                        statusBadges.push({ label: 'Processed', variant: 'default' as const, color: 'bg-purple-500' });
                                    }
                                    if (video.step_script_generation_status === 'completed') {
                                        statusBadges.push({ label: 'Script', variant: 'default' as const, color: 'bg-cyan-500' });
                                    }
                                    if (video.is_downloaded) {
                                        statusBadges.push({ label: 'Downloaded', variant: 'default' as const, color: 'bg-green-500' });
                                    }

                                    return (
                                        <div
                                            key={video.id}
                                            className={`rounded-lg border bg-card p-4 shadow-sm transition hover:shadow-md ${
                                                isSelected ? 'ring-2 ring-primary' : ''
                                            }`}
                                        >
                                            <div className="flex items-start gap-3">
                                                <input
                                                    type="checkbox"
                                                    checked={isSelected}
                                                    onChange={(e) => {
                                                        if (e.target.checked) {
                                                            setSelectedVideos([...selectedVideos, video.id]);
                                                        } else {
                                                            setSelectedVideos(selectedVideos.filter((id) => id !== video.id));
                                                        }
                                                    }}
                                                    className="mt-1 rounded"
                                                    onClick={(e) => e.stopPropagation()}
                                                />
                                                {video.cover_url && (
                                                    <img
                                                        src={video.cover_url}
                                                        alt={video.title || 'Video cover'}
                                                        className="h-20 w-32 rounded object-cover"
                                                    />
                                                )}
                                                <div className="flex-1">
                                                    <h3 className="mb-2 text-base font-semibold">
                                                        {video.title || 'Untitled'}
                                                    </h3>
                                                    <div className="mb-2 flex flex-wrap gap-1">
                                                        {statusBadges.map((badge, idx) => (
                                                            <Badge
                                                                key={idx}
                                                                variant={badge.variant}
                                                                className={`${badge.color} text-white`}
                                                            >
                                                                {badge.label}
                                                            </Badge>
                                                        ))}
                                                    </div>
                                                    <p className="mb-3 text-xs text-muted-foreground">
                                                        {video.created_at}
                                                    </p>
                                                    <div className="flex items-center gap-2">
                                                        <Button
                                                            variant="outline"
                                                            size="sm"
                                                            onClick={() => handleReprocess(video.id)}
                                                            className="gap-1"
                                                        >
                                                            <RefreshCw className="size-3" />
                                                            Reprocess
                                                        </Button>
                                                        <Link href={`/videos/${video.id}`}>
                                                            <Button variant="ghost" size="icon" className="h-8 w-8">
                                                                <Eye className="size-4" />
                                                            </Button>
                                                        </Link>
                                                        <Button
                                                            variant="ghost"
                                                            size="icon"
                                                            className="h-8 w-8 text-destructive hover:text-destructive"
                                                            onClick={() => handleDelete(video.id)}
                                                        >
                                                            <Trash2 className="size-4" />
                                                        </Button>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </>
                    ) : (
                        <div className="py-12 text-center">
                            <p className="mb-2 text-muted-foreground">
                                No videos found
                            </p>
                            <p className="mb-4 text-sm text-muted-foreground">
                                Click "Add Video" to extract your first video from
                                Xiaohongshu
                            </p>
                        </div>
                    )}
                </div>
            </div>
        </AppLayout>
    );
}
