import React, { useState } from 'react';
import { generateAvatarPreview, getVideoUrl } from '../api';

export default function VideoStudio({
  topic,
  setTopic,
  quality,
  setQuality,
  targetDuration,
  setTargetDuration,
  voice,
  setVoice,
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

  const handleAvatarPreviewClick = async () => {
    setPreviewLoading(true);
    setPreviewError('');
    try {
      const data = await generateAvatarPreview(10, characterPosition);
      if (data && data.video_path) {
        setAvatarPreviewUrl(getVideoUrl(data.video_path));
      }
    } catch (err) {
      setPreviewError(err.message || 'Avatar preview failed.');
    } finally {
      setPreviewLoading(false);
    }
  };

  return (
    <div className="video-studio-container">
      <div className="studio-header">
        <div className="studio-badge">
          <span className="studio-icon">🎬</span>
          VIDEO STUDIO
        </div>
        <p className="studio-subtitle">
          Configure educational visual parameters, local neural narration, and optional AI Teacher avatar.
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
            Narration Voice
          </label>
          <div className="pill-group">
            <button
              type="button"
              className={`pill-btn ${voice === 'indicf5' ? 'active' : ''}`}
              onClick={() => setVoice('indicf5')}
              disabled={loading}
            >
              <span className="pill-dot green"></span>
              IndicF5 — Local
            </button>
            <button
              type="button"
              className="pill-btn disabled"
              title="ElevenLabs cloud integration is reserved for future releases."
              disabled
            >
              <span className="pill-dot muted"></span>
              ElevenLabs — Premium
              <span className="pill-tag">Future</span>
            </button>
          </div>
        </div>

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

        {/* Visual Style */}
        <div className="studio-control-group">
          <label className="control-label">Visual Style</label>
          <div className="pill-group">
            <button
              type="button"
              className={`pill-btn ${visualStyle === 'academic' ? 'active' : ''}`}
              onClick={() => setVisualStyle('academic')}
              disabled={loading}
            >
              Academic
            </button>
            <button
              type="button"
              className={`pill-btn ${visualStyle === 'explainer' ? 'active' : ''}`}
              onClick={() => setVisualStyle('explainer')}
              disabled={loading}
            >
              Explainer
            </button>
            <button
              type="button"
              className={`pill-btn ${visualStyle === 'classroom' ? 'active' : ''}`}
              onClick={() => setVisualStyle('classroom')}
              disabled={loading}
            >
              Classroom
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
