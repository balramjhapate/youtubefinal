import { useState, useRef, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { Upload, Mic2, X, Play, Pause, FileAudio } from 'lucide-react';
import { Button, Input, Textarea } from '../common';
import { voiceProfilesApi } from '../../api';

export function VoiceProfileForm({ onSuccess }) {
  const [name, setName] = useState('');
  const [referenceText, setReferenceText] = useState('');
  const [audioFile, setAudioFile] = useState(null);
  const [audioPreviewUrl, setAudioPreviewUrl] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [audioDuration, setAudioDuration] = useState(null);
  const fileInputRef = useRef(null);
  const audioRef = useRef(null);
  const queryClient = useQueryClient();

  // Clean up audio URL on unmount
  useEffect(() => {
    return () => {
      if (audioPreviewUrl) {
        URL.revokeObjectURL(audioPreviewUrl);
      }
    };
  }, [audioPreviewUrl]);

  const createMutation = useMutation({
    mutationFn: (formData) => voiceProfilesApi.create(formData),
    onSuccess: () => {
      toast.success('Voice profile created successfully!');
      queryClient.invalidateQueries(['voice-profiles']);
      resetForm();
      onSuccess?.();
    },
    onError: (error) => toast.error(error),
  });

  const resetForm = () => {
    setName('');
    setReferenceText('');
    setAudioFile(null);
    if (audioPreviewUrl) {
      URL.revokeObjectURL(audioPreviewUrl);
    }
    setAudioPreviewUrl(null);
    setAudioDuration(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      // Validate file type
      const validTypes = ['audio/wav', 'audio/mpeg', 'audio/mp3', 'audio/x-wav', 'audio/wave'];
      if (!validTypes.includes(file.type) && !file.name.match(/\.(wav|mp3)$/i)) {
        toast.error('Please select a WAV or MP3 audio file');
        return;
      }

      // Validate file size (max 50MB)
      if (file.size > 50 * 1024 * 1024) {
        toast.error('File size must be less than 50MB');
        return;
      }

      setAudioFile(file);

      // Create preview URL
      const url = URL.createObjectURL(file);
      setAudioPreviewUrl(url);

      // Get audio duration
      const audio = new Audio(url);
      audio.onloadedmetadata = () => {
        setAudioDuration(audio.duration);
      };
    }
  };

  const handlePlayPreview = () => {
    if (!audioPreviewUrl) return;

    if (isPlaying && audioRef.current) {
      audioRef.current.pause();
      setIsPlaying(false);
      return;
    }

    const audio = new Audio(audioPreviewUrl);
    audio.onended = () => setIsPlaying(false);
    audio.onerror = () => {
      setIsPlaying(false);
      toast.error('Error playing audio preview');
    };
    audio.play();
    audioRef.current = audio;
    setIsPlaying(true);
  };

  const formatDuration = (seconds) => {
    if (!seconds) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    if (!name.trim()) {
      toast.error('Please enter a profile name');
      return;
    }

    if (!referenceText.trim()) {
      toast.error('Please enter reference text (transcript of the audio)');
      return;
    }

    if (!audioFile) {
      toast.error('Please select a reference audio file');
      return;
    }

    const formData = new FormData();
    formData.append('name', name);
    formData.append('reference_text', referenceText);
    formData.append('reference_audio', audioFile);

    createMutation.mutate(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Profile Name */}
      <Input
        label="Profile Name"
        placeholder="e.g., Hindi Male Voice, Narration Style, etc."
        value={name}
        onChange={(e) => setName(e.target.value)}
      />

      {/* Reference Audio Upload */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-1.5">
          Reference Audio <span className="text-red-400">*</span>
        </label>
        <div className="relative">
          <input
            ref={fileInputRef}
            type="file"
            accept="audio/wav,audio/mpeg,audio/mp3,.wav,.mp3"
            onChange={handleFileChange}
            className="hidden"
          />

          {audioFile ? (
            <div className="p-4 bg-white/5 rounded-lg border border-white/10">
              {/* File Info */}
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-lg bg-[var(--rednote-primary)]/20 flex items-center justify-center">
                  <FileAudio className="w-5 h-5 text-[var(--rednote-primary)]" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white truncate">{audioFile.name}</p>
                  <p className="text-xs text-gray-400">
                    {(audioFile.size / 1024 / 1024).toFixed(2)} MB
                    {audioDuration && ` • ${formatDuration(audioDuration)}`}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setAudioFile(null);
                    if (audioPreviewUrl) URL.revokeObjectURL(audioPreviewUrl);
                    setAudioPreviewUrl(null);
                    setAudioDuration(null);
                    if (fileInputRef.current) fileInputRef.current.value = '';
                  }}
                  className="p-1.5 hover:bg-white/10 rounded"
                >
                  <X className="w-4 h-4 text-gray-400" />
                </button>
              </div>

              {/* Audio Preview */}
              {audioPreviewUrl && (
                <div className="flex items-center gap-3">
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    icon={isPlaying ? Pause : Play}
                    onClick={handlePlayPreview}
                  >
                    {isPlaying ? 'Stop' : 'Preview'}
                  </Button>
                  <div className="flex-1 h-1 bg-white/10 rounded-full">
                    <div className="h-full w-0 bg-[var(--rednote-primary)] rounded-full" />
                  </div>
                </div>
              )}
            </div>
          ) : (
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="w-full p-8 border-2 border-dashed border-white/20 rounded-lg hover:border-[var(--rednote-primary)]/50 transition-colors group"
            >
              <div className="flex flex-col items-center gap-2 text-gray-400 group-hover:text-gray-300">
                <Upload className="w-8 h-8" />
                <span className="text-sm font-medium">Click to upload audio file</span>
                <span className="text-xs text-gray-500">WAV or MP3 (max 50MB)</span>
              </div>
            </button>
          )}
        </div>
        <p className="mt-1.5 text-xs text-gray-500">
          Upload a clear voice sample (10-60 seconds recommended) for best cloning results.
        </p>
      </div>

      {/* Reference Text */}
      <div>
        <Textarea
          label={
            <span>
              Reference Text (Transcript) <span className="text-red-400">*</span>
            </span>
          }
          placeholder="Enter the exact transcript of what is spoken in the audio file..."
          value={referenceText}
          onChange={(e) => setReferenceText(e.target.value)}
          rows={4}
        />
        <p className="mt-1.5 text-xs text-gray-500">
          This should be the exact text spoken in the reference audio. Accuracy is important for voice cloning.
        </p>
      </div>

      {/* Character count */}
      <div className="flex justify-between text-xs text-gray-500">
        <span>Reference text: {referenceText.length} characters</span>
        <span className={referenceText.length < 20 ? 'text-yellow-400' : 'text-green-400'}>
          {referenceText.length < 20 ? 'Too short' : 'Good length'}
        </span>
      </div>

      {/* Submit Buttons */}
      <div className="flex gap-3 pt-2">
        <Button
          type="button"
          variant="secondary"
          onClick={resetForm}
          className="flex-1"
        >
          Reset
        </Button>
        <Button
          type="submit"
          variant="primary"
          loading={createMutation.isPending}
          className="flex-1"
          disabled={!name || !referenceText || !audioFile}
        >
          Create Profile
        </Button>
      </div>
    </form>
  );
}

export default VoiceProfileForm;
