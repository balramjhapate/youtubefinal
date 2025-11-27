              {activeTab === 'transcript' && (
                <div className="space-y-6">
                  {/* Comparison Header */}
                  {(video.transcript || video.whisper_transcript) && (
                    <div className="bg-gradient-to-r from-blue-500/10 via-purple-500/10 to-green-500/10 rounded-lg p-4 border border-white/10">
                      <h3 className="text-lg font-semibold text-white mb-2">📊 Transcription Comparison</h3>
                      <p className="text-sm text-gray-400">
                        Compare NCA Toolkit and Whisper AI transcriptions side-by-side to evaluate accuracy and quality.
                      </p>
                    </div>
                  )}

                  {/* Dual Transcription Comparison */}
                  {(video.transcript || video.whisper_transcript) ? (
                    <div className="grid lg:grid-cols-2 gap-6">
                      {/* NCA TOOLKIT TRANSCRIPTION */}
                      <div className="space-y-4">
                        <div className="bg-blue-500/10 rounded-lg p-4 border border-blue-500/30">
                          <div className="flex items-center justify-between mb-3">
                            <h4 className="text-base font-semibold text-blue-300 flex items-center gap-2">
                              🔷 NCA Toolkit
                            </h4>
                            <span className={`px-2 py-1 text-xs rounded ${
                              video.transcription_status === 'transcribed' ? 'bg-green-500/20 text-green-300' :
                              video.transcription_status === 'transcribing' ? 'bg-yellow-500/20 text-yellow-300' :
                              video.transcription_status === 'failed' ? 'bg-red-500/20 text-red-300' :
                              'bg-gray-500/20 text-gray-400'
                            }`}>
                              {video.transcription_status === 'transcribed' ? '✓ Complete' :
                               video.transcription_status === 'transcribing' ? '⏳ Processing' :
                               video.transcription_status === 'failed' ? '✗ Failed' : 'Pending'}
                            </span>
                          </div>
                          
                          {video.transcript ? (
                            <>
                              <div className="grid grid-cols-2 gap-2 text-xs mb-3">
                                <div className="bg-white/5 rounded px-2 py-1">
                                  <span className="text-gray-400">Language:</span>
                                  <span className="text-white ml-1">{video.transcript_language || 'Unknown'}</span>
                                </div>
                                <div className="bg-white/5 rounded px-2 py-1">
                                  <span className="text-gray-400">Length:</span>
                                  <span className="text-white ml-1">{video.transcript_without_timestamps?.length || video.transcript?.length || 0} chars</span>
                                </div>
                              </div>

                              {/* With Timestamps */}
                              <div className="space-y-2 mb-3">
                                <div className="flex items-center justify-between">
                                  <h5 className="text-xs font-medium text-gray-300">With Timestamps</h5>
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    icon={Copy}
                                    onClick={() => copyToClipboard(video.transcript)}
                                    className="text-xs"
                                  >
                                    Copy
                                  </Button>
                                </div>
                                <div className="p-3 bg-white/5 rounded-lg max-h-64 overflow-y-auto border border-white/10">
                                  <p className="text-xs whitespace-pre-wrap leading-relaxed font-mono text-gray-300">
                                    {video.transcript}
                                  </p>
                                </div>
                              </div>

                              {/* Plain Text */}
                              <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                  <h5 className="text-xs font-medium text-gray-300">Plain Text</h5>
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    icon={Copy}
                                    onClick={() => copyToClipboard(video.transcript_without_timestamps || video.transcript)}
                                    className="text-xs"
                                  >
                                    Copy
                                  </Button>
                                </div>
                                <div className="p-3 bg-blue-500/5 rounded-lg max-h-64 overflow-y-auto border border-blue-500/20">
                                  <p className="text-xs whitespace-pre-wrap leading-relaxed text-gray-300">
                                    {video.transcript_without_timestamps || video.transcript}
                                  </p>
                                </div>
                              </div>
                            </>
                          ) : (
                            <div className="text-center py-8 text-gray-500">
                              <p className="text-sm">No NCA transcription available</p>
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
                            <span className={`px-2 py-1 text-xs rounded ${
                              video.whisper_transcription_status === 'transcribed' ? 'bg-green-500/20 text-green-300' :
                              video.whisper_transcription_status === 'transcribing' ? 'bg-yellow-500/20 text-yellow-300' :
                              video.whisper_transcription_status === 'failed' ? 'bg-red-500/20 text-red-300' :
                              'bg-gray-500/20 text-gray-400'
                            }`}>
                              {video.whisper_transcription_status === 'transcribed' ? '✓ Complete' :
                               video.whisper_transcription_status === 'transcribing' ? '⏳ Processing' :
                               video.whisper_transcription_status === 'failed' ? '✗ Failed' : 'Pending'}
                            </span>
                          </div>
                          
                          {video.whisper_transcript ? (
                            <>
                              <div className="grid grid-cols-2 gap-2 text-xs mb-3">
                                <div className="bg-white/5 rounded px-2 py-1">
                                  <span className="text-gray-400">Language:</span>
                                  <span className="text-white ml-1">{video.whisper_transcript_language || 'Unknown'}</span>
                                </div>
                                <div className="bg-white/5 rounded px-2 py-1">
                                  <span className="text-gray-400">Length:</span>
                                  <span className="text-white ml-1">{video.whisper_transcript_without_timestamps?.length || video.whisper_transcript?.length || 0} chars</span>
                                </div>
                                <div className="bg-white/5 rounded px-2 py-1">
                                  <span className="text-gray-400">Model:</span>
                                  <span className="text-white ml-1">{video.whisper_model_used || 'base'}</span>
                                </div>
                                <div className="bg-white/5 rounded px-2 py-1">
                                  <span className="text-gray-400">Confidence:</span>
                                  <span className={`ml-1 ${
                                    video.whisper_confidence_avg && video.whisper_confidence_avg > -1.0 ? 'text-green-300' :
                                    video.whisper_confidence_avg && video.whisper_confidence_avg > -2.0 ? 'text-yellow-300' :
                                    'text-red-300'
                                  }`}>
                                    {video.whisper_confidence_avg ? 
                                      (video.whisper_confidence_avg > -1.0 ? 'High' :
                                       video.whisper_confidence_avg > -2.0 ? 'Medium' : 'Low') : 
                                      'N/A'}
                                  </span>
                                </div>
                              </div>

                              {/* With Timestamps */}
                              <div className="space-y-2 mb-3">
                                <div className="flex items-center justify-between">
                                  <h5 className="text-xs font-medium text-gray-300">With Timestamps</h5>
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    icon={Copy}
                                    onClick={() => copyToClipboard(video.whisper_transcript)}
                                    className="text-xs"
                                  >
                                    Copy
                                  </Button>
                                </div>
                                <div className="p-3 bg-white/5 rounded-lg max-h-64 overflow-y-auto border border-white/10">
                                  <p className="text-xs whitespace-pre-wrap leading-relaxed font-mono text-gray-300">
                                    {video.whisper_transcript}
                                  </p>
                                </div>
                              </div>

                              {/* Plain Text */}
                              <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                  <h5 className="text-xs font-medium text-gray-300">Plain Text</h5>
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    icon={Copy}
                                    onClick={() => copyToClipboard(video.whisper_transcript_without_timestamps || video.whisper_transcript)}
                                    className="text-xs"
                                  >
                                    Copy
                                  </Button>
                                </div>
                                <div className="p-3 bg-green-500/5 rounded-lg max-h-64 overflow-y-auto border border-green-500/20">
                                  <p className="text-xs whitespace-pre-wrap leading-relaxed text-gray-300">
                                    {video.whisper_transcript_without_timestamps || video.whisper_transcript}
                                  </p>
                                </div>
                              </div>
                            </>
                          ) : (
                            <div className="text-center py-8 text-gray-500">
                              <p className="text-sm">No Whisper transcription available</p>
                              {video.whisper_transcription_status === 'not_transcribed' && (
                                <p className="text-xs mt-2">Run dual transcription to generate</p>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-12 text-gray-400">
                      <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                      <p className="mb-2">No transcriptions available</p>
                      {video.transcription_status === 'not_transcribed' && (
                        <Button
                          size="sm"
                          variant="primary"
                          className="mt-4"
                          onClick={() => transcribeMutation.mutate()}
                          loading={transcribeMutation.isPending}
                        >
                          Start Dual Transcription
                        </Button>
                      )}
                    </div>
                  )}

                  {/* Hindi Translations Comparison */}
                  {(video.transcript_hindi || video.whisper_transcript_hindi) && (
                    <div className="space-y-4">
                      <h4 className="text-base font-semibold text-purple-300 flex items-center gap-2">
                        <Globe className="w-5 h-5" />
                        🌍 Hindi Translations Comparison
                      </h4>
                      
                      <div className="grid lg:grid-cols-2 gap-6">
                        {/* NCA Hindi */}
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <h5 className="text-sm font-medium text-blue-300">NCA Hindi Translation</h5>
                            {video.transcript_hindi && (
                              <Button
                                size="sm"
                                variant="ghost"
                                icon={Copy}
                                onClick={() => copyToClipboard(video.transcript_hindi)}
                                className="text-xs"
                              >
                                Copy
                              </Button>
                            )}
                          </div>
                          {video.transcript_hindi ? (
                            <div className="p-4 bg-blue-500/5 rounded-lg max-h-64 overflow-y-auto border border-blue-500/20">
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
                            <h5 className="text-sm font-medium text-green-300">Whisper Hindi Translation</h5>
                            {video.whisper_transcript_hindi && (
                              <Button
                                size="sm"
                                variant="ghost"
                                icon={Copy}
                                onClick={() => copyToClipboard(video.whisper_transcript_hindi)}
                                className="text-xs"
                              >
                                Copy
                              </Button>
                            )}
                          </div>
                          {video.whisper_transcript_hindi ? (
                            <div className="p-4 bg-green-500/5 rounded-lg max-h-64 overflow-y-auto border border-green-500/20">
                              <p className="text-sm whitespace-pre-wrap leading-relaxed text-gray-300">
                                {video.whisper_transcript_hindi}
                              </p>
                            </div>
                          ) : (
                            <div className="p-4 bg-white/5 rounded-lg text-center text-gray-500 text-sm">
                              No Whisper Hindi translation
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
