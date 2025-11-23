import { useState } from 'react';
import { Mic2, Trash2, Calendar, Play, Pause, TestTube, Eye } from 'lucide-react';
import { formatDate } from '../../utils/formatters';
import { Button } from '../common';

export function VoiceProfileCard({ profile, onDelete, onTest, onView }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [audioElement, setAudioElement] = useState(null);

  const handlePlayReference = () => {
    if (!profile.reference_audio_url) return;

    if (isPlaying && audioElement) {
      audioElement.pause();
      setIsPlaying(false);
      return;
    }

    const audio = new Audio(profile.reference_audio_url);
    audio.onended = () => setIsPlaying(false);
    audio.onerror = () => {
      setIsPlaying(false);
      console.error('Error playing audio');
    };
    audio.play();
    setAudioElement(audio);
    setIsPlaying(true);
  };

  return (
    <div className="glass-card p-4 hover:border-white/20 transition-all">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-lg bg-[var(--rednote-primary)]/20 flex items-center justify-center">
            <Mic2 className="w-6 h-6 text-[var(--rednote-primary)]" />
          </div>
          <div>
            <h3 className="font-medium text-white">{profile.name}</h3>
            <div className="flex items-center gap-2 text-xs text-gray-400 mt-1">
              <Calendar className="w-3 h-3" />
              {formatDate(profile.created_at)}
            </div>
          </div>
        </div>

        <button
          onClick={() => onDelete(profile.id)}
          className="p-2 rounded-lg hover:bg-white/10 text-gray-400 hover:text-red-400 transition-colors"
          title="Delete profile"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      {/* Reference Text Preview */}
      {profile.reference_text && (
        <div className="mt-3 p-3 bg-white/5 rounded-lg">
          <p className="text-xs text-gray-500 mb-1">Reference Text:</p>
          <p className="text-sm text-gray-300 line-clamp-2">
            {profile.reference_text}
          </p>
        </div>
      )}

      {/* Audio Controls */}
      <div className="mt-4 flex flex-wrap gap-2">
        {profile.reference_audio_url && (
          <Button
            size="sm"
            variant="secondary"
            icon={isPlaying ? Pause : Play}
            onClick={handlePlayReference}
          >
            {isPlaying ? 'Stop' : 'Play Reference'}
          </Button>
        )}

        <Button
          size="sm"
          variant="secondary"
          icon={TestTube}
          onClick={() => onTest(profile)}
        >
          Test Voice
        </Button>

        <Button
          size="sm"
          variant="ghost"
          icon={Eye}
          onClick={() => onView(profile)}
        >
          Details
        </Button>
      </div>
    </div>
  );
}

export default VoiceProfileCard;
