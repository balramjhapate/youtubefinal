import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { Save, Eye, EyeOff, Info, ExternalLink, Cloud, FileSpreadsheet, TestTube, Image } from 'lucide-react';
import { Button, Input, Select, LoadingSpinner } from '../components/common';
import { settingsApi } from '../api';
import { AI_PROVIDERS } from '../utils/constants';

export function Settings() {
  const [provider, setProvider] = useState('gemini');
  const [apiKey, setApiKey] = useState('');
  const [showApiKey, setShowApiKey] = useState(false);
  
  // Cloudinary state
  const [cloudName, setCloudName] = useState('');
  const [cloudinaryApiKey, setCloudinaryApiKey] = useState('');
  const [cloudinaryApiSecret, setCloudinaryApiSecret] = useState('');
  const [cloudinaryEnabled, setCloudinaryEnabled] = useState(false);
  const [showCloudinarySecret, setShowCloudinarySecret] = useState(false);
  
  // Google Sheets state
  const [spreadsheetId, setSpreadsheetId] = useState('');
  const [sheetName, setSheetName] = useState('Sheet1');
  const [credentialsJson, setCredentialsJson] = useState('');
  const [googleSheetsEnabled, setGoogleSheetsEnabled] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [serviceAccountEmail, setServiceAccountEmail] = useState('');
  const [jsonValidationError, setJsonValidationError] = useState('');
  
  // Watermark state
  const [watermarkEnabled, setWatermarkEnabled] = useState(false);
  const [watermarkText, setWatermarkText] = useState('');
  const [watermarkFontSize, setWatermarkFontSize] = useState(24);
  const [watermarkFontColor, setWatermarkFontColor] = useState('white');
  const [watermarkOpacity, setWatermarkOpacity] = useState(0.7);
  const [watermarkInterval, setWatermarkInterval] = useState(1.0);
  
  const queryClient = useQueryClient();

  // Fetch current settings
  const { data: settings, isLoading } = useQuery({
    queryKey: ['ai-settings'],
    queryFn: settingsApi.getAISettings,
  });

  const { data: cloudinarySettings } = useQuery({
    queryKey: ['cloudinary-settings'],
    queryFn: settingsApi.getCloudinarySettings,
  });

  const { data: googleSheetsSettings } = useQuery({
    queryKey: ['google-sheets-settings'],
    queryFn: settingsApi.getGoogleSheetsSettings,
  });

  const { data: watermarkSettings } = useQuery({
    queryKey: ['watermark-settings'],
    queryFn: settingsApi.getWatermarkSettings,
  });

  // Update state when settings load
  useEffect(() => {
    if (settings) {
      setProvider(settings.provider || 'gemini');
      setApiKey(settings.api_key || '');
    }
  }, [settings]);

  useEffect(() => {
    if (cloudinarySettings) {
      setCloudName(cloudinarySettings.cloud_name || '');
      setCloudinaryApiKey(cloudinarySettings.api_key || '');
      setCloudinaryApiSecret(cloudinarySettings.api_secret || '');
      setCloudinaryEnabled(cloudinarySettings.enabled || false);
    }
  }, [cloudinarySettings]);

  useEffect(() => {
    if (googleSheetsSettings) {
      setSpreadsheetId(googleSheetsSettings.spreadsheet_id || '');
      setSheetName(googleSheetsSettings.sheet_name || 'Sheet1');
      setCredentialsJson(googleSheetsSettings.credentials_json || '');
      setGoogleSheetsEnabled(googleSheetsSettings.enabled || false);
      
      // Extract service account email from credentials
      if (googleSheetsSettings.credentials_json) {
        try {
          const creds = JSON.parse(googleSheetsSettings.credentials_json);
          setServiceAccountEmail(creds.client_email || '');
        } catch (e) {
          setServiceAccountEmail('');
        }
      }
    }
  }, [googleSheetsSettings]);

  useEffect(() => {
    if (watermarkSettings) {
      setWatermarkEnabled(watermarkSettings.enabled || false);
      setWatermarkText(watermarkSettings.watermark_text || '');
      setWatermarkFontSize(watermarkSettings.font_size || 24);
      setWatermarkFontColor(watermarkSettings.font_color || 'white');
      setWatermarkOpacity(watermarkSettings.opacity || 0.7);
      setWatermarkInterval(watermarkSettings.position_change_interval || 1.0);
    }
  }, [watermarkSettings]);

  // Extract service account email when credentials JSON changes
  useEffect(() => {
    if (credentialsJson) {
      try {
        // Try to parse and validate JSON
        const creds = JSON.parse(credentialsJson);
        setServiceAccountEmail(creds.client_email || '');
        setJsonValidationError('');
      } catch (e) {
        setServiceAccountEmail('');
        setJsonValidationError(`Invalid JSON: ${e.message}`);
      }
    } else {
      setServiceAccountEmail('');
      setJsonValidationError('');
    }
  }, [credentialsJson]);

  // Validate and format JSON credentials
  const validateAndFormatCredentials = (jsonString) => {
    if (!jsonString || !jsonString.trim()) {
      return { valid: false, error: 'Credentials JSON is empty' };
    }
    
    try {
      // Parse the JSON to validate it
      const parsed = JSON.parse(jsonString);
      
      // Check required fields
      if (!parsed.type || parsed.type !== 'service_account') {
        return { valid: false, error: 'Invalid service account type. Must be "service_account"' };
      }
      if (!parsed.project_id) {
        return { valid: false, error: 'Missing required field: project_id' };
      }
      if (!parsed.private_key) {
        return { valid: false, error: 'Missing required field: private_key' };
      }
      if (!parsed.client_email) {
        return { valid: false, error: 'Missing required field: client_email' };
      }
      
      // Return formatted JSON (stringified to ensure proper formatting)
      return { valid: true, formatted: JSON.stringify(parsed, null, 2) };
    } catch (e) {
      return { valid: false, error: `Invalid JSON: ${e.message}` };
    }
  };

  // Save mutations
  const saveAIMutation = useMutation({
    mutationFn: () => settingsApi.saveAISettings(provider, apiKey),
    onSuccess: () => {
      toast.success('AI settings saved successfully');
      queryClient.invalidateQueries(['ai-settings']);
    },
    onError: (error) => toast.error(error.message || 'Failed to save AI settings'),
  });

  const saveCloudinaryMutation = useMutation({
    mutationFn: () => settingsApi.saveCloudinarySettings(cloudName, cloudinaryApiKey, cloudinaryApiSecret, cloudinaryEnabled),
    onSuccess: () => {
      toast.success('Cloudinary settings saved successfully');
      queryClient.invalidateQueries(['cloudinary-settings']);
    },
    onError: (error) => toast.error(error.message || 'Failed to save Cloudinary settings'),
  });

  const saveGoogleSheetsMutation = useMutation({
    mutationFn: () => {
      // Validate and format credentials JSON before saving
      if (credentialsJson) {
        const validation = validateAndFormatCredentials(credentialsJson);
        if (!validation.valid) {
          throw new Error(validation.error);
        }
        // Use formatted JSON to ensure proper encoding
        return settingsApi.saveGoogleSheetsSettings(
          spreadsheetId, 
          sheetName, 
          validation.formatted || credentialsJson, 
          googleSheetsEnabled
        );
      }
      return settingsApi.saveGoogleSheetsSettings(spreadsheetId, sheetName, credentialsJson, googleSheetsEnabled);
    },
    onSuccess: () => {
      toast.success('Google Sheets settings saved successfully');
      queryClient.invalidateQueries(['google-sheets-settings']);
    },
    onError: (error) => {
      const errorMessage = error.message || error?.response?.data?.error || 'Failed to save Google Sheets settings';
      toast.error(errorMessage, { duration: 7000 });
    },
  });

  const testGoogleSheetsMutation = useMutation({
    mutationFn: async () => {
      // Validate credentials JSON first
      if (credentialsJson) {
        const validation = validateAndFormatCredentials(credentialsJson);
        if (!validation.valid) {
          throw new Error(validation.error);
        }
      }
      
      // First save the settings if they haven't been saved yet
      if (googleSheetsEnabled && spreadsheetId && credentialsJson) {
        try {
          // Use validated and formatted JSON
          const validation = validateAndFormatCredentials(credentialsJson);
          const jsonToSave = validation.formatted || credentialsJson;
          
          // Save settings first, then test
          await settingsApi.saveGoogleSheetsSettings(spreadsheetId, sheetName, jsonToSave, googleSheetsEnabled);
          // Invalidate queries to refresh settings
          queryClient.invalidateQueries(['google-sheets-settings']);
          // Wait a moment for the database to update
          await new Promise(resolve => setTimeout(resolve, 500));
        } catch (saveError) {
          // If save fails, throw error
          const errorMsg = saveError.message || saveError?.response?.data?.error || 'Failed to save settings before testing';
          throw new Error(errorMsg);
        }
      }
      // Now test the connection
      return settingsApi.testGoogleSheets();
    },
    onSuccess: (data) => {
      setTestResult(data);
      if (data.success) {
        toast.success('Google Sheets connection test passed!', {
          duration: 5000,
        });
        // Show detailed info
        if (data.info) {
          console.log('Google Sheets Test Results:', data.info);
        }
      } else {
        const errorMessages = data.errors || ['Test failed'];
        errorMessages.forEach(error => toast.error(error, { duration: 7000 }));
        
        if (data.warnings) {
          data.warnings.forEach(warning => toast(warning, { icon: '⚠️', duration: 5000 }));
        }
      }
    },
    onError: (error) => {
      const errorData = error?.response?.data;
      setTestResult(errorData || { success: false, errors: ['Failed to test connection'] });
      
      // Handle different error scenarios
      if (errorData?.errors && Array.isArray(errorData.errors)) {
        errorData.errors.forEach(err => toast.error(err, { duration: 7000 }));
      } else if (errorData?.error) {
        toast.error(errorData.error, { duration: 7000 });
      } else if (error?.message) {
        toast.error(error.message, { duration: 7000 });
      } else {
        toast.error('Failed to test Google Sheets connection. Please ensure settings are saved first.', { duration: 7000 });
      }
    },
  });

  const saveWatermarkMutation = useMutation({
    mutationFn: () => {
      return settingsApi.saveWatermarkSettings({
        enabled: watermarkEnabled,
        watermark_text: watermarkText,
        font_size: watermarkFontSize,
        font_color: watermarkFontColor,
        opacity: watermarkOpacity,
        position_change_interval: watermarkInterval,
      });
    },
    onSuccess: () => {
      toast.success('Watermark settings saved successfully');
      queryClient.invalidateQueries(['watermark-settings']);
    },
    onError: (error) => toast.error(error.message || 'Failed to save watermark settings'),
  });

  const handleAISubmit = (e) => {
    e.preventDefault();
    saveAIMutation.mutate();
  };

  const handleCloudinarySubmit = (e) => {
    e.preventDefault();
    saveCloudinaryMutation.mutate();
  };

  const handleGoogleSheetsSubmit = (e) => {
    e.preventDefault();
    saveGoogleSheetsMutation.mutate();
  };

  const handleWatermarkSubmit = (e) => {
    e.preventDefault();
    saveWatermarkMutation.mutate();
  };


  // Extract spreadsheet ID from Google Sheets URL
  const handleSpreadsheetUrlChange = (url) => {
    if (url) {
      // Extract ID from Google Sheets URL
      // Format: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit
      const match = url.match(/\/spreadsheets\/d\/([a-zA-Z0-9-_]+)/);
      if (match) {
        setSpreadsheetId(match[1]);
      } else {
        // If it doesn't match the pattern, assume it's just the ID
        setSpreadsheetId(url);
      }
    } else {
      setSpreadsheetId('');
    }
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

      {/* Settings Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        {/* AI Settings Card */}
        <div className="glass-card p-6">
        <h2 className="text-lg font-semibold text-white mb-6">AI Provider Settings</h2>

        <form onSubmit={handleAISubmit} className="space-y-6">
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
            loading={saveAIMutation.isPending}
          >
            Save AI Settings
          </Button>
        </form>
      </div>

        {/* Cloudinary Settings Card */}
        <div className="glass-card p-6">
        <div className="flex items-center gap-2 mb-6">
          <Cloud className="w-5 h-5 text-blue-400" />
          <h2 className="text-lg font-semibold text-white">Cloudinary Settings</h2>
        </div>
        <p className="text-sm text-gray-400 mb-4">
          Configure Cloudinary to automatically upload final processed videos. Videos will be uploaded after processing is complete.
        </p>

        <form onSubmit={handleCloudinarySubmit} className="space-y-6">
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="cloudinary-enabled"
              checked={cloudinaryEnabled}
              onChange={(e) => setCloudinaryEnabled(e.target.checked)}
              className="w-4 h-4 rounded"
            />
            <label htmlFor="cloudinary-enabled" className="text-sm font-medium text-gray-300">
              Enable Cloudinary uploads
            </label>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">
              Cloud Name
            </label>
            <Input
              type="text"
              value={cloudName}
              onChange={(e) => setCloudName(e.target.value)}
              placeholder="your-cloud-name"
              disabled={!cloudinaryEnabled}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">
              API Key
            </label>
            <div className="relative">
              <input
                type={showApiKey ? 'text' : 'password'}
                value={cloudinaryApiKey}
                onChange={(e) => setCloudinaryApiKey(e.target.value)}
                placeholder="Enter your Cloudinary API key"
                disabled={!cloudinaryEnabled}
                className="w-full px-4 py-2.5 pr-12 rounded-lg input-dark disabled:opacity-50"
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

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">
              API Secret
            </label>
            <div className="relative">
              <input
                type={showCloudinarySecret ? 'text' : 'password'}
                value={cloudinaryApiSecret}
                onChange={(e) => setCloudinaryApiSecret(e.target.value)}
                placeholder="Enter your Cloudinary API secret"
                disabled={!cloudinaryEnabled}
                className="w-full px-4 py-2.5 pr-12 rounded-lg input-dark disabled:opacity-50"
              />
              <button
                type="button"
                onClick={() => setShowCloudinarySecret(!showCloudinarySecret)}
                className="absolute right-3 top-1/2 -translate-y-1/2 p-1 hover:bg-white/10 rounded"
              >
                {showCloudinarySecret ? (
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
            loading={saveCloudinaryMutation.isPending}
            disabled={!cloudinaryEnabled}
          >
            Save Cloudinary Settings
          </Button>
        </form>

        <div className="mt-4 p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg">
          <p className="text-xs text-gray-400">
            Get your Cloudinary credentials from{' '}
            <a
              href="https://cloudinary.com/console"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-400 hover:underline"
            >
              Cloudinary Dashboard <ExternalLink className="w-3 h-3 inline" />
            </a>
          </p>
        </div>
      </div>

        {/* Google Sheets Settings Card */}
        <div className="glass-card p-6">
        <div className="flex items-center gap-2 mb-6">
          <FileSpreadsheet className="w-5 h-5 text-green-400" />
          <h2 className="text-lg font-semibold text-white">Google Sheets Settings</h2>
        </div>
        <p className="text-sm text-gray-400 mb-4">
          Configure Google Sheets to automatically track video data. Title, description, tags, and video links will be added to your sheet.
        </p>

        <form onSubmit={handleGoogleSheetsSubmit} className="space-y-6">
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="google-sheets-enabled"
              checked={googleSheetsEnabled}
              onChange={(e) => setGoogleSheetsEnabled(e.target.checked)}
              className="w-4 h-4 rounded"
            />
            <label htmlFor="google-sheets-enabled" className="text-sm font-medium text-gray-300">
              Enable Google Sheets tracking
            </label>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">
              Google Sheets URL or Spreadsheet ID
            </label>
            <Input
              type="text"
              value={spreadsheetId}
              onChange={(e) => handleSpreadsheetUrlChange(e.target.value)}
              placeholder="https://docs.google.com/spreadsheets/d/... or spreadsheet ID"
              disabled={!googleSheetsEnabled}
            />
            <p className="mt-1 text-xs text-gray-500">
              Paste the full Google Sheets URL or just the spreadsheet ID
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">
              Sheet Name
            </label>
            <Input
              type="text"
              value={sheetName}
              onChange={(e) => setSheetName(e.target.value)}
              placeholder="Sheet1"
              disabled={!googleSheetsEnabled}
            />
            <p className="mt-1 text-xs text-gray-500">
              Name of the sheet tab where data will be written (default: Sheet1)
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">
              Service Account JSON Credentials
            </label>
            <textarea
              value={credentialsJson}
              onChange={(e) => setCredentialsJson(e.target.value)}
              placeholder='{"type": "service_account", "project_id": "...", ...}'
              disabled={!googleSheetsEnabled}
              rows={8}
              className={`w-full px-4 py-2.5 rounded-lg input-dark font-mono text-xs disabled:opacity-50 ${
                jsonValidationError ? 'border-red-500/50 focus:border-red-500' : ''
              }`}
            />
            {jsonValidationError && (
              <div className="mt-2 p-2 bg-red-500/10 border border-red-500/20 rounded">
                <p className="text-xs text-red-300">
                  ⚠️ {jsonValidationError}
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  Please check your JSON format. Make sure all quotes are properly escaped and the JSON is valid.
                </p>
              </div>
            )}
            <div className="mt-1 flex items-center justify-between">
              {!jsonValidationError && credentialsJson && (
                <p className="text-xs text-green-400">
                  ✓ Valid JSON format detected
                </p>
              )}
              {credentialsJson && (
                <button
                  type="button"
                  onClick={() => {
                    const validation = validateAndFormatCredentials(credentialsJson);
                    if (validation.valid && validation.formatted) {
                      setCredentialsJson(validation.formatted);
                      toast.success('JSON formatted successfully');
                    } else {
                      toast.error(validation.error || 'Cannot format invalid JSON');
                    }
                  }}
                  className="text-xs text-blue-400 hover:text-blue-300 underline"
                >
                  Format JSON
                </button>
              )}
            </div>
            {!jsonValidationError && !credentialsJson && (
              <p className="mt-1 text-xs text-gray-500">
                Paste the complete JSON credentials from your Google Service Account
              </p>
            )}
            {serviceAccountEmail && !jsonValidationError && (
              <div className="mt-2 p-2 bg-blue-500/10 border border-blue-500/20 rounded">
                <p className="text-xs text-gray-300 mb-1">
                  <strong>Service Account Email:</strong>
                </p>
                <p className="text-xs text-white font-mono bg-black/20 p-2 rounded break-all">
                  {serviceAccountEmail}
                </p>
                <p className="text-xs text-yellow-300 mt-1">
                  ⚠️ Make sure to share your Google Sheet with this email address and give it "Editor" access!
                </p>
              </div>
            )}
          </div>

          <div className="flex gap-3">
            <Button
              type="submit"
              variant="primary"
              icon={Save}
              loading={saveGoogleSheetsMutation.isPending}
              disabled={!googleSheetsEnabled}
            >
              Save Google Sheets Settings
            </Button>
            <Button
              type="button"
              variant="secondary"
              icon={TestTube}
              onClick={() => {
                // Warn user if settings aren't filled
                if (!googleSheetsEnabled || !spreadsheetId || !credentialsJson) {
                  toast.error('Please fill in all Google Sheets settings before testing', { duration: 5000 });
                  return;
                }
                testGoogleSheetsMutation.mutate();
              }}
              loading={testGoogleSheetsMutation.isPending}
              disabled={!googleSheetsEnabled || !spreadsheetId || !credentialsJson}
            >
              Test Connection
            </Button>
          </div>
        </form>

        {/* Test Results Display */}
        {testResult && (
          <div className={`mt-4 p-4 rounded-lg border ${
            testResult.success 
              ? 'bg-green-500/10 border-green-500/20' 
              : 'bg-red-500/10 border-red-500/20'
          }`}>
            <h4 className={`text-sm font-semibold mb-2 ${
              testResult.success ? 'text-green-300' : 'text-red-300'
            }`}>
              {testResult.success ? '✅ Connection Test Passed' : '❌ Connection Test Failed'}
            </h4>
            
            {testResult.errors && testResult.errors.length > 0 && (
              <div className="mb-3">
                {testResult.errors.map((error, idx) => (
                  <p key={idx} className="text-xs text-red-300 mb-1">{error}</p>
                ))}
              </div>
            )}
            
            {testResult.info && (
              <div className="space-y-2">
                {testResult.info.service_account_email && (
                  <div className="p-2 bg-white/5 rounded">
                    <p className="text-xs text-gray-300 mb-1">
                      <strong>Service Account Email:</strong>
                    </p>
                    <p className="text-xs text-white font-mono bg-black/20 p-2 rounded break-all">
                      {testResult.info.service_account_email}
                    </p>
                    <p className="text-xs text-yellow-300 mt-1">
                      ⚠️ Share your Google Sheet with this email address!
                    </p>
                  </div>
                )}
                
                {testResult.info.fix_instructions && (
                  <div className="p-2 bg-blue-500/10 rounded">
                    <p className="text-xs font-semibold text-blue-300 mb-2">How to Fix:</p>
                    <ol className="text-xs text-gray-300 space-y-1 list-decimal list-inside">
                      {testResult.info.fix_instructions.map((instruction, idx) => (
                        <li key={idx}>{instruction}</li>
                      ))}
                    </ol>
                  </div>
                )}
                
                {testResult.info.extracted_spreadsheet_id && (
                  <p className="text-xs text-gray-400">
                    Spreadsheet ID: <span className="font-mono">{testResult.info.extracted_spreadsheet_id}</span>
                  </p>
                )}
              </div>
            )}
            
            {testResult.warnings && testResult.warnings.length > 0 && (
              <div className="mt-2">
                {testResult.warnings.map((warning, idx) => (
                  <p key={idx} className="text-xs text-yellow-300">{warning}</p>
                ))}
              </div>
            )}
          </div>
        )}

        <div className="mt-4 p-3 bg-green-500/10 border border-green-500/20 rounded-lg">
          <p className="text-xs text-gray-400 mb-2">
            <strong className="text-white">How to set up Google Sheets API:</strong>
          </p>
          <ol className="text-xs text-gray-400 space-y-1 list-decimal list-inside">
            <li>Go to{' '}
              <a
                href="https://console.cloud.google.com/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-green-400 hover:underline"
              >
                Google Cloud Console <ExternalLink className="w-3 h-3 inline" />
              </a>
            </li>
            <li>Create a new project or select an existing one</li>
            <li>Enable Google Sheets API</li>
            <li>Create a Service Account and download the JSON key file</li>
            <li>Share your Google Sheet with the service account email</li>
            <li>Paste the JSON content in the field above</li>
          </ol>
        </div>
      </div>

        {/* Watermark Settings Card */}
        <div className="glass-card p-6">
          <div className="flex items-center gap-2 mb-6">
            <Image className="w-5 h-5 text-purple-400" />
            <h2 className="text-lg font-semibold text-white">Watermark Settings</h2>
          </div>
          <p className="text-sm text-gray-400 mb-4">
            Add a moving text watermark to your videos. The watermark will change position at regular intervals to prevent easy removal.
          </p>

          <form onSubmit={handleWatermarkSubmit} className="space-y-6">
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="watermark-enabled"
                checked={watermarkEnabled}
                onChange={(e) => setWatermarkEnabled(e.target.checked)}
                className="w-4 h-4 rounded"
              />
              <label htmlFor="watermark-enabled" className="text-sm font-medium text-gray-300">
                Enable watermark on videos
              </label>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">
                Watermark Text
              </label>
              <Input
                type="text"
                value={watermarkText}
                onChange={(e) => setWatermarkText(e.target.value)}
                placeholder="Enter watermark text (e.g., Your Channel Name)"
                disabled={!watermarkEnabled}
                maxLength={100}
              />
              <p className="mt-1 text-xs text-gray-500">
                Text that will appear as watermark on videos
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">
                Font Size: {watermarkFontSize}px
              </label>
              <input
                type="range"
                min="12"
                max="72"
                step="2"
                value={watermarkFontSize}
                onChange={(e) => setWatermarkFontSize(parseInt(e.target.value))}
                disabled={!watermarkEnabled}
                className="w-full"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">
                Font Color
              </label>
              <div className="flex gap-2">
                <select
                  value={watermarkFontColor.startsWith('#') ? 'custom' : watermarkFontColor}
                  onChange={(e) => {
                    if (e.target.value === 'custom') {
                      setWatermarkFontColor('#FFFFFF');
                    } else {
                      setWatermarkFontColor(e.target.value);
                    }
                  }}
                  disabled={!watermarkEnabled}
                  className="flex-1 px-4 py-2.5 rounded-lg input-dark disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <option value="white">White</option>
                  <option value="black">Black</option>
                  <option value="yellow">Yellow</option>
                  <option value="red">Red</option>
                  <option value="blue">Blue</option>
                  <option value="green">Green</option>
                  <option value="custom">Custom Color</option>
                </select>
                <input
                  type="color"
                  value={watermarkFontColor.startsWith('#') ? watermarkFontColor : 
                         watermarkFontColor === 'white' ? '#FFFFFF' : 
                         watermarkFontColor === 'black' ? '#000000' :
                         watermarkFontColor === 'yellow' ? '#FFFF00' :
                         watermarkFontColor === 'red' ? '#FF0000' :
                         watermarkFontColor === 'blue' ? '#0000FF' :
                         watermarkFontColor === 'green' ? '#00FF00' : '#FFFFFF'}
                  onChange={(e) => {
                    setWatermarkFontColor(e.target.value);
                  }}
                  disabled={!watermarkEnabled}
                  className="w-16 h-10 rounded cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">
                Opacity: {Math.round(watermarkOpacity * 100)}%
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={watermarkOpacity}
                onChange={(e) => setWatermarkOpacity(parseFloat(e.target.value))}
                disabled={!watermarkEnabled}
                className="w-full"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">
                Position Change Interval: {watermarkInterval} seconds
              </label>
              <input
                type="range"
                min="0.5"
                max="5"
                step="0.5"
                value={watermarkInterval}
                onChange={(e) => setWatermarkInterval(parseFloat(e.target.value))}
                disabled={!watermarkEnabled}
                className="w-full"
              />
              <p className="mt-1 text-xs text-gray-500">
                How often the watermark moves to a new position
              </p>
            </div>

            <Button
              type="submit"
              variant="primary"
              icon={Save}
              loading={saveWatermarkMutation.isPending}
              disabled={!watermarkEnabled || !watermarkText.trim()}
            >
              Save Watermark Settings
            </Button>
          </form>
        </div>
      </div>

      {/* Provider Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
      <div className="glass-card p-4 border-l-4 border-blue-500">
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
