import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
    FileText,
    Bot,
    Sparkles,
    Copy,
    Check,
    RefreshCw,
    MessageSquare
} from 'lucide-react';
import toast from 'react-hot-toast';
import { videosApi, settingsApi } from '../api';
import { scriptGeneratorApi } from '../api/scriptGenerator';
import { Button, Card, LoadingSpinner, Select } from '../components/common';

export function ScriptGenerator() {
    const [selectedVideos, setSelectedVideos] = useState([]);
    const [selectedProvider, setSelectedProvider] = useState('gemini');
    const [prompt, setPrompt] = useState('');
    const [generatedScript, setGeneratedScript] = useState('');
    const [isCopied, setIsCopied] = useState(false);

    // Fetch videos
    const { data: videos, isLoading: isLoadingVideos } = useQuery({
        queryKey: ['videos'],
        queryFn: videosApi.getAll,
    });

    // Fetch AI settings to get available provider (optional, can default to gemini)
    const { data: aiSettings } = useQuery({
        queryKey: ['aiSettings'],
        queryFn: settingsApi.get,
    });

    // Generate script mutation
    const generateMutation = useMutation({
        mutationFn: scriptGeneratorApi.generate,
        onSuccess: (data) => {
            setGeneratedScript(data.script);
            toast.success('Script generated successfully!');
        },
        onError: (error) => {
            toast.error(error.response?.data?.error || 'Failed to generate script');
        },
    });

    const handleGenerate = () => {
        if (!prompt.trim()) {
            toast.error('Please enter a prompt');
            return;
        }

        generateMutation.mutate({
            video_ids: selectedVideos,
            prompt: prompt,
            provider: selectedProvider
        });
    };

    const handleCopy = () => {
        navigator.clipboard.writeText(generatedScript);
        setIsCopied(true);
        toast.success('Copied to clipboard');
        setTimeout(() => setIsCopied(false), 2000);
    };

    const toggleVideoSelection = (videoId) => {
        setSelectedVideos(prev =>
            prev.includes(videoId)
                ? prev.filter(id => id !== videoId)
                : [...prev, videoId]
        );
    };

    const providerOptions = [
        { value: 'gemini', label: 'Google Gemini' },
        { value: 'openai', label: 'OpenAI GPT-4' },
        { value: 'anthropic', label: 'Anthropic Claude' },
    ];

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold">Script Generator</h1>
                    <p className="text-gray-400">Generate creative scripts from your videos using AI</p>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Left Panel: Inputs */}
                <div className="space-y-6">
                    {/* Video Selection */}
                    <Card className="p-6">
                        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                            <FileText className="w-5 h-5 text-[var(--rednote-primary)]" />
                            Select Context Videos
                        </h2>

                        {isLoadingVideos ? (
                            <div className="flex justify-center py-8">
                                <LoadingSpinner />
                            </div>
                        ) : (
                            <div className="space-y-2 max-h-60 overflow-y-auto pr-2 custom-scrollbar">
                                {videos?.map(video => (
                                    <div
                                        key={video.id}
                                        onClick={() => toggleVideoSelection(video.id)}
                                        className={`p-3 rounded-lg border cursor-pointer transition-all flex items-center gap-3 ${selectedVideos.includes(video.id)
                                                ? 'bg-[var(--rednote-primary)]/10 border-[var(--rednote-primary)]'
                                                : 'bg-white/5 border-white/10 hover:bg-white/10'
                                            }`}
                                    >
                                        <div className={`w-5 h-5 rounded border flex items-center justify-center ${selectedVideos.includes(video.id)
                                                ? 'bg-[var(--rednote-primary)] border-[var(--rednote-primary)]'
                                                : 'border-gray-500'
                                            }`}>
                                            {selectedVideos.includes(video.id) && <Check className="w-3 h-3 text-white" />}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="font-medium truncate">{video.title || 'Untitled Video'}</p>
                                            <p className="text-xs text-gray-400 truncate">{video.original_title}</p>
                                        </div>
                                    </div>
                                ))}

                                {videos?.length === 0 && (
                                    <p className="text-center text-gray-400 py-4">No videos available</p>
                                )}
                            </div>
                        )}
                        <p className="text-xs text-gray-500 mt-2">
                            Selected: {selectedVideos.length} videos
                        </p>
                    </Card>

                    {/* Model & Prompt */}
                    <Card className="p-6 space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-400 mb-2">
                                AI Model
                            </label>
                            <Select
                                options={providerOptions}
                                value={selectedProvider}
                                onChange={(e) => setSelectedProvider(e.target.value)}
                                className="w-full"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-400 mb-2">
                                Prompt
                            </label>
                            <div className="relative">
                                <textarea
                                    value={prompt}
                                    onChange={(e) => setPrompt(e.target.value)}
                                    placeholder="e.g., Write a 60-second Instagram Reel script summarizing these videos. Include a hook, 3 main points, and a call to action."
                                    className="w-full h-40 bg-black/20 border border-white/10 rounded-lg p-4 text-sm focus:border-[var(--rednote-primary)] focus:ring-1 focus:ring-[var(--rednote-primary)] transition-colors resize-none"
                                />
                                <Bot className="absolute bottom-4 right-4 w-5 h-5 text-gray-500" />
                            </div>
                        </div>

                        <Button
                            fullWidth
                            size="lg"
                            onClick={handleGenerate}
                            loading={generateMutation.isPending}
                            icon={Sparkles}
                            disabled={!prompt.trim()}
                        >
                            Generate Script
                        </Button>
                    </Card>
                </div>

                {/* Right Panel: Output */}
                <div className="h-full">
                    <Card className="h-full flex flex-col p-6 min-h-[600px]">
                        <div className="flex items-center justify-between mb-4">
                            <h2 className="text-lg font-semibold flex items-center gap-2">
                                <MessageSquare className="w-5 h-5 text-[var(--rednote-primary)]" />
                                Generated Script
                            </h2>

                            {generatedScript && (
                                <Button
                                    size="sm"
                                    variant="ghost"
                                    icon={isCopied ? Check : Copy}
                                    onClick={handleCopy}
                                >
                                    {isCopied ? 'Copied' : 'Copy'}
                                </Button>
                            )}
                        </div>

                        <div className="flex-1 bg-black/20 rounded-lg border border-white/10 p-6 overflow-y-auto custom-scrollbar">
                            {generatedScript ? (
                                <div className="prose prose-invert max-w-none whitespace-pre-wrap">
                                    {generatedScript}
                                </div>
                            ) : (
                                <div className="h-full flex flex-col items-center justify-center text-gray-500 opacity-50">
                                    <Bot className="w-16 h-16 mb-4" />
                                    <p className="text-lg">Ready to generate</p>
                                    <p className="text-sm">Select videos and enter a prompt to start</p>
                                </div>
                            )}
                        </div>
                    </Card>
                </div>
            </div>
        </div>
    );
}

export default ScriptGenerator;
