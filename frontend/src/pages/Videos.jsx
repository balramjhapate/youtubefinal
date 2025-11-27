import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, Filter, Plus, Loader2 } from "lucide-react";
import { VideoList, VideoExtractModal } from "../components/video";
import { Button, Input, Select } from "../components/common";
import { videosApi } from "../api";
import { isVideoProcessing } from "../utils/formatters";

const STATUS_OPTIONS = [
	{ value: "", label: "All Status" },
	{ value: "success", label: "Success" },
	{ value: "failed", label: "Failed" },
	{ value: "pending", label: "Pending" },
];

const TRANSCRIPTION_OPTIONS = [
	{ value: "", label: "All Transcription" },
	{ value: "not_transcribed", label: "Not Transcribed" },
	{ value: "transcribing", label: "Transcribing" },
	{ value: "transcribed", label: "Transcribed" },
	{ value: "failed", label: "Failed" },
];

export function Videos() {
	const [extractModalOpen, setExtractModalOpen] = useState(false);
	const [filters, setFilters] = useState({
		status: "",
		transcription_status: "",
		search: "",
	});

	// Fetch videos
	const { data: videos, isLoading } = useQuery({
		queryKey: ["videos", filters],
		queryFn: () => videosApi.getAll(filters),
	});

	// Filter videos locally for search
	const filteredVideos = videos?.filter((video) => {
		if (!filters.search) return true;
		const searchLower = filters.search.toLowerCase();
		return (
			video.title?.toLowerCase().includes(searchLower) ||
			video.original_title?.toLowerCase().includes(searchLower) ||
			video.video_id?.toLowerCase().includes(searchLower)
		);
	});

	// Count processing videos
	const processingVideos = filteredVideos?.filter(isVideoProcessing) || [];
	const processingCount = processingVideos.length;

	return (
		<div className="space-y-6">
			{/* Header */}
			<div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
				<div>
					<h1 className="text-2xl font-bold text-white">Videos</h1>
					<p className="text-gray-400 mt-1">
						Manage your extracted Xiaohongshu videos
					</p>
				</div>

				<Button
					variant="primary"
					icon={Plus}
					onClick={() => setExtractModalOpen(true)}>
					Add Video
				</Button>
			</div>

			{/* Processing Alert */}
			{processingCount > 0 && (
				<div className="glass-card p-4 bg-yellow-500/10 border border-yellow-500/30">
					<div className="flex items-center gap-3">
						<Loader2 className="w-5 h-5 text-yellow-400 animate-spin" />
						<div>
							<p className="text-sm font-medium text-yellow-400">
								{processingCount} video
								{processingCount !== 1 ? "s" : ""} currently
								processing
							</p>
							<p className="text-xs text-yellow-300/70 mt-0.5">
								Reprocess buttons are disabled while videos are
								being processed
							</p>
						</div>
					</div>
				</div>
			)}

			{/* Filters */}
			<div className="glass-card p-4">
				<div className="flex flex-col md:flex-row gap-4">
					{/* Search */}
					<div className="flex-1 relative">
						<Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
						<input
							type="text"
							placeholder="Search by title or video ID..."
							value={filters.search}
							onChange={(e) =>
								setFilters({
									...filters,
									search: e.target.value,
								})
							}
							className="w-full pl-10 pr-4 py-2.5 rounded-lg input-dark"
						/>
					</div>

					{/* Status filter */}
					<div className="w-full md:w-48">
						<Select
							value={filters.status}
							onChange={(e) =>
								setFilters({
									...filters,
									status: e.target.value,
								})
							}
							options={STATUS_OPTIONS}
							placeholder="Status"
						/>
					</div>

					{/* Transcription filter */}
					<div className="w-full md:w-48">
						<Select
							value={filters.transcription_status}
							onChange={(e) =>
								setFilters({
									...filters,
									transcription_status: e.target.value,
								})
							}
							options={TRANSCRIPTION_OPTIONS}
							placeholder="Transcription"
						/>
					</div>

					{/* Clear filters */}
					{(filters.status ||
						filters.transcription_status ||
						filters.search) && (
						<Button
							variant="ghost"
							onClick={() =>
								setFilters({
									status: "",
									transcription_status: "",
									search: "",
								})
							}>
							Clear
						</Button>
					)}
				</div>
			</div>

			{/* Video List */}
			<VideoList videos={filteredVideos || []} isLoading={isLoading} />

			{/* Extract Modal */}
			<VideoExtractModal
				isOpen={extractModalOpen}
				onClose={() => setExtractModalOpen(false)}
			/>
		</div>
	);
}

export default Videos;
