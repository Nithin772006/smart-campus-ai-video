import React from 'react';

export default function GenerationDetails({ result }) {
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
          <div className="metric-label">File Size</div>
          <div className="metric-value">
            {output_size_mb !== null && output_size_mb !== undefined ? `${output_size_mb} MB` : 'N/A'}
          </div>
        </div>

        <div className="metric-item">
          <div className="metric-label">AI Planner</div>
          <div className="metric-value" style={{ fontSize: '0.95rem' }}>{plannerLabel}</div>
        </div>
      </div>

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
