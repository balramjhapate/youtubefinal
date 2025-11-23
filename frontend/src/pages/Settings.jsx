import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { Save, Eye, EyeOff, Info, ExternalLink } from 'lucide-react';
import { Button, Input, Select, LoadingSpinner } from '../components/common';
import { settingsApi } from '../api';
import { AI_PROVIDERS } from '../utils/constants';

export function Settings() {
  const [provider, setProvider] = useState('gemini');
  const [apiKey, setApiKey] = useState('');
  const [showApiKey, setShowApiKey] = useState(false);
  const queryClient = useQueryClient();

  // Fetch current settings
  const { data: settings, isLoading } = useQuery({
    queryKey: ['ai-settings'],
    queryFn: settingsApi.getAISettings,
  });

  // Update state when settings load
  useEffect(() => {
    if (settings) {
      setProvider(settings.provider || 'gemini');
      setApiKey(settings.api_key || '');
    }
  }, [settings]);

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: () => settingsApi.saveAISettings(provider, apiKey),
    onSuccess: () => {
      toast.success('Settings saved successfully');
      queryClient.invalidateQueries(['ai-settings']);
    },
    onError: (error) => toast.error(error),
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    saveMutation.mutate();
  };

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-gray-400 mt-1">
          Configure your AI provider and other settings
        </p>
      </div>

      {/* AI Settings Card */}
      <div className="glass-card p-6 max-w-2xl">
        <h2 className="text-lg font-semibold text-white mb-6">AI Provider Settings</h2>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <Select
              label="AI Provider"
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              options={AI_PROVIDERS}
            />
            <p className="mt-1 text-xs text-gray-500">
              Select the AI provider for generating audio prompts
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">
              API Key
            </label>
            <div className="relative">
              <input
                type={showApiKey ? 'text' : 'password'}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="Enter your API key"
                className="w-full px-4 py-2.5 pr-12 rounded-lg input-dark"
              />
              <button
                type="button"
                onClick={() => setShowApiKey(!showApiKey)}
                className="absolute right-3 top-1/2 -translate-y-1/2 p-1 hover:bg-white/10 rounded"
              >
                {showApiKey ? (
                  <EyeOff className="w-4 h-4 text-gray-400" />
                ) : (
                  <Eye className="w-4 h-4 text-gray-400" />
                )}
              </button>
            </div>
          </div>

          <Button
            type="submit"
            variant="primary"
            icon={Save}
            loading={saveMutation.isPending}
          >
            Save Settings
          </Button>
        </form>
      </div>

      {/* Provider Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-4xl">
        {/* Gemini */}
        <div className={`glass-card p-4 ${provider === 'gemini' ? 'ring-2 ring-[var(--rednote-primary)]' : ''}`}>
          <h3 className="font-medium text-white mb-2">Google Gemini</h3>
          <ul className="text-xs text-gray-400 space-y-1 mb-3">
            <li>• Free tier available</li>
            <li>• Fast response times</li>
            <li>• Good for Hindi content</li>
          </ul>
          <a
            href="https://aistudio.google.com/app/apikey"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs text-[var(--rednote-primary)] hover:underline"
          >
            Get API Key <ExternalLink className="w-3 h-3" />
          </a>
        </div>

        {/* OpenAI */}
        <div className={`glass-card p-4 ${provider === 'openai' ? 'ring-2 ring-[var(--rednote-primary)]' : ''}`}>
          <h3 className="font-medium text-white mb-2">OpenAI GPT-4</h3>
          <ul className="text-xs text-gray-400 space-y-1 mb-3">
            <li>• High-quality outputs</li>
            <li>• Excellent instructions</li>
            <li>• Pay-per-use pricing</li>
          </ul>
          <a
            href="https://platform.openai.com/api-keys"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs text-[var(--rednote-primary)] hover:underline"
          >
            Get API Key <ExternalLink className="w-3 h-3" />
          </a>
        </div>

        {/* Anthropic */}
        <div className={`glass-card p-4 ${provider === 'anthropic' ? 'ring-2 ring-[var(--rednote-primary)]' : ''}`}>
          <h3 className="font-medium text-white mb-2">Anthropic Claude</h3>
          <ul className="text-xs text-gray-400 space-y-1 mb-3">
            <li>• Nuanced content</li>
            <li>• Great for creativity</li>
            <li>• Pay-per-use pricing</li>
          </ul>
          <a
            href="https://console.anthropic.com/"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs text-[var(--rednote-primary)] hover:underline"
          >
            Get API Key <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>

      {/* Help section */}
      <div className="glass-card p-4 max-w-2xl border-l-4 border-blue-500">
        <div className="flex items-start gap-3">
          <Info className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-medium text-white">About Audio Prompts</h3>
            <p className="text-sm text-gray-400 mt-1">
              Audio prompts are AI-generated scripts designed for Hindi voiceover production.
              They include character descriptions, voice directions, and a mandatory call-to-action.
              Make sure your video has been transcribed before generating audio prompts.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Settings;
