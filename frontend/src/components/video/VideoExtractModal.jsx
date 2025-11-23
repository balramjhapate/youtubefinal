import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { Link2 } from 'lucide-react';
import { Modal, Button, Input } from '../common';
import { videosApi } from '../../api';
import { isValidXhsUrl } from '../../utils/formatters';

export function VideoExtractModal({ isOpen, onClose }) {
  const [url, setUrl] = useState('');
  const [error, setError] = useState('');
  const queryClient = useQueryClient();

  const extractMutation = useMutation({
    mutationFn: videosApi.extract,
    onSuccess: (data) => {
      toast.success(data.cached ? 'Video found in cache!' : 'Video extracted successfully!');
      queryClient.invalidateQueries(['videos']);
      queryClient.invalidateQueries(['dashboard-stats']);
      handleClose();
    },
    onError: (error) => {
      setError(error);
      toast.error(error);
    },
  });

  const handleClose = () => {
    setUrl('');
    setError('');
    onClose();
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');

    if (!url.trim()) {
      setError('Please enter a URL');
      return;
    }

    if (!isValidXhsUrl(url)) {
      setError('Please enter a valid Xiaohongshu URL');
      return;
    }

    extractMutation.mutate(url);
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Add New Video"
      size="md"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <Input
            label="Xiaohongshu URL"
            placeholder="https://www.xiaohongshu.com/explore/..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            error={error}
            autoFocus
          />
          <p className="mt-2 text-xs text-gray-500">
            Paste a Xiaohongshu video URL to extract and save the video
          </p>
        </div>

        <div className="flex gap-3 justify-end">
          <Button
            type="button"
            variant="secondary"
            onClick={handleClose}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            icon={Link2}
            loading={extractMutation.isPending}
          >
            Extract Video
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export default VideoExtractModal;
