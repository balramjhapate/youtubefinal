import { useState } from 'react';
import {
  Download,
  FileText,
  Brain,
  MessageSquare,
  Volume2,
  MoreVertical,
  Trash2,
  Eye,
} from 'lucide-react';
import { StatusBadge, Button } from '../common';
import { truncateText, formatRelativeTime } from '../../utils/formatters';
import { useStore } from '../../store';

export function VideoCard({
  video,
  onDownload,
  onTranscribe,
  onProcessAI,
  onGeneratePrompt,
  onSynthesize,
  onDelete,
  isSelected,
  onSelect,
}) {
  const [showMenu, setShowMenu] = useState(false);
  const { openVideoDetail } = useStore();

  const handleAction = (action, e) => {
    e.stopPropagation();
    action();
    setShowMenu(false);
  };

  return (
    <div
      className={`glass-card p-4 transition-all cursor-pointer hover:border-white/20 ${
        isSelected ? 'ring-2 ring-[var(--rednote-primary)]' : ''
      }`}
      onClick={() => openVideoDetail(video.id)}
    >
      <div className="flex gap-4">
        {/* Selection checkbox */}
        <div className="flex items-start pt-1">
          <input
            type="checkbox"
            checked={isSelected}
            onChange={(e) => {
              e.stopPropagation();
              onSelect(video.id);
            }}
            className="w-4 h-4 rounded border-gray-600 bg-white/10 text-[var(--rednote-primary)] focus:ring-[var(--rednote-primary)]"
          />
        </div>

        {/* Thumbnail */}
        <div className="w-24 h-24 flex-shrink-0 rounded-lg overflow-hidden bg-white/5">
          {video.cover_url ? (
            <img
              src={video.cover_url}
              alt={video.title}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-gray-500">
              No Image
            </div>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <h3 className="font-medium text-white truncate">
              {truncateText(video.title, 60) || 'Untitled'}
            </h3>

            {/* Menu */}
            <div className="relative">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShowMenu(!showMenu);
                }}
                className="p-1 rounded hover:bg-white/10"
              >
                <MoreVertical className="w-4 h-4 text-gray-400" />
              </button>

              {showMenu && (
                <>
                  <div
                    className="fixed inset-0 z-10"
                    onClick={(e) => {
                      e.stopPropagation();
                      setShowMenu(false);
                    }}
                  />
                  <div className="absolute right-0 top-full mt-1 z-20 glass-card p-2 min-w-[160px]">
                    <button
                      onClick={(e) => handleAction(() => openVideoDetail(video.id), e)}
                      className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left rounded hover:bg-white/10"
                    >
                      <Eye className="w-4 h-4" />
                      View Details
                    </button>
                    <button
                      onClick={(e) => handleAction(onDelete, e)}
                      className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left rounded hover:bg-white/10 text-red-400"
                    >
                      <Trash2 className="w-4 h-4" />
                      Delete
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Status badges */}
          <div className="flex flex-wrap gap-2 mt-2">
            <StatusBadge status={video.status} />
            <StatusBadge status={video.transcription_status} />
            <StatusBadge status={video.ai_processing_status} />
            <StatusBadge status={video.audio_prompt_status} />
            {video.synthesis_status !== 'not_synthesized' && (
              <StatusBadge status={video.synthesis_status} />
            )}
          </div>

          {/* Meta info */}
          <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
            <span>{formatRelativeTime(video.created_at)}</span>
            {video.is_downloaded && (
              <span className="text-green-400">Downloaded</span>
            )}
            {video.voice_profile_name && (
              <span>Voice: {video.voice_profile_name}</span>
            )}
          </div>

          {/* Action buttons */}
          <div className="flex flex-wrap gap-2 mt-3">
            {!video.is_downloaded && video.status === 'success' && (
              <Button
                size="sm"
                variant="secondary"
                icon={Download}
                onClick={(e) => handleAction(onDownload, e)}
              >
                Download
              </Button>
            )}

            {video.transcription_status === 'not_transcribed' && (
              <Button
                size="sm"
                variant="secondary"
                icon={FileText}
                onClick={(e) => handleAction(onTranscribe, e)}
              >
                Transcribe
              </Button>
            )}

            {video.ai_processing_status === 'not_processed' && (
              <Button
                size="sm"
                variant="secondary"
                icon={Brain}
                onClick={(e) => handleAction(onProcessAI, e)}
              >
                AI Process
              </Button>
            )}

            {video.audio_prompt_status === 'not_generated' &&
              video.transcription_status === 'transcribed' && (
                <Button
                  size="sm"
                  variant="secondary"
                  icon={MessageSquare}
                  onClick={(e) => handleAction(onGeneratePrompt, e)}
                >
                  Gen Prompt
                </Button>
              )}

            {video.audio_prompt_status === 'generated' &&
              video.synthesis_status !== 'synthesized' && (
                <Button
                  size="sm"
                  variant="secondary"
                  icon={Volume2}
                  onClick={(e) => handleAction(onSynthesize, e)}
                >
                  Synthesize
                </Button>
              )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default VideoCard;
