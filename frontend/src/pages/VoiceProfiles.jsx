import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { Plus, Mic2, Info } from 'lucide-react';
import {
  VoiceProfileCard,
  VoiceProfileForm,
  VoiceTestModal,
  VoiceProfileDetailModal
} from '../components/voice';
import { Button, Modal, LoadingOverlay } from '../components/common';
import { voiceProfilesApi } from '../api';

export function VoiceProfiles() {
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [testModalOpen, setTestModalOpen] = useState(false);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [selectedProfile, setSelectedProfile] = useState(null);
  const queryClient = useQueryClient();

  // Fetch profiles
  const { data: profiles, isLoading } = useQuery({
    queryKey: ['voice-profiles'],
    queryFn: voiceProfilesApi.getAll,
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: voiceProfilesApi.delete,
    onSuccess: () => {
      toast.success('Voice profile deleted');
      queryClient.invalidateQueries(['voice-profiles']);
    },
    onError: (error) => toast.error(error),
  });

  const handleDelete = (id) => {
    if (window.confirm('Are you sure you want to delete this voice profile?')) {
      deleteMutation.mutate(id);
    }
  };

  const handleTest = (profile) => {
    setSelectedProfile(profile);
    setTestModalOpen(true);
  };

  const handleView = (profile) => {
    setSelectedProfile(profile);
    setDetailModalOpen(true);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Voice Profiles</h1>
          <p className="text-gray-400 mt-1">
            Manage voice profiles for audio synthesis
          </p>
        </div>

        <Button
          variant="primary"
          icon={Plus}
          onClick={() => setCreateModalOpen(true)}
        >
          New Profile
        </Button>
      </div>

      {/* Info card */}
      <div className="glass-card p-4 border-l-4 border-[var(--rednote-primary)]">
        <div className="flex items-start gap-3">
          <Mic2 className="w-5 h-5 text-[var(--rednote-primary)] flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-medium text-white">Voice Cloning</h3>
            <p className="text-sm text-gray-400 mt-1">
              Create voice profiles by uploading a reference audio file and its transcript.
              You can test the voice with custom text and use profiles to synthesize audio for your videos.
            </p>
            <div className="flex flex-wrap gap-2 mt-3">
              <span className="text-xs px-2 py-1 bg-white/10 rounded">Play Reference</span>
              <span className="text-xs px-2 py-1 bg-white/10 rounded">Test Voice</span>
              <span className="text-xs px-2 py-1 bg-white/10 rounded">View Details</span>
            </div>
          </div>
        </div>
      </div>

      {/* Profiles list */}
      {isLoading ? (
        <LoadingOverlay message="Loading voice profiles..." />
      ) : profiles && profiles.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {profiles.map((profile) => (
            <VoiceProfileCard
              key={profile.id}
              profile={profile}
              onDelete={handleDelete}
              onTest={handleTest}
              onView={handleView}
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <Mic2 className="w-12 h-12 mx-auto text-gray-500 mb-4" />
          <p className="text-gray-400 mb-2">No voice profiles yet</p>
          <p className="text-sm text-gray-500 mb-4">
            Create a voice profile to clone voices for your videos
          </p>
          <Button
            variant="primary"
            icon={Plus}
            onClick={() => setCreateModalOpen(true)}
          >
            Create Your First Profile
          </Button>
        </div>
      )}

      {/* How to use section */}
      <div className="glass-card p-6">
        <div className="flex items-center gap-2 mb-4">
          <Info className="w-5 h-5 text-blue-400" />
          <h3 className="font-medium text-white">How to Use Voice Profiles</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <div className="w-8 h-8 rounded-full bg-[var(--rednote-primary)]/20 flex items-center justify-center text-[var(--rednote-primary)] font-bold mb-2">1</div>
            <h4 className="font-medium text-white mb-1">Create Profile</h4>
            <p className="text-sm text-gray-400">
              Upload a clear audio sample (10-60s) and provide its exact transcript.
            </p>
          </div>
          <div>
            <div className="w-8 h-8 rounded-full bg-[var(--rednote-primary)]/20 flex items-center justify-center text-[var(--rednote-primary)] font-bold mb-2">2</div>
            <h4 className="font-medium text-white mb-1">Test Voice</h4>
            <p className="text-sm text-gray-400">
              Use the "Test Voice" button to generate sample audio and verify quality.
            </p>
          </div>
          <div>
            <div className="w-8 h-8 rounded-full bg-[var(--rednote-primary)]/20 flex items-center justify-center text-[var(--rednote-primary)] font-bold mb-2">3</div>
            <h4 className="font-medium text-white mb-1">Synthesize</h4>
            <p className="text-sm text-gray-400">
              Select the profile when synthesizing audio for your video prompts.
            </p>
          </div>
        </div>
      </div>

      {/* Create Modal */}
      <Modal
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        title="Create Voice Profile"
        size="md"
      >
        <VoiceProfileForm
          onSuccess={() => setCreateModalOpen(false)}
        />
      </Modal>

      {/* Test Modal */}
      <VoiceTestModal
        isOpen={testModalOpen}
        onClose={() => {
          setTestModalOpen(false);
          setSelectedProfile(null);
        }}
        profile={selectedProfile}
      />

      {/* Detail Modal */}
      <VoiceProfileDetailModal
        isOpen={detailModalOpen}
        onClose={() => {
          setDetailModalOpen(false);
          setSelectedProfile(null);
        }}
        profile={selectedProfile}
      />
    </div>
  );
}

export default VoiceProfiles;
