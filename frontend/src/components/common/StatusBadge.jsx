import { STATUS_BADGE_CONFIG } from '../../utils/constants';
import { Check, X, Loader2, Clock } from 'lucide-react';

export function StatusBadge({ status, showIcon = true, className = '' }) {
  const config = STATUS_BADGE_CONFIG[status] || {
    label: status,
    className: 'badge-pending',
  };

  const getIcon = () => {
    if (!showIcon) return null;

    if (status === 'success' || status === 'transcribed' || status === 'processed' || status === 'generated' || status === 'synthesized') {
      return <Check className="w-3 h-3" />;
    }
    if (status === 'failed') {
      return <X className="w-3 h-3" />;
    }
    if (status === 'transcribing' || status === 'processing' || status === 'generating' || status === 'synthesizing') {
      return <Loader2 className="w-3 h-3 animate-spin" />;
    }
    return <Clock className="w-3 h-3" />;
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full ${config.className} ${className}`}
    >
      {getIcon()}
      {config.label}
    </span>
  );
}

export default StatusBadge;
