import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
	Download,
	FileText,
	Brain,
	MessageSquare,
	Volume2,
	Trash2,
	Eye,
	RefreshCw,
	Loader2,
} from "lucide-react";
import { StatusBadge, Button } from "../common";
import { VideoProgressIndicator } from "./VideoProgressIndicator";
import {
	truncateText,
	formatRelativeTime,
	formatDuration,
} from "../../utils/formatters";
import { useStore } from "../../store";
import { videosApi } from "../../api";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { showSuccess, showError, showConfirm } from "../../utils/alerts";

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
	const [progress, setProgress] = useState(0);
	const queryClient = useQueryClient();
	const navigate = useNavigate();
	const {
		getProcessingState,
		startProcessing,
		updateProcessingProgress,
		completeProcessing,
	} = useStore();

	// Reprocess mutation
	const reprocessMutation = useMutation({
		mutationFn: () => {
			startProcessing(video.id, "transcribe");
			return videosApi.reprocess(video.id);
		},
		onSuccess: () => {
			showSuccess("Reprocessing Started", "Video reprocessing has been started in the background.", { timer: 3000 });
			queryClient.invalidateQueries(["videos"]);
			queryClient.invalidateQueries(["video", video.id]);
			// Start polling for updates
			const pollInterval = setInterval(() => {
				queryClient.invalidateQueries(["video", video.id]);
				queryClient.invalidateQueries(["videos"]);
			}, 2000);

			setTimeout(() => clearInterval(pollInterval), 5 * 60 * 1000);
		},
		onError: (error) => {
			completeProcessing(video.id);
			showError("Reprocessing Failed", error?.response?.data?.error || "Reprocessing failed. Please try again.");
		},
	});

	// Get current processing state
	const processingState = getProcessingState(video.id);

	// Check if video is currently processing (any stage)
	const isVideoProcessing = 
		video.transcription_status === "transcribing" ||
		video.ai_processing_status === "processing" ||
		video.script_status === "generating" ||
		video.synthesis_status === "synthesizing" ||
		(!!processingState && processingState.type === "transcribe");

	// Simulate progress for active processing
	useEffect(() => {
		if (!processingState) {
			setProgress(0);
			return;
		}

		const interval = setInterval(() => {
			setProgress((prev) => {
				// Increase progress gradually, cap at 95% until actually completed
				if (prev < 95) {
					return Math.min(prev + Math.random() * 3, 95);
				}
				return prev;
			});
		}, 300);

		return () => clearInterval(interval);
	}, [processingState]);

	// Check if video status changed to completed
	useEffect(() => {
		if (processingState) {
			const { type } = processingState;
			let isCompleted = false;

			if (type === "download" && video.is_downloaded) {
				isCompleted = true;
			} else if (
				type === "transcribe" &&
				video.transcription_status === "transcribed"
			) {
				isCompleted = true;
			} else if (
				type === "processAI" &&
				video.ai_processing_status === "processed"
			) {
				isCompleted = true;
			}

			if (isCompleted) {
				setProgress(100);
				setTimeout(() => {
					completeProcessing(video.id);
					setProgress(0);
				}, 1000);
			}
		}
	}, [video, processingState, completeProcessing]);

	const handleDelete = async (e) => {
		e.stopPropagation();
		const result = await showConfirm(
			"Delete Video",
			`Are you sure you want to delete "${video.title || "this video"}"? This action cannot be undone.`,
			{
				confirmText: "Yes, Delete",
				cancelText: "Cancel",
				confirmButtonColor: "#dc2626",
			}
		);
		if (result.isConfirmed) {
			onDelete();
		}
	};

	return (
		<div
			className={`glass-card p-4 transition-all hover:border-white/20 cursor-pointer ${
				isSelected ? "ring-2 ring-[var(--rednote-primary)]" : ""
			}`}
			onClick={() => navigate(`/videos/${video.id}`)}>
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
				<div className="w-20 h-20 flex-shrink-0 rounded-lg overflow-hidden bg-white/5">
					{video.cover_url ? (
						<img
							src={video.cover_url}
							alt={video.title}
							className="w-full h-full object-cover"
						/>
					) : (
						<div className="w-full h-full flex items-center justify-center text-gray-500 text-xs">
							No Image
						</div>
					)}
				</div>

				{/* Content */}
				<div className="flex-1 min-w-0">
					<div className="flex items-start justify-between gap-2">
						<h3 className="font-medium text-white truncate text-sm">
							{truncateText(video.title, 50) || "Untitled"}
						</h3>

						{/* Action buttons - View Details and Delete */}
						<div className="flex gap-1 flex-shrink-0">
							<Button
								size="sm"
								variant="ghost"
								icon={Eye}
								onClick={(e) => {
									e.stopPropagation();
									navigate(`/videos/${video.id}`);
								}}
								title="View Details"
								className="p-1"
							/>
							<Button
								size="sm"
								variant="ghost"
								icon={Trash2}
								onClick={(e) => {
									e.stopPropagation();
									handleDelete(e);
								}}
								title="Delete"
								className="p-1 text-red-400 hover:text-red-300"
							/>
						</div>
					</div>

					{/* Status badges - compact row - Each with unique color */}
					<div className="flex flex-wrap gap-1.5 mt-1.5">
						{/* Processing indicator - Show when video is processing */}
						{isVideoProcessing && (
							<span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full bg-yellow-500/20 text-yellow-400 border border-yellow-500/30">
								<Loader2 className="w-3 h-3 animate-spin" />
								Processing...
							</span>
						)}
						{/* Success status - Green */}
						{video.status === "success" && (
							<StatusBadge status={video.status} />
						)}
					{/* Transcribed status - Blue */}
					{video.transcription_status !== "not_transcribed" && (
						<>
							<StatusBadge status={video.transcription_status} />
							{/* Show error message if transcription failed */}
							{video.transcription_status === "failed" && video.transcript_error_message && (
								<span 
									className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full bg-red-500/20 text-red-400 border border-red-500/30"
									title={video.transcript_error_message}
								>
									⚠️ Error
								</span>
							)}
						</>
					)}
						{/* Processed status - Purple */}
						{video.ai_processing_status !== "not_processed" && (
							<StatusBadge status={video.ai_processing_status} />
						)}
						{/* Script status - Indigo */}
						{video.script_status === "generated" && (
							<span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full badge-script">
								📝 Script
							</span>
						)}
						{/* Downloaded status - Cyan */}
						{video.is_downloaded && (
							<span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full badge-downloaded">
								✓ Downloaded
							</span>
						)}
						{/* Cloudinary Upload status - Blue */}
						{video.cloudinary_url && (
							<span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full badge-cloudinary">
								☁️ Cloudinary
							</span>
						)}
						{/* Google Sheets Sync status - Indigo */}
						{video.google_sheets_synced && (
							<span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full badge-sheets">
								📊 Sheets
							</span>
						)}
					</div>

					{/* Meta info - compact row */}
					<div className="flex items-center gap-3 mt-1.5 text-xs text-gray-400">
						<span>{formatRelativeTime(video.created_at)}</span>
						{video.duration && (
							<span className="text-gray-500">
								⏱️ {formatDuration(video.duration)}
							</span>
						)}
					</div>

					{/* Progress Indicators */}
					{processingState && (
						<div className="mt-2 space-y-1">
							{processingState.type === "download" && (
								<VideoProgressIndicator
									label="Downloading video..."
									progress={progress}
								/>
							)}
							{processingState.type === "transcribe" && (
								<>
									<VideoProgressIndicator
										label={
											video.transcription_status ===
											"transcribing"
												? "Transcribing..."
												: "Transcribed ✓"
										}
										progress={
											video.transcription_status ===
											"transcribing"
												? progress
												: 100
										}
									/>
									{video.transcription_status ===
										"transcribed" &&
										video.ai_processing_status ===
											"processing" && (
											<VideoProgressIndicator
												label="AI Processing..."
												progress={progress}
											/>
										)}
									{video.ai_processing_status ===
										"processed" &&
										video.script_status ===
											"generating" && (
											<VideoProgressIndicator
												label="Scripting..."
												progress={progress}
											/>
										)}
								</>
							)}
							{processingState.type === "processAI" && (
								<VideoProgressIndicator
									label="Processing with AI..."
									progress={progress}
								/>
							)}
						</div>
					)}
					{/* Show status when not actively processing but steps are in progress */}
					{!processingState &&
						video.transcription_status === "transcribing" && (
							<div className="mt-2">
								<VideoProgressIndicator
									label="Transcribing..."
									progress={progress}
								/>
							</div>
						)}
					{!processingState &&
						video.transcription_status === "transcribed" &&
						video.ai_processing_status === "processing" && (
							<div className="mt-2">
								<VideoProgressIndicator
									label="AI Processing..."
									progress={progress}
								/>
							</div>
						)}
					{!processingState &&
						video.ai_processing_status === "processed" &&
						video.script_status === "generating" && (
							<div className="mt-2">
								<VideoProgressIndicator
									label="Scripting..."
									progress={progress}
								/>
							</div>
						)}
					{!processingState &&
						video.script_status === "generated" &&
						video.synthesis_status === "synthesizing" && (
							<div className="mt-2">
								<VideoProgressIndicator
									label="Synthesizing Audio..."
									progress={progress}
								/>
							</div>
						)}

					{/* Error message display */}
					{video.transcription_status === "failed" && video.transcript_error_message && (
						<div className="mt-2 p-2 bg-red-500/10 border border-red-500/30 rounded-lg">
							<p className="text-xs text-red-400 font-medium mb-1">Transcription Error:</p>
							<p className="text-xs text-red-300/80 break-words">{video.transcript_error_message}</p>
						</div>
					)}

					{/* Action buttons - Compact row */}
					<div className="flex flex-wrap gap-1.5 mt-2">
						{/* Hide download/process buttons when video is processing or completed */}
						{!isVideoProcessing && !video.final_processed_video_url && (
							<>
								{!video.is_downloaded && video.status === "success" && (
									<Button
										size="sm"
										variant="secondary"
										icon={Download}
										onClick={(e) => {
											e.stopPropagation();
											startProcessing(video.id, "download");
											onDownload();
										}}
										disabled={
											!!processingState &&
											processingState.type === "download"
										}
										loading={
											!!processingState &&
											processingState.type === "download"
										}>
										Download
									</Button>
								)}

								{(video.transcription_status === "not_transcribed" ||
									video.transcription_status === "failed") && (
									<Button
										size="sm"
										variant={
											video.transcription_status === "failed"
												? "danger"
												: "primary"
										}
										icon={FileText}
										onClick={(e) => {
											e.stopPropagation();
											startProcessing(video.id, "transcribe");
											onTranscribe();
										}}
										disabled={
											(!!processingState &&
												processingState.type ===
													"transcribe") ||
											video.transcription_status ===
												"transcribing" ||
											video.ai_processing_status ===
												"processing" ||
											video.script_status === "generating"
										}
										loading={
											(!!processingState &&
												processingState.type ===
													"transcribe") ||
											video.transcription_status ===
												"transcribing" ||
											video.ai_processing_status ===
												"processing" ||
											video.script_status === "generating"
										}>
										{video.transcription_status === "failed" ? "Retry" : "Process"}
									</Button>
								)}
							</>
						)}

						{/* Reprocess button - Show only when video is completed (has final_processed_video_url) or when processing failed */}
						{(video.final_processed_video_url || 
							(video.transcription_status === "transcribed" && !isVideoProcessing && !video.final_processed_video_url) ||
							video.transcription_status === "failed" ||
							video.script_status === "failed" ||
							video.synthesis_status === "failed") && (
							<Button
								size="sm"
								variant="secondary"
								icon={RefreshCw}
								onClick={async (e) => {
									e.stopPropagation();
									const result = await showConfirm(
										"Reprocess Video",
										"Are you sure you want to reprocess this video? This will reset all processing and regenerate the video with new audio.",
										{
											confirmText: "Yes, Reprocess",
											cancelText: "Cancel",
										}
									);
									if (result.isConfirmed) {
										reprocessMutation.mutate();
									}
								}}
								disabled={isVideoProcessing}
								loading={isVideoProcessing}>
								{isVideoProcessing ? 'Processing...' : 'Reprocess'}
							</Button>
						)}
					</div>
				</div>
			</div>
		</div>
	);
}

export default VideoCard;
