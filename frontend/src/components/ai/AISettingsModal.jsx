import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { showSuccess, showError } from '../../utils/alerts';
import { Eye, EyeOff, Save } from 'lucide-react';
import { Modal, Button, Input, Select } from '../common';
import { settingsApi } from '../../api';
import { AI_PROVIDERS } from '../../utils/constants';

export function AISettingsModal({ isOpen, onClose }) {
  const [provider, setProvider] = useState('gemini');
  const [apiKey, setApiKey] = useState('');
  const [showApiKey, setShowApiKey] = useState(false);
  const queryClient = useQueryClient();

  // Fetch current settings
  const { data: settings, isLoading } = useQuery({
    queryKey: ['ai-settings'],
    queryFn: settingsApi.getAISettings,
    enabled: isOpen,
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
      showSuccess('Settings Saved', 'Settings saved successfully.', { timer: 3000 });
      queryClient.invalidateQueries(['ai-settings']);
      onClose();
    },
    onError: (error) => showError('Save Failed', error?.message || 'Failed to save settings. Please try again.'),
  });

  const handleSubmit = (e) => {
    e.preventDefault();

    if (!apiKey.trim()) {
      showError('API Key Required', 'Please enter an API key to save settings.');
      return;
    }

    saveMutation.mutate();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="AI Provider Settings"
      size="md"
    >
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
          <p className="mt-1 text-xs text-gray-500">
            {provider === 'gemini' && 'Get your API key from Google AI Studio'}
            {provider === 'openai' && 'Get your API key from OpenAI Dashboard'}
            {provider === 'anthropic' && 'Get your API key from Anthropic Console'}
          </p>
        </div>

        <div className="bg-white/5 rounded-lg p-4">
          <h4 className="text-sm font-medium mb-2">Provider Features</h4>
          <ul className="text-xs text-gray-400 space-y-1">
            {provider === 'gemini' && (
              <>
                <li>• Free tier available with generous limits</li>
                <li>• Fast response times</li>
                <li>• Good for Hindi content generation</li>
              </>
            )}
            {provider === 'openai' && (
              <>
                <li>• GPT-4 for high-quality outputs</li>
                <li>• Excellent at following instructions</li>
                <li>• Pay-per-use pricing</li>
              </>
            )}
            {provider === 'anthropic' && (
              <>
                <li>• Claude for nuanced content</li>
                <li>• Great for creative writing</li>
                <li>• Pay-per-use pricing</li>
              </>
            )}
          </ul>
        </div>

        <div className="flex gap-3 justify-end">
          <Button
            type="button"
            variant="secondary"
            onClick={onClose}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            icon={Save}
            loading={saveMutation.isPending}
          >
            Save Settings
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export default AISettingsModal;
