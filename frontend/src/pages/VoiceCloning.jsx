import { useState, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
    Mic,
    Upload,
    Download,
    Loader2,
    Save,
    Trash2,
    ChevronDown,
    ChevronUp,
    Settings2,
} from 'lucide-react';
import { Button, Input, Textarea, Select, AudioPlayer, LoadingSpinner } from '../components/common';
import { xttsApi } from '../api';

export function VoiceCloning() {
    const [activeTab, setActiveTab] = useState('generate'); // 'generate' or 'voices'
    const [text, setText] = useState('');
    const [language, setLanguage] = useState('en');
    const [referenceFile, setReferenceFile] = useState(null);
    const [selectedVoiceId, setSelectedVoiceId] = useState('');
    const [useExistingVoice, setUseExistingVoice] = useState(false);
    const [generatedAudioUrl, setGeneratedAudioUrl] = useState(null);
    const [showAdvanced, setShowAdvanced] = useState(false);

    // Advanced parameters
    const [speed, setSpeed] = useState(1.0);
    const [temperature, setTemperature] = useState(0.75);
    const [repetitionPenalty, setRepetitionPenalty] = useState(2.0);
    const [topK, setTopK] = useState(50);
    const [topP, setTopP] = useState(0.85);

    // Voice saving
    const [voiceName, setVoiceName] = useState('');
    const [saveVoiceAfterGen, setSaveVoiceAfterGen] = useState(false);

    // Progress tracking
    const [isGenerating, setIsGenerating] = useState(false);
    const [startTime, setStartTime] = useState(null);
    const [elapsedTime, setElapsedTime] = useState(0);

    const queryClient = useQueryClient();

    // Fetch languages
    const { data: languages = [] } = useQuery({
        queryKey: ['xtts-languages'],
        queryFn: xttsApi.getLanguages,
    });

    // Fetch saved voices
    const { data: savedVoices = [], isLoading: voicesLoading } = useQuery({
        queryKey: ['xtts-voices'],
        queryFn: xttsApi.getVoices,
    });

    // Timer effect for progress tracking
    useEffect(() => {
        let interval;
        if (isGenerating && startTime) {
            interval = setInterval(() => {
                setElapsedTime(Math.floor((Date.now() - startTime) / 1000));
            }, 1000);
        } else {
            setElapsedTime(0);
        }
        return () => clearInterval(interval);
    }, [isGenerating, startTime]);

    // Generate speech mutation
    const generateMutation = useMutation({
        mutationFn: async (formData) => {
            setIsGenerating(true);
            setStartTime(Date.now());
            return await xttsApi.generate(formData);
        },
        onSuccess: (data) => {
            setGeneratedAudioUrl(data.audio_url);
            toast.success('Audio generated successfully!');
            setIsGenerating(false);
            setStartTime(null);
        },
        onError: (error) => {
            toast.error(error.response?.data?.error || 'Failed to generate audio');
            setIsGenerating(false);
            setStartTime(null);
        },
    });

    // Save voice mutation
    const saveVoiceMutation = useMutation({
        mutationFn: async (formData) => {
            return await xttsApi.saveVoice(formData);
        },
        onSuccess: () => {
            toast.success('Voice saved successfully!');
            queryClient.invalidateQueries(['xtts-voices']);
            setVoiceName('');
            setReferenceFile(null);
        },
        onError: (error) => {
            toast.error(error.response?.data?.error || 'Failed to save voice');
        },
    });

    // Delete voice mutation
    const deleteVoiceMutation = useMutation({
        mutationFn: async (voiceId) => {
            return await xttsApi.deleteVoice(voiceId);
        },
        onSuccess: () => {
            toast.success('Voice deleted successfully!');
            queryClient.invalidateQueries(['xtts-voices']);
        },
        onError: (error) => {
            toast.error(error.response?.data?.error || 'Failed to delete voice');
        },
    });

    const handleGenerate = () => {
        if (!text.trim()) {
            toast.error('Please enter text to generate');
            return;
        }

        if (!language) {
            toast.error('Please select a language');
            return;
        }

        if (!useExistingVoice && !referenceFile) {
            toast.error('Please upload a reference audio file');
            return;
        }

        if (useExistingVoice && !selectedVoiceId) {
            toast.error('Please select a saved voice');
            return;
        }

        const formData = new FormData();
        formData.append('text', text);
        formData.append('language', language);
        formData.append('speed', speed);
        formData.append('temperature', temperature);
        formData.append('repetition_penalty', repetitionPenalty);
        formData.append('top_k', topK);
        formData.append('top_p', topP);

        if (useExistingVoice) {
            formData.append('voice_id', selectedVoiceId);
        } else {
            formData.append('reference_audio', referenceFile);
        }

        generateMutation.mutate(formData);

        // Save voice if requested
        if (!useExistingVoice && saveVoiceAfterGen && voiceName.trim() && referenceFile) {
            const voiceFormData = new FormData();
            voiceFormData.append('name', voiceName);
            voiceFormData.append('file', referenceFile);
            saveVoiceMutation.mutate(voiceFormData);
        }
    };

    const handleSaveVoice = () => {
        if (!voiceName.trim()) {
            toast.error('Please enter a voice name');
            return;
        }

        if (!referenceFile) {
            toast.error('Please upload a voice file');
            return;
        }

        const formData = new FormData();
        formData.append('name', voiceName);
        formData.append('file', referenceFile);

        saveVoiceMutation.mutate(formData);
    };

    const handleResetDefaults = () => {
        setSpeed(1.0);
        setTemperature(0.75);
        setRepetitionPenalty(2.0);
        setTopK(50);
        setTopP(0.85);
        toast.success('Settings reset to defaults');
    };

    const formatTime = (seconds) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    const languageOptions = languages && typeof languages === 'object' && !Array.isArray(languages)
        ? Object.entries(languages).map(([code, name]) => ({
            value: code,  // Use language code (e.g., 'en', 'es')
            label: name,  // Display language name (e.g., 'English', 'Spanish')
        }))
        : [];

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-gray-900 p-6">
            <div className="max-w-6xl mx-auto">
                {/* Header */}
                <div className="mb-8">
                    <h1 className="text-4xl font-bold text-white mb-2 flex items-center gap-3">
                        <Mic className="w-10 h-10 text-purple-400" />
                        Voice Cloning
                    </h1>
                    <p className="text-gray-400">
                        Generate realistic speech using XTTS v2 multilingual voice cloning
                    </p>
                </div>

                {/* Tabs */}
                <div className="flex gap-4 mb-6">
                    <button
                        onClick={() => setActiveTab('generate')}
                        className={`px-6 py-3 rounded-lg font-semibold transition-all ${activeTab === 'generate'
                            ? 'bg-purple-600 text-white shadow-lg shadow-purple-500/50'
                            : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                            }`}
                    >
                        Generate Speech
                    </button>
                    <button
                        onClick={() => setActiveTab('voices')}
                        className={`px-6 py-3 rounded-lg font-semibold transition-all ${activeTab === 'voices'
                            ? 'bg-purple-600 text-white shadow-lg shadow-purple-500/50'
                            : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                            }`}
                    >
                        Saved Voices ({savedVoices.length})
                    </button>
                </div>

                {/* Generate Tab */}
                {activeTab === 'generate' && (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {/* Input Section */}
                        <div className="bg-gray-800/50 backdrop-blur-lg rounded-xl p-6 border border-gray-700 shadow-xl">
                            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
                                <Settings2 className="w-6 h-6 text-purple-400" />
                                Configuration
                            </h2>

                            {/* Text Input */}
                            <Textarea
                                label="Text to Synthesize"
                                value={text}
                                onChange={(e) => setText(e.target.value)}
                                placeholder="Enter the text you want to convert to speech..."
                                rows={6}
                                className="mb-4"
                            />

                            {/* Language Selection */}
                            <Select
                                label="Language"
                                value={language}
                                onChange={(e) => setLanguage(e.target.value)}
                                options={languageOptions}
                                className="mb-4"
                            />

                            {/* Voice Source Toggle */}
                            <div className="mb-4">
                                <label className="flex items-center gap-2 text-gray-300 mb-3">
                                    <input
                                        type="checkbox"
                                        checked={useExistingVoice}
                                        onChange={(e) => setUseExistingVoice(e.target.checked)}
                                        className="w-4 h-4 text-purple-600 rounded focus:ring-purple-500"
                                    />
                                    <span className="font-medium">Use Saved Voice</span>
                                </label>

                                {useExistingVoice ? (
                                    <Select
                                        label="Select Voice"
                                        value={selectedVoiceId}
                                        onChange={(e) => setSelectedVoiceId(e.target.value)}
                                        options={savedVoices.map(v => ({
                                            value: v.id,
                                            label: v.name,
                                        }))}
                                        placeholder="Choose a saved voice..."
                                    />
                                ) : (
                                    <>
                                        <Input
                                            type="file"
                                            label="Reference Audio"
                                            accept="audio/*"
                                            onChange={(e) => setReferenceFile(e.target.files[0])}
                                            className="mb-3"
                                        />
                                        {referenceFile && (
                                            <div className="mt-3">
                                                <label className="flex items-center gap-2 text-gray-300 mb-2">
                                                    <input
                                                        type="checkbox"
                                                        checked={saveVoiceAfterGen}
                                                        onChange={(e) => setSaveVoiceAfterGen(e.target.checked)}
                                                        className="w-4 h-4 text-purple-600 rounded focus:ring-purple-500"
                                                    />
                                                    <span className="text-sm">Save this voice for future use</span>
                                                </label>
                                                {saveVoiceAfterGen && (
                                                    <Input
                                                        label="Voice Name"
                                                        value={voiceName}
                                                        onChange={(e) => setVoiceName(e.target.value)}
                                                        placeholder="e.g., Trump, Obama, etc."
                                                    />
                                                )}
                                            </div>
                                        )}
                                    </>
                                )}
                            </div>

                            {/* Advanced Settings */}
                            <div className="mb-4">
                                <div className="flex items-center justify-between mb-3">
                                    <button
                                        onClick={() => setShowAdvanced(!showAdvanced)}
                                        className="flex items-center gap-2 text-purple-400 hover:text-purple-300 font-medium"
                                    >
                                        {showAdvanced ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                                        Advanced Settings
                                    </button>

                                    {showAdvanced && (
                                        <button
                                            onClick={handleResetDefaults}
                                            className="text-xs text-gray-400 hover:text-white underline"
                                        >
                                            Reset to Defaults
                                        </button>
                                    )}
                                </div>

                                {showAdvanced && (
                                    <div className="space-y-3 pl-4 border-l-2 border-purple-500/30">
                                        <div>
                                            <label className="block text-sm text-gray-400 mb-1">
                                                Speed: {speed}x
                                            </label>
                                            <input
                                                type="range"
                                                min="0.5"
                                                max="2.0"
                                                step="0.1"
                                                value={speed}
                                                onChange={(e) => setSpeed(parseFloat(e.target.value))}
                                                className="w-full"
                                            />
                                        </div>

                                        <div>
                                            <label className="block text-sm text-gray-400 mb-1">
                                                Temperature: {temperature}
                                            </label>
                                            <input
                                                type="range"
                                                min="0.1"
                                                max="1.0"
                                                step="0.05"
                                                value={temperature}
                                                onChange={(e) => setTemperature(parseFloat(e.target.value))}
                                                className="w-full"
                                            />
                                        </div>

                                        <div>
                                            <label className="block text-sm text-gray-400 mb-1">
                                                Repetition Penalty: {repetitionPenalty}
                                            </label>
                                            <input
                                                type="range"
                                                min="1.0"
                                                max="10.0"
                                                step="0.5"
                                                value={repetitionPenalty}
                                                onChange={(e) => setRepetitionPenalty(parseFloat(e.target.value))}
                                                className="w-full"
                                            />
                                        </div>

                                        <div>
                                            <label className="block text-sm text-gray-400 mb-1">
                                                Top K: {topK}
                                            </label>
                                            <input
                                                type="range"
                                                min="10"
                                                max="100"
                                                step="5"
                                                value={topK}
                                                onChange={(e) => setTopK(parseInt(e.target.value))}
                                                className="w-full"
                                            />
                                        </div>

                                        <div>
                                            <label className="block text-sm text-gray-400 mb-1">
                                                Top P: {topP}
                                            </label>
                                            <input
                                                type="range"
                                                min="0.5"
                                                max="1.0"
                                                step="0.05"
                                                value={topP}
                                                onChange={(e) => setTopP(parseFloat(e.target.value))}
                                                className="w-full"
                                            />
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Progress Indicator */}
                            {isGenerating && (
                                <div className="mb-4 p-4 bg-purple-900/30 border border-purple-500/50 rounded-lg">
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="text-purple-300 font-medium">Generating...</span>
                                        <span className="text-purple-400 text-sm">{formatTime(elapsedTime)} elapsed</span>
                                    </div>
                                    <div className="w-full bg-gray-700 rounded-full h-2">
                                        <div className="bg-purple-500 h-2 rounded-full animate-pulse" style={{ width: '100%' }}></div>
                                    </div>
                                </div>
                            )}

                            {/* Generate Button */}
                            <Button
                                onClick={handleGenerate}
                                disabled={isGenerating}
                                className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {isGenerating ? (
                                    <>
                                        <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                                        Generating...
                                    </>
                                ) : (
                                    <>
                                        <Mic className="w-5 h-5 mr-2" />
                                        Generate Speech
                                    </>
                                )}
                            </Button>
                        </div>

                        {/* Output Section */}
                        <div className="bg-gray-800/50 backdrop-blur-lg rounded-xl p-6 border border-gray-700 shadow-xl">
                            <h2 className="text-2xl font-bold text-white mb-6">Generated Audio</h2>

                            {generatedAudioUrl ? (
                                <div className="space-y-4">
                                    <AudioPlayer src={generatedAudioUrl} />
                                    <a
                                        href={generatedAudioUrl}
                                        download
                                        className="flex items-center justify-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
                                    >
                                        <Download className="w-5 h-5" />
                                        Download Audio
                                    </a>
                                </div>
                            ) : (
                                <div className="flex flex-col items-center justify-center h-64 text-gray-500">
                                    <Mic className="w-16 h-16 mb-4 opacity-30" />
                                    <p className="text-center">
                                        Generated audio will appear here
                                    </p>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* Saved Voices Tab */}
                {activeTab === 'voices' && (
                    <div className="bg-gray-800/50 backdrop-blur-lg rounded-xl p-6 border border-gray-700 shadow-xl">
                        <h2 className="text-2xl font-bold text-white mb-6">Manage Saved Voices</h2>

                        {/* Save New Voice Section */}
                        <div className="mb-8 p-4 bg-gray-900/50 rounded-lg border border-gray-700">
                            <h3 className="text-lg font-semibold text-white mb-4">Save New Voice</h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <Input
                                    label="Voice Name"
                                    value={voiceName}
                                    onChange={(e) => setVoiceName(e.target.value)}
                                    placeholder="e.g., Trump, Morgan Freeman, etc."
                                />
                                <Input
                                    type="file"
                                    label="Voice File"
                                    accept="audio/*"
                                    onChange={(e) => setReferenceFile(e.target.files[0])}
                                />
                            </div>
                            <Button
                                onClick={handleSaveVoice}
                                disabled={saveVoiceMutation.isPending}
                                className="mt-4 bg-purple-600 hover:bg-purple-700"
                            >
                                {saveVoiceMutation.isPending ? (
                                    <>
                                        <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                                        Saving...
                                    </>
                                ) : (
                                    <>
                                        <Save className="w-5 h-5 mr-2" />
                                        Save Voice
                                    </>
                                )}
                            </Button>
                        </div>

                        {/* Saved Voices List */}
                        <div>
                            <h3 className="text-lg font-semibold text-white mb-4">Your Saved Voices</h3>
                            {voicesLoading ? (
                                <div className="flex justify-center py-8">
                                    <LoadingSpinner />
                                </div>
                            ) : savedVoices.length === 0 ? (
                                <div className="text-center py-12 text-gray-500">
                                    <Mic className="w-16 h-16 mx-auto mb-4 opacity-30" />
                                    <p>No saved voices yet. Save a voice to get started!</p>
                                </div>
                            ) : (
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                    {savedVoices.map((voice) => (
                                        <div
                                            key={voice.id}
                                            className="p-4 bg-gray-900/50 rounded-lg border border-gray-700 hover:border-purple-500 transition-colors"
                                        >
                                            <div className="flex items-start justify-between mb-3">
                                                <div className="flex-1">
                                                    <h4 className="text-white font-semibold mb-1">{voice.name}</h4>
                                                    <p className="text-gray-400 text-sm">
                                                        {new Date(voice.created_at).toLocaleDateString()}
                                                    </p>
                                                </div>
                                                <button
                                                    onClick={() => deleteVoiceMutation.mutate(voice.id)}
                                                    className="text-red-400 hover:text-red-300 transition-colors"
                                                    title="Delete voice"
                                                >
                                                    <Trash2 className="w-5 h-5" />
                                                </button>
                                            </div>
                                            <audio
                                                controls
                                                src={voice.file}
                                                className="w-full mt-2"
                                                style={{ height: '40px' }}
                                            />
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
