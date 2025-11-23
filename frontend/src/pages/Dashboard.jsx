import { useQuery } from '@tanstack/react-query';
import {
  Video,
  Download,
  FileText,
  Brain,
  MessageSquare,
  Volume2,
  AlertCircle,
  CheckCircle,
} from 'lucide-react';
import { PageLoader } from '../components/common';
import { VideoList } from '../components/video';
import { settingsApi, videosApi } from '../api';

function StatCard({ icon: Icon, label, value, color }) {
  const colorClasses = {
    primary: 'bg-[var(--rednote-primary)]/20 text-[var(--rednote-primary)]',
    green: 'bg-green-500/20 text-green-400',
    blue: 'bg-blue-500/20 text-blue-400',
    purple: 'bg-purple-500/20 text-purple-400',
    orange: 'bg-orange-500/20 text-orange-400',
    pink: 'bg-pink-500/20 text-pink-400',
    red: 'bg-red-500/20 text-red-400',
    gray: 'bg-gray-500/20 text-gray-400',
  };

  return (
    <div className="glass-card p-4">
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${colorClasses[color]}`}>
          <Icon className="w-5 h-5" />
        </div>
        <div>
          <p className="text-2xl font-bold text-white">{value}</p>
          <p className="text-xs text-gray-400">{label}</p>
        </div>
      </div>
    </div>
  );
}

export function Dashboard() {
  // Fetch stats
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: settingsApi.getDashboardStats,
    refetchInterval: 10000, // Refresh every 10 seconds
  });

  // Fetch videos
  const { data: videos, isLoading: videosLoading } = useQuery({
    queryKey: ['videos'],
    queryFn: () => videosApi.getAll(),
    refetchInterval: 5000, // Refresh every 5 seconds
  });

  if (statsLoading && videosLoading) {
    return <PageLoader />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-gray-400 mt-1">
          Overview of your RedNote video collection
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          icon={Video}
          label="Total Videos"
          value={stats?.total_videos || 0}
          color="primary"
        />
        <StatCard
          icon={CheckCircle}
          label="Successful"
          value={stats?.successful_extractions || 0}
          color="green"
        />
        <StatCard
          icon={Download}
          label="Downloaded"
          value={stats?.downloaded_locally || 0}
          color="blue"
        />
        <StatCard
          icon={FileText}
          label="Transcribed"
          value={stats?.transcribed || 0}
          color="purple"
        />
        <StatCard
          icon={Brain}
          label="AI Processed"
          value={stats?.ai_processed || 0}
          color="orange"
        />
        <StatCard
          icon={MessageSquare}
          label="Prompts Generated"
          value={stats?.audio_prompts_generated || 0}
          color="pink"
        />
        <StatCard
          icon={Volume2}
          label="Synthesized"
          value={stats?.synthesized || 0}
          color="green"
        />
        <StatCard
          icon={AlertCircle}
          label="Failed"
          value={stats?.failed || 0}
          color="red"
        />
      </div>

      {/* Recent Videos */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-4">Recent Videos</h2>
        <VideoList
          videos={videos?.slice(0, 10) || []}
          isLoading={videosLoading}
        />
      </div>
    </div>
  );
}

export default Dashboard;
