import { useState, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
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
    Edit,
    Star,
    StarOff,
} from 'lucide-react';
import { Button, Input, Textarea, Select, AudioPlayer, LoadingSpinner } from '../components/common';
import { xttsApi } from '../api';
import { showSuccess, showError, showWarning, showLoading, closeAlert } from '../utils/alerts';

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
    
    // Voice editing
    const [editingVoice, setEditingVoice] = useState(null);
    const [editVoiceName, setEditVoiceName] = useState('');
    const [editVoiceFile, setEditVoiceFile] = useState(null);

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

    // Fetch saved voices - sort with default first
    const { data: savedVoicesRaw = [], isLoading: voicesLoading, error: voicesError } = useQuery({
        queryKey: ['xtts-voices'],
        queryFn: xttsApi.getVoices,
        retry: false,
    });
    
    // Sort voices: default first, then by creation date
    const savedVoices = savedVoicesRaw ? [...savedVoicesRaw].sort((a, b) => {
        if (a.is_default && !b.is_default) return -1;
        if (!a.is_default && b.is_default) return 1;
        return new Date(b.created_at) - new Date(a.created_at);
    }) : [];
    
    // Check if TTS service is unavailable
    const [ttsUnavailable, setTtsUnavailable] = useState(false);

    // Generate speech mutation - must be declared before useEffect that uses it
    const generateMutation = useMutation({
        mutationFn: async (formData) => {
            setIsGenerating(true);
            setStartTime(Date.now());
            showLoading('Generating Audio', 'Please wait while we generate your audio...');
            return await xttsApi.generate(formData);
        },
        onSuccess: (data) => {
            closeAlert();
            setGeneratedAudioUrl(data.audio_url);
            showSuccess('Success!', 'Audio generated successfully!');
            setIsGenerating(false);
            setStartTime(null);
        },
        onError: (error) => {
            closeAlert();
            // Extract error message properly
            let errorMessage = 'Failed to generate audio';
            let errorTitle = 'Generation Failed';
            
            if (error.response?.data?.error) {
                errorMessage = error.response.data.error;
            } else if (error.data?.error) {
                errorMessage = error.data.error;
            } else if (error.message) {
                errorMessage = error.message;
            }
            
            // Special handling for service unavailable
            if (error.status === 503) {
                errorTitle = 'Service Unavailable';
                showError(
                    errorTitle,
                    errorMessage,
                    { width: 600, confirmButtonText: 'Understood' }
                );
            } else {
                showError(errorTitle, errorMessage);
            }
            
            setIsGenerating(false);
            setStartTime(null);
        },
    });

    // Check for TTS unavailability after mutation is declared
    useEffect(() => {
        // Check if we got a 503 error from generate mutation
        if (generateMutation.error?.status === 503) {
            setTtsUnavailable(true);
        }
    }, [generateMutation.error]);

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

    // Save voice mutation
    const saveVoiceMutation = useMutation({
        mutationFn: async (formData) => {
            return await xttsApi.saveVoice(formData);
        },
        onSuccess: () => {
            showSuccess('Success!', 'Voice saved successfully!');
            queryClient.invalidateQueries(['xtts-voices']);
            setVoiceName('');
            setReferenceFile(null);
        },
        onError: (error) => {
            let errorMessage = 'Failed to save voice';
            if (error.response?.data?.error) {
                errorMessage = error.response.data.error;
            } else if (error.data?.error) {
                errorMessage = error.data.error;
            } else if (error.message) {
                errorMessage = error.message;
            }
            showError('Save Failed', errorMessage);
        },
    });

    // Delete voice mutation
    const deleteVoiceMutation = useMutation({
        mutationFn: async (voiceId) => {
            return await xttsApi.deleteVoice(voiceId);
        },
        onSuccess: () => {
            showSuccess('Success!', 'Voice deleted successfully!');
            queryClient.invalidateQueries(['xtts-voices']);
        },
        onError: (error) => {
            let errorMessage = 'Failed to delete voice';
            if (error.response?.data?.error) {
                errorMessage = error.response.data.error;
            } else if (error.data?.error) {
                errorMessage = error.data.error;
            } else if (error.message) {
                errorMessage = error.message;
            }
            showError('Delete Failed', errorMessage);
        },
    });

    // Update voice mutation
    const updateVoiceMutation = useMutation({
        mutationFn: async ({ voiceId, formData }) => {
            return await xttsApi.updateVoice(voiceId, formData);
        },
        onSuccess: () => {
            showSuccess('Success!', 'Voice updated successfully!');
            queryClient.invalidateQueries(['xtts-voices']);
            setEditingVoice(null);
            setEditVoiceName('');
            setEditVoiceFile(null);
        },
        onError: (error) => {
            let errorMessage = 'Failed to update voice';
            if (error.response?.data?.error) {
                errorMessage = error.response.data.error;
            } else if (error.data?.error) {
                errorMessage = error.data.error;
            } else if (error.message) {
                errorMessage = error.message;
            }
            showError('Update Failed', errorMessage);
        },
    });

    // Set default voice mutation
    const setDefaultVoiceMutation = useMutation({
        mutationFn: async (voiceId) => {
            return await xttsApi.setDefaultVoice(voiceId);
        },
        onSuccess: () => {
            showSuccess('Success!', 'Default voice set successfully!');
            queryClient.invalidateQueries(['xtts-voices']);
        },
        onError: (error) => {
            let errorMessage = 'Failed to set default voice';
            if (error.response?.data?.error) {
                errorMessage = error.response.data.error;
            } else if (error.data?.error) {
                errorMessage = error.data.error;
            } else if (error.message) {
                errorMessage = error.message;
            }
            showError('Set Default Failed', errorMessage);
        },
    });

    const handleGenerate = () => {
        if (!text.trim()) {
            showWarning('Validation Error', 'Please enter text to generate');
            return;
        }

        if (!language) {
            showWarning('Validation Error', 'Please select a language');
            return;
        }

        if (!useExistingVoice && !referenceFile) {
            showWarning('Validation Error', 'Please upload a reference audio file');
            return;
        }

        if (useExistingVoice && !selectedVoiceId) {
            showWarning('Validation Error', 'Please select a saved voice');
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
            showWarning('Validation Error', 'Please enter a voice name');
            return;
        }

        if (!referenceFile) {
            showWarning('Validation Error', 'Please upload a voice file');
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
        showSuccess('Settings Reset', 'Settings have been reset to defaults');
    };

    const handleEditVoice = (voice) => {
        setEditingVoice(voice.id);
        setEditVoiceName(voice.name);
        setEditVoiceFile(null);
    };

    const handleCancelEdit = () => {
        setEditingVoice(null);
        setEditVoiceName('');
        setEditVoiceFile(null);
    };

    const handleSaveEdit = () => {
        if (!editVoiceName.trim()) {
            showWarning('Validation Error', 'Please enter a voice name');
            return;
        }

        const formData = new FormData();
        formData.append('name', editVoiceName);
        if (editVoiceFile) {
            formData.append('file', editVoiceFile);
        }

        updateVoiceMutation.mutate({ voiceId: editingVoice, formData });
    };

    const handleSetDefault = (voiceId) => {
        setDefaultVoiceMutation.mutate(voiceId);
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
                                onChange={(e) => {
                                    const selectedValue = e.target.value;
                                    console.log('Language selected:', selectedValue, 'from options:', languageOptions.find(opt => opt.value === selectedValue));
                                    setLanguage(selectedValue);
                                }}
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
                                    <div className="space-y-3">
                                        {savedVoices.length === 0 ? (
                                            <div className="p-4 bg-gray-900/50 rounded-lg border border-gray-700 text-center text-gray-400">
                                                <p className="text-sm">No saved voices available. Please save a voice first.</p>
                                            </div>
                                        ) : (
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-64 overflow-y-auto">
                                                {savedVoices.map((voice) => {
                                                    const voiceIdStr = voice.id.toString();
                                                    const isSelected = selectedVoiceId === voiceIdStr || selectedVoiceId === voice.id;
                                                    return (
                                                        <div
                                                            key={voice.id}
                                                            onClick={() => setSelectedVoiceId(voiceIdStr)}
                                                            className={`p-3 rounded-lg border-2 cursor-pointer transition-all ${
                                                                isSelected
                                                                    ? 'border-purple-500 bg-purple-500/20'
                                                                    : voice.is_default
                                                                    ? 'border-yellow-500/50 bg-yellow-900/10 hover:border-yellow-500'
                                                                    : 'border-gray-700 bg-gray-900/50 hover:border-purple-500/50'
                                                            }`}
                                                        >
                                                            <div className="flex items-center justify-between mb-2">
                                                                <div className="flex items-center gap-2 flex-1 min-w-0">
                                                                    <h4 className="text-white font-semibold text-sm truncate">{voice.name}</h4>
                                                                    {voice.is_default && (
                                                                        <span className="px-2 py-0.5 text-xs bg-yellow-500/20 text-yellow-300 rounded-full border border-yellow-500/30 flex items-center gap-1 flex-shrink-0">
                                                                            <Star className="w-3 h-3" />
                                                                            Default
                                                                        </span>
                                                                    )}
                                                                </div>
                                                                {isSelected && (
                                                                    <div className="w-5 h-5 rounded-full bg-purple-500 flex items-center justify-center flex-shrink-0 ml-2">
                                                                        <span className="text-white text-xs">✓</span>
                                                                    </div>
                                                                )}
                                                            </div>
                                                            <div className="flex items-center gap-2 mb-2">
                                                                {!voice.is_default && (
                                                                    <button
                                                                        onClick={(e) => {
                                                                            e.stopPropagation();
                                                                            handleSetDefault(voice.id);
                                                                        }}
                                                                        className="text-yellow-400 hover:text-yellow-300 transition-colors text-xs flex items-center gap-1"
                                                                        title="Set as default"
                                                                        disabled={setDefaultVoiceMutation.isPending}
                                                                    >
                                                                        <StarOff className="w-4 h-4" />
                                                                        <span>Set Default</span>
                                                                    </button>
                                                                )}
                                                            </div>
                                                            <audio
                                                                controls
                                                                src={voice.file_url || voice.file}
                                                                className="w-full"
                                                                style={{ height: '32px' }}
                                                                onClick={(e) => e.stopPropagation()}
                                                            />
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                        )}
                                    </div>
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
                                            className={`p-4 bg-gray-900/50 rounded-lg border transition-colors ${
                                                voice.is_default 
                                                    ? 'border-yellow-500/50 bg-yellow-900/20' 
                                                    : 'border-gray-700 hover:border-purple-500'
                                            }`}
                                        >
                                            <div className="flex items-start justify-between mb-3">
                                                <div className="flex-1">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <h4 className="text-white font-semibold">{voice.name}</h4>
                                                        {voice.is_default && (
                                                            <span className="px-2 py-0.5 text-xs bg-yellow-500/20 text-yellow-300 rounded-full border border-yellow-500/30 flex items-center gap-1">
                                                                <Star className="w-3 h-3" />
                                                                Default
                                                            </span>
                                                        )}
                                                    </div>
                                                    <p className="text-gray-400 text-sm">
                                                        {new Date(voice.created_at).toLocaleDateString()}
                                                    </p>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    {!voice.is_default && (
                                                        <button
                                                            onClick={() => handleSetDefault(voice.id)}
                                                            className="text-yellow-400 hover:text-yellow-300 transition-colors"
                                                            title="Set as default"
                                                            disabled={setDefaultVoiceMutation.isPending}
                                                        >
                                                            <StarOff className="w-5 h-5" />
                                                        </button>
                                                    )}
                                                    <button
                                                        onClick={() => handleEditVoice(voice)}
                                                        className="text-blue-400 hover:text-blue-300 transition-colors"
                                                        title="Edit voice"
                                                    >
                                                        <Edit className="w-5 h-5" />
                                                    </button>
                                                    <button
                                                        onClick={() => {
                                                            if (window.confirm(`Are you sure you want to delete "${voice.name}"?`)) {
                                                                deleteVoiceMutation.mutate(voice.id);
                                                            }
                                                        }}
                                                        className="text-red-400 hover:text-red-300 transition-colors"
                                                        title="Delete voice"
                                                        disabled={deleteVoiceMutation.isPending}
                                                    >
                                                        <Trash2 className="w-5 h-5" />
                                                    </button>
                                                </div>
                                            </div>
                                            
                                            {editingVoice === voice.id ? (
                                                <div className="space-y-3 mt-3 p-3 bg-gray-800/50 rounded-lg border border-purple-500/30">
                                                    <Input
                                                        label="Voice Name"
                                                        value={editVoiceName}
                                                        onChange={(e) => setEditVoiceName(e.target.value)}
                                                        placeholder="Enter voice name"
                                                    />
                                                    <Input
                                                        type="file"
                                                        label="Voice File (optional)"
                                                        accept="audio/*"
                                                        onChange={(e) => setEditVoiceFile(e.target.files[0])}
                                                    />
                                                    <div className="flex gap-2">
                                                        <Button
                                                            size="sm"
                                                            onClick={handleSaveEdit}
                                                            disabled={updateVoiceMutation.isPending}
                                                            className="flex-1 bg-purple-600 hover:bg-purple-700"
                                                        >
                                                            {updateVoiceMutation.isPending ? (
                                                                <>
                                                                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                                                    Saving...
                                                                </>
                                                            ) : (
                                                                <>
                                                                    <Save className="w-4 h-4 mr-2" />
                                                                    Save
                                                                </>
                                                            )}
                                                        </Button>
                                                        <Button
                                                            size="sm"
                                                            variant="secondary"
                                                            onClick={handleCancelEdit}
                                                            disabled={updateVoiceMutation.isPending}
                                                        >
                                                            Cancel
                                                        </Button>
                                                    </div>
                                                </div>
                                            ) : (
                                                <audio
                                                    controls
                                                    src={voice.file_url || voice.file}
                                                    className="w-full mt-2"
                                                    style={{ height: '40px' }}
                                                />
                                            )}
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
