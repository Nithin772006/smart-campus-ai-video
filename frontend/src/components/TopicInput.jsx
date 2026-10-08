import React from 'react';

export default function TopicInput({
  topic,
  setTopic,
  quality,
  setQuality,
  targetDuration = 30,
  setTargetDuration,
  loading,
  onGenerate,
  onFullGenerate,
}) {
  const handleSubmit = (e) => {
    e.preventDefault();
    if (!loading && topic.trim()) {
      onGenerate();
    }
  };

  return (
    <form onSubmit={handleSubmit} className="topic-form">
      <div className="input-group-row">
        <div className="input-wrapper">
          <input
            type="text"
            className="topic-input"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="Enter an academic topic... (e.g. Explain Newton's Second Law)"
            disabled={loading}
            autoFocus
          />
        </div>
        <select
          className="duration-select"
          value={targetDuration}
          onChange={(e) => setTargetDuration && setTargetDuration(Number(e.target.value))}
          disabled={loading}
          title="Video & Narration target duration"
          style={{
            padding: '0.65rem 0.85rem',
            background: 'rgba(255, 255, 255, 0.05)',
            border: '1px solid rgba(255, 255, 255, 0.15)',
            borderRadius: '10px',
            color: '#f8fafc',
            fontSize: '0.9rem',
            outline: 'none',
            cursor: 'pointer',
          }}
        >
          <option value={30} style={{ background: '#0f172a', color: '#fff' }}>30 sec</option>
          <option value={45} style={{ background: '#0f172a', color: '#fff' }}>45 sec</option>
          <option value={60} style={{ background: '#0f172a', color: '#fff' }}>60 sec</option>
          <option value={90} style={{ background: '#0f172a', color: '#fff' }}>90 sec</option>
          <option value={120} style={{ background: '#0f172a', color: '#fff' }}>120 sec</option>
        </select>
        <select
          className="quality-select"
          value={quality}
          onChange={(e) => setQuality(e.target.value)}
          disabled={loading}
          title="Video render resolution"
        >
          <option value="medium_quality">Medium (720p)</option>
          <option value="low_quality">Fast Draft (480p)</option>
          <option value="high_quality">High Definition (1080p)</option>
        </select>
        <button
          type="submit"
          className="generate-button"
          disabled={loading || !topic.trim()}
        >
          {loading ? (
            <>
              <span className="btn-spinner"></span>
              Generating...
            </>
          ) : (
            <>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="5 3 19 12 5 21 5 3"></polygon>
              </svg>
              Generate Video
            </>
          )}
        </button>
        {onFullGenerate && (
          <button
            id="create-final-video-btn"
            type="button"
            className="generate-button"
            onClick={onFullGenerate}
            disabled={loading || !topic.trim()}
            title="Run complete 5-stage pipeline: Qwen Plan → Manim Scenes → IndicF5 Voiceover → Whisper Subtitles → FFmpeg Final MP4"
            style={{
              background: 'linear-gradient(135deg, #059669 0%, #10b981 100%)',
              boxShadow: '0 4px 14px rgba(16, 185, 129, 0.35)',
              whiteSpace: 'nowrap',
            }}
          >
            {loading ? (
              <>
                <span className="btn-spinner"></span>
                Composing...
              </>
            ) : (
              <>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="5 3 19 12 5 21 5 3"></polygon>
                </svg>
                Create Final Video
              </>
            )}
          </button>
        )}
      </div>
    </form>
  );
}
