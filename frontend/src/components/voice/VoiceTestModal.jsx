import { useState, useRef, useEffect } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { Volume2, Play, Pause, Download, Loader2, Mic2, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { Modal, Button, Textarea, AudioPlayer } from '../common';
import apiClient from '../../api/client';

export function VoiceTestModal({ isOpen, onClose, profile }) {
  const [testText, setTestText] = useState(
    'नमस्ते दोस्तों, यह एक टेस्ट मैसेज है। आज हम देखेंगे कि यह वॉइस कैसे सुनाई देती है।'
  );
  const [synthesizedAudioUrl, setSynthesizedAudioUrl] = useState(null);
  const [isPlayingRef, setIsPlayingRef] = useState(false);
  const [synthesisError, setSynthesisError] = useState(null);
  const refAudioRef = useRef(null);

  // Check synthesis service status
  const { data: serviceStatus } = useQuery({
    queryKey: ['synthesis-status'],
    queryFn: async () => {
      const response = await apiClient.get('/voice-profiles/synthesis-status/');
      return response.data;
    },
    enabled: isOpen,
    staleTime: 30000, // Cache for 30 seconds
  });

  // Reset error when modal opens
  useEffect(() => {
    if (isOpen) {
      setSynthesisError(null);
    }
  }, [isOpen]);

  // Synthesis mutation
  const synthesizeMutation = useMutation({
    mutationFn: async () => {
      setSynthesisError(null);
      setSynthesizedAudioUrl(null);
      const response = await apiClient.post('/voice-profiles/test-synthesis/', {
        profile_id: profile.id,
        text: testText,
      });
      return response.data;
    },
    onSuccess: (data) => {
      setSynthesisError(null); // Clear any previous errors
      if (data.audio_url) {
        setSynthesizedAudioUrl(data.audio_url);
        toast.success('Voice synthesis completed!');
      }
    },
    onError: (error) => {
      // Extract error message from response if available
      let errorMessage = 'Synthesis failed';
      if (error?.response?.data?.error) {
        errorMessage = error.response.data.error;
      } else if (error?.message) {
        errorMessage = error.message;
      } else if (error?.code === 'ERR_NETWORK') {
        errorMessage = 'Cannot connect to server. Make sure Django is running on port 8000.';
      }
      setSynthesisError(errorMessage);
      toast.error(errorMessage);
    },
  });

  const handlePlayReference = () => {
    if (!profile?.reference_audio_url) return;

    if (isPlayingRef && refAudioRef.current) {
      refAudioRef.current.pause();
      setIsPlayingRef(false);
      return;
    }

    const audio = new Audio(profile.reference_audio_url);
    audio.onended = () => setIsPlayingRef(false);
    audio.onerror = () => {
      setIsPlayingRef(false);
      toast.error('Error playing reference audio');
    };
    audio.play();
    refAudioRef.current = audio;
    setIsPlayingRef(true);
  };

  const handleClose = () => {
    // Stop any playing audio
    if (refAudioRef.current) {
      refAudioRef.current.pause();
    }
    setSynthesizedAudioUrl(null);
    onClose();
  };

  if (!profile) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={`Test Voice: ${profile.name}`}
      size="lg"
    >
      <div className="space-y-6">
        {/* Profile Info */}
        <div className="flex items-center gap-4 p-4 bg-white/5 rounded-lg">
          <div className="w-16 h-16 rounded-lg bg-[var(--rednote-primary)]/20 flex items-center justify-center">
            <Mic2 className="w-8 h-8 text-[var(--rednote-primary)]" />
          </div>
          <div className="flex-1">
            <h3 className="font-medium text-white text-lg">{profile.name}</h3>
            <p className="text-sm text-gray-400 mt-1">
              Reference: {profile.reference_text?.substring(0, 100)}
              {profile.reference_text?.length > 100 ? '...' : ''}
            </p>
          </div>
        </div>

        {/* Reference Audio Player */}
        {profile.reference_audio_url && (
          <div>
            <h4 className="text-sm font-medium text-gray-300 mb-2">
              Reference Audio (Original Sample)
            </h4>
            <div className="flex items-center gap-3 p-3 bg-white/5 rounded-lg">
              <Button
                size="sm"
                variant="secondary"
                icon={isPlayingRef ? Pause : Play}
                onClick={handlePlayReference}
              >
                {isPlayingRef ? 'Stop' : 'Play Reference'}
              </Button>
              <span className="text-xs text-gray-500">
                Listen to the original voice sample
              </span>
            </div>
          </div>
        )}

        {/* Test Text Input */}
        <div>
          <h4 className="text-sm font-medium text-gray-300 mb-2">
            Test Text (Hindi recommended)
          </h4>
          <Textarea
            value={testText}
            onChange={(e) => setTestText(e.target.value)}
            placeholder="Enter text to synthesize..."
            rows={4}
          />
          <div className="flex gap-2 mt-2">
            <button
              onClick={() => setTestText('नमस्ते दोस्तों, यह एक टेस्ट मैसेज है।')}
              className="text-xs px-2 py-1 bg-white/10 rounded hover:bg-white/20"
            >
              Hindi Sample
            </button>
            <button
              onClick={() => setTestText('Hello friends, this is a test message.')}
              className="text-xs px-2 py-1 bg-white/10 rounded hover:bg-white/20"
            >
              English Sample
            </button>
            <button
              onClick={() => setTestText('Maa baap ki kasam subscribe and like kar ke jao agar maa bap se pyar karte ho toh!')}
              className="text-xs px-2 py-1 bg-white/10 rounded hover:bg-white/20"
            >
              CTA Sample
            </button>
          </div>
        </div>

        {/* Service Status Warning */}
        {serviceStatus && !serviceStatus.available && (
          <div className="p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
              <div>
                <h5 className="text-sm font-medium text-yellow-400">Voice Synthesis Unavailable</h5>
                <p className="text-xs text-gray-400 mt-1">
                  {serviceStatus.error || 'The voice synthesis service is not available.'}
                </p>
                {serviceStatus.python_version_required && (
                  <div className="mt-2 p-2 bg-black/20 rounded text-xs">
                    <p className="text-yellow-300">Python Version Requirement:</p>
                    <p className="text-gray-400 mt-1">
                      Required: <span className="text-white">{serviceStatus.python_version_required}</span>
                    </p>
                    <p className="text-gray-400">
                      Current: <span className="text-red-400">{serviceStatus.python_version_current}</span>
                    </p>
                  </div>
                )}
                <p className="text-xs text-gray-500 mt-2">
                  {serviceStatus.python_version_required
                    ? 'Please upgrade to Python 3.10 or higher to use voice synthesis.'
                    : 'Please ensure the NeuTTS Air model is properly installed and configured.'}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Service Status OK */}
        {serviceStatus?.available && (
          <div className="p-3 bg-green-500/10 border border-green-500/30 rounded-lg">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-green-400" />
              <span className="text-sm text-green-400">
                Voice synthesis service is ready
                {serviceStatus.model_loaded ? ' (model loaded)' : ' (model will load on first use)'}
              </span>
            </div>
          </div>
        )}

        {/* Synthesis Error Display */}
        {synthesisError && (
          <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <h5 className="text-sm font-medium text-red-400">Synthesis Failed</h5>
                <p className="text-xs text-gray-400 mt-1">{synthesisError}</p>
              </div>
            </div>
          </div>
        )}

        {/* Synthesize Button */}
        <Button
          variant="primary"
          icon={synthesizeMutation.isPending ? Loader2 : Volume2}
          onClick={() => synthesizeMutation.mutate()}
          loading={synthesizeMutation.isPending}
          disabled={!testText.trim() || (serviceStatus && !serviceStatus.available)}
          className="w-full"
        >
          {synthesizeMutation.isPending ? 'Synthesizing...' : 'Generate Voice'}
        </Button>

        {/* Synthesized Audio Result */}
        {synthesizedAudioUrl && (
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-gray-300">
              Synthesized Audio Result
            </h4>
            <AudioPlayer
              src={synthesizedAudioUrl}
              title={`${profile.name}_test.wav`}
            />
            <div className="flex gap-2">
              <a
                href={synthesizedAudioUrl}
                download={`${profile.name}_test.wav`}
                className="inline-flex items-center gap-2 text-sm text-[var(--rednote-primary)] hover:underline"
              >
                <Download className="w-4 h-4" />
                Download Audio
              </a>
            </div>
          </div>
        )}

        {/* Tips */}
        <div className="p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
          <h5 className="text-sm font-medium text-blue-400 mb-1">Tips for best results:</h5>
          <ul className="text-xs text-gray-400 space-y-1">
            <li>• Use Hindi text for best voice cloning results</li>
            <li>• Keep test text between 20-200 characters</li>
            <li>• The synthesized voice will mimic the reference audio style</li>
            <li>• First synthesis may take longer as the model loads</li>
          </ul>
        </div>
      </div>
    </Modal>
  );
}

export default VoiceTestModal;
