import React from 'react';

export default function TopicInput({ topic, setTopic, quality, setQuality, loading, onGenerate }) {
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
      </div>
    </form>
  );
}
