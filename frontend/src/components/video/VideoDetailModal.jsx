import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  Download,
  FileText,
  Brain,
  MessageSquare,
  Volume2,
  Play,
  Globe,
  Copy,
  ExternalLink,
} from 'lucide-react';
import { Modal, Button, StatusBadge, AudioPlayer, LoadingSpinner, Select } from '../common';
import { videosApi, voiceProfilesApi } from '../../api';
import { formatDate, truncateText } from '../../utils/formatters';
import { useStore } from '../../store';

export function VideoDetailModal() {
  const { videoDetailModalOpen, selectedVideoId, closeVideoDetail } = useStore();
  const queryClient = useQueryClient();
  const [selectedProfileId, setSelectedProfileId] = useState('');
  const [activeTab, setActiveTab] = useState('info');

  // Fetch video details
  const { data: video, isLoading } = useQuery({
    queryKey: ['video', selectedVideoId],
    queryFn: () => videosApi.getById(selectedVideoId),
    enabled: !!selectedVideoId,
  });

  // Fetch voice profiles
  const { data: profiles } = useQuery({
    queryKey: ['voice-profiles'],
    queryFn: voiceProfilesApi.getAll,
  });

  // Mutations
  const downloadMutation = useMutation({
    mutationFn: () => videosApi.download(selectedVideoId),
    onSuccess: () => {
      toast.success('Video downloaded successfully');
      queryClient.invalidateQueries(['video', selectedVideoId]);
    },
    onError: (error) => toast.error(error),
  });

  const transcribeMutation = useMutation({
    mutationFn: () => videosApi.transcribe(selectedVideoId),
    onSuccess: () => {
      toast.success('Transcription started');
      queryClient.invalidateQueries(['video', selectedVideoId]);
    },
    onError: (error) => toast.error(error),
  });

  const processAIMutation = useMutation({
    mutationFn: () => videosApi.processAI(selectedVideoId),
    onSuccess: () => {
      toast.success('AI processing completed');
      queryClient.invalidateQueries(['video', selectedVideoId]);
    },
    onError: (error) => toast.error(error),
  });

  const generatePromptMutation = useMutation({
    mutationFn: () => videosApi.generateAudioPrompt(selectedVideoId),
    onSuccess: () => {
      toast.success('Audio prompt generated');
      queryClient.invalidateQueries(['video', selectedVideoId]);
    },
    onError: (error) => toast.error(error),
  });

  const synthesizeMutation = useMutation({
    mutationFn: () => videosApi.synthesize(selectedVideoId, selectedProfileId),
    onSuccess: () => {
      toast.success('Audio synthesized successfully');
      queryClient.invalidateQueries(['video', selectedVideoId]);
    },
    onError: (error) => toast.error(error),
  });

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  if (!videoDetailModalOpen) return null;

  const tabs = [
    { id: 'info', label: 'Info' },
    { id: 'transcript', label: 'Transcript' },
    { id: 'ai', label: 'AI Summary' },
    { id: 'audio', label: 'Audio Prompt' },
    { id: 'synthesis', label: 'Synthesis' },
  ];

  return (
    <Modal
      isOpen={videoDetailModalOpen}
      onClose={closeVideoDetail}
      title="Video Details"
      size="xl"
    >
      {isLoading ? (
        <div className="flex justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      ) : video ? (
        <div className="space-y-6">
          {/* Video preview */}
          <div className="flex flex-col md:flex-row gap-6">
            {/* Video player or thumbnail */}
            <div className="w-full md:w-1/2">
              {video.video_url ? (
                <div className="relative rounded-lg overflow-hidden bg-black aspect-video">
                  <video
                    src={video.video_url}
                    poster={video.cover_url}
                    controls
                    className="w-full h-full"
                  />
                </div>
              ) : video.cover_url ? (
                <img
                  src={video.cover_url}
                  alt={video.title}
                  className="w-full rounded-lg"
                />
              ) : (
                <div className="w-full aspect-video bg-white/5 rounded-lg flex items-center justify-center">
                  <Play className="w-12 h-12 text-gray-500" />
                </div>
              )}
            </div>

            {/* Info panel */}
            <div className="w-full md:w-1/2 space-y-4">
              <h3 className="text-lg font-semibold">
                {video.title || 'Untitled'}
              </h3>

              {video.original_title && video.original_title !== video.title && (
                <p className="text-sm text-gray-400">
                  {video.original_title}
                </p>
              )}

              {/* Status badges */}
              <div className="flex flex-wrap gap-2">
                <StatusBadge status={video.status} />
                <StatusBadge status={video.transcription_status} />
                <StatusBadge status={video.ai_processing_status} />
                <StatusBadge status={video.audio_prompt_status} />
                <StatusBadge status={video.synthesis_status} />
              </div>

              {/* Meta info */}
              <div className="text-sm text-gray-400 space-y-1">
                <p>Created: {formatDate(video.created_at)}</p>
                <p>Method: {video.extraction_method || '-'}</p>
                {video.is_downloaded && (
                  <p className="text-green-400">Downloaded locally</p>
                )}
              </div>

              {/* Action buttons */}
              <div className="flex flex-wrap gap-2">
                {!video.is_downloaded && video.status === 'success' && (
                  <Button
                    size="sm"
                    variant="secondary"
                    icon={Download}
                    onClick={() => downloadMutation.mutate()}
                    loading={downloadMutation.isPending}
                  >
                    Download
                  </Button>
                )}

                {video.transcription_status === 'not_transcribed' && (
                  <Button
                    size="sm"
                    variant="secondary"
                    icon={FileText}
                    onClick={() => transcribeMutation.mutate()}
                    loading={transcribeMutation.isPending}
                  >
                    Transcribe
                  </Button>
                )}

                {video.ai_processing_status === 'not_processed' && (
                  <Button
                    size="sm"
                    variant="secondary"
                    icon={Brain}
                    onClick={() => processAIMutation.mutate()}
                    loading={processAIMutation.isPending}
                  >
                    Process AI
                  </Button>
                )}

                <a
                  href={video.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg btn-secondary"
                >
                  <ExternalLink className="w-4 h-4" />
                  Original
                </a>
              </div>
            </div>
          </div>

          {/* Tabs */}
          <div className="border-b border-white/10">
            <div className="flex gap-1">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
                    activeTab === tab.id
                      ? 'bg-white/10 text-white'
                      : 'text-gray-400 hover:text-white hover:bg-white/5'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {/* Tab content */}
          <div className="min-h-[200px]">
            {activeTab === 'info' && (
              <div className="space-y-4">
                <div>
                  <h4 className="text-sm font-medium text-gray-400 mb-2">Description</h4>
                  <p className="text-sm">
                    {video.description || 'No description available'}
                  </p>
                </div>
                {video.original_description && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-400 mb-2">Original Description</h4>
                    <p className="text-sm text-gray-400">
                      {video.original_description}
                    </p>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'transcript' && (
              <div className="space-y-4">
                {video.transcript ? (
                  <>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-400">
                        Language: {video.transcript_language || 'Unknown'}
                      </span>
                      <Button
                        size="sm"
                        variant="ghost"
                        icon={Copy}
                        onClick={() => copyToClipboard(video.transcript)}
                      >
                        Copy
                      </Button>
                    </div>
                    <div className="p-4 bg-white/5 rounded-lg max-h-64 overflow-y-auto">
                      <p className="text-sm whitespace-pre-wrap">{video.transcript}</p>
                    </div>
                    {video.transcript_hindi && (
                      <div>
                        <h4 className="text-sm font-medium text-gray-400 mb-2 flex items-center gap-2">
                          <Globe className="w-4 h-4" />
                          Hindi Translation
                        </h4>
                        <div className="p-4 bg-white/5 rounded-lg max-h-64 overflow-y-auto">
                          <p className="text-sm whitespace-pre-wrap">{video.transcript_hindi}</p>
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="text-center py-8 text-gray-400">
                    <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>No transcript available</p>
                    {video.transcription_status === 'not_transcribed' && (
                      <Button
                        size="sm"
                        variant="primary"
                        className="mt-4"
                        onClick={() => transcribeMutation.mutate()}
                        loading={transcribeMutation.isPending}
                      >
                        Start Transcription
                      </Button>
                    )}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'ai' && (
              <div className="space-y-4">
                {video.ai_summary ? (
                  <>
                    <div>
                      <h4 className="text-sm font-medium text-gray-400 mb-2">Summary</h4>
                      <div className="p-4 bg-white/5 rounded-lg">
                        <p className="text-sm">{video.ai_summary}</p>
                      </div>
                    </div>
                    {video.ai_tags && (
                      <div>
                        <h4 className="text-sm font-medium text-gray-400 mb-2">Tags</h4>
                        <div className="flex flex-wrap gap-2">
                          {video.ai_tags.split(',').map((tag, i) => (
                            <span
                              key={i}
                              className="px-2 py-1 text-xs bg-white/10 rounded"
                            >
                              {tag.trim()}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="text-center py-8 text-gray-400">
                    <Brain className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>No AI summary available</p>
                    {video.ai_processing_status === 'not_processed' && (
                      <Button
                        size="sm"
                        variant="primary"
                        className="mt-4"
                        onClick={() => processAIMutation.mutate()}
                        loading={processAIMutation.isPending}
                      >
                        Process with AI
                      </Button>
                    )}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'audio' && (
              <div className="space-y-4">
                {video.audio_generation_prompt ? (
                  <>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-400">
                        Generated at: {formatDate(video.audio_prompt_generated_at)}
                      </span>
                      <Button
                        size="sm"
                        variant="ghost"
                        icon={Copy}
                        onClick={() => copyToClipboard(video.audio_generation_prompt)}
                      >
                        Copy
                      </Button>
                    </div>
                    <div className="p-4 bg-white/5 rounded-lg max-h-96 overflow-y-auto">
                      <p className="text-sm whitespace-pre-wrap">
                        {video.audio_generation_prompt}
                      </p>
                    </div>
                  </>
                ) : (
                  <div className="text-center py-8 text-gray-400">
                    <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>No audio prompt generated</p>
                    {video.audio_prompt_status === 'not_generated' &&
                      video.transcription_status === 'transcribed' && (
                        <Button
                          size="sm"
                          variant="primary"
                          className="mt-4"
                          onClick={() => generatePromptMutation.mutate()}
                          loading={generatePromptMutation.isPending}
                        >
                          Generate Audio Prompt
                        </Button>
                      )}
                    {video.transcription_status !== 'transcribed' && (
                      <p className="text-sm mt-2">
                        Transcribe the video first to generate audio prompts
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'synthesis' && (
              <div className="space-y-4">
                {video.synthesized_audio_url ? (
                  <div>
                    <h4 className="text-sm font-medium text-gray-400 mb-3">
                      Synthesized Audio
                    </h4>
                    <AudioPlayer
                      src={video.synthesized_audio_url}
                      title={`${video.title}_synthesized.wav`}
                    />
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <Volume2 className="w-12 h-12 mx-auto mb-3 opacity-50 text-gray-400" />
                    <p className="text-gray-400 mb-4">No synthesized audio yet</p>

                    {video.audio_prompt_status === 'generated' && (
                      <div className="max-w-sm mx-auto space-y-4">
                        <Select
                          label="Voice Profile"
                          value={selectedProfileId}
                          onChange={(e) => setSelectedProfileId(e.target.value)}
                          options={
                            profiles?.map((p) => ({
                              value: p.id,
                              label: p.name,
                            })) || []
                          }
                          placeholder="Select a voice profile"
                        />

                        <Button
                          variant="primary"
                          icon={Volume2}
                          onClick={() => synthesizeMutation.mutate()}
                          loading={synthesizeMutation.isPending}
                          disabled={!selectedProfileId}
                          className="w-full"
                        >
                          Synthesize Audio
                        </Button>
                      </div>
                    )}

                    {video.audio_prompt_status !== 'generated' && (
                      <p className="text-sm text-gray-500">
                        Generate an audio prompt first to synthesize audio
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="text-center py-12 text-gray-400">
          Video not found
        </div>
      )}
    </Modal>
  );
}

export default VideoDetailModal;
