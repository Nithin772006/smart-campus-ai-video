import React, { useState } from 'react';
import {
  generateNarrationFromPlan,
  getAudioUrl,
  transcribeAudio,
  getSubtitleUrl,
  composeVideo,
  getVideoUrl,
} from '../api';

export default function GenerationDetails({ result, targetDuration = 30, onFinalVideoComposed }) {
  if (!result) return null;

  const {
    topic,
    duration_seconds,
    generation_time_seconds,
    scene_count,
    output_size_mb,
    planner,
    used_fallback,
    plan,
  } = result;

  const isFallback = Boolean(used_fallback);
  const plannerLabel = isFallback ? 'Rule-Based Fallback' : 'Qwen2.5 3B (Local)';

  // TTS State
  const [ttsLoading, setTtsLoading] = useState(false);
  const [ttsError, setTtsError] = useState(null);
  const [audioResult, setAudioResult] = useState(null);

  // Subtitle / Whisper State
  const [subLoading, setSubLoading] = useState(false);
  const [subError, setSubError] = useState(null);
  const [subResult, setSubResult] = useState(null);

  // FFmpeg Composition State
  const [composeLoading, setComposeLoading] = useState(false);
  const [composeError, setComposeError] = useState(null);
  const [composedResult, setComposedResult] = useState(null);

  const handleGenerateNarration = async () => {
    if (!plan) return;
    setTtsLoading(true);
    setTtsError(null);

    try {
      const data = await generateNarrationFromPlan(plan, targetDuration);
      setAudioResult(data);
    } catch (err) {
      setTtsError(err.message || 'Failed to synthesize narration.');
    } finally {
      setTtsLoading(false);
    }
  };

  const handleGenerateSubtitles = async () => {
    if (!audioResult?.audio_path) return;
    setSubLoading(true);
    setSubError(null);

    try {
      const data = await transcribeAudio(audioResult.audio_path);
      setSubResult(data);
    } catch (err) {
      setSubError(err.message || 'Failed to transcribe audio with faster-whisper.');
    } finally {
      setSubLoading(false);
    }
  };

  const handleCreateFinalVideo = async () => {
    if (!result?.video_path || !audioResult?.audio_path) return;
    setComposeLoading(true);
    setComposeError(null);

    try {
      const subPath = subResult ? subResult.subtitle_srt_path : null;
      const data = await composeVideo(
        result.video_path,
        audioResult.audio_path,
        subPath,
        Boolean(subPath)
      );
      setComposedResult(data);
      if (onFinalVideoComposed && data.video_path) {
        onFinalVideoComposed(getVideoUrl(data.video_path));
      }
    } catch (err) {
      setComposeError(err.message || 'Failed to compose final video with FFmpeg.');
    } finally {
      setComposeLoading(false);
    }
  };

  return (
    <div className="details-card">
      <div className="details-header">
        <h3 className="details-title">Generation Details</h3>
        <span className={`badge ${isFallback ? 'badge-amber' : 'badge-green'}`}>
          {isFallback ? 'Rule-based fallback was used' : 'Generated using local Qwen2.5 3B'}
        </span>
      </div>

      <div className="metrics-grid">
        <div className="metric-item">
          <div className="metric-label">Topic</div>
          <div className="metric-value" style={{ fontSize: '1rem' }}>{topic}</div>
        </div>

        <div className="metric-item">
          <div className="metric-label">Duration</div>
          <div className="metric-value">
            {typeof duration_seconds === 'number' ? `${duration_seconds.toFixed(1)}s` : 'N/A'}
          </div>
        </div>

        {result?.audio_duration_seconds !== undefined && (
          <div className="metric-item">
            <div className="metric-label">Audio Duration</div>
            <div className="metric-value" style={{ color: '#38bdf8' }}>
              {result.audio_duration_seconds.toFixed(1)}s
            </div>
          </div>
        )}

        {(result?.subtitles_burned !== undefined || composedResult?.subtitles_burned !== undefined) && (
          <div className="metric-item">
            <div className="metric-label">Subtitle Status</div>
            <div className="metric-value" style={{ color: '#34d399', fontSize: '0.95rem' }}>
              {(result?.subtitles_burned ?? composedResult?.subtitles_burned) ? '✓ Burned' : 'Not Burned'}
            </div>
          </div>
        )}

        {result?.character_enabled && (
          <div className="metric-item">
            <div className="metric-label">AI Teacher</div>
            <div className="metric-value" style={{ color: '#818cf8', fontSize: '0.95rem' }}>
              ✓ Presenter ({result.character_position || 'Right'})
            </div>
          </div>
        )}


        <div className="metric-item">
          <div className="metric-label">Speech Rate</div>
          <div className="metric-value" style={{ color: '#fbbf24' }}>
            {result?.speech_rate_wpm ? `${result.speech_rate_wpm} WPM` : audioResult?.actual_wpm ? `${audioResult.actual_wpm} WPM` : '~160 WPM'}
          </div>
        </div>

        <div className="metric-item">
          <div className="metric-label">Scenes</div>
          <div className="metric-value">{scene_count || plan?.scenes?.length || 'N/A'}</div>
        </div>

        <div className="metric-item">
          <div className="metric-label">Generation Time</div>
          <div className="metric-value">
            {typeof generation_time_seconds === 'number' ? `${generation_time_seconds.toFixed(2)}s` : 'N/A'}
          </div>
        </div>

        <div className="metric-item">
          <div className="metric-label">AI Planner</div>
          <div className="metric-value" style={{ fontSize: '0.95rem' }}>{plannerLabel}</div>
        </div>

        <div className="metric-item">
          <div className="metric-label">Voice Provider</div>
          <div className="metric-value" style={{
            color: (result?.voice_provider === 'elevenlabs' || result?.audio_provider === 'elevenlabs') ? '#38bdf8' : '#34d399',
            fontSize: '0.95rem'
          }}>
            {(result?.voice_provider === 'elevenlabs' || result?.audio_provider === 'elevenlabs') ? 'ElevenLabs' : 'IndicF5 Local'}
          </div>
        </div>

        <div className="metric-item">
          <div className="metric-label">Spoken Language</div>
          <div className="metric-value" style={{
            color: result?.localization_fallback ? '#f59e0b' : '#a7f3d0',
            fontSize: '0.95rem'
          }}>
            {result?.actual_language === 'ta' ? 'Tamil' : result?.actual_language === 'hi' ? 'Hindi' : 'English'}
            {result?.localization_fallback && ' (Fallback)'}
          </div>
        </div>
      </div>

      {result?.localization_fallback && (
        <div className="fallback-banner" style={{
          margin: '1rem 0',
          padding: '0.85rem 1rem',
          background: 'rgba(245, 158, 11, 0.15)',
          border: '1px solid rgba(245, 158, 11, 0.4)',
          borderRadius: '10px',
          color: '#fde68a',
          fontSize: '0.9rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
        }}>
          <span>⚠️</span>
          <div>
            <strong>Localization Warning: Synthesized in English</strong>
            <div style={{ fontSize: '0.8rem', opacity: 0.9 }}>
              {result.fallback_reason || `Could not produce authentic ${result?.language === 'ta' ? 'Tamil' : 'Hindi'} translation; defaulted to English.`}
            </div>
          </div>
        </div>
      )}

      {result?.fallback_used && !result?.localization_fallback && (
        <div className="fallback-banner" style={{
          margin: '1rem 0',
          padding: '0.85rem 1rem',
          background: 'rgba(239, 68, 68, 0.15)',
          border: '1px solid rgba(239, 68, 68, 0.4)',
          borderRadius: '10px',
          color: '#fca5a5',
          fontSize: '0.9rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
        }}>
          <span>⚠️</span>
          <div>
            <strong>ElevenLabs failed → Using IndicF5 fallback</strong>
            {result.fallback_reason && <div style={{ fontSize: '0.8rem', opacity: 0.9 }}>Reason: {result.fallback_reason}</div>}
          </div>
        </div>
      )}

      {/* TTS Narration Action and Audio Player */}
      {plan && (
        <div className="tts-section" style={{
          marginTop: '1.5rem',
          padding: '1.25rem',
          background: 'rgba(255, 255, 255, 0.03)',
          borderRadius: '12px',
          border: '1px solid rgba(255, 255, 255, 0.08)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
            <div>
              <h4 style={{ margin: '0 0 0.25rem 0', fontSize: '1.05rem', color: '#f1f5f9' }}>
                🎙️ Local IndicF5 Text-to-Speech
              </h4>
              <p style={{ margin: 0, fontSize: '0.85rem', color: '#94a3b8' }}>
                Synthesize spoken educational voiceover for this plan (PLAN → TEXT → INDICF5 → WAV)
              </p>
            </div>
            <button
              id="generate-narration-btn"
              type="button"
              className="btn btn-secondary"
              onClick={handleGenerateNarration}
              disabled={ttsLoading}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.6rem 1.2rem',
                fontSize: '0.9rem',
                cursor: ttsLoading ? 'not-allowed' : 'pointer'
              }}
            >
              {ttsLoading ? (
                <>
                  <span className="spinner-sm" style={{ width: 14, height: 14, border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff', borderRadius: '50%', display: 'inline-block', animation: 'spin 1s linear infinite' }} />
                  Synthesizing Speech...
                </>
              ) : (
                <>🔊 Generate Narration</>
              )}
            </button>
          </div>

          {ttsError && (
            <div style={{ marginTop: '1rem', padding: '0.75rem', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '8px', color: '#fca5a5', fontSize: '0.875rem' }}>
              <strong>Error: </strong> {ttsError}
            </div>
          )}

          {audioResult && (
            <div style={{ marginTop: '1.25rem', padding: '1rem', background: 'rgba(99, 102, 241, 0.07)', borderRadius: '8px', border: '1px solid rgba(99, 102, 241, 0.2)' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                <span style={{ fontWeight: 600, color: '#a5b4fc', fontSize: '0.9rem' }}>
                  ✓ Voiceover Audio Generated ({audioResult.duration_seconds}s)
                </span>
                <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                  Sample Rate: {audioResult.sample_rate}Hz • Synth Time: {audioResult.generation_time_seconds}s
                </span>
              </div>
              <audio
                controls
                src={getAudioUrl(audioResult.audio_path)}
                style={{ width: '100%', borderRadius: '6px', height: '40px' }}
              />
              {audioResult.narration_text && (
                <div style={{ marginTop: '0.75rem' }}>
                  <div style={{ fontSize: '0.78rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#64748b', marginBottom: '0.25rem' }}>
                    Spoken Script
                  </div>
                  <p style={{ margin: 0, fontSize: '0.85rem', color: '#cbd5e1', lineHeight: '1.4', background: 'rgba(0,0,0,0.2)', padding: '0.5rem 0.75rem', borderRadius: '6px' }}>
                    {audioResult.narration_text}
                  </p>
                </div>
              )}

              {/* Subtitle Generation Action */}
              <div style={{ marginTop: '1rem', paddingTop: '0.75rem', borderTop: '1px solid rgba(255, 255, 255, 0.08)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem' }}>
                <div>
                  <div style={{ fontSize: '0.88rem', fontWeight: 600, color: '#e2e8f0' }}>
                    Generate Timestamps & Subtitles
                  </div>
                  <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                    faster-whisper local alignment for SRT, WebVTT, and video synchronization
                  </div>
                </div>
                <button
                  id="generate-subtitles-btn"
                  type="button"
                  className="btn btn-secondary"
                  onClick={handleGenerateSubtitles}
                  disabled={subLoading}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    padding: '0.5rem 1rem',
                    fontSize: '0.85rem',
                    cursor: subLoading ? 'not-allowed' : 'pointer'
                  }}
                >
                  {subLoading ? (
                    <>
                      <span className="spinner-sm" style={{ width: 14, height: 14, border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff', borderRadius: '50%', display: 'inline-block', animation: 'spin 1s linear infinite' }} />
                      Transcribing Audio...
                    </>
                  ) : (
                    <>📝 Generate Subtitles</>
                  )}
                </button>
              </div>

              {subError && (
                <div style={{ marginTop: '0.75rem', padding: '0.6rem', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '6px', color: '#fca5a5', fontSize: '0.825rem' }}>
                  <strong>Error: </strong> {subError}
                </div>
              )}

              {subResult && (
                <div style={{ marginTop: '0.85rem', padding: '0.85rem', background: 'rgba(16, 185, 129, 0.08)', borderRadius: '8px', border: '1px solid rgba(16, 185, 129, 0.25)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.5rem' }}>
                    <span style={{ fontWeight: 600, color: '#6ee7b7', fontSize: '0.88rem' }}>
                      ✓ faster-whisper ({subResult.device}) • {subResult.segment_count} segments ({subResult.generation_time_seconds}s)
                    </span>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                      <a
                        href={getSubtitleUrl(subResult.subtitle_srt_path)}
                        target="_blank"
                        rel="noreferrer"
                        className="badge badge-green"
                        style={{ textDecoration: 'none', padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}
                      >
                        SRT File
                      </a>
                      <a
                        href={getSubtitleUrl(subResult.subtitle_vtt_path)}
                        target="_blank"
                        rel="noreferrer"
                        className="badge badge-green"
                        style={{ textDecoration: 'none', padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}
                      >
                        WebVTT File
                      </a>
                      <a
                        href={getSubtitleUrl(subResult.transcription_path)}
                        target="_blank"
                        rel="noreferrer"
                        className="badge badge-green"
                        style={{ textDecoration: 'none', padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}
                      >
                        JSON Metadata
                      </a>
                    </div>
                  </div>

                  {subResult.segments && subResult.segments.length > 0 && (
                    <div style={{ maxHeight: '180px', overflowY: 'auto', background: 'rgba(0, 0, 0, 0.25)', borderRadius: '6px', padding: '0.5rem', marginTop: '0.5rem' }}>
                      {subResult.segments.map((seg) => (
                        <div key={seg.id} style={{ display: 'flex', gap: '0.75rem', fontSize: '0.8rem', padding: '0.25rem 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                          <span style={{ color: '#10b981', fontFamily: 'monospace', whiteSpace: 'nowrap' }}>
                            [{seg.start.toFixed(2)}s → {seg.end.toFixed(2)}s]
                          </span>
                          <span style={{ color: '#e2e8f0' }}>{seg.text}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Final FFmpeg Video Composition Section */}
              <div style={{ marginTop: '1.25rem', paddingTop: '1rem', borderTop: '1px solid rgba(255, 255, 255, 0.08)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem' }}>
                <div>
                  <div style={{ fontSize: '0.92rem', fontWeight: 600, color: '#f8fafc' }}>
                    🎬 Compose Final Video (FFmpeg)
                  </div>
                  <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                    Combine Manim visuals + IndicF5 voiceover + burned subtitles into a single MP4
                  </div>
                </div>
                <button
                  id="compose-final-video-btn"
                  type="button"
                  className="btn btn-primary"
                  onClick={handleCreateFinalVideo}
                  disabled={composeLoading}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    padding: '0.6rem 1.25rem',
                    fontSize: '0.88rem',
                    cursor: composeLoading ? 'not-allowed' : 'pointer'
                  }}
                >
                  {composeLoading ? (
                    <>
                      <span className="spinner-sm" style={{ width: 14, height: 14, border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff', borderRadius: '50%', display: 'inline-block', animation: 'spin 1s linear infinite' }} />
                      Muxing with FFmpeg...
                    </>
                  ) : (
                    <>🎬 Create Final Video</>
                  )}
                </button>
              </div>

              {composeError && (
                <div style={{ marginTop: '0.75rem', padding: '0.6rem', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '6px', color: '#fca5a5', fontSize: '0.825rem' }}>
                  <strong>Error: </strong> {composeError}
                </div>
              )}

              {composedResult && (
                <div style={{ marginTop: '0.85rem', padding: '1rem', background: 'rgba(59, 130, 246, 0.1)', borderRadius: '8px', border: '1px solid rgba(59, 130, 246, 0.3)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.5rem' }}>
                    <span style={{ fontWeight: 600, color: '#93c5fd', fontSize: '0.9rem' }}>
                      ✓ Final MP4 Ready ({composedResult.video_codec?.toUpperCase()} + {composedResult.audio_codec?.toUpperCase()}) • {composedResult.duration_seconds}s • {composedResult.file_size_mb} MB
                    </span>
                    <a
                      href={getVideoUrl(composedResult.video_path)}
                      target="_blank"
                      rel="noreferrer"
                      className="badge badge-green"
                      style={{ textDecoration: 'none', padding: '0.3rem 0.75rem', fontSize: '0.8rem' }}
                    >
                      Open Final MP4
                    </a>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(110px, 1fr))', gap: '0.5rem', margin: '0.65rem 0' }}>
                    <div style={{ padding: '0.5rem 0.6rem', background: 'rgba(0, 0, 0, 0.25)', borderRadius: '6px', textAlign: 'center' }}>
                      <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Video Duration</div>
                      <div style={{ fontSize: '0.92rem', fontWeight: 600, color: '#f8fafc' }}>
                        {composedResult.video_duration_seconds !== undefined ? `${composedResult.video_duration_seconds}s` : '—'}
                      </div>
                    </div>
                    <div style={{ padding: '0.5rem 0.6rem', background: 'rgba(0, 0, 0, 0.25)', borderRadius: '6px', textAlign: 'center' }}>
                      <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Narration Duration</div>
                      <div style={{ fontSize: '0.92rem', fontWeight: 600, color: '#f8fafc' }}>
                        {composedResult.audio_duration_seconds !== undefined ? `${composedResult.audio_duration_seconds}s` : '—'}
                      </div>
                    </div>
                    <div style={{ padding: '0.5rem 0.6rem', background: 'rgba(0, 0, 0, 0.25)', borderRadius: '6px', textAlign: 'center' }}>
                      <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Final Duration</div>
                      <div style={{ fontSize: '0.92rem', fontWeight: 600, color: '#38bdf8' }}>
                        {composedResult.duration_seconds !== undefined ? `${composedResult.duration_seconds}s` : '—'}
                      </div>
                    </div>
                    <div style={{ padding: '0.5rem 0.6rem', background: 'rgba(0, 0, 0, 0.25)', borderRadius: '6px', textAlign: 'center' }}>
                      <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Sync Difference</div>
                      <div style={{ fontSize: '0.92rem', fontWeight: 600, color: '#34d399' }}>
                        {composedResult.sync_difference !== undefined ? `${composedResult.sync_difference}s` : '0.00s'}
                      </div>
                    </div>
                    <div style={{ padding: '0.5rem 0.6rem', background: 'rgba(0, 0, 0, 0.25)', borderRadius: '6px', textAlign: 'center' }}>
                      <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Speech Rate</div>
                      <div style={{ fontSize: '0.92rem', fontWeight: 600, color: '#fbbf24' }}>
                        {audioResult?.actual_wpm ? `${audioResult.actual_wpm} WPM` : result?.speech_rate_wpm ? `${result.speech_rate_wpm} WPM` : '156 WPM'}
                      </div>
                    </div>
                    <div style={{ padding: '0.5rem 0.6rem', background: 'rgba(0, 0, 0, 0.25)', borderRadius: '6px', textAlign: 'center' }}>
                      <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Audio Speed</div>
                      <div style={{ fontSize: '0.92rem', fontWeight: 600, color: '#a78bfa' }}>
                        {composedResult.audio_speed || '1.00x'}
                      </div>
                    </div>
                  </div>
                  <div style={{ fontSize: '0.82rem', color: '#cbd5e1' }}>
                    Subtitles Burned: <strong>{composedResult.has_subtitles ? 'Yes' : 'No'}</strong> • Mux Time: <strong>{composedResult.generation_time_seconds}s</strong> • Sync: <strong>{composedResult.is_synchronized ? '✓ Aligned' : 'Review'}</strong>
                  </div>
                  <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.8rem', color: '#38bdf8' }}>
                    ✓ Playing in the main video player above with synchronized voiceover and burned subtitles!
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {plan?.scenes && plan.scenes.length > 0 && (
        <div className="scenes-section">
          <div className="scenes-heading">Planned Scene Sequence ({plan.scenes.length} Scenes)</div>
          <div className="scenes-timeline">
            {plan.scenes.map((scene, i) => (
              <div key={scene.id || i} className="scene-timeline-item">
                <span className="scene-index-badge">Scene {scene.id || i + 1}</span>
                <span className="scene-type-badge">{scene.type}</span>
                <span className="scene-title-text">{scene.title || `Scene ${i + 1}`}</span>
                <span className="scene-duration-text">{scene.duration ? `${scene.duration}s` : '5s'}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
