import { Button } from '@/components/ui/button';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import {
    Facebook,
    Instagram,
    Link as LinkIcon,
    Upload,
    Video,
    Youtube,
} from 'lucide-react';
import { useState } from 'react';
import { router } from '@inertiajs/react';

interface VideoSource {
    id: string;
    name: string;
    icon: typeof Video;
    description?: string;
}

const videoSources: VideoSource[] = [
    {
        id: 'xiaohongshu',
        name: 'RedNote/Xiaohongshu',
        icon: Video,
        description: 'Extract videos from Xiaohongshu',
    },
    {
        id: 'youtube',
        name: 'YouTube',
        icon: Youtube,
        description: 'Download videos from YouTube',
    },
    {
        id: 'facebook',
        name: 'Facebook',
        icon: Facebook,
        description: 'Extract videos from Facebook',
    },
    {
        id: 'instagram',
        name: 'Instagram',
        icon: Instagram,
        description: 'Download videos from Instagram',
    },
    {
        id: 'vimeo',
        name: 'Vimeo',
        icon: Video,
        description: 'Download videos from Vimeo',
    },
    {
        id: 'local',
        name: 'Local Upload',
        icon: Upload,
        description: 'Upload video from your device',
    },
];

interface AddVideoModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export default function AddVideoModal({
    isOpen,
    onClose,
}: AddVideoModalProps) {
    const [selectedSource, setSelectedSource] = useState<string>('xiaohongshu');

    const handleExtract = () => {
        onClose();
        // Navigate to extract page with selected source
        router.visit(`/videos/extract?source=${selectedSource}`, {
            preserveState: false,
        });
    };

    return (
        <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
            <DialogContent className="sm:max-w-2xl">
                <DialogHeader>
                    <DialogTitle>Add New Video</DialogTitle>
                    <DialogDescription>Select Video Source</DialogDescription>
                </DialogHeader>

                <div className="grid grid-cols-2 gap-3 py-4">
                    {videoSources.map((source) => {
                        const Icon = source.icon;
                        const isSelected = selectedSource === source.id;

                        return (
                            <button
                                key={source.id}
                                type="button"
                                onClick={() => setSelectedSource(source.id)}
                                className={`relative flex flex-col items-center justify-center gap-2 rounded-lg border-2 p-4 transition-all hover:bg-accent ${
                                    isSelected
                                        ? 'border-primary bg-primary/5'
                                        : 'border-border'
                                }`}
                            >
                                {isSelected && (
                                    <div className="absolute left-2 top-2 size-2 rounded-full bg-red-600" />
                                )}
                                <Icon className="size-6" />
                                <span className="text-sm font-medium">
                                    {source.name}
                                </span>
                            </button>
                        );
                    })}
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={onClose}>
                        Cancel
                    </Button>
                    <Button
                        onClick={handleExtract}
                        className="bg-red-600 hover:bg-red-700 text-white"
                    >
                        <LinkIcon className="mr-2 size-4" />
                        Extract Video
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

