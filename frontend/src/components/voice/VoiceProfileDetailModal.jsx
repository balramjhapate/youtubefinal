import { useState, useRef } from 'react';
import { Mic2, Play, Pause, Calendar, FileAudio, FileText, Copy } from 'lucide-react';
import { Modal, Button, AudioPlayer } from '../common';
import { formatDate } from '../../utils/formatters';
import toast from 'react-hot-toast';

export function VoiceProfileDetailModal({ isOpen, onClose, profile }) {
  const [isPlayingRef, setIsPlayingRef] = useState(false);
  const refAudioRef = useRef(null);

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
      toast.error('Error playing audio');
    };
    audio.play();
    refAudioRef.current = audio;
    setIsPlayingRef(true);
  };

  const handleCopyText = () => {
    if (profile?.reference_text) {
      navigator.clipboard.writeText(profile.reference_text);
      toast.success('Reference text copied!');
    }
  };

  const handleClose = () => {
    if (refAudioRef.current) {
      refAudioRef.current.pause();
    }
    onClose();
  };

  if (!profile) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Voice Profile Details"
      size="lg"
    >
      <div className="space-y-6">
        {/* Profile Header */}
        <div className="flex items-center gap-4">
          <div className="w-20 h-20 rounded-xl bg-[var(--rednote-primary)]/20 flex items-center justify-center">
            <Mic2 className="w-10 h-10 text-[var(--rednote-primary)]" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-white">{profile.name}</h2>
            <div className="flex items-center gap-2 text-sm text-gray-400 mt-1">
              <Calendar className="w-4 h-4" />
              Created: {formatDate(profile.created_at)}
            </div>
          </div>
        </div>

        {/* Reference Audio Section */}
        <div className="glass-card p-4">
          <div className="flex items-center gap-2 mb-3">
            <FileAudio className="w-5 h-5 text-[var(--rednote-primary)]" />
            <h3 className="font-medium text-white">Reference Audio</h3>
          </div>

          {profile.reference_audio_url ? (
            <div className="space-y-3">
              <AudioPlayer
                src={profile.reference_audio_url}
                title={`${profile.name}_reference.wav`}
              />
              <p className="text-xs text-gray-500">
                This is the original voice sample used to create this profile.
                The synthesized voice will mimic this style.
              </p>
            </div>
          ) : (
            <p className="text-gray-400 text-sm">No reference audio available</p>
          )}
        </div>

        {/* Reference Text Section */}
        <div className="glass-card p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-[var(--rednote-primary)]" />
              <h3 className="font-medium text-white">Reference Text (Transcript)</h3>
            </div>
            <Button
              size="sm"
              variant="ghost"
              icon={Copy}
              onClick={handleCopyText}
            >
              Copy
            </Button>
          </div>

          {profile.reference_text ? (
            <div className="p-3 bg-white/5 rounded-lg max-h-48 overflow-y-auto">
              <p className="text-sm text-gray-300 whitespace-pre-wrap">
                {profile.reference_text}
              </p>
            </div>
          ) : (
            <p className="text-gray-400 text-sm">No reference text available</p>
          )}
        </div>

        {/* Profile Info */}
        <div className="glass-card p-4">
          <h3 className="font-medium text-white mb-3">Profile Information</h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-gray-500">Profile ID</p>
              <p className="text-white">{profile.id}</p>
            </div>
            <div>
              <p className="text-gray-500">Name</p>
              <p className="text-white">{profile.name}</p>
            </div>
            <div>
              <p className="text-gray-500">Created</p>
              <p className="text-white">{formatDate(profile.created_at)}</p>
            </div>
            <div>
              <p className="text-gray-500">Text Length</p>
              <p className="text-white">{profile.reference_text?.length || 0} characters</p>
            </div>
          </div>
        </div>

        {/* Usage Tips */}
        <div className="p-4 bg-[var(--rednote-primary)]/10 border border-[var(--rednote-primary)]/30 rounded-lg">
          <h4 className="font-medium text-[var(--rednote-primary)] mb-2">How to use this voice profile:</h4>
          <ol className="text-sm text-gray-300 space-y-1 list-decimal list-inside">
            <li>Go to a video's detail page</li>
            <li>Generate an audio prompt from the transcript</li>
            <li>Select this voice profile for synthesis</li>
            <li>Click "Synthesize Audio" to generate the voiceover</li>
          </ol>
        </div>
      </div>
    </Modal>
  );
}

export default VoiceProfileDetailModal;
