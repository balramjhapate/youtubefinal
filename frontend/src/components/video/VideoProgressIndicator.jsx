import { Loader2 } from 'lucide-react';

export function VideoProgressIndicator({ label, progress, showPercentage = true }) {
  return (
    <div className="mt-2 space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-gray-400 flex items-center gap-1.5">
          <Loader2 className="w-3 h-3 animate-spin" />
          {label}
        </span>
        {showPercentage && (
          <span className="text-gray-300 font-medium">{Math.round(progress)}%</span>
        )}
      </div>
      <div className="w-full h-1.5 bg-white/10 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-[var(--rednote-primary)] to-[var(--rednote-primary)]/80 transition-all duration-300 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}

export default VideoProgressIndicator;

