import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useWebSocket } from "../hooks/useWebSocket";
import {
	Download,
	FileText,
	Brain,
	MessageSquare,
	Play,
	Globe,
	Copy,
	ExternalLink,
	RefreshCw,
	ArrowLeft,
	ArrowRight,
	FileEdit,
	Loader2,
	ChevronLeft,
	ChevronRight,
} from "lucide-react";
import {
	Button,
	StatusBadge,
	AudioPlayer,
	LoadingSpinner,
} from "../components/common";
import { ProcessingStatusCard } from "../components/video/ProcessingStatusCard";
import { videosApi } from "../api";
import { formatDate, truncateText, formatDuration } from "../utils/formatters";
import { useStore } from "../store";
import {
	showError,
	showWarning,
	showSuccess,
	showConfirm,
	showInfo,
} from "../utils/alerts";

export function VideoDetail() {
	const { id } = useParams();
	const navigate = useNavigate();
	const queryClient = useQueryClient();
	const {
		startProcessing,
		completeProcessing,
		getProcessingState,
		clearProcessingForVideo,
	} = useStore();

	const [activeTab, setActiveTab] = useState("info");
	// Script editor state
	const [isEditingScript, setIsEditingScript] = useState(false);
	const [editedScript, setEditedScript] = useState("");
	// Timer state
	const [elapsedTime, setElapsedTime] = useState(0);
	const [isTimerRunning, setIsTimerRunning] = useState(false);

	const formatElapsedTime = (seconds) => {
		const mins = Math.floor(seconds / 60);
		const secs = seconds % 60;
		return `${mins}m ${secs}s`;
	};

	// Get processing state early so it can be used in refetchInterval
	const processingState = id ? getProcessingState(id) : null;

	// WebSocket handler - defined before useQuery so we can use wsConnected in refetchInterval
	const handleWebSocketUpdate = useCallback((updateData) => {
		console.log('[VideoDetail] WebSocket update received:', updateData);
		
		// Update query cache directly with new data (no API call needed)
		if (updateData) {
			queryClient.setQueryData(['video', id], (oldData) => {
				if (!oldData) return updateData;
				return {
					...oldData,
					...updateData
				};
			});
		}
		
		// Check for stuck processes and clear them
		if (updateData) {
			const stuckThreshold = 30 * 60 * 1000; // 30 minutes in milliseconds
			const now = new Date();
			
			// Check transcription stuck
			if (updateData.transcription_status === 'transcribing' && updateData.transcript_started_at) {
				const started = new Date(updateData.transcript_started_at);
				const elapsed = now - started;
				if (elapsed > stuckThreshold) {
					console.log('[VideoDetail] Transcription stuck for', Math.floor(elapsed / 60000), 'minutes, clearing...');
					clearProcessingForVideo(id);
				}
			}
			
			// Check AI processing stuck
			if (updateData.ai_processing_status === 'processing' && updateData.ai_processing_started_at) {
				const started = new Date(updateData.ai_processing_started_at);
				const elapsed = now - started;
				if (elapsed > stuckThreshold) {
					console.log('[VideoDetail] AI processing stuck for', Math.floor(elapsed / 60000), 'minutes, clearing...');
					clearProcessingForVideo(id);
				}
			}
			
			// Check visual analysis stuck
			if (updateData.visual_transcript_started_at && !updateData.visual_transcript_finished_at) {
				const started = new Date(updateData.visual_transcript_started_at);
				const elapsed = now - started;
				if (elapsed > stuckThreshold) {
					console.log('[VideoDetail] Visual analysis stuck for', Math.floor(elapsed / 60000), 'minutes, clearing...');
					clearProcessingForVideo(id);
				}
			}
		}
		
		// NO refetch() call - WebSocket updates the cache directly
		// Only invalidate to trigger UI updates, but don't make API call
		queryClient.invalidateQueries(['video', id], { refetch: false });
	}, [id, queryClient, clearProcessingForVideo]);

	// WebSocket for real-time updates (defined before useQuery so we can use wsConnected)
	const { isConnected: wsConnected, lastUpdate: wsUpdate, error: wsError } = useWebSocket(
		id,
		handleWebSocketUpdate,
		{
			maxReconnectAttempts: 10,
			reconnectDelay: 3000,
			pingInterval: 30000,
		}
	);

	// Fetch video list for navigation
	const {
		data: videosList,
	} = useQuery({
		queryKey: ["videos", "navigation"],
		queryFn: () => videosApi.getAll({ ordering: "-created_at" }),
		staleTime: 60 * 1000, // Consider data fresh for 1 minute
		cacheTime: 5 * 60 * 1000, // Keep in cache for 5 minutes
	});

	// Find current video index and get previous/next video IDs
	// API returns array directly, not { results: [...] }
	const videosArray = Array.isArray(videosList) ? videosList : videosList?.results || [];
	const currentVideoIndex = videosArray.findIndex(v => v.id === parseInt(id));
	const previousVideo = currentVideoIndex > 0 ? videosArray[currentVideoIndex - 1] : null;
	const nextVideo = currentVideoIndex >= 0 && currentVideoIndex < videosArray.length - 1 
		? videosArray[currentVideoIndex + 1] 
		: null;

	// Fetch video details - use polling ONLY as fallback when WebSocket is not connected
	const {
		data: video,
		isLoading,
		refetch,
	} = useQuery({
		queryKey: ["video", id],
		queryFn: () => videosApi.getById(id),
		enabled: !!id,
		staleTime: 30000, // Consider data fresh for 30 seconds
		cacheTime: 5 * 60 * 1000, // Keep in cache for 5 minutes
		// Only poll if WebSocket is NOT connected (fallback mechanism)
		refetchInterval: (query) => {
			// If WebSocket is connected, don't poll - rely on WebSocket updates
			if (wsConnected) {
				return false;
			}

			const video = query.state.data;
			if (!video) return false;

			// Get current processing state dynamically
			const currentProcessingState = id ? getProcessingState(id) : null;

			// Check if any processing is active (only poll as fallback when WS is disconnected)
			const isProcessing =
				video.transcription_status === "transcribing" ||
				video.ai_processing_status === "processing" ||
				video.script_status === "generating" ||
				video.synthesis_status === "synthesizing" ||
				// Check for final video assembly (new status tracking)
				video.final_video_status === "removing_audio" ||
				video.final_video_status === "combining_audio" ||
				// Legacy check for videos without final_video_status field
				(video.synthesis_status === "synthesized" &&
					!video.final_processed_video_url &&
					(!video.final_video_status ||
						video.final_video_status === "not_started")) ||
				(currentProcessingState && currentProcessingState.type) ||
				// Poll if Cloudinary/Sheets are pending (after final video is ready)
				(video.final_processed_video_url && !video.cloudinary_url) ||
				(video.final_processed_video_url &&
					!video.google_sheets_synced) ||
				// Poll if we are in a transition state (e.g., Transcribed but AI not started yet)
				(video.transcription_status === "transcribed" &&
					(video.ai_processing_status === "pending" ||
						video.ai_processing_status === "not_processed")) ||
				(video.ai_processing_status === "processed" &&
					video.script_status === "pending");

			if (isProcessing) {
				// Poll every 10 seconds as fallback (slower than before since WebSocket is primary)
				return 10000;
			}
			return false;
		},
	});
	
	useEffect(() => {
		let interval;
		if (isTimerRunning) {
			interval = setInterval(() => {
				setElapsedTime((prev) => prev + 1);
			}, 1000);
		} else {
			clearInterval(interval);
		}
		return () => clearInterval(interval);
	}, [isTimerRunning]);

	// Calculate elapsed time for transcription (after video is loaded)
	const transcriptionElapsedMinutes =
		video && video.transcript_started_at
			? Math.floor(
					(new Date() - new Date(video.transcript_started_at)) /
						1000 /
						60
			  )
			: 0;

	// Check if transcription is stuck (running for more than 2 minutes)
	const isTranscriptionStuck =
		video?.transcription_status === "transcribing" &&
		transcriptionElapsedMinutes > 2;

	// Auto-clear stuck processing state on mount and when video status changes
	useEffect(() => {
		if (!video || !processingState) return;

		const { type } = processingState;
		let shouldClear = false;

		// Check if processing state doesn't match actual video status
		if (type === "transcribe") {
			// Clear if transcription is not actually transcribing (failed, completed, or stuck)
			if (video.transcription_status !== "transcribing") {
				shouldClear = true;
			} else if (isTranscriptionStuck) {
				// Clear if transcription is stuck (>2 minutes)
				shouldClear = true;
			}
		} else if (type === "processAI") {
			// Clear if AI processing is not actually processing
			// BUT allow it if transcription is done (predictive state)
			if (video.ai_processing_status !== "processing" && video.transcription_status !== "transcribed") {
				shouldClear = true;
			}
		} else if (type === "download") {
			// Clear if video is already downloaded
			if (video.is_downloaded) {
				shouldClear = true;
			}
		}

		if (shouldClear) {
			console.log(`Auto-clearing stuck processing state for ${type}`);
			clearProcessingForVideo(id);
			if (isTranscriptionStuck) {
			showWarning(
				"Processing State Cleared",
				"Processing state cleared. Transcription appears stuck. You can retry now."
			);
			}
		}
	}, [
		video,
		processingState,
		id,
		clearProcessingForVideo,
		isTranscriptionStuck,
	]);

	// Force clear on initial load if transcription is stuck
	useEffect(() => {
		if (video && isTranscriptionStuck && processingState) {
			console.log(
				"Force clearing stuck processing state on initial load"
			);
			clearProcessingForVideo(id);
		}
	}, [video?.id]); // Only run once when video loads

	// Removed simulated progress effect

	// Check completion and clear stuck processing states
	useEffect(() => {
		if (processingState && video) {
			const { type } = processingState;
			let isCompleted = false;
			let isStuck = false;

			if (type === "download" && video.is_downloaded) {
				isCompleted = true;
			} else if (type === "transcribe") {
				if (video.transcription_status === "transcribed") {
					// Don't complete yet if we expect AI processing to follow
					// But if we are just tracking "transcribe" action, maybe we should?
					// For now, let's keep it simple: if transcribed, this step is done.
					isCompleted = true;
				} else if (video.transcription_status === "failed") {
					isCompleted = true;
				} else if (
					video.transcription_status === "transcribing" &&
					isTranscriptionStuck
				) {
					isStuck = true;
				}
			} else if (type === "processAI") {
				if (video.ai_processing_status === "processed") {
					isCompleted = true;
				} else if (video.ai_processing_status === "failed") {
					isCompleted = true;
				}
			}

			if (isCompleted || isStuck) {
				// setProgress(100); // Removed
				setTimeout(() => {
					completeProcessing(id);
					// setProgress(0); // Removed
					if (isStuck) {
						showWarning(
							"Processing Stuck",
							"Processing state cleared. You can now retry the operation."
						);
					}
				}, 1000);
			}
		}
	}, [video, processingState, id, completeProcessing, isTranscriptionStuck]);

	// Completion Summary
	useEffect(() => {
		if (video?.final_processed_video_url && video?.status === "success") {
			// Check if we just finished processing (could track previous state, but for now just show if we are viewing it)
			// To avoid showing it every time, we might need a local state "hasShownCompletion".
			// But the user asked for "show the box to know whichone is done".
			// Maybe just relying on the ProcessingStatusCard is enough?
			// The user said: "for the process complites also show the box to know whichone is done and which is pending"
			// The ProcessingStatusCard does exactly this.
		}
	}, [video?.final_processed_video_url]);

	// Mutations
	const downloadMutation = useMutation({
		mutationFn: async () => {
			startProcessing(id, "download");
			return videosApi.download(id);
		},
		onSuccess: () => {
			queryClient.invalidateQueries(["video", id]);
			queryClient.invalidateQueries(["videos"]);
			showSuccess(
				"Download Started",
				"Video download has been started."
			);
		},
		onError: (error) => {
			completeProcessing(id);
			showError(
				"Download Failed",
				error?.response?.data?.error ||
					"Download failed. Please try again."
			);
		},
	});

	const transcribeMutation = useMutation({
		mutationFn: () => {
			// Check if already transcribing and stuck - reset first
			if (
				video?.transcription_status === "transcribing" &&
				isTranscriptionStuck
			) {
				// Reset stuck transcription first
				return videosApi.resetTranscription(id).then(() => {
					// Then start new transcription
					startProcessing(id, "transcribe");
					return videosApi.transcribe(id);
				});
			}
			startProcessing(id, "transcribe");
			return videosApi.transcribe(id);
		},
		onSuccess: (response) => {
			// Check for warnings in response (visual/enhanced errors)
			if (response?.data?.warnings && response.data.warnings.length > 0) {
				const warnings = response.data.warnings;
				let warningMessage = warnings.join("\n\n");

				showWarning(
					"Transcription Completed with Warnings",
					warningMessage,
					{ confirmButtonText: "OK", width: "600px" }
				);
			} else {
				showSuccess(
					"Processing Started",
					"Video processing has been started."
				);
			}

			let pollCount = 0;
			const pollInterval = setInterval(() => {
				pollCount++;
				refetch()
					.then(({ data }) => {
						if (
							data &&
							data.transcription_status !== "transcribing" &&
							data.ai_processing_status !== "processing" &&
							data.script_status !== "generating" &&
							data.synthesis_status !== "synthesizing" &&
							(data.synthesis_status !== "synthesized" ||
								data.final_processed_video_url)
						) {
							clearInterval(pollInterval);
							completeProcessing(id);
							if (data.final_processed_video_url) {
								showSuccess(
									"Video Processing Completed!",
									"All steps completed successfully."
								);
							} else if (data.transcription_status === "failed") {
								showError(
									"Transcription Failed",
									data.transcript_error_message ||
										"Transcription failed. Please check your settings and try again.",
									{ confirmButtonText: "OK" }
								);
							} else if (
								data.transcription_status === "transcribed"
							) {
								// Check for visual or enhanced errors
								const hasVisual = data.visual_transcript;
								const hasEnhanced = data.enhanced_transcript;

								if (!hasVisual || !hasEnhanced) {
									let missingItems = [];
									if (!hasVisual)
										missingItems.push("Visual Analysis");
									if (!hasEnhanced)
										missingItems.push("AI Enhancement");

									showWarning(
										"Transcription Completed",
										`Transcription completed, but ${missingItems.join(
											" and "
										)} ${
											missingItems.length > 1
												? "were"
												: "was"
										} not generated. Please check your AI provider settings (Gemini required for Visual Analysis).`,
										{
											confirmButtonText: "OK",
											width: "600px",
										}
									);
								} else {
									showSuccess(
										"Transcription Completed",
										"Transcription completed successfully!"
									);
								}
							}
						} else if (data) {
							// Show progress updates for long-running processes
							if (pollCount % 15 === 0) {
								// Show updates every 30 seconds (15 * 2s)
								if (
									data.transcription_status === "transcribing"
								) {
									const elapsed = data.elapsed_seconds || 0;
									showInfo(
										"Transcription in progress...",
										`Elapsed: ${Math.floor(
											elapsed / 60
										)}m ${elapsed % 60}s`,
										{
											toast: true,
											position: "top-end",
										}
									);
								} else if (
									data.ai_processing_status === "processing"
								) {
									showInfo(
										"AI Processing...",
										"This may take a few minutes.",
										{
											toast: true,
											position: "top-end",
										}
									);
								} else if (
									data.script_status === "generating"
								) {
									showInfo(
										"Generating Script...",
										"Creating Hindi script...",
										{
											toast: true,
											position: "top-end",
										}
									);
								} else if (
									data.synthesis_status === "synthesizing"
								) {
									showInfo(
										"Synthesizing...",
										"Generating audio...",
										{
											toast: true,
											position: "top-end",
										}
									);
								}
							}
							// Auto-clear processing state if stuck
							if (data.transcription_status === "transcribing") {
								const elapsed = data.elapsed_seconds || 0;
								if (elapsed > 2 * 60) {
									// 2 minutes
									completeProcessing(id);
									showWarning(
										"Transcription Appears Stuck",
										"Transcription has been running for more than 2 minutes. Processing state cleared. You can retry now.",
										{ confirmButtonText: "OK" }
									);
								}
							}
						}
					})
					.catch((err) => {
						// If refetch fails, don't stop polling immediately - might be temporary network issue
						console.warn("Polling error:", err);
					});
			}, 5000); // Poll every 5 seconds (reduced from 2s)
			// Increased timeout to 30 minutes for large videos
			setTimeout(() => {
				clearInterval(pollInterval);
				// Check final status before showing timeout message
				refetch().then(({ data }) => {
					if (data && data.transcription_status === "transcribing") {
						completeProcessing(id); // Clear processing state
						showWarning(
							"Processing Timeout",
							"Processing is taking longer than expected. Processing state cleared. You can check back later or retry.",
							{ confirmButtonText: "OK", width: "600px" }
						);
					}
				});
			}, 30 * 60 * 1000); // 30 minutes
		},
		onError: (error) => {
			completeProcessing(id);
			const errorMsg =
				error?.response?.data?.error ||
				error?.message ||
				"Processing failed";
			const errorDetails = error?.response?.data?.detail || "";

			// Provide more helpful error messages with SweetAlert
			if (
				errorMsg.includes("timeout") ||
				errorMsg.includes("timed out")
			) {
				showError(
					"Processing Timeout",
					"Processing timed out. The video may be too long. Please try again or use a shorter video.",
					{ confirmButtonText: "OK", width: "600px" }
				);
			} else if (errorMsg.includes("already_processing")) {
				showInfo(
					"Processing in Progress",
					"Processing is already in progress. Please wait."
				);
			} else {
				showError("Processing Failed", errorDetails || errorMsg, {
					confirmButtonText: "OK",
					width: "600px",
				});
			}
		},
	});

	const processAIMutation = useMutation({
		mutationFn: () => {
			startProcessing(id, "processAI");
			return videosApi.processAI(id);
		},
		onSuccess: () => {
			queryClient.invalidateQueries(["video", id]);
			showSuccess(
				"AI Processing Started",
				"AI processing has been started."
			);
		},
		onError: (error) => {
			completeProcessing(id);
			showError(
				"AI Processing Failed",
				error?.response?.data?.error ||
					"AI processing failed. Please try again."
			);
		},
	});

	// Helper function to get current processing step
	const getCurrentProcessingStep = (video) => {
		if (!video) return null;

		if (video.transcription_status === "transcribing") {
			return "Transcribing...";
		}
		if (video.ai_processing_status === "processing") {
			return "AI Processing...";
		}
		if (video.script_status === "generating") {
			return "Generating Script...";
		}
		if (video.synthesis_status === "synthesizing") {
			return "Synthesizing Audio...";
		}
		// Check for final video assembly with dedicated status tracking
		if (video.final_video_status === "removing_audio") {
			return "Removing Original Audio...";
		}
		if (video.final_video_status === "combining_audio") {
			return "Combining with TTS Audio...";
		}
		// Legacy check for videos without final_video_status field
		if (
			video.synthesis_status === "synthesized" &&
			!video.final_processed_video_url &&
			(!video.final_video_status ||
				video.final_video_status === "not_started")
		) {
			return "Creating Final Video...";
		}
		if (video.final_processed_video_url && !video.cloudinary_url) {
			return "Uploading to Cloudinary...";
		}
		if (video.cloudinary_url && !video.google_sheets_synced) {
			return "Syncing to Google Sheets...";
		}

		return null;
	};

	// Check if video needs processing or has failed steps
	const needsProcessing = (video) => {
		if (!video) return false;

		// Needs download
		if (!video.is_downloaded && video.status === "success") return true;

		// Needs transcription (unless skipped)
		if (
			video.transcription_status === "not_transcribed" ||
			video.transcription_status === "failed"
		)
			return true;

		// Needs AI processing
		if (
			video.ai_processing_status === "not_processed" ||
			video.ai_processing_status === "failed"
		)
			return true;

		// Needs script generation
		if (
			video.script_status === "not_generated" ||
			video.script_status === "failed"
		)
			return true;

		// Needs TTS synthesis
		if (
			video.synthesis_status === "not_synthesized" ||
			video.synthesis_status === "failed"
		)
			return true;

		// Needs final video
		if (
			video.synthesis_status === "synthesized" &&
			!video.final_processed_video_url
		)
			return true;

		// Needs Cloudinary upload
		if (video.final_processed_video_url && !video.cloudinary_url)
			return true;

		// Needs Google Sheets sync
		if (video.cloudinary_url && !video.google_sheets_synced) return true;

		return false;
	};

	// Check if any step has failed
	const hasFailedStep = (video) => {
		if (!video) return false;
		return (
			video.transcription_status === "failed" ||
			video.ai_processing_status === "failed" ||
			video.script_status === "failed" ||
			video.synthesis_status === "failed"
		);
	};

	// Unified Process All Mutation
	const processAllMutation = useMutation({
		mutationFn: async () => {
			// Reset timer
			setElapsedTime(0);
			setIsTimerRunning(true);
			
			// Start with Download
			startProcessing(id, "download");

			// Get current video state
			let currentVideo = await videosApi.getById(id);

			// Step 1: Download if not downloaded
			if (
				!currentVideo.is_downloaded &&
				currentVideo.status === "success"
			) {
				showInfo("Step 1/8: Downloading video...", "", {
					toast: true,
					position: "top-end",
				});
				
				await videosApi.download(id);
				
				// Wait for download to complete
				let downloadComplete = false;
				let attempts = 0;
				while (!downloadComplete && attempts < 60) { // 2 minutes max for download start
					await new Promise((resolve) => setTimeout(resolve, 2000));
					currentVideo = await videosApi.getById(id);
					
					// Update cache to reflect download status immediately
					queryClient.setQueryData(["video", id], currentVideo);
					
					if (currentVideo.is_downloaded) {
						downloadComplete = true;
					}
					attempts++;
				}
				if (!downloadComplete) {
					throw new Error("Download timed out");
				}
			}

			// Step 2: Start Transcription (triggers the rest of the pipeline)
			startProcessing(id, "transcribe"); // Switch status to transcribe
			
			showInfo("Step 2/8: Starting transcription and processing...", "", {
				toast: true,
				position: "top-end",
			});
			
			const transcribeResult = await videosApi.transcribe(id);

			// If transcription was skipped (no audio), continue with other steps if transcript exists
			if (transcribeResult.status === "skipped") {
				showWarning(
					"Transcription skipped (no audio stream). Continuing with other steps...",
					"",
					{ toast: true, position: "top-end" }
				);
			}

			// Wait for all processing steps to complete
			// Poll for completion
			let processingComplete = false;
			let attempts = 0;
			while (!processingComplete && attempts < 300) { // 25 minutes max
				await new Promise((resolve) => setTimeout(resolve, 5000));
				currentVideo = await videosApi.getById(id);
				
				// Update cache to reflect live status
				queryClient.setQueryData(["video", id], currentVideo);
				
				// Update local processing state based on backend status AND predictive logic
				// This ensures the UI shows "Processing" immediately when one step finishes, even if backend status lags slightly
				
				let activeStep = null;

				if (currentVideo.transcription_status === 'transcribing') {
					activeStep = 'transcribe';
				} else if (currentVideo.transcription_status === 'transcribed' || currentVideo.transcription_status === 'skipped') {
					// Transcription done. Check AI.
					if (currentVideo.ai_processing_status !== 'processed' && currentVideo.ai_processing_status !== 'failed') {
						// If AI not done/failed, assume it's processing (or about to be)
						activeStep = 'processAI';
					} else {
						// AI done. Check Script.
						if (currentVideo.script_status !== 'generated' && currentVideo.script_status !== 'failed') {
							activeStep = 'script';
						} else {
							// Script done. Check TTS.
							if (currentVideo.synthesis_status !== 'synthesized' && currentVideo.synthesis_status !== 'failed') {
								activeStep = 'synthesis';
							} else {
								// TTS done. Check Final Video.
								if (!currentVideo.final_processed_video_url && currentVideo.synthesis_status !== 'failed') {
									activeStep = 'final_video';
								}
							}
						}
					}
				}

				if (activeStep) {
					startProcessing(id, activeStep);
				}

				// Check completion
				const transcriptionDone =
					currentVideo.transcription_status === "transcribed" ||
					currentVideo.transcription_status === "skipped";
				const aiDone =
					currentVideo.ai_processing_status === "processed" ||
					currentVideo.ai_processing_status === "failed";
				const scriptDone =
					currentVideo.script_status === "generated" ||
					currentVideo.script_status === "failed";
				const ttsDone =
					currentVideo.synthesis_status === "synthesized" ||
					currentVideo.synthesis_status === "failed";
				const finalVideoDone =
					currentVideo.final_processed_video_url ||
					currentVideo.synthesis_status === "failed";

				if (
					transcriptionDone &&
					aiDone &&
					scriptDone &&
					ttsDone &&
					finalVideoDone
				) {
					processingComplete = true;
				}
				attempts++;
			}

			// Step 7 & 8: Upload and Sync (if needed)
			if (processingComplete && currentVideo.final_processed_video_url) {
				if (!currentVideo.cloudinary_url) {
					startProcessing(id, "cloudinary");
					showInfo("Step 7/8: Uploading to Cloudinary...", "", {
						toast: true,
						position: "top-end",
					});
					try {
						await videosApi.uploadAndSync(id);
						// Wait for upload to complete
						let uploadComplete = false;
						let attempts = 0;
						while (!uploadComplete && attempts < 30) {
							await new Promise((resolve) =>
								setTimeout(resolve, 2000)
							);
							currentVideo = await videosApi.getById(id);
							queryClient.setQueryData(["video", id], currentVideo);
							if (currentVideo.cloudinary_url) {
								uploadComplete = true;
							}
							attempts++;
						}
					} catch (error) {
						console.warn("Cloudinary upload failed:", error);
						// Continue even if upload fails
					}
				}

				if (!currentVideo.google_sheets_synced) {
					startProcessing(id, "sheets");
					showInfo("Step 8/8: Syncing to Google Sheets...", "", {
						toast: true,
						position: "top-end",
					});
					try {
						await videosApi.uploadAndSync(id);
						// Wait for sync to complete
						let syncComplete = false;
						let attempts = 0;
						while (!syncComplete && attempts < 30) {
							await new Promise((resolve) =>
								setTimeout(resolve, 2000)
							);
							currentVideo = await videosApi.getById(id);
							queryClient.setQueryData(["video", id], currentVideo);
							if (currentVideo.google_sheets_synced) {
								syncComplete = true;
							}
							attempts++;
						}
					} catch (error) {
						console.warn("Google Sheets sync failed:", error);
						// Continue even if sync fails
					}
				}
			}

			return { success: true };
		},
		onSuccess: () => {
			setIsTimerRunning(false);
			queryClient.invalidateQueries(["video", id]);
			completeProcessing(id);
			showSuccess(
				"Processing Completed",
				`Video processing completed in ${formatElapsedTime(elapsedTime)}! 🎉`,
				{ timer: 5000 }
			);
		},
		onError: (error) => {
			setIsTimerRunning(false);
			completeProcessing(id);
			const errorMsg =
				error?.response?.data?.error ||
				error?.message ||
				"Processing failed";
			showError("Processing Failed", `Processing failed: ${errorMsg}`);
		},
	});

	const reprocessMutation = useMutation({
		mutationFn: () => {
			startProcessing(id, "reprocess");
			return videosApi.reprocess(id);
		},
		onSuccess: () => {
			showSuccess(
				"Reprocessing Started",
				"Video reprocessing has been started in the background."
			);
			queryClient.invalidateQueries(["video", id]);
			queryClient.invalidateQueries(["videos"]);
			// Start immediate refetch to get updated status
			refetch();

			// Set up polling to check for completion
			const pollInterval = setInterval(() => {
				refetch().then(({ data }) => {
					if (data) {
						// Check if all processing is complete
						const isProcessing =
							data.transcription_status === "transcribing" ||
							data.ai_processing_status === "processing" ||
							data.script_status === "generating" ||
							data.synthesis_status === "synthesizing" ||
							(data.synthesis_status === "synthesized" &&
								!data.final_processed_video_url) ||
							(data.final_processed_video_url &&
								!data.cloudinary_url) ||
							(data.cloudinary_url && !data.google_sheets_synced);

						if (!isProcessing) {
							clearInterval(pollInterval);
							completeProcessing(id);
							if (data.final_processed_video_url) {
								showSuccess(
									"Reprocessing Completed",
									"Video reprocessing completed successfully!",
									{ timer: 5000 }
								);
							} else if (data.synthesis_status === "failed") {
								showError(
									"Reprocessing Incomplete",
									"Reprocessing completed but TTS synthesis failed. Check video details."
								);
							}
						}
					}
				});
			}, 5000); // Poll every 5 seconds (reduced from 2s)

			// Clean up polling after 5 minutes
			setTimeout(() => {
				clearInterval(pollInterval);
				completeProcessing(id);
			}, 5 * 60 * 1000);
		},
		onError: (error) => {
			completeProcessing(id);
			showError(
				"Reprocessing Failed",
				error?.response?.data?.error ||
					"Reprocessing failed. Please try again."
			);
		},
	});

	// Script editor mutations
	const updateScriptMutation = useMutation({
		mutationFn: (scriptData) => videosApi.updateScript(id, scriptData),
		onSuccess: () => {
			setIsEditingScript(false);
			queryClient.invalidateQueries(["video", id]);
			showSuccess("Script Updated", "Script saved successfully!");

			// Automatically trigger TTS synthesis after saving script
			synthesizeTTSMutation.mutate();
		},
		onError: (error) => {
			showError(
				"Update Failed",
				error?.response?.data?.error || "Failed to update script"
			);
		},
	});

	const synthesizeTTSMutation = useMutation({
		mutationFn: () => videosApi.synthesizeTTS(id),
		onSuccess: (response) => {
			showSuccess(
				"TTS Synthesis Started",
				`TTS synthesis started with speed ${response.tts_speed}x to match video duration`
			);
			queryClient.invalidateQueries(["video", id]);
			// Start polling for synthesis completion
			refetch();
		},
		onError: (error) => {
			showError(
				"TTS Failed",
				error?.response?.data?.error || "TTS synthesis failed"
			);
		},
	});

	// Helper function to estimate speech duration
	const estimateSpeechDuration = (script) => {
		if (!script) return 0;
		const wordCount = script
			.split(/\s+/)
			.filter((word) => word.length > 0).length;
		// Average Hindi speaking rate: ~150 words/minute = 2.5 words/second
		return Math.ceil(wordCount / 2.5);
	};

	// Handler for saving script
	const handleSaveScript = () => {
		if (!editedScript || !editedScript.trim()) {
			showError("Empty Script", "Script cannot be empty");
			return;
		}

		updateScriptMutation.mutate({
			hindi_script: editedScript,
		});
	};

	// Check if script needs editing
	// Helper to clean script for editor (remove timestamps)
	const getCleanScript = (script) => {
		if (!script) return "";
		// Remove timestamps like 00:00:00 or 00:00
		let clean = script.replace(/\b\d{1,2}:\d{2}(?::\d{2})?\b/g, "");
		// Remove extra spaces
		clean = clean.replace(/\s+/g, " ").trim();
		return clean;
	};



	const resetTranscriptionMutation = useMutation({
		mutationFn: () => {
			return videosApi.resetTranscription(id);
		},
		onSuccess: (data) => {
			showSuccess(
				"Transcription Reset",
				data.message || "Transcription reset successfully."
			);
			queryClient.invalidateQueries(["video", id]);
			queryClient.invalidateQueries(["videos"]);
			refetch();
			completeProcessing(id);
		},
		onError: (error) => {
			showError(
				"Reset Failed",
				error?.response?.data?.error ||
					"Failed to reset transcription. Please try again."
			);
		},
	});

	const analyzeVisualMutation = useMutation({
		mutationFn: () => {
			return videosApi.analyzeVisual(id);
		},
		onSuccess: (data) => {
			showSuccess(
				"Visual Analysis Started",
				data.message || `Visual analysis started using Gemini Vision API. Analyzing ${video.total_frames_extracted || 0} frames.`
			);
			queryClient.invalidateQueries(["video", id]);
			refetch();
		},
		onError: (error) => {
			showError(
				"Visual Analysis Failed",
				error?.response?.data?.error ||
					"Failed to start visual analysis. Please try again."
			);
		},
	});

	const copyToClipboard = (text) => {
		navigator.clipboard.writeText(text);
		showSuccess("Copied", "Text copied to clipboard.");
	};

	const tabs = [
		{ id: "info", label: "Info" },
		{ id: "transcript", label: "Transcript" },
		{ id: "script", label: "Hindi Script" },
		{ id: "ai", label: "AI Summary" },
	];

	const handleRetry = async (stepId) => {
		try {
			startProcessing(id, stepId);
			let result;
			
			switch (stepId) {
				case "transcription":
					result = await videosApi.retryTranscription(id);
					showSuccess("Transcription Retried", "Transcription has been retried and will auto-progress to next step.", { timer: 3000 });
					break;
				case "ai_processing":
					result = await videosApi.retryAIProcessing(id);
					showSuccess("AI Processing Retried", "AI processing has been retried and will auto-progress to next step.", { timer: 3000 });
					break;
				case "script":
				case "script_generation":
					result = await videosApi.retryScriptGeneration(id);
					showSuccess("Script Generation Retried", "Script generation has been retried and will auto-progress to next step.", { timer: 3000 });
					break;
				case "synthesis":
					result = await videosApi.retrySynthesis(id);
					showSuccess("Synthesis Retried", "Synthesis has been retried and will auto-progress to next step.", { timer: 3000 });
					break;
				case "final_video":
					result = await videosApi.retryFinalVideo(id);
					showSuccess("Final Video Retried", "Final video generation has been retried and will auto-progress to next step.", { timer: 3000 });
					break;
				default:
					showError(
						"Unknown Step",
						"Unknown step to retry. Please select a valid step.",
						{ timer: 3000 }
					);
					completeProcessing(id);
					return;
			}
			
			// Refetch to get updated status
			refetch();
		} catch (error) {
			showError(
				"Retry Failed",
				error?.response?.data?.error || "Failed to retry step. Please try again.",
				{ timer: 5000 } // Longer timeout for errors so user can read
			);
			completeProcessing(id);
		}
	};

	if (isLoading) {
		return (
			<div className="flex justify-center items-center min-h-[60vh]">
				<LoadingSpinner size="lg" />
			</div>
		);
	}

	if (!video) {
		return (
			<div className="text-center py-12 text-gray-400">
				<p>Video not found</p>
				<Button
					variant="secondary"
					icon={ArrowLeft}
					onClick={() => navigate("/videos")}
					className="mt-4">
					Back to Videos
				</Button>
			</div>
		);
	}

	return (
		<div className="space-y-6 pb-8 relative">
			{/* Header with back button */}
			<div className="flex items-center gap-4">
				<Button
					variant="ghost"
					icon={ArrowLeft}
					onClick={() => navigate("/videos")}>
					Back
				</Button>
				<h1 className="text-2xl font-bold">Video Details</h1>
				{/* Video counter in header */}
				{videosArray.length > 0 && currentVideoIndex >= 0 && (
					<span className="text-sm text-gray-400 px-2 ml-auto">
						{currentVideoIndex + 1} / {videosArray.length}
					</span>
				)}
			</div>

			{/* Floating Previous/Next Navigation Buttons - Always visible, centered vertically */}
			{videosArray.length > 0 && (
				<>
					<button
						onClick={() => {
							if (previousVideo) {
								navigate(`/videos/${previousVideo.id}`);
								window.scrollTo({ top: 0, behavior: 'smooth' });
							}
						}}
						title={previousVideo ? (previousVideo.title || `Video ${previousVideo.id}`) : "No previous video"}
						disabled={!previousVideo}
						className="fixed lg:left-[280px] left-6 top-1/2 -translate-y-1/2 z-[100] w-14 h-14 rounded-full bg-white/10 hover:bg-white/20 backdrop-blur-md border border-white/30 flex items-center justify-center transition-all duration-200 hover:scale-110 disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:scale-100 shadow-xl hover:shadow-2xl group">
						<ChevronLeft className="w-7 h-7 text-white group-hover:text-white/90" />
					</button>

					<button
						onClick={() => {
							if (nextVideo) {
								navigate(`/videos/${nextVideo.id}`);
								window.scrollTo({ top: 0, behavior: 'smooth' });
							}
						}}
						title={nextVideo ? (nextVideo.title || `Video ${nextVideo.id}`) : "No next video"}
						disabled={!nextVideo}
						className="fixed right-6 top-1/2 -translate-y-1/2 z-[100] w-14 h-14 rounded-full bg-white/10 hover:bg-white/20 backdrop-blur-md border border-white/30 flex items-center justify-center transition-all duration-200 hover:scale-110 disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:scale-100 shadow-xl hover:shadow-2xl group">
						<ChevronRight className="w-7 h-7 text-white group-hover:text-white/90" />
					</button>
				</>
			)}

			{/* Main content - Full Width Layout */}
			<div className="grid grid-cols-1 xl:grid-cols-3 gap-6 w-full">
				{/* Left column - Video and main content */}
				<div className="xl:col-span-2 space-y-6 w-full">
					{/* Video Preview Strip - Same Source Videos Only (Compact for Shorts) */}
					{video?.video_url && videosArray.length > 0 && (() => {
						// Filter videos that share the same video_url (same source)
						const sameSourceVideos = videosArray.filter(v => v.video_url === video.video_url);
						const sameSourceIndex = sameSourceVideos.findIndex(v => v.id === parseInt(id));
						
						return sameSourceVideos.length > 1 ? (
							<div className="bg-white/5 rounded-lg p-2 border border-white/10">
								<div className="flex items-center justify-between mb-2">
									<h4 className="text-xs font-semibold text-gray-300 flex items-center gap-2">
										Video Versions
										<span className="text-[10px] text-gray-400">({sameSourceVideos.length})</span>
									</h4>
									{sameSourceIndex >= 0 && (
										<span className="text-[10px] text-gray-500">
											{sameSourceIndex + 1}/{sameSourceVideos.length}
										</span>
									)}
								</div>
								<div className="flex gap-1.5 overflow-x-auto pb-1 custom-scrollbar scroll-smooth">
									{sameSourceVideos.map((v) => {
										const isActive = v.id === parseInt(id);
										// Get thumbnail - prefer cover_url, then final video, then local file
										const thumbnailUrl = v.cover_url || v.final_processed_video_url || v.local_file_url || v.video_url;
										return (
											<button
												key={v.id}
												onClick={() => {
													navigate(`/videos/${v.id}`);
													window.scrollTo({ top: 0, behavior: 'smooth' });
												}}
												className={`flex-shrink-0 relative group transition-all ${
													isActive 
														? 'ring-1.5 ring-[var(--rednote-primary)] rounded-md scale-[1.02]' 
														: 'hover:scale-[1.02]'
												}`}
												title={v.title || `Video ${v.id}`}
											>
												<div className={`w-14 h-20 rounded-md overflow-hidden border transition-all ${
													isActive 
														? 'border-[var(--rednote-primary)] shadow-md shadow-[var(--rednote-primary)]/40' 
														: 'border-white/15 hover:border-white/30'
												}`}>
													{thumbnailUrl ? (
														<img
															src={thumbnailUrl}
															alt={v.title || `Video ${v.id}`}
															className="w-full h-full object-cover"
															onError={(e) => {
																// Fallback to placeholder if image fails to load
																e.target.style.display = 'none';
																e.target.nextElementSibling.style.display = 'flex';
															}}
														/>
													) : null}
													<div className={`w-full h-full bg-white/5 flex items-center justify-center ${thumbnailUrl ? 'hidden' : ''}`}>
														<Play className="w-4 h-4 text-gray-400" />
													</div>
												</div>
												{isActive && (
													<div className="absolute -bottom-0.5 left-1/2 -translate-x-1/2 w-1.5 h-1.5 rounded-full bg-[var(--rednote-primary)]"></div>
												)}
												<div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors rounded-md pointer-events-none"></div>
											</button>
										);
									})}
								</div>
							</div>
						) : null;
					})()}

					{/* Video player - Optimized for shorts (9:16 aspect ratio) */}
					<div className="bg-white/5 rounded-lg p-3 border border-white/10">
						{video.final_processed_video_url ||
						video.local_file_url ||
						video.video_url ? (
							<div className="relative rounded-lg overflow-hidden bg-black mx-auto" style={{ maxWidth: '400px', aspectRatio: '9/16' }}>
								<video
									src={
										video.final_processed_video_url ||
										video.local_file_url ||
										video.video_url
									}
									poster={video.cover_url}
									controls
									className="w-full h-full object-contain"
								/>
								{video.final_processed_video_url && (
									<div className="absolute top-2 right-2 px-2 py-1 bg-green-500/80 text-white text-xs rounded">
										✓ Final Video (with new Hindi audio)
									</div>
								)}
								{!video.final_processed_video_url &&
									video.local_file_url && (
										<div className="absolute top-2 right-2 px-2 py-1 bg-blue-500/80 text-white text-xs rounded">
											✓ Downloaded Video (original audio)
										</div>
									)}
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

					{/* Progress Indicators - Replaced with ProcessingStatusCard */}
					{(processingState ||
						video.transcription_status === "transcribing" ||
						video.ai_processing_status === "processing" ||
						video.script_status === "generating" ||
						video.synthesis_status === "synthesizing" ||
						video.transcription_status === "failed" ||
						video.ai_processing_status === "failed" ||
						video.script_status === "failed" ||
						video.synthesis_status === "failed" ||
						(video.synthesis_status === "synthesized" &&
							!video.final_processed_video_url)) && (
						<ProcessingStatusCard
							video={video}
							processingState={processingState}
							onRetry={handleRetry}
							wsConnected={wsConnected}
							wsUpdate={wsUpdate}
						/>
					)}

					{/* Actions and Video Versions - Combined in one card */}
					<div className="bg-white/5 rounded-lg p-4 border border-white/10">
						{/* Actions Section */}
						<div className="mb-6">
							<h4 className="text-sm font-semibold text-gray-300 mb-4">
								Actions
							</h4>
							<div className="grid grid-cols-2 md:grid-cols-4 gap-2">
								{/* Process All Button - The Master Button */}
								<Button
									size="sm"
									variant="primary" // Make it stand out
									icon={Play}
									onClick={() => processAllMutation.mutate()}
									loading={processAllMutation.isPending}
									disabled={
										processAllMutation.isPending ||
										(!!processingState && processingState.type === "process")
									}
									className="col-span-2 md:col-span-1 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 border-none"
								>
									{processAllMutation.isPending || isTimerRunning
										? `Processing... (${formatElapsedTime(elapsedTime)})`
										: "Process All"}
								</Button>
								{!video.is_downloaded &&
									video.status === "success" && (
										<Button
											size="sm"
											variant="secondary"
											icon={Download}
											onClick={() =>
												downloadMutation.mutate()
											}
											loading={
												downloadMutation.isPending ||
												(!!processingState &&
													processingState.type ===
														"download")
											}
											disabled={
												downloadMutation.isPending ||
												(!!processingState &&
													processingState.type ===
														"download")
											}>
											{downloadMutation.isPending ||
											processingState?.type === "download"
												? "Downloading..."
												: "Download"}
										</Button>
									)}

								{(video.transcription_status ===
									"not_transcribed" ||
									video.transcription_status === "failed" ||
									isTranscriptionStuck) && (
									<Button
										size="sm"
										variant={
											video.transcription_status ===
												"failed" || isTranscriptionStuck
												? "danger"
												: "secondary"
										}
										icon={FileText}
										onClick={() => {
											// Clear processing state if stuck before starting
											if (
												isTranscriptionStuck ||
												(processingState &&
													processingState.type ===
														"transcribe")
											) {
												clearProcessingForVideo(id);
											}
											transcribeMutation.mutate();
										}}
										loading={
											transcribeMutation.isPending ||
											(!!processingState &&
												processingState.type ===
													"transcribe" &&
												!isTranscriptionStuck)
										}
										disabled={
											transcribeMutation.isPending ||
											(!!processingState &&
												processingState.type ===
													"transcribe" &&
												!isTranscriptionStuck)
										}>
										{isTranscriptionStuck
											? `Retry Process (Stuck ${transcriptionElapsedMinutes}m)`
											: video.transcription_status ===
											  "failed"
											? "Retry Process"
											: "Process Video"}
									</Button>
								)}

								{/* Reset button for stuck transcriptions */}
								{isTranscriptionStuck && (
									<Button
										size="sm"
										variant="danger"
										icon={RefreshCw}
										onClick={async () => {
											const result = await showConfirm(
												"Reset Transcription?",
												`Transcription has been running for ${transcriptionElapsedMinutes} minutes. Do you want to reset it and try again?`,
												{
													confirmButtonText:
														"Yes, Reset",
													cancelButtonText: "Cancel",
												}
											);
											if (result.isConfirmed) {
												resetTranscriptionMutation.mutate();
												clearProcessingForVideo(id); // Clear processing state
											}
										}}
										loading={
											resetTranscriptionMutation.isPending
										}
										disabled={
					resetTranscriptionMutation.isPending
										}>
										Reset Transcription (
										{transcriptionElapsedMinutes}m)
									</Button>
								)}

								{/* Edit Script button */}
								{video.hindi_script && (
									<Button
										size="sm"
										variant="secondary"
										icon={FileEdit}
										onClick={() => {
											setIsEditingScript(true);
											setEditedScript(getCleanScript(video.hindi_script));
										}}>
										Edit Script
									</Button>
								)}

								{/* Visual Analysis button - shows when frames are extracted but visual analysis not done */}
								{video.frames_extracted && 
									!video.visual_transcript && 
									!video.visual_transcript_started_at && (
									<Button
										size="sm"
										variant="secondary"
										icon={Brain}
										onClick={() => {
											showInfo(
												"Starting Visual Analysis",
												`Analyzing ${video.total_frames_extracted || 0} frames using Gemini Vision API...`
											);
											analyzeVisualMutation.mutate();
										}}
										loading={analyzeVisualMutation.isPending}
										disabled={analyzeVisualMutation.isPending}>
										{analyzeVisualMutation.isPending
											? "Analyzing with Gemini AI..."
											: `Analyze Visual (${video.total_frames_extracted || 0} frames)`}
									</Button>
								)}
								{/* Show status if visual analysis is in progress */}
								{video.visual_transcript_started_at && !video.visual_transcript_finished_at && (
									<Button
										size="sm"
										variant="secondary"
										icon={Brain}
										disabled={true}
										loading={true}>
										Analyzing with Gemini AI...
									</Button>
								)}

								{/* Clear processing state button - shows when processingState exists but video is not actually processing or is stuck */}
								{processingState &&
									video &&
									((processingState.type === "transcribe" &&
										(video.transcription_status !==
											"transcribing" ||
											isTranscriptionStuck)) ||
										(processingState.type === "processAI" &&
											video.ai_processing_status !==
												"processing" &&
											video.ai_processing_status !==
												"processed") ||
										(processingState.type === "download" &&
											video.is_downloaded)) && (
										<Button
											size="sm"
											variant="danger"
											icon={RefreshCw}
											onClick={() => {
												clearProcessingForVideo(id);
												showSuccess(
													"Processing State Cleared",
													"Processing state cleared. You can now retry the operation."
												);
											}}>
											{isTranscriptionStuck
												? `Clear Stuck State (${transcriptionElapsedMinutes}m)`
												: "Clear Processing State"}
										</Button>
									)}

								{/* Show reprocess button when transcription is complete OR failed OR stuck OR when other steps are done */}
								{(video.transcription_status ===
									"transcribed" ||
									video.transcription_status === "failed" ||
									isTranscriptionStuck ||
									video.script_status === "generated" ||
									video.script_status === "failed" ||
									video.synthesis_status === "synthesized" ||
									video.synthesis_status === "failed" ||
									video.final_processed_video_url) && (
									<Button
										size="sm"
										variant="secondary"
										icon={RefreshCw}
										onClick={async () => {
											const result = await showConfirm(
												"Reprocess Video?",
												"Are you sure you want to reprocess this video? This will reset all processing and regenerate the video with new audio.",
												{
													confirmButtonText:
														"Yes, Reprocess",
													cancelButtonText: "Cancel",
												}
											);
											if (result.isConfirmed) {
												reprocessMutation.mutate();
											}
										}}
										loading={
											reprocessMutation.isPending ||
											!!processingState ||
											(video &&
												((video.transcription_status ===
													"transcribing" &&
													!isTranscriptionStuck) ||
													video.ai_processing_status ===
														"processing" ||
													video.script_status ===
														"generating" ||
													video.synthesis_status ===
														"synthesizing" ||
													(video.synthesis_status ===
														"synthesized" &&
														!video.final_processed_video_url)))
										}
										disabled={
											reprocessMutation.isPending ||
											!!processingState ||
											(video &&
												((video.transcription_status ===
													"transcribing" &&
													!isTranscriptionStuck) ||
													video.ai_processing_status ===
														"processing" ||
													video.script_status ===
														"generating" ||
													video.synthesis_status ===
														"synthesizing" ||
													(video.synthesis_status ===
														"synthesized" &&
														!video.final_processed_video_url)))
										}>
										{reprocessMutation.isPending ||
										!!processingState ||
										(video &&
											((video.transcription_status ===
												"transcribing" &&
												!isTranscriptionStuck) ||
												video.ai_processing_status ===
													"processing" ||
												video.script_status ===
													"generating" ||
												video.synthesis_status ===
													"synthesizing"))
											? "Reprocessing..."
											: isTranscriptionStuck
											? "Reset & Reprocess"
											: "Reprocess Video"}
									</Button>
								)}
							</div>
						</div>

						{/* Divider */}
						<div className="border-t border-white/10 mb-6"></div>

						{/* Video Versions Section - Updates via WebSocket */}
						<div>
							<h4 className="text-sm font-semibold text-gray-300 mb-4">
								Video Versions
								{wsConnected && (
									<span className="ml-2 text-xs text-green-400">
										● Live
									</span>
								)}
							</h4>
							<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
								{((video.local_file_url || video.video_url) || 
								  (wsUpdate?.local_file_url || wsUpdate?.video_url)) && (
									<a
										href={
											wsUpdate?.local_file_url || 
											video.local_file_url ||
											wsUpdate?.video_url ||
											video.video_url
										}
										target="_blank"
										rel="noopener noreferrer"
										className="inline-flex items-center gap-2 px-4 py-3 text-sm rounded-lg bg-blue-500/20 text-blue-300 hover:bg-blue-500/30 border border-blue-500/30 w-full justify-center transition-colors">
										<ExternalLink className="w-4 h-4" />
										<span className="text-center">
											Downloaded Video (Original with
											Audio)
										</span>
									</a>
								)}

								{(video.voice_removed_video_url || wsUpdate?.voice_removed_video_url) && (
									<a
										href={wsUpdate?.voice_removed_video_url || video.voice_removed_video_url}
										target="_blank"
										rel="noopener noreferrer"
										className="inline-flex items-center gap-2 px-4 py-3 text-sm rounded-lg bg-yellow-500/20 text-yellow-300 hover:bg-yellow-500/30 border border-yellow-500/30 w-full justify-center transition-colors">
										<ExternalLink className="w-4 h-4" />
										<span className="text-center">
											Voice Removed Video (No Audio)
										</span>
									</a>
								)}

								{(video.synthesized_audio_url || wsUpdate?.synthesized_audio_url) && (
									<a
										href={wsUpdate?.synthesized_audio_url || video.synthesized_audio_url}
										target="_blank"
										rel="noopener noreferrer"
										className="inline-flex items-center gap-2 px-4 py-3 text-sm rounded-lg bg-purple-500/20 text-purple-300 hover:bg-purple-500/30 border border-purple-500/30 w-full justify-center transition-colors">
										<ExternalLink className="w-4 h-4" />
										<span className="text-center">
											🎵 Synthesized TTS Audio (Hindi)
										</span>
									</a>
								)}

								{(video.final_processed_video_url || wsUpdate?.final_processed_video_url) && (
									<a
										href={wsUpdate?.final_processed_video_url || video.final_processed_video_url}
										target="_blank"
										rel="noopener noreferrer"
										className="inline-flex items-center gap-2 px-4 py-3 text-sm rounded-lg bg-green-500/20 text-green-300 hover:bg-green-500/30 border border-green-500/30 w-full justify-center transition-colors">
										<ExternalLink className="w-4 h-4" />
										<span className="text-center">
											Final Processed Video (with New
											Hindi Audio)
										</span>
									</a>
								)}
							</div>

							{((video.synthesis_status === "synthesized" || wsUpdate?.synthesis_status === "synthesized") &&
								!video.voice_removed_video_url &&
								!wsUpdate?.voice_removed_video_url &&
								!video.final_processed_video_url &&
								!wsUpdate?.final_processed_video_url) && (
									<div className="text-xs text-yellow-400 p-3 bg-yellow-500/10 rounded-lg border border-yellow-500/30 mt-3">
										⏳ Processing video files... (This may
										take a few moments)
									</div>
								)}
						</div>
					</div>
				</div>

				{/* Right column - Sidebar info */}
				<div className="space-y-6">
					{/* Video Info Card */}
					<div className="bg-white/5 rounded-lg p-4 border border-white/10">
						<h3 className="text-lg font-semibold mb-2">
							{video.title || "Untitled"}
						</h3>

						{video.original_title &&
							video.original_title !== video.title && (
								<p className="text-sm text-gray-400 mb-4">
									{video.original_title}
								</p>
							)}

						{/* Status badges */}
						<div className="flex flex-wrap gap-2 mb-4">
							<StatusBadge status={video.status} />
							{video.transcription_status !==
								"not_transcribed" && (
								<StatusBadge
									status={video.transcription_status}
								/>
							)}
							{video.ai_processing_status !== "not_processed" && (
								<StatusBadge
									status={video.ai_processing_status}
								/>
							)}
							{video.transcript_hindi && (
								<span className="px-2 py-1 text-xs bg-purple-500/20 text-purple-300 rounded-full border border-purple-500/30">
									🇮🇳 Hindi Available
								</span>
							)}
						</div>

						{/* Meta info */}
						<div className="text-sm text-gray-400 space-y-2">
							<p>
								<span className="text-gray-500">Created:</span>{" "}
								{formatDate(video.created_at)}
							</p>
							<p>
								<span className="text-gray-500">Source:</span>{" "}
								{video.video_source
									? video.video_source === "rednote"
										? "RedNote"
										: video.video_source === "youtube"
										? "YouTube"
										: video.video_source === "facebook"
										? "Facebook"
										: video.video_source === "instagram"
										? "Instagram"
										: video.video_source === "vimeo"
										? "Vimeo"
										: video.video_source === "local"
										? "Local"
										: video.video_source
									: "-"}
							</p>
							<p>
								<span className="text-gray-500">Method:</span>{" "}
								{video.extraction_method || "-"}
							</p>
							{video.duration && (
								<p>
									<span className="text-gray-500">
										Duration:
									</span>{" "}
									{formatDuration(video.duration)}
								</p>
							)}
						</div>
					</div>

					{/* Currently Processing Videos - Sidebar */}
					{(() => {
						// Get current processing step for this video
						const getCurrentStep = () => {
							if (processingState?.type === "download" || !video.is_downloaded) return "Download";
							if (!video.frames_extracted) return "Frame Extraction";
							if (video.visual_transcript_started_at && !video.visual_transcript_finished_at) return "Visual Analysis";
							if (video.transcription_status === "transcribing" || processingState?.type === "transcribe") return "Transcription";
							if (video.ai_processing_status === "processing" || processingState?.type === "processAI") return "AI Processing";
							if (video.enhanced_transcript_started_at && !video.enhanced_transcript_finished_at) return "Enhanced Transcript";
							if (video.script_status === "generating" || processingState?.type === "script") return "Script Generation";
							if (video.synthesis_status === "synthesizing" || processingState?.type === "synthesis") return "TTS Synthesis";
							if (video.synthesis_status === "synthesized" && !video.final_processed_video_url) return "Final Video Assembly";
							if (video.final_processed_video_url && !video.cloudinary_url) return "Cloudinary Upload";
							if (video.cloudinary_url && !video.google_sheets_synced) return "Google Sheets Sync";
							return null;
						};

						const currentStep = getCurrentStep();
						if (!currentStep) return null;

						return (
							<div className="bg-blue-500/10 rounded-lg p-4 border border-blue-500/30 mb-4">
								<div className="flex items-center gap-2 mb-2">
									<Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
									<h4 className="text-xs font-semibold text-blue-400 uppercase tracking-wide">
										Currently Processing
									</h4>
								</div>
								<div className="space-y-1">
									<div className="text-sm text-white font-medium">
										{video.title || "Untitled"}
									</div>
									<div className="text-xs text-blue-300">
										Step: {currentStep}
									</div>
									{(() => {
										const startedAt = 
											processingState?.type === "download" ? video.extraction_started_at :
											video.visual_transcript_started_at && !video.visual_transcript_finished_at ? video.visual_transcript_started_at :
											video.transcription_status === "transcribing" ? video.transcript_started_at :
											video.ai_processing_status === "processing" ? video.ai_processing_started_at :
											video.enhanced_transcript_started_at && !video.enhanced_transcript_finished_at ? video.enhanced_transcript_started_at :
											video.script_status === "generating" ? video.script_started_at :
											video.synthesis_status === "synthesizing" ? video.synthesis_started_at :
											video.synthesis_status === "synthesized" && !video.final_processed_video_url ? video.final_video_started_at :
											null;
										if (startedAt) {
											return (
												<div className="text-xs text-gray-400">
													Started: {formatDate(startedAt)}
												</div>
											);
										}
										return null;
									})()}
								</div>
							</div>
						);
					})()}

					{/* Processing Status Card - Sidebar */}
					<div className="bg-white/5 rounded-lg p-4 border border-white/10">
						<div className="flex items-center justify-between mb-3">
							<h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
								Processing Status
							</h4>
							{(() => {
								// Calculate overall progress percentage
								const isTranscribing =
									video.transcription_status ===
										"transcribing" ||
									processingState?.type === "transcribe";
								const isProcessingAI =
									video.ai_processing_status ===
										"processing" ||
									processingState?.type === "processAI";
								const isSynthesizing =
									video.synthesis_status === "synthesizing" ||
									processingState?.type === "synthesis";
								const isDownloading =
									processingState?.type === "download";

								const steps = [
									{
										done:
											video.is_downloaded ||
											isDownloading,
										weight: 8,
									},
									{
										done: video.frames_extracted,
										weight: 5,
									},
									{
										done: !!video.visual_transcript,
										weight: 8,
									},
									{
										done:
											video.transcription_status ===
											"transcribed",
										weight: 12,
									},
									{
										done:
											video.ai_processing_status ===
											"processed",
										weight: 10,
									},
									{
										done: !!video.enhanced_transcript,
										weight: 8,
									},
									{
										done:
											video.script_status === "generated",
										weight: 12,
									},
									{
										done:
											video.synthesis_status ===
											"synthesized",
										weight: 15,
									},
									{
										done: !!video.final_processed_video_url,
										weight: 12,
									},
									{ done: !!video.cloudinary_url, weight: 5 },
									{
										done: !!video.google_sheets_synced,
										weight: 5,
									},
								];
								const totalWeight = steps.reduce(
									(sum, step) => sum + step.weight,
									0
								);
								const completedWeight = steps.reduce(
									(sum, step) =>
										sum + (step.done ? step.weight : 0),
									0
								);
								const progressPercent = Math.round(
									(completedWeight / totalWeight) * 100
								);

								return (
									<div className="flex items-center gap-2">
										<div className="w-16 h-2 bg-gray-700 rounded-full overflow-hidden">
											<div
												className="h-full bg-gradient-to-r from-blue-500 to-green-500 transition-all duration-300"
												style={{
													width: `${progressPercent}%`,
												}}
											/>
										</div>
										<span className="text-xs font-semibold text-gray-300 min-w-[3rem] text-right">
											{progressPercent}%
										</span>
									</div>
								);
							})()}
						</div>
						<div className="space-y-2">
							<div className="flex items-center justify-between">
								<span className="text-xs text-gray-400">
									Download
								</span>
								<span
									className={`text-xs px-2 py-0.5 rounded ${
										video.is_downloaded
											? "bg-green-500/20 text-green-300"
											: processingState?.type ===
											  "download"
											? "bg-yellow-500/20 text-yellow-300 animate-pulse"
											: "bg-gray-500/20 text-gray-400"
									}`}>
									{video.is_downloaded
										? "✓ Complete"
										: processingState?.type === "download"
										? "⏳ Downloading"
										: "Pending"}
								</span>
							</div>
							{video.extraction_started_at && (
								<div className="text-xs text-gray-500 ml-2">
									Started: {formatDate(video.extraction_started_at)}
								</div>
							)}
							{video.extraction_finished_at && (
								<div className="text-xs text-gray-500 ml-2">
									Completed: {formatDate(video.extraction_finished_at)}
								</div>
							)}
							<div className="flex items-center justify-between">
								<span className="text-xs text-gray-400">
									Frame Extraction
								</span>
								<span
									className={`text-xs px-2 py-0.5 rounded ${
										video.frames_extracted
											? "bg-green-500/20 text-green-300"
											: "bg-gray-500/20 text-gray-400"
									}`}>
									{video.frames_extracted
										? `✓ ${video.total_frames_extracted || 0} frames`
										: "Pending"}
								</span>
							</div>
							{video.frames_extracted_at && (
								<div className="text-xs text-gray-500 ml-2">
									Extracted: {formatDate(video.frames_extracted_at)}
								</div>
							)}
							<div className="flex items-center justify-between">
								<span className="text-xs text-gray-400">
									Transcription
								</span>
								{(() => {
									const isTranscribing =
										video.transcription_status ===
											"transcribing" ||
										processingState?.type === "transcribe";
									const isFailed =
										video.transcription_status === "failed";
									const isComplete =
										video.transcription_status ===
										"transcribed";

									return (
										<span
											className={`text-xs px-2 py-0.5 rounded ${
												isComplete
													? "bg-green-500/20 text-green-300"
													: isTranscribing
													? "bg-yellow-500/20 text-yellow-300 animate-pulse"
													: isFailed
													? "bg-red-500/20 text-red-300"
													: "bg-gray-500/20 text-gray-400"
											}`}>
											{isComplete
												? "✓ Complete"
												: isTranscribing
												? "⏳ Processing"
												: isFailed
												? "✗ Failed"
												: "Pending"}
										</span>
									);
								})()}
							</div>
							{video.transcript_started_at && (
								<div className="text-xs text-gray-500 ml-2">
									Started: {formatDate(video.transcript_started_at)}
								</div>
							)}
							{video.transcript_processed_at && (
								<div className="text-xs text-gray-500 ml-2">
									Completed: {formatDate(video.transcript_processed_at)}
								</div>
							)}
							<div className="flex items-center justify-between">
								<span className="text-xs text-gray-400">
									Visual Analysis (Gemini)
								</span>
								{(() => {
									const isProcessing =
										video.visual_transcript_started_at &&
										!video.visual_transcript_finished_at;
									const isComplete = !!video.visual_transcript;

									return (
										<span
											className={`text-xs px-2 py-0.5 rounded ${
												isComplete
													? "bg-green-500/20 text-green-300"
													: isProcessing
													? "bg-yellow-500/20 text-yellow-300 animate-pulse"
													: "bg-gray-500/20 text-gray-400"
											}`}>
											{isComplete
												? "✓ Complete"
												: isProcessing
												? "⏳ Processing"
												: "Pending"}
										</span>
									);
								})()}
							</div>
							{video.visual_transcript_started_at && (
								<div className="text-xs text-gray-500 ml-2">
									Started: {formatDate(video.visual_transcript_started_at)}
								</div>
							)}
							{video.visual_transcript_finished_at && (
								<div className="text-xs text-gray-500 ml-2">
									Completed: {formatDate(video.visual_transcript_finished_at)}
								</div>
							)}
							<div className="flex items-center justify-between">
								<span className="text-xs text-gray-400">
									Enhanced Transcript
								</span>
								{(() => {
									const isProcessing =
										video.enhanced_transcript_started_at &&
										!video.enhanced_transcript_finished_at;
									const isComplete = !!video.enhanced_transcript;

									return (
										<span
											className={`text-xs px-2 py-0.5 rounded ${
												isComplete
													? "bg-green-500/20 text-green-300"
													: isProcessing
													? "bg-yellow-500/20 text-yellow-300 animate-pulse"
													: "bg-gray-500/20 text-gray-400"
											}`}>
											{isComplete
												? "✓ Complete"
												: isProcessing
												? "⏳ Processing"
												: "Pending"}
										</span>
									);
								})()}
							</div>
							{video.enhanced_transcript_started_at && (
								<div className="text-xs text-gray-500 ml-2">
									Started: {formatDate(video.enhanced_transcript_started_at)}
								</div>
							)}
							{video.enhanced_transcript_finished_at && (
								<div className="text-xs text-gray-500 ml-2">
									Completed: {formatDate(video.enhanced_transcript_finished_at)}
								</div>
							)}
							<div className="flex items-center justify-between">
								<span className="text-xs text-gray-400">
									AI Processing
								</span>
								{(() => {
									const isProcessing =
										video.ai_processing_status ===
											"processing" ||
										processingState?.type === "processAI";
									const isFailed =
										video.ai_processing_status === "failed";
									const isComplete =
										video.ai_processing_status ===
										"processed";

									return (
										<span
											className={`text-xs px-2 py-0.5 rounded ${
												isComplete
													? "bg-green-500/20 text-green-300"
													: isProcessing
													? "bg-yellow-500/20 text-yellow-300 animate-pulse"
													: isFailed
													? "bg-red-500/20 text-red-300"
													: "bg-gray-500/20 text-gray-400"
											}`}>
											{isComplete
												? "✓ Complete"
												: isProcessing
												? "⏳ Processing"
												: isFailed
												? "✗ Failed"
												: "Pending"}
										</span>
									);
								})()}
							</div>
							{video.ai_processing_started_at && (
								<div className="text-xs text-gray-500 ml-2">
									Started: {formatDate(video.ai_processing_started_at)}
								</div>
							)}
							{video.ai_processed_at && (
								<div className="text-xs text-gray-500 ml-2">
									Completed: {formatDate(video.ai_processed_at)}
								</div>
							)}
							<div className="flex items-center justify-between">
								<span className="text-xs text-gray-400">
									Script Generation
								</span>
								<span
									className={`text-xs px-2 py-0.5 rounded ${
										video.script_status === "generated"
											? "bg-green-500/20 text-green-300"
											: video.script_status ===
											  "generating"
											? "bg-yellow-500/20 text-yellow-300 animate-pulse"
											: video.script_status === "failed"
											? "bg-red-500/20 text-red-300"
											: "bg-gray-500/20 text-gray-400"
									}`}>
									{video.script_status === "generated"
										? "✓ Complete"
										: video.script_status === "generating"
										? "⏳ Processing"
										: video.script_status === "failed"
										? "✗ Failed"
										: "Pending"}
								</span>
							</div>
							{video.script_started_at && (
								<div className="text-xs text-gray-500 ml-2">
									Started: {formatDate(video.script_started_at)}
								</div>
							)}
							{video.script_generated_at && (
								<div className="text-xs text-gray-500 ml-2">
									Completed: {formatDate(video.script_generated_at)}
								</div>
							)}
							<div className="flex items-center justify-between">
								<span className="text-xs text-gray-400">
									TTS Synthesis
								</span>
								{(() => {
									const isSynthesizing =
										video.synthesis_status ===
											"synthesizing" ||
										processingState?.type === "synthesis";
									const isFailed =
										video.synthesis_status === "failed";
									const isComplete =
										video.synthesis_status ===
										"synthesized";

									return (
										<span
											className={`text-xs px-2 py-0.5 rounded ${
												isComplete
													? "bg-green-500/20 text-green-300"
													: isSynthesizing
													? "bg-yellow-500/20 text-yellow-300 animate-pulse"
													: isFailed
													? "bg-red-500/20 text-red-300"
													: "bg-gray-500/20 text-gray-400"
											}`}>
											{isComplete
												? "✓ Complete"
												: isSynthesizing
												? "⏳ Processing"
												: isFailed
												? "✗ Failed"
												: "Pending"}
										</span>
									);
								})()}
							</div>
							{video.synthesis_started_at && (
								<div className="text-xs text-gray-500 ml-2">
									Started: {formatDate(video.synthesis_started_at)}
								</div>
							)}
							{video.synthesized_at && (
								<div className="text-xs text-gray-500 ml-2">
									Completed: {formatDate(video.synthesized_at)}
								</div>
							)}
							<div className="flex items-center justify-between">
								<span className="text-xs text-gray-400">
									Final Video
								</span>
								<span
									className={`text-xs px-2 py-0.5 rounded ${
										video.final_processed_video_url
											? "bg-green-500/20 text-green-300"
											: video.synthesis_status ===
													"synthesized" &&
											  !video.final_processed_video_url
											? "bg-yellow-500/20 text-yellow-300 animate-pulse"
											: "bg-gray-500/20 text-gray-400"
									}`}>
									{video.final_processed_video_url
										? "✓ Ready"
										: video.synthesis_status ===
												"synthesized" &&
										  !video.final_processed_video_url
										? "⏳ Assembling"
										: "Pending"}
								</span>
							</div>
							{video.final_video_started_at && (
								<div className="text-xs text-gray-500 ml-2">
									Started: {formatDate(video.final_video_started_at)}
								</div>
							)}
							{video.final_video_finished_at && (
								<div className="text-xs text-gray-500 ml-2">
									Completed: {formatDate(video.final_video_finished_at)}
								</div>
							)}
							<div className="flex items-center justify-between">
								<span className="text-xs text-gray-400">
									Cloudinary Upload
								</span>
								<span
									className={`text-xs px-2 py-0.5 rounded ${
										video.cloudinary_url
											? "bg-green-500/20 text-green-300"
											: video.final_processed_video_url
											? "bg-yellow-500/20 text-yellow-300 animate-pulse"
											: "bg-gray-500/20 text-gray-400"
									}`}>
									{video.cloudinary_url
										? "✓ Uploaded"
										: video.final_processed_video_url
										? "⏳ Uploading..."
										: "Not Ready"}
								</span>
							</div>
							{video.cloudinary_upload_started_at && (
								<div className="text-xs text-gray-500 ml-2">
									Started: {formatDate(video.cloudinary_upload_started_at)}
								</div>
							)}
							{video.cloudinary_uploaded_at && (
								<div className="text-xs text-gray-500 ml-2">
									Completed: {formatDate(video.cloudinary_uploaded_at)}
								</div>
							)}
							<div className="flex items-center justify-between">
								<span className="text-xs text-gray-400">
									Google Sheets Sync
								</span>
								<span
									className={`text-xs px-2 py-0.5 rounded ${
										video.google_sheets_synced
											? "bg-green-500/20 text-green-300"
											: video.final_processed_video_url
											? "bg-yellow-500/20 text-yellow-300 animate-pulse"
											: "bg-gray-500/20 text-gray-400"
									}`}>
									{video.google_sheets_synced
										? "✓ Synced"
										: video.final_processed_video_url
										? "⏳ Syncing..."
										: "Not Ready"}
								</span>
							</div>
							{video.google_sheets_sync_started_at && (
								<div className="text-xs text-gray-500 ml-2">
									Started: {formatDate(video.google_sheets_sync_started_at)}
								</div>
							)}
							{video.google_sheets_synced_at && (
								<div className="text-xs text-gray-500 ml-2">
									Completed: {formatDate(video.google_sheets_synced_at)}
								</div>
							)}
						</div>
					</div>

					{/* Video Information Card */}
					<div className="bg-white/5 rounded-lg p-4 border border-white/10">
						<h4 className="text-xs font-semibold text-gray-400 mb-3 uppercase tracking-wide">
							Video Information
						</h4>
						<div className="space-y-2">
							{video.duration && (
								<div className="flex items-center justify-between">
									<span className="text-xs text-gray-400">
										Duration
									</span>
									<span className="text-xs text-gray-300 font-mono">
										{formatDuration(video.duration)}
									</span>
								</div>
							)}
							<div className="flex items-center justify-between">
								<span className="text-xs text-gray-400">
									Source
								</span>
								<span className="text-xs text-gray-300">
									{video.video_source
										? video.video_source === "rednote"
											? "RedNote"
											: video.video_source === "youtube"
											? "YouTube"
											: video.video_source === "facebook"
											? "Facebook"
											: video.video_source === "instagram"
											? "Instagram"
											: video.video_source === "vimeo"
											? "Vimeo"
											: video.video_source === "local"
											? "Local"
											: video.video_source
										: "-"}
								</span>
							</div>
							<div className="flex items-center justify-between">
								<span className="text-xs text-gray-400">
									Method
								</span>
								<span className="text-xs text-gray-300">
									{video.extraction_method || "-"}
								</span>
							</div>
							<div className="flex items-center justify-between">
								<span className="text-xs text-gray-400">
									Language
								</span>
								<span className="text-xs text-gray-300">
									{video.transcript_language || "Unknown"}
								</span>
							</div>
							{video.video_id && (
								<div className="flex items-center justify-between">
									<span className="text-xs text-gray-400">
										Video ID
									</span>
									<span
										className="text-xs text-gray-300 font-mono truncate max-w-[120px]"
										title={video.video_id}>
										{video.video_id}
									</span>
								</div>
							)}
							<div className="flex items-center justify-between">
								<span className="text-xs text-gray-400">
									Created
								</span>
								<span className="text-xs text-gray-300">
									{formatDate(video.created_at)}
								</span>
							</div>
						</div>
					</div>

					{/* TTS Settings Card */}
					<div className="bg-white/5 rounded-lg p-4 border border-white/10">
						<h4 className="text-xs font-semibold text-gray-400 mb-3 uppercase tracking-wide">
							TTS Settings
						</h4>
						<div className="space-y-2">
							{video.tts_speed ? (
								<div className="flex items-center justify-between">
									<span className="text-xs text-gray-400">
										Speed
									</span>
									<span className="text-xs text-gray-300 font-mono">
										{video.tts_speed}x
									</span>
								</div>
							) : (
								<div className="flex items-center justify-between">
									<span className="text-xs text-gray-400">
										Speed
									</span>
									<span className="text-xs text-gray-500">
										Default (1.0x)
									</span>
								</div>
							)}
							{video.tts_temperature !== undefined &&
							video.tts_temperature !== null ? (
								<div className="flex items-center justify-between">
									<span className="text-xs text-gray-400">
										Temperature
									</span>
									<span className="text-xs text-gray-300 font-mono">
										{video.tts_temperature}
									</span>
								</div>
							) : (
								<div className="flex items-center justify-between">
									<span className="text-xs text-gray-400">
										Temperature
									</span>
									<span className="text-xs text-gray-500">
										Default (0.75)
									</span>
								</div>
							)}
							{video.tts_repetition_penalty !== undefined &&
							video.tts_repetition_penalty !== null ? (
								<div className="flex items-center justify-between">
									<span className="text-xs text-gray-400">
										Repetition Penalty
									</span>
									<span className="text-xs text-gray-300 font-mono">
										{video.tts_repetition_penalty}
									</span>
								</div>
							) : (
								<div className="flex items-center justify-between">
									<span className="text-xs text-gray-400">
										Repetition Penalty
									</span>
									<span className="text-xs text-gray-500">
										Default (5.0)
									</span>
								</div>
							)}
							{video.transcript_hindi && (
								<div className="flex items-center justify-between">
									<span className="text-xs text-gray-400">
										Hindi Translation
									</span>
									<span className="text-xs text-purple-300">
										✓ Available
									</span>
								</div>
							)}
							{video.hindi_script && (
								<div className="flex items-center justify-between">
									<span className="text-xs text-gray-400">
										Hindi Script
									</span>
									<span className="text-xs text-indigo-300">
										✓ Generated
									</span>
								</div>
							)}
							{video.frames_extracted && (
								<div className="flex items-center justify-between">
									<span className="text-xs text-gray-400">
										Frames Extracted
									</span>
									<span className="text-xs text-blue-300">
										✓ {video.total_frames_extracted || 0} frames
									</span>
								</div>
							)}
							{video.frames_extracted_at && (
								<div className="flex items-center justify-between">
									<span className="text-xs text-gray-400">
										Frames Extracted At
									</span>
									<span className="text-xs text-gray-300">
										{formatDate(video.frames_extracted_at)}
									</span>
								</div>
							)}
							{video.visual_transcript && (
								<div className="flex items-center justify-between">
									<span className="text-xs text-gray-400">
										Visual Transcript
									</span>
									<span className="text-xs text-purple-300">
										✓ Available (Gemini AI)
									</span>
								</div>
							)}
						</div>
						{video.tts_speed && (
							<div className="mt-3 pt-3 border-t border-white/10">
								<p className="text-xs text-gray-400">
									TTS Speed: {video.tts_speed}x | Temp:{" "}
									{video.tts_temperature || "0.75"}
								</p>
							</div>
						)}
					</div>
				</div>
			</div>
			{/* Tabs */}
			<div className="bg-white/5 rounded-lg border border-white/10 overflow-hidden">
				<div className="border-b border-white/10">
					<div className="flex gap-1 p-2">
						{tabs.map((tab) => (
							<button
								key={tab.id}
								onClick={() => setActiveTab(tab.id)}
								className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
									activeTab === tab.id
										? "bg-white/10 text-white"
										: "text-gray-400 hover:text-white hover:bg-white/5"
								}`}>
								{tab.label}
							</button>
						))}
					</div>
				</div>

				{/* Tab content - Full Width */}
				<div className="p-6 min-h-[400px] w-full">
					{activeTab === "info" && (
						<div className="space-y-6">
							<div className="bg-white/5 rounded-lg p-4 border border-white/10">
								<h4 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
									<FileText className="w-4 h-4" />
									Description
								</h4>
								<p className="text-sm text-gray-300 leading-relaxed">
									{video.description || (
										<span className="text-gray-500 italic">
											No description available
										</span>
									)}
								</p>
							</div>

							{video.original_description && (
								<div className="bg-white/5 rounded-lg p-4 border border-white/10">
									<h4 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
										<Globe className="w-4 h-4" />
										Original Description
									</h4>
									<p className="text-sm text-gray-400 leading-relaxed">
										{video.original_description}
									</p>
								</div>
							)}

							<div className="bg-white/5 rounded-lg p-4 border border-white/10">
								<h4 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
									<RefreshCw className="w-4 h-4" />
									Processing Timeline
								</h4>
								<div className="space-y-3">
									{video.created_at && (
										<div className="flex items-start gap-3">
											<div className="w-2 h-2 rounded-full bg-blue-400 mt-1.5"></div>
											<div className="flex-1">
												<p className="text-xs font-medium text-gray-300">
													Video Added
												</p>
												<p className="text-xs text-gray-500">
													{formatDate(
														video.created_at
													)}
												</p>
											</div>
										</div>
									)}
									{video.transcript_processed_at && (
										<div className="flex items-start gap-3">
											<div className="w-2 h-2 rounded-full bg-green-400 mt-1.5"></div>
											<div className="flex-1">
												<p className="text-xs font-medium text-gray-300">
													Transcription Completed
												</p>
												<p className="text-xs text-gray-500">
													{formatDate(
														video.transcript_processed_at
													)}
												</p>
											</div>
										</div>
									)}
									{video.script_generated_at && (
										<div className="flex items-start gap-3">
											<div className="w-2 h-2 rounded-full bg-indigo-400 mt-1.5"></div>
											<div className="flex-1">
												<p className="text-xs font-medium text-gray-300">
													Hindi Script Generated
												</p>
												<p className="text-xs text-gray-500">
													{formatDate(
														video.script_generated_at
													)}
												</p>
											</div>
										</div>
									)}
									{video.synthesized_at && (
										<div className="flex items-start gap-3">
											<div className="w-2 h-2 rounded-full bg-purple-400 mt-1.5"></div>
											<div className="flex-1">
												<p className="text-xs font-medium text-gray-300">
													TTS Audio Synthesized
												</p>
												<p className="text-xs text-gray-500">
													{formatDate(
														video.synthesized_at
													)}
												</p>
											</div>
										</div>
									)}
									{video.final_processed_video_url && (
										<div className="flex items-start gap-3">
											<div className="w-2 h-2 rounded-full bg-green-500 mt-1.5"></div>
											<div className="flex-1">
												<p className="text-xs font-medium text-gray-300">
													Final Video Ready
												</p>
												<p className="text-xs text-gray-500">
													Processing complete
												</p>
											</div>
										</div>
									)}
									{video.cloudinary_uploaded_at && (
										<div className="flex items-start gap-3">
											<div className="w-2 h-2 rounded-full bg-blue-500 mt-1.5"></div>
											<div className="flex-1">
												<p className="text-xs font-medium text-gray-300">
													Uploaded to Cloudinary
												</p>
												<p className="text-xs text-gray-500">
													{formatDate(
														video.cloudinary_uploaded_at
													)}
												</p>
											</div>
										</div>
									)}
									{video.google_sheets_synced_at && (
										<div className="flex items-start gap-3">
											<div className="w-2 h-2 rounded-full bg-indigo-500 mt-1.5"></div>
											<div className="flex-1">
												<p className="text-xs font-medium text-gray-300">
													Synced to Google Sheets
												</p>
												<p className="text-xs text-gray-500">
													{formatDate(
														video.google_sheets_synced_at
													)}
												</p>
											</div>
										</div>
									)}
								</div>
							</div>

							<div className="bg-white/5 rounded-lg p-4 border border-white/10">
								<h4 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
									<ExternalLink className="w-4 h-4" />
									Original URL
								</h4>
								<div className="flex items-center gap-2 p-3 bg-white/5 rounded-lg group">
									<p className="text-sm text-gray-300 truncate flex-1 font-mono">
										{video.url}
									</p>
									<Button
										size="sm"
										variant="ghost"
										icon={Copy}
										onClick={() =>
											copyToClipboard(video.url)
										}
										className="opacity-0 group-hover:opacity-100 transition-opacity">
										Copy
									</Button>
									<a
										href={video.url}
										target="_blank"
										rel="noopener noreferrer"
										className="p-2 text-gray-400 hover:text-white transition-colors"
										title="Open in new tab">
										<ExternalLink className="w-4 h-4" />
									</a>
								</div>
							</div>

							{(video.local_file_url ||
								video.voice_removed_video_url ||
								video.final_processed_video_url ||
								video.synthesized_audio_url) && (
								<div className="bg-white/5 rounded-lg p-4 border border-white/10">
									<h4 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
										<Download className="w-4 h-4" />
										Generated Files
									</h4>
									<div className="grid grid-cols-2 gap-2">
										{video.local_file_url && (
											<div className="text-xs">
												<span className="text-gray-400">
													Original:
												</span>
												<span className="text-green-300 ml-1">
													✓ Available
												</span>
											</div>
										)}
										{video.voice_removed_video_url && (
											<div className="text-xs">
												<span className="text-gray-400">
													Voice Removed:
												</span>
												<span className="text-yellow-300 ml-1">
													✓ Available
												</span>
											</div>
										)}
										{video.synthesized_audio_url && (
											<div className="text-xs">
												<span className="text-gray-400">
													TTS Audio:
												</span>
												<span className="text-purple-300 ml-1">
													✓ Available
												</span>
											</div>
										)}
										{video.final_processed_video_url && (
											<div className="text-xs">
												<span className="text-gray-400">
													Final Video:
												</span>
												<span className="text-green-300 ml-1">
													✓ Available
												</span>
											</div>
										)}
									</div>
								</div>
							)}
						</div>
					)}

					{activeTab === "transcript" && (
						<div className="space-y-6">
							{/* Comparison Header */}
							{(video.transcript ||
								video.whisper_transcript ||
								video.visual_transcript ||
								video.enhanced_transcript) && (
								<div className="bg-gradient-to-r from-blue-500/10 via-purple-500/10 to-green-500/10 to-orange-500/10 rounded-lg p-4 border border-white/10">
									<h3 className="text-lg font-semibold text-white mb-2">
										📊 Triple Transcription Comparison + AI
										Enhancement
									</h3>
									<p className="text-sm text-gray-400">
										Compare NCA Toolkit, Whisper AI, and
										Visual Analysis transcriptions. The
										Enhanced transcript uses AI to merge all
										three sources for perfect accuracy.
									</p>
								</div>
							)}

							{/* Enhanced Transcript (Primary Display) - Show if available (Visual Analysis is optional) */}
							{video.enhanced_transcript && (
								<div className="bg-gradient-to-r from-orange-500/10 to-yellow-500/10 rounded-lg p-4 border border-orange-500/30 mb-6 w-full">
									<div className="flex items-center justify-between mb-3">
										<h4 className="text-base font-semibold text-orange-300 flex items-center gap-2">
											⭐ AI-Enhanced Transcript (Best
											Quality)
										</h4>
										<span className="px-2 py-1 text-xs rounded bg-orange-500/20 text-orange-300">
											✓ AI-Merged (All 3 Sources)
										</span>
									</div>
									<p className="text-xs text-gray-400 mb-3">
										This transcript combines the best parts
										from Whisper, NCA Toolkit, and Visual
										Analysis (if available) using AI for
										perfect accuracy.{" "}
										<strong className="text-orange-400">
											Visual Analysis is optional.
										</strong>
									</p>

									{/* With Timestamps */}
									<div className="space-y-2 mb-3">
										<div className="flex items-center justify-between">
											<h5 className="text-xs font-medium text-gray-300">
												With Timestamps
											</h5>
											<Button
												size="sm"
												variant="ghost"
												icon={Copy}
												onClick={() =>
													copyToClipboard(
														video.enhanced_transcript
													)
												}
												className="text-xs">
												Copy
											</Button>
										</div>
										<div className="p-3 bg-white/5 rounded-lg max-h-96 overflow-y-auto border border-white/10">
											<p className="text-xs whitespace-pre-wrap leading-relaxed font-mono text-gray-300">
												{video.enhanced_transcript}
											</p>
										</div>
									</div>

									{/* Plain Text */}
									<div className="space-y-2">
										<div className="flex items-center justify-between">
											<h5 className="text-xs font-medium text-gray-300">
												Plain Text
											</h5>
											<Button
												size="sm"
												variant="ghost"
												icon={Copy}
												onClick={() =>
													copyToClipboard(
														video.enhanced_transcript_without_timestamps ||
															video.enhanced_transcript
													)
												}
												className="text-xs">
												Copy
											</Button>
										</div>
										<div className="p-3 bg-orange-500/5 rounded-lg max-h-96 overflow-y-auto border border-orange-500/20">
											<p className="text-xs whitespace-pre-wrap leading-relaxed text-gray-300">
												{video.enhanced_transcript_without_timestamps ||
													video.enhanced_transcript}
											</p>
										</div>
									</div>

									{/* Hindi Translation - Show if available */}
									{video.enhanced_transcript_hindi && (
										<div className="space-y-2 mt-3">
											<div className="flex items-center justify-between">
												<h5 className="text-xs font-medium text-purple-300">
													Hindi Translation
												</h5>
												<Button
													size="sm"
													variant="ghost"
													icon={Copy}
													onClick={() =>
														copyToClipboard(
															video.enhanced_transcript_hindi
														)
													}
													className="text-xs">
													Copy
												</Button>
											</div>
											<div className="p-3 bg-purple-500/5 rounded-lg max-h-96 overflow-y-auto border border-purple-500/20">
												<p className="text-xs whitespace-pre-wrap leading-relaxed text-gray-300">
													{
														video.enhanced_transcript_hindi
													}
												</p>
											</div>
										</div>
									)}
								</div>
							)}

							{/* Show message if Enhanced Transcript is not available */}
							{!video.enhanced_transcript &&
								(video.transcript ||
									video.whisper_transcript) && (
									<div className="bg-yellow-500/10 rounded-lg p-4 border border-yellow-500/30 mb-6 w-full">
										<div className="flex items-center gap-2 mb-2">
											<span className="text-yellow-400">
												⏳
											</span>
											<h4 className="text-base font-semibold text-yellow-300">
												AI-Enhanced Transcript
												Processing
											</h4>
										</div>
										<p className="text-xs text-gray-400 mb-2">
											AI-Enhanced transcript is being
											generated. Status:
										</p>
										<ul className="text-xs text-gray-400 space-y-1 ml-4 list-disc">
											<li className="text-green-400">
												✓ NCA Toolkit / Whisper AI:
												Complete
											</li>
											<li
												className={
													video.visual_transcript
														? "text-green-400"
														: "text-gray-500"
												}>
												{video.visual_transcript
													? "✓"
													: "○"}{" "}
												Visual Analysis:{" "}
												{video.visual_transcript
													? "Complete"
													: "Optional (Not Available - continuing without it)"}
											</li>
										</ul>
										<p className="text-xs text-yellow-400 mt-3">
											<strong>Note:</strong> AI-Enhanced
											transcript is being generated using
											available sources. Visual Analysis
											is optional and will be included if
											available for better accuracy.
										</p>
									</div>
								)}

							{/* Show message if no transcript sources available */}
							{!video.enhanced_transcript &&
								!video.transcript &&
								!video.whisper_transcript && (
									<div className="bg-yellow-500/10 rounded-lg p-4 border border-yellow-500/30 mb-6 w-full">
										<div className="flex items-center gap-2 mb-2">
											<span className="text-yellow-400">
												⚠️
											</span>
											<h4 className="text-base font-semibold text-yellow-300">
												AI-Enhanced Transcript Not
												Available
											</h4>
										</div>
										<p className="text-xs text-gray-400 mb-2">
											AI-Enhanced transcript requires at
											least NCA/Whisper transcription:
										</p>
										<ul className="text-xs text-gray-400 space-y-1 ml-4 list-disc">
											<li
												className={
													video.transcript ||
													video.whisper_transcript
														? "text-green-400"
														: "text-yellow-400"
												}>
												{video.transcript ||
												video.whisper_transcript
													? "✓"
													: "⏳"}{" "}
												NCA Toolkit / Whisper AI:{" "}
												{video.transcript ||
												video.whisper_transcript
													? "Complete"
													: "Pending (Required)"}
											</li>
											<li
												className={
													video.visual_transcript
														? "text-green-400"
														: "text-gray-500"
												}>
												{video.visual_transcript
													? "✓"
													: "○"}{" "}
												Visual Analysis:{" "}
												{video.visual_transcript
													? "Complete"
													: "Optional (Not Available)"}
											</li>
										</ul>
										<p className="text-xs text-yellow-400 mt-3">
											<strong>Note:</strong> Please start
											transcription to generate
											AI-Enhanced transcript. Visual
											Analysis is optional and will be
											included if available for better
											accuracy.
										</p>
									</div>
								)}

							{/* Triple Transcription Comparison - Full Width Layout */}
							{video.transcript ||
							video.whisper_transcript ||
							video.visual_transcript ? (
								<div className="grid grid-cols-1 xl:grid-cols-3 gap-6 w-full">
									{/* NCA TOOLKIT TRANSCRIPTION */}
									<div className="space-y-4">
										<div className="bg-blue-500/10 rounded-lg p-4 border border-blue-500/30">
											<div className="flex items-center justify-between mb-3">
												<h4 className="text-base font-semibold text-blue-300 flex items-center gap-2">
													🔷 NCA Toolkit
												</h4>
												<span
													className={`px-2 py-1 text-xs rounded ${
														video.transcription_status ===
														"transcribed"
															? "bg-green-500/20 text-green-300"
															: video.transcription_status ===
															  "transcribing"
															? "bg-yellow-500/20 text-yellow-300"
															: video.transcription_status ===
															  "failed"
															? "bg-red-500/20 text-red-300"
															: "bg-gray-500/20 text-gray-400"
													}`}>
													{video.transcription_status ===
													"transcribed"
														? "✓ Complete"
														: video.transcription_status ===
														  "transcribing"
														? isTranscriptionStuck
															? `⏳ Processing (${transcriptionElapsedMinutes}m - Stuck?)`
															: `⏳ Processing (${transcriptionElapsedMinutes}m)`
														: video.transcription_status ===
														  "failed"
														? "✗ Failed"
														: "Pending"}
												</span>
											</div>

											{video.transcript ? (
												<>
													<div className="grid grid-cols-2 gap-2 text-xs mb-3">
														<div className="bg-white/5 rounded px-2 py-1">
															<span className="text-gray-400">
																Language:
															</span>
															<span className="text-white ml-1">
																{video.transcript_language ||
																	"Unknown"}
															</span>
														</div>
														<div className="bg-white/5 rounded px-2 py-1">
															<span className="text-gray-400">
																Length:
															</span>
															<span className="text-white ml-1">
																{video
																	.transcript_without_timestamps
																	?.length ||
																	video
																		.transcript
																		?.length ||
																	0}{" "}
																chars
															</span>
														</div>
													</div>

													{/* With Timestamps */}
													<div className="space-y-2 mb-3">
														<div className="flex items-center justify-between">
															<h5 className="text-xs font-medium text-gray-300">
																With Timestamps
															</h5>
															<Button
																size="sm"
																variant="ghost"
																icon={Copy}
																onClick={() =>
																	copyToClipboard(
																		video.transcript
																	)
																}
																className="text-xs">
																Copy
															</Button>
														</div>
														<div className="p-3 bg-white/5 rounded-lg max-h-96 overflow-y-auto border border-white/10">
															<p className="text-xs whitespace-pre-wrap leading-relaxed font-mono text-gray-300">
																{
																	video.transcript
																}
															</p>
														</div>
													</div>

													{/* Plain Text */}
													<div className="space-y-2">
														<div className="flex items-center justify-between">
															<h5 className="text-xs font-medium text-gray-300">
																Plain Text
															</h5>
															<Button
																size="sm"
																variant="ghost"
																icon={Copy}
																onClick={() =>
																	copyToClipboard(
																		video.transcript_without_timestamps ||
																			video.transcript
																	)
																}
																className="text-xs">
																Copy
															</Button>
														</div>
														<div className="p-3 bg-blue-500/5 rounded-lg max-h-96 overflow-y-auto border border-blue-500/20">
															<p className="text-xs whitespace-pre-wrap leading-relaxed text-gray-300">
																{video.transcript_without_timestamps ||
																	video.transcript}
															</p>
														</div>
													</div>
												</>
											) : (
												<div className="text-center py-8 text-gray-500">
													<p className="text-sm">
														No NCA transcription
														available
													</p>
												</div>
											)}
										</div>
									</div>

									{/* VISUAL ANALYSIS TRANSCRIPTION */}
									<div className="space-y-4">
										<div className="bg-purple-500/10 rounded-lg p-4 border border-purple-500/30">
											<div className="flex items-center justify-between mb-3">
												<h4 className="text-base font-semibold text-purple-300 flex items-center gap-2">
													👁️ Visual Analysis
												</h4>
												<span
													className={`px-2 py-1 text-xs rounded ${
														video.visual_transcript
															? "bg-green-500/20 text-green-300"
															: "bg-gray-500/20 text-gray-400"
													}`}>
													{video.visual_transcript
														? "✓ Complete"
														: "Pending"}
												</span>
											</div>

											{video.visual_transcript ? (
												<>
													<div className="grid grid-cols-1 gap-2 text-xs mb-3">
														<div className="bg-white/5 rounded px-2 py-1">
															<span className="text-gray-400">
																Frames Analyzed:
															</span>
															<span className="text-white ml-1">
																Every 3ms
															</span>
														</div>
														<div className="bg-white/5 rounded px-2 py-1">
															<span className="text-gray-400">
																Length:
															</span>
															<span className="text-white ml-1">
																{video
																	.visual_transcript_without_timestamps
																	?.length ||
																	video
																		.visual_transcript
																		?.length ||
																	0}{" "}
																chars
															</span>
														</div>
													</div>

													{/* With Timestamps */}
													<div className="space-y-2 mb-3">
														<div className="flex items-center justify-between">
															<h5 className="text-xs font-medium text-gray-300">
																With Timestamps
															</h5>
															<Button
																size="sm"
																variant="ghost"
																icon={Copy}
																onClick={() =>
																	copyToClipboard(
																		video.visual_transcript
																	)
																}
																className="text-xs">
																Copy
															</Button>
														</div>
														<div className="p-3 bg-white/5 rounded-lg max-h-96 overflow-y-auto border border-white/10">
															<p className="text-xs whitespace-pre-wrap leading-relaxed font-mono text-gray-300">
																{
																	video.visual_transcript
																}
															</p>
														</div>
													</div>

													{/* Plain Text */}
													<div className="space-y-2">
														<div className="flex items-center justify-between">
															<h5 className="text-xs font-medium text-gray-300">
																Plain Text
															</h5>
															<Button
																size="sm"
																variant="ghost"
																icon={Copy}
																onClick={() =>
																	copyToClipboard(
																		video.visual_transcript_without_timestamps ||
																			video.visual_transcript
																	)
																}
																className="text-xs">
																Copy
															</Button>
														</div>
														<div className="p-3 bg-purple-500/5 rounded-lg max-h-96 overflow-y-auto border border-purple-500/20">
															<p className="text-xs whitespace-pre-wrap leading-relaxed text-gray-300">
																{video.visual_transcript_without_timestamps ||
																	video.visual_transcript}
															</p>
														</div>
													</div>
												</>
											) : (
												<div className="text-center py-8 text-gray-500">
													<p className="text-sm mb-2">
														Visual Analysis in
														Progress
													</p>
													<p className="text-xs text-gray-600">
														Analyzing video frames
														every 3 milliseconds
														using Gemini Vision
														API...
													</p>
													{video.transcription_status ===
														"transcribing" && (
														<p className="text-xs text-yellow-400 mt-2 animate-pulse">
															⏳ Frame extraction
															and analysis
															running...
														</p>
													)}
													{video.transcription_status ===
														"transcribed" &&
														!video.visual_transcript && (
															<p className="text-xs text-yellow-400 mt-2">
																⚠ Visual
																analysis may
																still be
																processing.
																Check back in a
																moment or
																reprocess the
																video.
															</p>
														)}
												</div>
											)}

											{/* Show visual transcript segments if available */}
											{video.visual_transcript_segments &&
												Array.isArray(
													video.visual_transcript_segments
												) &&
												video.visual_transcript_segments
													.length > 0 && (
													<div className="space-y-2 mt-4">
														<h5 className="text-xs font-medium text-purple-300">
															Frame-by-Frame
															Analysis
														</h5>
														<div className="p-3 bg-purple-500/5 rounded-lg max-h-64 overflow-y-auto border border-purple-500/20">
															<div className="space-y-2">
																{video.visual_transcript_segments.map(
																	(
																		segment,
																		idx
																	) => (
																		<div
																			key={
																				idx
																			}
																			className="text-xs border-b border-purple-500/10 pb-2 last:border-0">
																			<span className="text-purple-300 font-mono">
																				{segment.timestamp_str ||
																					`${Math.floor(
																						segment.start /
																							60
																					)}:${String(
																						Math.floor(
																							segment.start %
																								60
																						)
																					).padStart(
																						2,
																						"0"
																					)}`}
																			</span>
																			<span className="text-gray-300 ml-2">
																				{segment.text ||
																					segment.description}
																			</span>
																		</div>
																	)
																)}
															</div>
														</div>
													</div>
												)}
										</div>
									</div>

									{/* WHISPER AI TRANSCRIPTION */}
									<div className="space-y-4">
										<div className="bg-green-500/10 rounded-lg p-4 border border-green-500/30">
											<div className="flex items-center justify-between mb-3">
												<h4 className="text-base font-semibold text-green-300 flex items-center gap-2">
													🎯 Whisper AI
												</h4>
												<span
													className={`px-2 py-1 text-xs rounded ${
														video.whisper_transcription_status ===
														"transcribed"
															? "bg-green-500/20 text-green-300"
															: video.whisper_transcription_status ===
															  "transcribing"
															? "bg-yellow-500/20 text-yellow-300"
															: video.whisper_transcription_status ===
															  "failed"
															? "bg-red-500/20 text-red-300"
															: "bg-gray-500/20 text-gray-400"
													}`}>
													{video.whisper_transcription_status ===
													"transcribed"
														? "✓ Complete"
														: video.whisper_transcription_status ===
														  "transcribing"
														? "⏳ Processing"
														: video.whisper_transcription_status ===
														  "failed"
														? "✗ Failed"
														: "Pending"}
												</span>
											</div>

											{video.whisper_transcript ? (
												<>
													<div className="grid grid-cols-2 gap-2 text-xs mb-3">
														<div className="bg-white/5 rounded px-2 py-1">
															<span className="text-gray-400">
																Language:
															</span>
															<span className="text-white ml-1">
																{video.whisper_transcript_language ||
																	"Unknown"}
															</span>
														</div>
														<div className="bg-white/5 rounded px-2 py-1">
															<span className="text-gray-400">
																Length:
															</span>
															<span className="text-white ml-1">
																{video
																	.whisper_transcript_without_timestamps
																	?.length ||
																	video
																		.whisper_transcript
																		?.length ||
																	0}{" "}
																chars
															</span>
														</div>
														<div className="bg-white/5 rounded px-2 py-1">
															<span className="text-gray-400">
																Model:
															</span>
															<span className="text-white ml-1">
																{video.whisper_model_used ||
																	"base"}
															</span>
														</div>
														<div className="bg-white/5 rounded px-2 py-1">
															<span className="text-gray-400">
																Confidence:
															</span>
															<span
																className={`ml-1 ${
																	video.whisper_confidence_avg &&
																	video.whisper_confidence_avg >
																		-1.0
																		? "text-green-300"
																		: video.whisper_confidence_avg &&
																		  video.whisper_confidence_avg >
																				-2.0
																		? "text-yellow-300"
																		: "text-red-300"
																}`}>
																{video.whisper_confidence_avg
																	? video.whisper_confidence_avg >
																	  -1.0
																		? "High"
																		: video.whisper_confidence_avg >
																		  -2.0
																		? "Medium"
																		: "Low"
																	: "N/A"}
															</span>
														</div>
													</div>

													{/* With Timestamps */}
													<div className="space-y-2 mb-3">
														<div className="flex items-center justify-between">
															<h5 className="text-xs font-medium text-gray-300">
																With Timestamps
															</h5>
															<Button
																size="sm"
																variant="ghost"
																icon={Copy}
																onClick={() =>
																	copyToClipboard(
																		video.whisper_transcript
																	)
																}
																className="text-xs">
																Copy
															</Button>
														</div>
														<div className="p-3 bg-white/5 rounded-lg max-h-96 overflow-y-auto border border-white/10">
															<p className="text-xs whitespace-pre-wrap leading-relaxed font-mono text-gray-300">
																{
																	video.whisper_transcript
																}
															</p>
														</div>
													</div>

													{/* Plain Text */}
													<div className="space-y-2">
														<div className="flex items-center justify-between">
															<h5 className="text-xs font-medium text-gray-300">
																Plain Text
															</h5>
															<Button
																size="sm"
																variant="ghost"
																icon={Copy}
																onClick={() =>
																	copyToClipboard(
																		video.whisper_transcript_without_timestamps ||
																			video.whisper_transcript
																	)
																}
																className="text-xs">
																Copy
															</Button>
														</div>
														<div className="p-3 bg-green-500/5 rounded-lg max-h-96 overflow-y-auto border border-green-500/20">
															<p className="text-xs whitespace-pre-wrap leading-relaxed text-gray-300">
																{video.whisper_transcript_without_timestamps ||
																	video.whisper_transcript}
															</p>
														</div>
													</div>
												</>
											) : (
												<div className="text-center py-8 text-gray-500">
													<p className="text-sm">
														No Whisper transcription
														available
													</p>
													{video.whisper_transcription_status ===
														"not_transcribed" && (
														<p className="text-xs mt-2">
															Run dual
															transcription to
															generate
														</p>
													)}
												</div>
											)}
										</div>
									</div>
								</div>
							) : (
								<div className="text-center py-12 text-gray-400">
									<FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
									<p className="mb-2">
										No transcriptions available
									</p>
									{video.transcription_status ===
										"not_transcribed" && (
										<Button
											size="sm"
											variant="primary"
											className="mt-4"
											onClick={() =>
												transcribeMutation.mutate()
											}
											loading={
												transcribeMutation.isPending
											}>
											Start Triple Transcription + AI
											Enhancement
										</Button>
									)}
								</div>
							)}

							{/* Hindi Translations Comparison - Full Width */}
							{(video.transcript_hindi ||
								video.whisper_transcript_hindi ||
								video.visual_transcript_hindi ||
								video.enhanced_transcript_hindi) && (
								<div className="space-y-4 w-full">
									<h4 className="text-base font-semibold text-purple-300 flex items-center gap-2">
										<Globe className="w-5 h-5" />
										🌍 Hindi Translations Comparison
									</h4>

									<div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 w-full">
										{/* NCA Hindi */}
										<div className="space-y-2">
											<div className="flex items-center justify-between">
												<h5 className="text-sm font-medium text-blue-300">
													NCA Hindi Translation
												</h5>
												{video.transcript_hindi && (
													<Button
														size="sm"
														variant="ghost"
														icon={Copy}
														onClick={() =>
															copyToClipboard(
																video.transcript_hindi
															)
														}
														className="text-xs">
														Copy
													</Button>
												)}
											</div>
											{video.transcript_hindi ? (
												<div className="p-4 bg-blue-500/5 rounded-lg max-h-96 overflow-y-auto border border-blue-500/20">
													<p className="text-sm whitespace-pre-wrap leading-relaxed text-gray-300">
														{video.transcript_hindi}
													</p>
												</div>
											) : (
												<div className="p-4 bg-white/5 rounded-lg text-center text-gray-500 text-sm">
													No NCA Hindi translation
												</div>
											)}
										</div>

										{/* Whisper Hindi */}
										<div className="space-y-2">
											<div className="flex items-center justify-between">
												<h5 className="text-sm font-medium text-green-300">
													Whisper Hindi Translation
												</h5>
												{video.whisper_transcript_hindi && (
													<Button
														size="sm"
														variant="ghost"
														icon={Copy}
														onClick={() =>
															copyToClipboard(
																video.whisper_transcript_hindi
															)
														}
														className="text-xs">
														Copy
													</Button>
												)}
											</div>
											{video.whisper_transcript_hindi ? (
												<div className="p-4 bg-green-500/5 rounded-lg max-h-96 overflow-y-auto border border-green-500/20">
													<p className="text-sm whitespace-pre-wrap leading-relaxed text-gray-300">
														{
															video.whisper_transcript_hindi
														}
													</p>
												</div>
											) : (
												<div className="p-4 bg-white/5 rounded-lg text-center text-gray-500 text-sm">
													No Whisper Hindi translation
												</div>
											)}
										</div>

										{/* Visual Hindi - Always Show */}
										<div className="space-y-2">
											<div className="flex items-center justify-between">
												<h5 className="text-sm font-medium text-purple-300 flex items-center gap-2">
													👁️ Visual Hindi Translation
												</h5>
												{video.visual_transcript_hindi && (
													<Button
														size="sm"
														variant="ghost"
														icon={Copy}
														onClick={() =>
															copyToClipboard(
																video.visual_transcript_hindi
															)
														}
														className="text-xs">
														Copy
													</Button>
												)}
											</div>
											{video.visual_transcript_hindi ? (
												<div className="p-4 bg-purple-500/5 rounded-lg max-h-96 overflow-y-auto border border-purple-500/20">
													<p className="text-sm whitespace-pre-wrap leading-relaxed text-gray-300">
														{
															video.visual_transcript_hindi
														}
													</p>
												</div>
											) : (
												<div className="p-4 bg-white/5 rounded-lg text-center text-gray-500 text-sm">
													{video.visual_transcript
														? "Visual analysis in progress, translation will appear soon..."
														: "No Visual Hindi translation available"}
												</div>
											)}
										</div>

										{/* Enhanced Hindi - Always Show */}
										<div className="space-y-2">
											<div className="flex items-center justify-between">
												<h5 className="text-sm font-medium text-orange-300 flex items-center gap-2">
													⭐ Enhanced Hindi
													Translation
												</h5>
												{video.enhanced_transcript_hindi && (
													<Button
														size="sm"
														variant="ghost"
														icon={Copy}
														onClick={() =>
															copyToClipboard(
																video.enhanced_transcript_hindi
															)
														}
														className="text-xs">
														Copy
													</Button>
												)}
											</div>
											{video.enhanced_transcript_hindi ? (
												<div className="p-4 bg-orange-500/5 rounded-lg max-h-96 overflow-y-auto border border-orange-500/20">
													<p className="text-sm whitespace-pre-wrap leading-relaxed text-gray-300">
														{
															video.enhanced_transcript_hindi
														}
													</p>
												</div>
											) : (
												<div className="p-4 bg-white/5 rounded-lg text-center text-gray-500 text-sm">
													{video.enhanced_transcript
														? "Enhanced transcript in progress, translation will appear soon..."
														: "No Enhanced Hindi translation available"}
												</div>
											)}
										</div>
									</div>
								</div>
							)}

							{/* Additional Information Section */}
							<div className="mt-6 bg-gradient-to-r from-blue-500/5 via-purple-500/5 to-green-500/5 rounded-lg p-4 border border-white/10">
								<h4 className="text-sm font-semibold text-gray-300 mb-3">
									📋 Transcription Sources Summary
								</h4>
								<div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
									<div className="bg-blue-500/10 rounded p-3 border border-blue-500/20">
										<div className="font-semibold text-blue-300 mb-1">
											NCA Toolkit
										</div>
										<div className="text-gray-400">
											Status:{" "}
											{video.transcription_status ===
											"transcribed"
												? "✓ Complete"
												: video.transcription_status ===
												  "transcribing"
												? "⏳ Processing"
												: "Pending"}
										</div>
										{video.transcript_language && (
											<div className="text-gray-400">
												Language:{" "}
												{video.transcript_language}
											</div>
										)}
										{video.transcript_without_timestamps && (
											<div className="text-gray-400">
												Length:{" "}
												{
													video
														.transcript_without_timestamps
														.length
												}{" "}
												chars
											</div>
										)}
									</div>

									<div className="bg-purple-500/10 rounded p-3 border border-purple-500/20">
										<div className="font-semibold text-purple-300 mb-1">
											Visual Analysis
										</div>
										<div className="text-gray-400">
											Status:{" "}
											{video.visual_transcript
												? "✓ Complete"
												: "⏳ Processing"}
										</div>
										<div className="text-gray-400">
											Method: Frame extraction (every 3ms)
										</div>
										{video.visual_transcript_without_timestamps && (
											<div className="text-gray-400">
												Length:{" "}
												{
													video
														.visual_transcript_without_timestamps
														.length
												}{" "}
												chars
											</div>
										)}
										{video.visual_transcript_segments &&
											Array.isArray(
												video.visual_transcript_segments
											) && (
												<div className="text-gray-400">
													Frames:{" "}
													{
														video
															.visual_transcript_segments
															.length
													}{" "}
													analyzed
												</div>
											)}
									</div>

									<div className="bg-green-500/10 rounded p-3 border border-green-500/20">
										<div className="font-semibold text-green-300 mb-1">
											Whisper AI
										</div>
										<div className="text-gray-400">
											Status:{" "}
											{video.whisper_transcription_status ===
											"transcribed"
												? "✓ Complete"
												: video.whisper_transcription_status ===
												  "transcribing"
												? "⏳ Processing"
												: "Pending"}
										</div>
										{video.whisper_transcript_language && (
											<div className="text-gray-400">
												Language:{" "}
												{
													video.whisper_transcript_language
												}
											</div>
										)}
										{video.whisper_model_used && (
											<div className="text-gray-400">
												Model:{" "}
												{video.whisper_model_used}
											</div>
										)}
										{video.whisper_transcript_without_timestamps && (
											<div className="text-gray-400">
												Length:{" "}
												{
													video
														.whisper_transcript_without_timestamps
														.length
												}{" "}
												chars
											</div>
										)}
									</div>
								</div>

								{video.enhanced_transcript && (
									<div className="mt-4 bg-orange-500/10 rounded p-3 border border-orange-500/20">
										<div className="font-semibold text-orange-300 mb-1">
											⭐ AI-Enhanced Transcript
										</div>
										<div className="text-gray-400">
											Status: ✓ Complete (Merged from all
											three sources)
										</div>
										{video.enhanced_transcript_without_timestamps && (
											<div className="text-gray-400">
												Length:{" "}
												{
													video
														.enhanced_transcript_without_timestamps
														.length
												}{" "}
												chars
											</div>
										)}
										<div className="text-gray-400 text-xs mt-1">
											This is the final, AI-enhanced
											transcript combining the best parts
											from all sources.
										</div>
									</div>
								)}
							</div>
						</div>
					)}

					{activeTab === "script" && (
						<div className="space-y-4">
							{video.hindi_script ? (
								<>
									<div className="mb-4">
										<h4 className="text-sm font-medium text-gray-400 mb-1">
											Hindi Script for TTS
										</h4>
										{video.script_generated_at && (
											<p className="text-xs text-gray-500">
												Generated:{" "}
												{formatDate(
													video.script_generated_at
												)}
											</p>
										)}
										{video.duration && (
											<p className="text-xs text-gray-500">
												Video Duration:{" "}
												{formatDuration(video.duration)}
											</p>
										)}
										{video.tts_speed && (
											<p className="text-xs text-gray-500">
												TTS Parameters: Speed{" "}
												{video.tts_speed}x | Temperature{" "}
												{video.tts_temperature} |
												Repetition Penalty{" "}
												{video.tts_repetition_penalty}
											</p>
										)}
									</div>

									<div className="grid md:grid-cols-2 gap-4">
										<div className="space-y-2">
											<div className="flex items-center justify-between">
												<h4 className="text-sm font-medium text-gray-300">
													Script with Timestamps
												</h4>
												<Button
													size="sm"
													variant="ghost"
													icon={Copy}
													onClick={() =>
														copyToClipboard(
															video.hindi_script
														)
													}>
													Copy
												</Button>
											</div>
											<div className="p-4 bg-white/5 rounded-lg max-h-96 overflow-y-auto border border-white/10">
												<p className="text-sm whitespace-pre-wrap leading-relaxed font-mono">
													{video.hindi_script}
												</p>
											</div>
										</div>

										<div className="space-y-2">
											<div className="flex items-center justify-between">
												<h4 className="text-sm font-medium text-green-300">
													Clean Script (for TTS)
												</h4>
												<Button
													size="sm"
													variant="ghost"
													icon={Copy}
													onClick={() =>
														copyToClipboard(
															video.clean_script_for_tts ||
																video.hindi_script
														)
													}>
													Copy
												</Button>
											</div>
											<div className="p-4 bg-green-500/5 rounded-lg max-h-96 overflow-y-auto border border-green-500/20">
												<p className="text-sm whitespace-pre-wrap leading-relaxed">
													{video.clean_script_for_tts ||
														video.hindi_script}
												</p>
											</div>
										</div>
									</div>
								</>
							) : video.script_status === "generating" ? (
								<div className="text-center py-8 text-gray-400">
									<FileText className="w-12 h-12 mx-auto mb-3 opacity-50 animate-pulse" />
									<p>Generating Hindi script...</p>
									<p className="text-xs mt-2">
										This may take a few moments
									</p>
								</div>
							) : video.script_status === "failed" ? (
								<div className="text-center py-8 text-red-400">
									<FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
									<p>Script generation failed</p>
									{video.script_error_message && (
										<p className="text-xs mt-2 text-gray-400">
											{video.script_error_message}
										</p>
									)}
								</div>
							) : (
								<div className="text-center py-8 text-gray-400">
									<FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
									<p>No script available</p>
									<p className="text-xs mt-2">
										Script will be automatically generated
										after video download
									</p>
								</div>
							)}
						</div>
					)}

					{activeTab === "ai" && (
						<div className="space-y-4">
							{video.ai_summary ? (
								<>
									<div>
										<h4 className="text-sm font-medium text-gray-400 mb-2">
											Summary
										</h4>
										<div className="p-4 bg-white/5 rounded-lg">
											<p className="text-sm">
												{video.ai_summary}
											</p>
										</div>
									</div>
									{video.ai_tags && (
										<div>
											<h4 className="text-sm font-medium text-gray-400 mb-2">
												Tags
											</h4>
											<div className="flex flex-wrap gap-2">
												{video.ai_tags
													.split(",")
													.map((tag, i) => (
														<span
															key={i}
															className="px-2 py-1 text-xs bg-white/10 rounded">
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
									{video.ai_processing_status ===
										"not_processed" && (
										<Button
											size="sm"
											variant="primary"
											className="mt-4"
											onClick={() =>
												processAIMutation.mutate()
											}
											loading={
												processAIMutation.isPending
											}>
											Process with AI
										</Button>
									)}
								</div>
							)}
						</div>
					)}
				</div>
			</div>

			{/* Script Editor Modal */}
			{isEditingScript && (
				<div className="script-editor-overlay">
					<div className="script-editor-modal">
						<div className="script-editor-header">
							<h2>📝 Review & Edit Hindi Script</h2>
							<p className="script-editor-subtitle">
								Review the generated script and make any changes
								to improve the narration tone before TTS
								synthesis.
							</p>
						</div>

						<div className="script-editor-body">
							<div className="mb-4">
								<details className="group bg-white/5 border border-white/10 rounded-lg overflow-hidden">
									<summary className="flex items-center justify-between p-3 cursor-pointer hover:bg-white/10 transition-colors">
										<span className="font-medium flex items-center gap-2 text-sm">
											<Brain size={16} className="text-yellow-400" />
											Gemini TTS Prompting Tips & Markup Guide
										</span>
										<span className="text-xs text-white/50 group-open:rotate-180 transition-transform">▼</span>
									</summary>
									<div className="p-4 text-sm text-gray-300 space-y-4 bg-black/20 max-h-60 overflow-y-auto custom-scrollbar">
										<div>
											<h4 className="font-semibold text-white mb-1">The Three Levers of Speech Control</h4>
											<p className="text-xs opacity-80">Ensure Style Prompt, Text Content, and Markup Tags are consistent for best results.</p>
										</div>
										
										<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
											<div>
												<h4 className="font-semibold text-white mb-2">Mode 1: Non-speech sounds</h4>
												<ul className="list-disc pl-4 space-y-1 text-xs">
													<li><code className="bg-white/10 px-1 rounded">[sigh]</code> - Disappointment, relief</li>
													<li><code className="bg-white/10 px-1 rounded">[laughing]</code> - Humor, amusement</li>
													<li><code className="bg-white/10 px-1 rounded">[uhm]</code> - Hesitation</li>
												</ul>
											</div>
											<div>
												<h4 className="font-semibold text-white mb-2">Mode 2: Style modifiers</h4>
												<ul className="list-disc pl-4 space-y-1 text-xs">
													<li><code className="bg-white/10 px-1 rounded">[sarcasm]</code> - Sarcastic tone</li>
													<li><code className="bg-white/10 px-1 rounded">[whispering]</code> - Quiet delivery</li>
													<li><code className="bg-white/10 px-1 rounded">[shouting]</code> - Loud delivery</li>
													<li><code className="bg-white/10 px-1 rounded">[extremely fast]</code> - Rushed speech</li>
												</ul>
											</div>
										</div>

										<div>
											<h4 className="font-semibold text-white mb-2">Mode 4: Pacing and pauses</h4>
											<div className="grid grid-cols-3 gap-2 text-xs text-center">
												<div className="bg-white/5 p-2 rounded"><code className="block mb-1">[short pause]</code>~250ms (comma)</div>
												<div className="bg-white/5 p-2 rounded"><code className="block mb-1">[medium pause]</code>~500ms (sentence)</div>
												<div className="bg-white/5 p-2 rounded"><code className="block mb-1">[long pause]</code>~1000ms+ (drama)</div>
											</div>
										</div>
										
										<div className="bg-yellow-500/10 border border-yellow-500/20 p-3 rounded text-xs">
											<strong>Key Strategy:</strong> Use emotionally rich text. Don't rely on tags alone. "I think someone is in the house" works better for [scared] than neutral text.
										</div>
									</div>
								</details>
							</div>

							<textarea
								className="script-editor-textarea"
								value={editedScript}
								onChange={(e) =>
									setEditedScript(e.target.value)
								}
								placeholder="Enter Hindi script here..."
								rows={15}
							/>

							<div className="script-editor-stats">
								<div className="stat-item">
									<span className="stat-label">Words:</span>
									<span className="stat-value">
										{editedScript
											? editedScript
													.split(/\s+/)
													.filter((w) => w.length > 0)
													.length
											: 0}
									</span>
								</div>
								<div className="stat-item">
									<span className="stat-label">
										Estimated Speech:
									</span>
									<span className="stat-value">
										{estimateSpeechDuration(editedScript)}s
									</span>
								</div>
								<div className="stat-item">
									<span className="stat-label">
										Video Duration:
									</span>
									<span className="stat-value">
										{video?.duration || 0}s
									</span>
								</div>
								<div className="stat-item">
									<span className="stat-label">
										TTS Speed:
									</span>
									<span
										className={`stat-value ${
											estimateSpeechDuration(
												editedScript
											) > (video?.duration || 0)
												? "stat-warning"
												: "stat-success"
										}`}>
										{estimateSpeechDuration(editedScript) >
										(video?.duration || 0)
											? `~${Math.min(
													1.5,
													estimateSpeechDuration(
														editedScript
													) /
														((video?.duration ||
															1) *
															0.95)
											  ).toFixed(2)}x`
											: "1.0x"}
									</span>
								</div>
							</div>

							{estimateSpeechDuration(editedScript) >
								(video?.duration || 0) * 1.3 && (
								<div className="script-editor-warning">
									⚠️ <strong>Warning:</strong> Script is
									significantly longer than video duration.
									Consider shortening it for better audio
									quality (max recommended speed is 1.5x).
								</div>
							)}
						</div>

						<div className="script-editor-footer">
							<button
								className="script-editor-btn script-editor-btn-secondary"
								onClick={() => {
									setEditedScript(video?.hindi_script || "");
									showInfo(
										"Script Reset",
										"Script reset to original generated version."
									);
								}}
								disabled={updateScriptMutation.isPending}>
								Reset to Original
							</button>
							<div className="script-editor-actions">
								<button
									className="script-editor-btn script-editor-btn-cancel"
									onClick={() => {
										setIsEditingScript(false);
										setScriptEditorDismissed(true); // Mark as dismissed so it won't auto-show again
									}}
									disabled={updateScriptMutation.isPending}>
									Cancel
								</button>
								<button
									className="script-editor-btn script-editor-btn-primary"
									onClick={handleSaveScript}
									disabled={
										updateScriptMutation.isPending ||
										!editedScript?.trim()
									}>
									{updateScriptMutation.isPending
										? "💾 Saving..."
										: "💾 Save & Continue to TTS"}
								</button>
							</div>
						</div>
					</div>
				</div>
			)}
		</div>
	);
}

export default VideoDetail;
