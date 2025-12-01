import { Button } from '@/components/ui/button';
import AppLayout from '@/layouts/app-layout';
import { Head, Link } from '@inertiajs/react';
import { Mic } from 'lucide-react';

export default function VoiceCloningIndex() {
    return (
        <AppLayout>
            <Head title="Voice Cloning" />

            <div className="container mx-auto px-4 py-8">
                <div className="mb-8">
                    <h1 className="mb-2 text-4xl font-bold">Voice Cloning</h1>
                    <p className="text-muted-foreground">
                        Manage and clone voices for text-to-speech synthesis
                    </p>
                </div>

                <div className="rounded-lg border bg-card p-12 text-center shadow-sm">
                    <div className="mb-4 flex justify-center">
                        <div className="flex size-16 items-center justify-center rounded-full bg-muted">
                            <Mic className="size-8 text-muted-foreground" />
                        </div>
                    </div>
                    <h2 className="mb-2 text-2xl font-semibold">
                        Voice Cloning Coming Soon
                    </h2>
                    <p className="mb-6 text-muted-foreground">
                        This feature will allow you to clone voices and use them
                        for text-to-speech synthesis.
                    </p>
                    <Link href="/dashboard">
                        <Button>Back to Dashboard</Button>
                    </Link>
                </div>
            </div>
        </AppLayout>
    );
}

