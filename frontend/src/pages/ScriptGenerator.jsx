import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
    FileText,
    Bot,
    Sparkles,
    Copy,
    Check,
    RefreshCw,
    MessageSquare,
    Tag,
    ChevronDown,
    ChevronUp
} from 'lucide-react';
import { showSuccess, showError } from '../utils/alerts';
import { videosApi, settingsApi } from '../api';
import { scriptGeneratorApi } from '../api/scriptGenerator';
import { Button, Card, LoadingSpinner, Select } from '../components/common';

export function ScriptGenerator() {
    const [selectedVideos, setSelectedVideos] = useState([]);
    const [selectedProvider, setSelectedProvider] = useState('gemini');
    const [prompt, setPrompt] = useState('');
    const [generatedScript, setGeneratedScript] = useState('');
    const [isCopied, setIsCopied] = useState(false);
    const [expandedVideos, setExpandedVideos] = useState([]);

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
            showSuccess('Script Generated', 'Script generated successfully!', { timer: 3000 });
        },
        onError: (error) => {
            showError('Generation Failed', error.response?.data?.error || 'Failed to generate script. Please try again.');
        },
    });

    const handleGenerate = () => {
        if (!prompt.trim()) {
            showError('Prompt Required', 'Please enter a prompt to generate the script.');
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
        showSuccess('Copied', 'Text copied to clipboard.', { timer: 2000 });
        setTimeout(() => setIsCopied(false), 2000);
    };

    const toggleVideoSelection = (videoId) => {
        setSelectedVideos(prev =>
            prev.includes(videoId)
                ? prev.filter(id => id !== videoId)
                : [...prev, videoId]
        );
    };

    const toggleVideoExpand = (videoId, e) => {
        e.stopPropagation();
        setExpandedVideos(prev =>
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
                            <div className="space-y-3 max-h-[600px] overflow-y-auto pr-2 custom-scrollbar">
                                {videos?.map(video => {
                                    const isExpanded = expandedVideos.includes(video.id);
                                    const isSelected = selectedVideos.includes(video.id);
                                    
                                    return (
                                        <div
                                            key={video.id}
                                            className={`rounded-lg border transition-all ${isSelected
                                                    ? 'bg-[var(--rednote-primary)]/10 border-[var(--rednote-primary)]'
                                                    : 'bg-white/5 border-white/10 hover:bg-white/10'
                                                }`}
                                        >
                                            {/* Video Header */}
                                            <div
                                                onClick={() => toggleVideoSelection(video.id)}
                                                className="p-4 cursor-pointer flex items-start gap-3"
                                            >
                                                {/* Checkbox */}
                                                <div className={`mt-1 w-5 h-5 rounded border flex items-center justify-center flex-shrink-0 ${isSelected
                                                        ? 'bg-[var(--rednote-primary)] border-[var(--rednote-primary)]'
                                                        : 'border-gray-500'
                                                    }`}>
                                                    {isSelected && <Check className="w-3 h-3 text-white" />}
                                                </div>

                                                {/* Video Thumbnail */}
                                                {video.cover_url && (
                                                    <div className="w-24 h-16 rounded overflow-hidden flex-shrink-0">
                                                        <img
                                                            src={video.cover_url}
                                                            alt={video.title}
                                                            className="w-full h-full object-cover"
                                                        />
                                                    </div>
                                                )}

                                                {/* Video Info */}
                                                <div className="flex-1 min-w-0">
                                                    <p className="font-medium line-clamp-2">{video.title || 'Untitled Video'}</p>
                                                    <p className="text-xs text-gray-400 line-clamp-1 mt-1">{video.original_title}</p>
                                                    
                                                    {/* Status Badges */}
                                                    <div className="flex gap-2 mt-2 flex-wrap">
                                                        {video.transcription_status === 'transcribed' && (
                                                            <span className="text-xs px-2 py-1 rounded bg-green-500/20 text-green-400">
                                                                Transcribed
                                                            </span>
                                                        )}
                                                        {video.ai_processing_status === 'processed' && (
                                                            <span className="text-xs px-2 py-1 rounded bg-blue-500/20 text-blue-400">
                                                                AI Processed
                                                            </span>
                                                        )}
                                                    </div>
                                                </div>

                                                {/* Expand Button */}
                                                <button
                                                    onClick={(e) => toggleVideoExpand(video.id, e)}
                                                    className="flex-shrink-0 p-1 hover:bg-white/10 rounded transition-colors"
                                                >
                                                    {isExpanded ? (
                                                        <ChevronUp className="w-5 h-5 text-gray-400" />
                                                    ) : (
                                                        <ChevronDown className="w-5 h-5 text-gray-400" />
                                                    )}
                                                </button>
                                            </div>

                                            {/* Expanded Content */}
                                            {isExpanded && (
                                                <div className="px-4 pb-4 space-y-3 border-t border-white/10 pt-3">
                                                    {/* Description */}
                                                    {video.description && (
                                                        <div>
                                                            <h4 className="text-xs font-semibold text-gray-400 mb-1 flex items-center gap-1">
                                                                <FileText className="w-3 h-3" />
                                                                Description
                                                            </h4>
                                                            <p className="text-sm text-gray-300 line-clamp-3">{video.description}</p>
                                                        </div>
                                                    )}

                                                    {/* AI Summary */}
                                                    {video.ai_summary && (
                                                        <div>
                                                            <h4 className="text-xs font-semibold text-gray-400 mb-1 flex items-center gap-1">
                                                                <Bot className="w-3 h-3" />
                                                                AI Summary (English)
                                                            </h4>
                                                            <p className="text-sm text-gray-300 line-clamp-4">{video.ai_summary}</p>
                                                        </div>
                                                    )}

                                                    {/* Transcript Preview */}
                                                    {video.transcript && (
                                                        <div>
                                                            <h4 className="text-xs font-semibold text-gray-400 mb-1 flex items-center gap-1">
                                                                <MessageSquare className="w-3 h-3" />
                                                                Transcript
                                                            </h4>
                                                            <p className="text-sm text-gray-300 line-clamp-3">{video.transcript}</p>
                                                        </div>
                                                    )}

                                                    {/* Tags */}
                                                    {video.ai_tags && (
                                                        <div>
                                                            <h4 className="text-xs font-semibold text-gray-400 mb-1 flex items-center gap-1">
                                                                <Tag className="w-3 h-3" />
                                                                Tags
                                                            </h4>
                                                            <div className="flex flex-wrap gap-1">
                                                                {video.ai_tags.split(',').map((tag, idx) => (
                                                                    <span
                                                                        key={idx}
                                                                        className="text-xs px-2 py-1 rounded bg-[var(--rednote-primary)]/20 text-[var(--rednote-primary)]"
                                                                    >
                                                                        {tag.trim()}
                                                                    </span>
                                                                ))}
                                                            </div>
                                                        </div>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}

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
