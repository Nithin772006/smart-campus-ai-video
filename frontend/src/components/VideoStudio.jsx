import React, { useState, useEffect } from 'react';
import { generateAvatarPreview, getAvatarStatus, getVideoUrl, getElevenLabsVoices } from '../api';

export default function VideoStudio({
  topic,
  setTopic,
  quality,
  setQuality,
  targetDuration,
  setTargetDuration,
  voice = 'indicf5',
  setVoice,
  language = 'en',
  setLanguage,
  voiceId = '',
  setVoiceId,
  character,
  setCharacter,
  characterPosition,
  setCharacterPosition,
  visualStyle,
  setVisualStyle,
  loading,
  onGenerateVisual,
  onGenerateFull,
  onPreviewAvatar,
}) {
  const [previewLoading, setPreviewLoading] = useState(false);
  const [avatarPreviewUrl, setAvatarPreviewUrl] = useState('');
  const [previewError, setPreviewError] = useState('');
  const [avatarProvider, setAvatarProvider] = useState('auto');
  const [avatarStatus, setAvatarStatus] = useState(null);

  // ElevenLabs Voice State
  const [elevenLabsVoices, setElevenLabsVoices] = useState([]);
  const [voicesLoading, setVoicesLoading] = useState(false);

  useEffect(() => {
    if (character) {
      getAvatarStatus(avatarProvider).then((st) => {
        if (st) setAvatarStatus(st);
      });
    }
  }, [character, avatarProvider]);

  // Load ElevenLabs voices when ElevenLabs is selected
  useEffect(() => {
    if (voice === 'elevenlabs' && elevenLabsVoices.length === 0) {
      setVoicesLoading(true);
      getElevenLabsVoices()
        .then((voicesList) => {
          if (Array.isArray(voicesList) && voicesList.length > 0) {
            setElevenLabsVoices(voicesList);
            if (!voiceId && setVoiceId) {
              setVoiceId(voicesList[0].voice_id);
            }
          }
        })
        .finally(() => {
          setVoicesLoading(false);
        });
    }
  }, [voice, elevenLabsVoices.length, voiceId, setVoiceId]);

  const handleAvatarPreviewClick = async () => {
    setPreviewLoading(true);
    setPreviewError('');
    try {
      const data = await generateAvatarPreview(10, characterPosition, avatarProvider);
      if (data && data.video_path) {
        setAvatarPreviewUrl(getVideoUrl(data.video_path));
      }
    } catch (err) {
      setPreviewError(err.message || 'Avatar preview failed.');
    } finally {
      setPreviewLoading(false);
    }
  };

  const selectedVoiceName =
    elevenLabsVoices.find((v) => v.voice_id === voiceId)?.name || 'Default Voice';

  return (
    <div className="video-studio-container">
      <div className="studio-header">
        <div className="studio-badge">
          <span className="studio-icon">🎬</span>
          VIDEO STUDIO
        </div>
        <p className="studio-subtitle">
          Configure educational visual parameters, local neural narration or ElevenLabs cloud TTS, and optional AI Teacher avatar.
        </p>
      </div>

      {/* Primary Topic Input */}
      <div className="studio-field">
        <label htmlFor="studio-topic-input" className="studio-label">Topic / Educational Lesson</label>
        <div className="studio-input-wrap">
          <input
            id="studio-topic-input"
            type="text"
            className="studio-text-input"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g. Explain Newton's Second Law of Motion"
            disabled={loading}
          />
        </div>
      </div>

      {/* Grid of Studio Controls */}
      <div className="studio-grid">
        {/* Render Quality */}
        <div className="studio-control-group">
          <label className="control-label">Video Quality</label>
          <select
            className="studio-select"
            value={quality}
            onChange={(e) => setQuality(e.target.value)}
            disabled={loading}
          >
            <option value="medium_quality">Medium (720p - Recommended)</option>
            <option value="low_quality">Fast Draft (480p)</option>
            <option value="high_quality">High Definition (1080p)</option>
          </select>
        </div>

        {/* Target Duration */}
        <div className="studio-control-group">
          <label className="control-label">Target Duration</label>
          <select
            className="studio-select"
            value={targetDuration}
            onChange={(e) => setTargetDuration(Number(e.target.value))}
            disabled={loading}
          >
            <option value={30}>30 Seconds (Core Lesson)</option>
            <option value={45}>45 Seconds</option>
            <option value={60}>60 Seconds (Full Overview)</option>
            <option value={90}>90 Seconds (Deep Dive)</option>
            <option value={120}>120 Seconds (Comprehensive)</option>
          </select>
        </div>

        {/* Voice Selection */}
        <div className="studio-control-group">
          <label className="control-label">
            Voice Provider
          </label>
          <div className="pill-group">
            <button
              type="button"
              id="voice-toggle-indicf5"
              className={`pill-btn ${voice === 'indicf5' ? 'active' : ''}`}
              onClick={() => setVoice && setVoice('indicf5')}
              disabled={loading}
            >
              <span className="pill-dot green"></span>
              IndicF5 Local
            </button>
            <button
              type="button"
              id="voice-toggle-elevenlabs"
              className={`pill-btn ${voice === 'elevenlabs' ? 'active' : ''}`}
              onClick={() => setVoice && setVoice('elevenlabs')}
              disabled={loading}
            >
              <span className="pill-dot blue" style={{ background: '#38bdf8' }}></span>
              ElevenLabs Cloud
            </button>
          </div>
        </div>

        {/* When ElevenLabs is selected: Language & Voice ID Selectors */}
        {voice === 'elevenlabs' && (
          <>
            <div className="studio-control-group">
              <label className="control-label">Narration Language</label>
              <select
                id="elevenlabs-language-select"
                className="studio-select"
                value={language || 'en'}
                onChange={(e) => setLanguage && setLanguage(e.target.value)}
                disabled={loading}
              >
                <option value="en">English (en)</option>
                <option value="ta">Tamil (ta)</option>
                <option value="hi">Hindi (hi)</option>
              </select>
            </div>

            <div className="studio-control-group">
              <label className="control-label">
                ElevenLabs Voice {voicesLoading && <span style={{ fontSize: '0.75rem', opacity: 0.7 }}>(Loading...)</span>}
              </label>
              <select
                id="elevenlabs-voice-select"
                className="studio-select"
                value={voiceId || ''}
                onChange={(e) => setVoiceId && setVoiceId(e.target.value)}
                disabled={loading}
              >
                {elevenLabsVoices.length > 0 ? (
                  elevenLabsVoices.map((v) => (
                    <option key={v.voice_id} value={v.voice_id}>
                      {v.name} {v.category ? `(${v.category})` : ''}
                    </option>
                  ))
                ) : (
                  <>
                    <option value="21m00Tcm4TlvDq8ikWAM">Rachel (Calm American Female)</option>
                    <option value="AZnzlk1XvdvUeBnXmlld">Domi (Clear Educational)</option>
                    <option value="EXAVITQu4vr4xnSDxMaL">Bella (Expressive Academic)</option>
                    <option value="ErXwobaYiN019PkySvjV">Antoni (Engaging Male)</option>
                  </>
                )}
              </select>
            </div>

            <div className="elevenlabs-summary-badge" style={{
              gridColumn: '1 / -1',
              padding: '0.75rem 1rem',
              background: 'rgba(56, 189, 248, 0.08)',
              border: '1px solid rgba(56, 189, 248, 0.25)',
              borderRadius: '10px',
              fontSize: '0.85rem',
              color: '#e2e8f0',
              display: 'flex',
              flexWrap: 'wrap',
              gap: '1.25rem',
              alignItems: 'center',
            }}>
              <div><span style={{ color: '#94a3b8' }}>Provider:</span> <strong style={{ color: '#38bdf8' }}>ElevenLabs</strong></div>
              <div><span style={{ color: '#94a3b8' }}>Language:</span> <strong style={{ color: '#a7f3d0' }}>{language === 'ta' ? 'Tamil' : language === 'hi' ? 'Hindi' : 'English'}</strong></div>
              <div><span style={{ color: '#94a3b8' }}>Voice:</span> <strong style={{ color: '#fde68a' }}>{selectedVoiceName}</strong></div>
              <div><span style={{ color: '#94a3b8' }}>Subtitles:</span> <strong style={{ color: '#c084fc' }}>Direct Timestamps</strong></div>
            </div>
          </>
        )}

        {/* Character Selection */}
        <div className="studio-control-group">
          <label className="control-label">
            AI Character
          </label>
          <div className="pill-group">
            <button
              type="button"
              id="char-toggle-none"
              className={`pill-btn ${!character ? 'active' : ''}`}
              onClick={() => setCharacter(false)}
              disabled={loading}
            >
              No Character (Visuals Only)
            </button>
            <button
              type="button"
              id="char-toggle-teacher"
              className={`pill-btn ${character ? 'active' : ''}`}
              onClick={() => setCharacter(true)}
              disabled={loading}
            >
              <span className="pill-dot blue"></span>
              AI Teacher
              <span className="pill-tag accent">3D Educator</span>
            </button>
          </div>
        </div>

        {/* Character Position (Only when character is active) */}
        {character && (
          <div className="studio-control-group animate-slide">
            <label className="control-label">Teacher Position</label>
            <div className="pill-group">
              <button
                type="button"
                className={`pill-btn ${characterPosition === 'auto' ? 'active' : ''}`}
                onClick={() => setCharacterPosition('auto')}
                disabled={loading}
              >
                Auto (Optimal)
              </button>
              <button
                type="button"
                className={`pill-btn ${characterPosition === 'left' ? 'active' : ''}`}
                onClick={() => setCharacterPosition('left')}
                disabled={loading}
              >
                Left
              </button>
              <button
                type="button"
                className={`pill-btn ${characterPosition === 'right' ? 'active' : ''}`}
                onClick={() => setCharacterPosition('right')}
                disabled={loading}
              >
                Right
              </button>
            </div>
          </div>
        )}

        {/* Avatar Provider (When character is active) */}
        {character && (
          <div className="studio-control-group animate-slide">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
              <label className="control-label" style={{ margin: 0 }}>Avatar Provider</label>
              <span style={{ fontSize: '0.75rem', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                AI Teacher:
                {avatarStatus?.animated ? (
                  <span style={{ color: '#10b981' }}>● Animated</span>
                ) : (
                  <span style={{ color: '#f59e0b' }} title={avatarStatus?.reason || 'Static teacher overlay active'}>
                    ● Static fallback
                  </span>
                )}
              </span>
            </div>
            <select
              className="studio-select"
              value={avatarProvider}
              onChange={(e) => setAvatarProvider(e.target.value)}
              disabled={loading}
              id="avatar-provider-select"
            >
              <option value="auto">Auto</option>
              <option value="musetalk">MuseTalk</option>
              <option value="cloud">Cloud Avatar</option>
              <option value="overlay">Static Teacher</option>
            </select>
          </div>
        )}


        {/* Visual Style */}
        <div className="studio-control-group">
          <label className="control-label">Visual Style</label>
          <div className="pill-group">
            <button
              type="button"
              className={`pill-btn ${visualStyle === 'educational' ? 'active' : ''}`}
              onClick={() => setVisualStyle('educational')}
              disabled={loading}
              id="style-educational"
            >
              Educational
            </button>
            <button
              type="button"
              className={`pill-btn ${visualStyle === 'cinematic_educational' ? 'active' : ''}`}
              onClick={() => setVisualStyle('cinematic_educational')}
              disabled={loading}
              id="style-cinematic"
            >
              Cinematic Educational
            </button>
            <button
              type="button"
              className={`pill-btn ${visualStyle === '3blue1brown' ? 'active' : ''}`}
              onClick={() => setVisualStyle('3blue1brown')}
              disabled={loading}
              id="style-3b1b"
            >
              3Blue1Brown Inspired
            </button>
            <button
              type="button"
              className={`pill-btn ${visualStyle === 'auto' ? 'active' : ''}`}
              onClick={() => setVisualStyle('auto')}
              disabled={loading}
              id="style-auto"
            >
              Auto
            </button>
          </div>
        </div>
      </div>

      {/* Avatar Preview Box (if Character enabled) */}
      {character && (
        <div className="avatar-preview-banner">
          <div className="avatar-meta-info">
            <div className="avatar-avatar-thumb">
              <img
                src="/assets/character/teacher.png"
                alt="SmartCampus Teacher"
                onError={(e) => { e.target.style.display = 'none'; }}
              />
            </div>
            <div>
              <div className="avatar-name">SmartCampus Canonical Teacher</div>
              <div className="avatar-spec-note">Upper-body 3D educator • Transparent overlay • Synchronized with narration</div>
            </div>
          </div>
          <button
            type="button"
            className="avatar-test-btn"
            onClick={handleAvatarPreviewClick}
            disabled={previewLoading || loading}
          >
            {previewLoading ? 'Generating Preview...' : 'Preview AI Teacher'}
          </button>
        </div>
      )}

      {/* Video Preview Player if generated */}
      {avatarPreviewUrl && (
        <div className="avatar-preview-modal animate-slide">
          <div className="modal-header">
            <span>AI Teacher Avatar Preview</span>
            <button type="button" onClick={() => setAvatarPreviewUrl('')}>✕</button>
          </div>
          <video src={avatarPreviewUrl} controls autoPlay className="avatar-preview-video" />
        </div>
      )}

      {previewError && (
        <div className="preview-error-note">
          ⚠️ {previewError}
        </div>
      )}

      {/* Studio Primary Action Buttons */}
      <div className="studio-actions-row">
        <button
          type="button"
          className="studio-btn secondary"
          onClick={onGenerateVisual}
          disabled={loading || !topic.trim()}
          title="Render Manim animation scenes only"
        >
          {loading ? 'Rendering...' : 'Visuals Only (Manim)'}
        </button>

        <button
          id="create-final-video-btn"
          type="button"
          className="studio-btn primary"
          onClick={onGenerateFull}
          disabled={loading || !topic.trim()}
          title="Full Pipeline: Qwen → Manim → IndicF5 → Whisper → (Optional AI Teacher) → FFmpeg"
        >
          {loading ? (
            <>
              <span className="btn-spinner"></span>
              Generating Full Educational Video...
            </>
          ) : (
            <>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polygon points="5 3 19 12 5 21 5 3"></polygon>
              </svg>
              {character ? 'Create Video with AI Teacher' : 'Create Final Video (Full Pipeline)'}
            </>
          )}
        </button>
      </div>
    </div>
  );
}
