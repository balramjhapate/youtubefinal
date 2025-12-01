import AddVideoModal from '@/components/add-video-modal';
import { PasswordInput } from '@/components/password-input';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { Textarea } from '@/components/ui/textarea';
import AppLayout from '@/layouts/app-layout';
import { Head, Link, router, useForm } from '@inertiajs/react';
import { AlertCircle, ExternalLink, Info, Video } from 'lucide-react';
import { FormEventHandler, useState } from 'react';

interface Setting {
    id: number;
    key: string;
    value: string | number | boolean | null;
    type: string;
    group: string;
    description: string | null;
}

function getSettingValue(
    settings: Setting[],
    key: string,
    defaultValue: string | boolean = '',
): string | boolean {
    const setting = settings.find((s) => s.key === key);
    if (!setting) return defaultValue;
    if (setting.type === 'boolean') {
        return setting.value === true || setting.value === '1' || setting.value === 1;
    }
    return setting.value?.toString() || defaultValue;
}

function setSettingValue(
    settings: Setting[],
    key: string,
    value: string | boolean,
): Setting[] {
    return settings.map((s) => (s.key === key ? { ...s, value } : s));
}

export default function Index({
    settings: settingsByGroup,
}: {
    settings: Record<string, Setting[]>;
}) {
    const [isAddVideoModalOpen, setIsAddVideoModalOpen] = useState(false);
    const [jsonError, setJsonError] = useState<string | null>(null);

    const allSettings = Object.values(settingsByGroup).flat();

    const { data, setData, post, processing, errors } = useForm({
        // AI Provider Settings
        gemini_api_key: getSettingValue(allSettings, 'gemini_api_key', '') as string,
        openai_api_key: getSettingValue(allSettings, 'openai_api_key', '') as string,
        script_generation_provider: getSettingValue(allSettings, 'script_generation_provider', 'gemini') as string,
        general_tasks_provider: getSettingValue(allSettings, 'general_tasks_provider', 'gemini') as string,

        // Cloudinary Settings
        cloudinary_enabled: getSettingValue(allSettings, 'cloudinary_enabled', false) as boolean,
        cloudinary_cloud_name: getSettingValue(allSettings, 'cloudinary_cloud_name', '') as string,
        cloudinary_api_key: getSettingValue(allSettings, 'cloudinary_api_key', '') as string,
        cloudinary_api_secret: getSettingValue(allSettings, 'cloudinary_api_secret', '') as string,

        // Google Sheets Settings
        google_sheets_enabled: getSettingValue(allSettings, 'google_sheets_enabled', false) as boolean,
        google_sheets_url: getSettingValue(allSettings, 'google_sheets_url', '') as string,
        google_sheets_sheet_name: getSettingValue(allSettings, 'google_sheets_sheet_name', 'Sheet1') as string,
        google_sheets_service_account: getSettingValue(allSettings, 'google_sheets_service_account', '') as string,

        // Watermark Settings
        watermark_enabled: getSettingValue(allSettings, 'watermark_enabled', false) as boolean,
        watermark_text: getSettingValue(allSettings, 'watermark_text', '') as string,
        watermark_font_size: parseInt(getSettingValue(allSettings, 'watermark_font_size', '32') as string),
        watermark_font_color: getSettingValue(allSettings, 'watermark_font_color', 'white') as string,
        watermark_opacity: parseInt(getSettingValue(allSettings, 'watermark_opacity', '70') as string),
        watermark_position_interval: parseInt(getSettingValue(allSettings, 'watermark_position_interval', '1') as string),
    });

    const handleSaveAISettings: FormEventHandler = (e) => {
        e.preventDefault();
        const settings = [
            { key: 'gemini_api_key', value: data.gemini_api_key, type: 'string', group: 'ai' },
            { key: 'openai_api_key', value: data.openai_api_key, type: 'string', group: 'ai' },
            { key: 'script_generation_provider', value: data.script_generation_provider, type: 'string', group: 'ai' },
            { key: 'general_tasks_provider', value: data.general_tasks_provider, type: 'string', group: 'ai' },
        ];
        router.post('/app-settings', { settings }, { preserveScroll: true });
    };

    const handleSaveCloudinarySettings: FormEventHandler = (e) => {
        e.preventDefault();
        const settings = [
            { key: 'cloudinary_enabled', value: data.cloudinary_enabled, type: 'boolean', group: 'cloudinary' },
            { key: 'cloudinary_cloud_name', value: data.cloudinary_cloud_name, type: 'string', group: 'cloudinary' },
            { key: 'cloudinary_api_key', value: data.cloudinary_api_key, type: 'string', group: 'cloudinary' },
            { key: 'cloudinary_api_secret', value: data.cloudinary_api_secret, type: 'string', group: 'cloudinary' },
        ];
        router.post('/app-settings', { settings }, { preserveScroll: true });
    };

    const handleSaveGoogleSheetsSettings: FormEventHandler = (e) => {
        e.preventDefault();
        setJsonError(null);
        
        // Validate JSON
        if (data.google_sheets_service_account && data.google_sheets_service_account !== '***hidden***') {
            try {
                JSON.parse(data.google_sheets_service_account);
            } catch (err) {
                setJsonError(`Invalid JSON: ${err instanceof Error ? err.message : 'Unknown error'}. Please check your JSON format. Make sure all quotes are properly escaped and the JSON is valid.`);
                return;
            }
        }

        const settings = [
            { key: 'google_sheets_enabled', value: data.google_sheets_enabled, type: 'boolean', group: 'google_sheets' },
            { key: 'google_sheets_url', value: data.google_sheets_url, type: 'string', group: 'google_sheets' },
            { key: 'google_sheets_sheet_name', value: data.google_sheets_sheet_name, type: 'string', group: 'google_sheets' },
            { key: 'google_sheets_service_account', value: data.google_sheets_service_account, type: 'json', group: 'google_sheets' },
        ];
        router.post('/app-settings', { settings }, { preserveScroll: true });
    };

    const handleSaveWatermarkSettings: FormEventHandler = (e) => {
        e.preventDefault();
        const settings = [
            { key: 'watermark_enabled', value: data.watermark_enabled, type: 'boolean', group: 'watermark' },
            { key: 'watermark_text', value: data.watermark_text, type: 'string', group: 'watermark' },
            { key: 'watermark_font_size', value: data.watermark_font_size.toString(), type: 'integer', group: 'watermark' },
            { key: 'watermark_font_color', value: data.watermark_font_color, type: 'string', group: 'watermark' },
            { key: 'watermark_opacity', value: data.watermark_opacity.toString(), type: 'integer', group: 'watermark' },
            { key: 'watermark_position_interval', value: data.watermark_position_interval.toString(), type: 'integer', group: 'watermark' },
        ];
        router.post('/app-settings', { settings }, { preserveScroll: true });
    };

    const handleFormatJSON = () => {
        if (!data.google_sheets_service_account || data.google_sheets_service_account === '***hidden***') {
            return;
        }
        try {
            const parsed = JSON.parse(data.google_sheets_service_account);
            setData('google_sheets_service_account', JSON.stringify(parsed, null, 2));
            setJsonError(null);
        } catch {
            setJsonError('Invalid JSON format');
        }
    };

    const handleTestConnection = () => {
        // TODO: Implement test connection
        alert('Test connection functionality will be implemented');
    };

    return (
        <AppLayout>
            <Head title="Settings" />

            <div className="container mx-auto px-4 py-8">
                {/* Header */}
                <div className="mb-6 flex items-center justify-between">
                    <div>
                        <h1 className="mb-2 text-3xl font-bold">Settings</h1>
                        <p className="text-muted-foreground">
                            Configure your AI provider and other settings
                        </p>
                    </div>
                    <Button
                        size="lg"
                        className="gap-2 bg-red-600 hover:bg-red-700 text-white"
                        onClick={() => setIsAddVideoModalOpen(true)}
                    >
                        <Video className="size-4" />
                        + Add Video
                    </Button>
                </div>

                <AddVideoModal
                    isOpen={isAddVideoModalOpen}
                    onClose={() => setIsAddVideoModalOpen(false)}
                />

                {/* Top Row - Three Cards */}
                <div className="mb-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
                    {/* AI Provider Settings */}
                    <Card>
                        <CardHeader>
                            <CardTitle>AI Provider Settings</CardTitle>
                            <CardDescription>
                                Configure API keys for multiple AI providers and Text-to-Speech (TTS)
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <form onSubmit={handleSaveAISettings} className="space-y-4">
                                <div className="space-y-2">
                                    <Label htmlFor="gemini_api_key">Google Gemini API Key</Label>
                                    <PasswordInput
                                        id="gemini_api_key"
                                        value={data.gemini_api_key}
                                        onChange={(e) => setData('gemini_api_key', e.target.value)}
                                        placeholder="Enter your Gemini API key"
                                    />
                                    <p className="text-xs text-muted-foreground">
                                        Used for TTS generation (Google TTS), script enhancement
                                    </p>
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="openai_api_key">OpenAI API Key (GPT-4o-mini)</Label>
                                    <PasswordInput
                                        id="openai_api_key"
                                        value={data.openai_api_key}
                                        onChange={(e) => setData('openai_api_key', e.target.value)}
                                        placeholder="Enter your OpenAI API key"
                                    />
                                    <p className="text-xs text-muted-foreground">
                                        Used for script generation with GPT-4o-mini
                                    </p>
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="script_generation_provider">Script Generation Provider</Label>
                                    <Select
                                        value={data.script_generation_provider}
                                        onValueChange={(value) => setData('script_generation_provider', value)}
                                    >
                                        <SelectTrigger>
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="gemini">Google Gemini</SelectItem>
                                            <SelectItem value="openai">OpenAI</SelectItem>
                                            <SelectItem value="claude">Anthropic Claude</SelectItem>
                                        </SelectContent>
                                    </Select>
                                    <p className="text-xs text-muted-foreground">
                                        AI provider used for generating Hindi scripts
                                    </p>
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="general_tasks_provider">General Tasks Provider</Label>
                                    <Select
                                        value={data.general_tasks_provider}
                                        onValueChange={(value) => setData('general_tasks_provider', value)}
                                    >
                                        <SelectTrigger>
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="gemini">Google Gemini</SelectItem>
                                            <SelectItem value="openai">OpenAI</SelectItem>
                                            <SelectItem value="claude">Anthropic Claude</SelectItem>
                                        </SelectContent>
                                    </Select>
                                    <p className="text-xs text-muted-foreground">
                                        AI provider for transcription enhancement, TTS markup, etc.
                                    </p>
                                </div>

                                <Button
                                    type="submit"
                                    disabled={processing}
                                    className="w-full bg-red-600 hover:bg-red-700 text-white"
                                >
                                    Save AI Settings
                                </Button>
                            </form>
                        </CardContent>
                    </Card>

                    {/* Cloudinary Settings */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Cloudinary Settings</CardTitle>
                            <CardDescription>
                                Configure Cloudinary for automatic video uploads
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <form onSubmit={handleSaveCloudinarySettings} className="space-y-4">
                                <div className="flex items-center gap-2">
                                    <input
                                        type="checkbox"
                                        id="cloudinary_enabled"
                                        checked={data.cloudinary_enabled}
                                        onChange={(e) => setData('cloudinary_enabled', e.target.checked)}
                                        className="rounded"
                                    />
                                    <Label htmlFor="cloudinary_enabled" className="cursor-pointer">
                                        Enable Cloudinary uploads
                                    </Label>
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="cloudinary_cloud_name">Cloud Name</Label>
                                    <Input
                                        id="cloudinary_cloud_name"
                                        value={data.cloudinary_cloud_name}
                                        onChange={(e) => setData('cloudinary_cloud_name', e.target.value)}
                                        placeholder="Enter your Cloudinary cloud name"
                                    />
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="cloudinary_api_key">API Key</Label>
                                    <PasswordInput
                                        id="cloudinary_api_key"
                                        value={data.cloudinary_api_key}
                                        onChange={(e) => setData('cloudinary_api_key', e.target.value)}
                                        placeholder="Enter your Cloudinary API key"
                                    />
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="cloudinary_api_secret">API Secret</Label>
                                    <PasswordInput
                                        id="cloudinary_api_secret"
                                        value={data.cloudinary_api_secret}
                                        onChange={(e) => setData('cloudinary_api_secret', e.target.value)}
                                        placeholder="Enter your Cloudinary API secret"
                                    />
                                </div>

                                <Button
                                    type="submit"
                                    disabled={processing}
                                    className="w-full bg-red-600 hover:bg-red-700 text-white"
                                >
                                    Save Cloudinary Settings
                                </Button>

                                <Link
                                    href="https://cloudinary.com/console"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="flex items-center gap-1 text-sm text-primary hover:underline"
                                >
                                    Get your Cloudinary credentials from Cloudinary Dashboard
                                    <ExternalLink className="size-3" />
                                </Link>
                            </form>
                        </CardContent>
                    </Card>

                    {/* Google Sheets Settings */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Google Sheets Settings</CardTitle>
                            <CardDescription>
                                Configure Google Sheets to automatically track video data
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <form onSubmit={handleSaveGoogleSheetsSettings} className="space-y-4">
                                <div className="flex items-center gap-2">
                                    <input
                                        type="checkbox"
                                        id="google_sheets_enabled"
                                        checked={data.google_sheets_enabled}
                                        onChange={(e) => setData('google_sheets_enabled', e.target.checked)}
                                        className="rounded"
                                    />
                                    <Label htmlFor="google_sheets_enabled" className="cursor-pointer">
                                        Enable Google Sheets tracking
                                    </Label>
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="google_sheets_url">Google Sheets URL or Spreadsheet ID</Label>
                                    <Input
                                        id="google_sheets_url"
                                        value={data.google_sheets_url}
                                        onChange={(e) => setData('google_sheets_url', e.target.value)}
                                        placeholder="Enter Google Sheets URL or ID"
                                    />
                                    <p className="text-xs text-muted-foreground">
                                        Paste the full Google Sheets URL or just the spreadsheet ID
                                    </p>
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="google_sheets_sheet_name">Sheet Name</Label>
                                    <Input
                                        id="google_sheets_sheet_name"
                                        value={data.google_sheets_sheet_name}
                                        onChange={(e) => setData('google_sheets_sheet_name', e.target.value)}
                                        placeholder="Sheet1"
                                    />
                                    <p className="text-xs text-muted-foreground">
                                        Name of the sheet tab where data will be written (default: Sheet1)
                                    </p>
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="google_sheets_service_account">Service Account JSON Credentials</Label>
                                    <Textarea
                                        id="google_sheets_service_account"
                                        value={data.google_sheets_service_account === '***hidden***' ? '' : data.google_sheets_service_account}
                                        onChange={(e) => setData('google_sheets_service_account', e.target.value)}
                                        placeholder="Paste your service account JSON here"
                                        rows={6}
                                        className="font-mono text-xs"
                                    />
                                    {jsonError && (
                                        <Alert className="border-destructive bg-destructive/10">
                                            <AlertCircle className="size-4" />
                                            <AlertDescription>{jsonError}</AlertDescription>
                                        </Alert>
                                    )}
                                </div>

                                <div className="flex gap-2">
                                    <Button
                                        type="button"
                                        variant="outline"
                                        size="sm"
                                        onClick={handleFormatJSON}
                                        className="bg-red-600 hover:bg-red-700 text-white"
                                    >
                                        Format JSON
                                    </Button>
                                    <Button
                                        type="submit"
                                        disabled={processing}
                                        className="flex-1 bg-red-600 hover:bg-red-700 text-white"
                                    >
                                        Save Google Sheets Settings
                                    </Button>
                                </div>

                                <Button
                                    type="button"
                                    variant="outline"
                                    onClick={handleTestConnection}
                                    className="w-full"
                                >
                                    Test Connection
                                </Button>

                                <Alert>
                                    <Info className="size-4" />
                                    <AlertDescription>
                                        <strong>How to set up Google Sheets API:</strong>
                                        <ol className="mt-2 list-inside list-decimal space-y-1 text-xs">
                                            <li>Go to Google Cloud Console</li>
                                            <li>Create a new project or select existing one</li>
                                            <li>Enable Google Sheets API</li>
                                            <li>Create a Service Account</li>
                                            <li>Download the JSON key file</li>
                                            <li>Paste the JSON content above</li>
                                        </ol>
                                    </AlertDescription>
                                </Alert>
                            </form>
                        </CardContent>
                    </Card>
                </div>

                {/* Bottom Row - Watermark and Info Cards */}
                <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
                    {/* Watermark Settings */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Watermark Settings</CardTitle>
                            <CardDescription>
                                Add a moving text watermark to videos
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <form onSubmit={handleSaveWatermarkSettings} className="space-y-4">
                                <div className="flex items-center gap-2">
                                    <input
                                        type="checkbox"
                                        id="watermark_enabled"
                                        checked={data.watermark_enabled}
                                        onChange={(e) => setData('watermark_enabled', e.target.checked)}
                                        className="rounded"
                                    />
                                    <Label htmlFor="watermark_enabled" className="cursor-pointer">
                                        Enable watermark on videos
                                    </Label>
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="watermark_text">Watermark Text</Label>
                                    <Input
                                        id="watermark_text"
                                        value={data.watermark_text}
                                        onChange={(e) => setData('watermark_text', e.target.value)}
                                        placeholder="Enter watermark text"
                                    />
                                    <p className="text-xs text-muted-foreground">
                                        Text that will appear as watermark on videos
                                    </p>
                                </div>

                                <div className="space-y-2">
                                    <div className="flex items-center justify-between">
                                        <Label htmlFor="watermark_font_size">Font Size</Label>
                                        <span className="text-sm text-muted-foreground">{data.watermark_font_size}px</span>
                                    </div>
                                    <Slider
                                        id="watermark_font_size"
                                        value={[data.watermark_font_size]}
                                        onValueChange={([value]) => setData('watermark_font_size', value)}
                                        min={10}
                                        max={100}
                                        step={1}
                                    />
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="watermark_font_color">Font Color</Label>
                                    <Select
                                        value={data.watermark_font_color}
                                        onValueChange={(value) => setData('watermark_font_color', value)}
                                    >
                                        <SelectTrigger>
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="white">
                                                <div className="flex items-center gap-2">
                                                    <div className="size-4 rounded border bg-white" />
                                                    White
                                                </div>
                                            </SelectItem>
                                            <SelectItem value="black">
                                                <div className="flex items-center gap-2">
                                                    <div className="size-4 rounded border bg-black" />
                                                    Black
                                                </div>
                                            </SelectItem>
                                            <SelectItem value="red">
                                                <div className="flex items-center gap-2">
                                                    <div className="size-4 rounded border bg-red-500" />
                                                    Red
                                                </div>
                                            </SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>

                                <div className="space-y-2">
                                    <div className="flex items-center justify-between">
                                        <Label htmlFor="watermark_opacity">Opacity</Label>
                                        <span className="text-sm text-muted-foreground">{data.watermark_opacity}%</span>
                                    </div>
                                    <Slider
                                        id="watermark_opacity"
                                        value={[data.watermark_opacity]}
                                        onValueChange={([value]) => setData('watermark_opacity', value)}
                                        min={0}
                                        max={100}
                                        step={1}
                                    />
                                </div>

                                <div className="space-y-2">
                                    <div className="flex items-center justify-between">
                                        <Label htmlFor="watermark_position_interval">Position Change Interval</Label>
                                        <span className="text-sm text-muted-foreground">{data.watermark_position_interval} seconds</span>
                                    </div>
                                    <Slider
                                        id="watermark_position_interval"
                                        value={[data.watermark_position_interval]}
                                        onValueChange={([value]) => setData('watermark_position_interval', value)}
                                        min={1}
                                        max={10}
                                        step={1}
                                    />
                                    <p className="text-xs text-muted-foreground">
                                        How often the watermark moves to a new position
                                    </p>
                                </div>

                                <Button
                                    type="submit"
                                    disabled={processing}
                                    className="w-full bg-red-600 hover:bg-red-700 text-white"
                                >
                                    Save Watermark Settings
                                </Button>
                            </form>
                        </CardContent>
                    </Card>

                    {/* AI Model Info Cards */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Google Gemini</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-3">
                            <ul className="space-y-1 text-sm">
                                <li className="flex items-start gap-2">
                                    <span className="mt-1">•</span>
                                    <span>Free tier available</span>
                                </li>
                                <li className="flex items-start gap-2">
                                    <span className="mt-1">•</span>
                                    <span>Fast response times</span>
                                </li>
                                <li className="flex items-start gap-2">
                                    <span className="mt-1">•</span>
                                    <span>Good for Hindi content</span>
                                </li>
                            </ul>
                            <Link
                                href="https://ai.google.dev/"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-1 text-sm text-primary hover:underline"
                            >
                                Get API Key
                                <ExternalLink className="size-3" />
                            </Link>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle>OpenAI GPT-4</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-3">
                            <ul className="space-y-1 text-sm">
                                <li className="flex items-start gap-2">
                                    <span className="mt-1">•</span>
                                    <span>High-quality outputs</span>
                                </li>
                                <li className="flex items-start gap-2">
                                    <span className="mt-1">•</span>
                                    <span>Excellent instructions</span>
                                </li>
                                <li className="flex items-start gap-2">
                                    <span className="mt-1">•</span>
                                    <span>Pay-per-use pricing</span>
                                </li>
                            </ul>
                            <Link
                                href="https://platform.openai.com/"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-1 text-sm text-primary hover:underline"
                            >
                                Get API Key
                                <ExternalLink className="size-3" />
                            </Link>
                        </CardContent>
                    </Card>
                </div>

                {/* About Audio Prompts */}
                <Card className="mt-6">
                    <CardContent className="pt-6">
                        <div className="flex items-start gap-3">
                            <Info className="mt-0.5 size-5 shrink-0 text-primary" />
                            <div className="text-sm">
                                <p className="font-medium">About Audio Prompts</p>
                                <p className="mt-1 text-muted-foreground">
                                    Audio prompts are AI-generated scripts designed for Hindi voiceover production. They include character descriptions, voice directions, and a mandatory call-to-action. Make sure your video has been transcribed before generating audio prompts.
                                </p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </AppLayout>
    );
}
