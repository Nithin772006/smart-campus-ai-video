import React, { useState, useEffect } from 'react';

const PIPELINE_SPEC = [
  {
    id: 'understanding_topic',
    name: 'Understanding topic',
    description: 'Analyzing academic scope and requirements',
  },
  {
    id: 'creating_lesson',
    name: 'Creating lesson',
    description: 'Structuring pedagogical video plan via Qwen2.5 3B',
  },
  {
    id: 'rendering_visuals',
    name: 'Rendering educational visuals',
    description: 'Generating programmatic animation with Manim',
  },
  {
    id: 'generating_narration',
    name: 'Generating narration',
    description: 'Synthesizing spoken audio with IndicF5 TTS',
  },
  {
    id: 'creating_subtitles',
    name: 'Creating subtitles',
    description: 'Transcribing and aligning timestamps via faster-whisper',
  },
  {
    id: 'creating_teacher',
    name: 'Creating AI teacher',
    description: 'Preparing transparent 3D educator presenter layer',
  },
  {
    id: 'composing_final_video',
    name: 'Composing final video',
    description: 'Multiplexing video, audio, subtitles, and avatar via FFmpeg',
  },
];

export default function GenerationStatus({
  topic,
  characterEnabled = false,
  progressData = null,
  error = null,
}) {
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  // Live timer counting up while generation is ongoing
  useEffect(() => {
    if (progressData?.overall_progress === 100 || error) {
      return;
    }

    const interval = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, [progressData?.overall_progress, error]);

  // Combine static stage definitions with live SSE progress state
  const rawStages = progressData?.stages || [];

  const stages = PIPELINE_SPEC.map((spec, idx) => {
    const live = rawStages.find((s) => s.id === spec.id);
    let status = 'pending';
    let progress = 0;
    let message = 'Waiting to start...';
    let stageError = null;

    if (live) {
      status = live.status || 'pending';
      progress = typeof live.progress === 'number' ? live.progress : 0;
      message = live.message || spec.description;
      stageError = live.error || null;
    } else if (idx === 0) {
      // Before first SSE packet arrives, stage 1 is starting
      status = 'running';
      progress = 10;
      message = 'Initializing topic analysis...';
    }

    return {
      id: spec.id,
      index: idx + 1,
      name: spec.name,
      description: spec.description,
      status, // 'pending' | 'running' | 'completed' | 'error'
      progress: Math.min(100, Math.max(0, progress)),
      message,
      error: stageError,
    };
  });

  // Calculate overall progress as sum(stage.progress) / numberOfStages
  const computedOverall = stages.length > 0
    ? Math.min(100, Math.max(0, Math.round(stages.reduce((acc, s) => acc + s.progress, 0) / stages.length)))
    : 0;

  const overallProgress = typeof progressData?.overall_progress === 'number'
    ? progressData.overall_progress
    : computedOverall;

  const isCompleted = overallProgress === 100;
  const activeStage = stages.find((s) => s.status === 'running') || stages[0];

  const formatElapsed = (sec) => {
    const mins = Math.floor(sec / 60);
    const remainder = sec % 60;
    if (mins > 0) {
      return `${mins}m ${remainder < 10 ? '0' : ''}${remainder}s`;
    }
    return `${remainder}s`;
  };

  return (
    <div className="status-card pipeline-progress-container" id="generation-status-card">
      {/* Overall Header Section */}
      <div className="pipeline-header">
        <div className="pipeline-title-row">
          <div className="pipeline-brand-icon">
            {isCompleted ? (
              <span className="icon-complete-badge">✓</span>
            ) : error ? (
              <span className="icon-error-badge">✕</span>
            ) : (
              <div className="spinner-mini"></div>
            )}
          </div>
          <div>
            <h3 className="status-title">Educational Video Generation Pipeline</h3>
            <p className="status-subtitle">
              Topic: <span className="status-topic-name">"{topic}"</span>
            </p>
          </div>
        </div>

        <div className="pipeline-meta-row">
          <div className="pipeline-active-badge">
            {isCompleted ? (
              <span className="badge-text success">✓ All 7 stages completed</span>
            ) : error ? (
              <span className="badge-text error">✕ Generation failed</span>
            ) : (
              <span className="badge-text running">
                Stage {activeStage.index} of {stages.length}: {activeStage.name}...
              </span>
            )}
          </div>
          <div className="pipeline-timer-badge">
            ⏱ Elapsed: <span className="timer-val">{formatElapsed(elapsedSeconds)}</span>
          </div>
        </div>

        {/* Overall Progress Bar */}
        <div className="overall-progress-wrapper">
          <div className="overall-progress-header">
            <span className="overall-label">Overall Progress</span>
            <span className="overall-percent">{overallProgress}%</span>
          </div>
          <div className="overall-progress-track">
            <div
              className={`overall-progress-fill ${isCompleted ? 'is-complete' : error ? 'is-error' : ''}`}
              style={{ width: `${overallProgress}%` }}
              role="progressbar"
              aria-valuenow={overallProgress}
              aria-valuemin="0"
              aria-valuemax="100"
            />
          </div>
        </div>
      </div>

      {/* Completion Success Banner */}
      {isCompleted && (
        <div className="completion-success-banner">
          <div className="banner-icon">✓</div>
          <div className="banner-details">
            <span className="banner-title">Video generation completed (100%)</span>
            <span className="banner-subtitle">
              All 7 educational pipeline stages executed and verified successfully in {formatElapsed(elapsedSeconds)}.
            </span>
          </div>
        </div>
      )}

      {/* Error Alert Banner */}
      {error && (
        <div className="stage-error-banner">
          <div className="banner-icon">✕</div>
          <div className="banner-details">
            <span className="banner-title">Pipeline Execution Stopped</span>
            <span className="banner-subtitle">{error}</span>
          </div>
        </div>
      )}

      {/* Notice */}
      <div className="pipeline-notice">
        <span>⚡ Hardware Pipeline:</span> Each stage executes sequentially on local AI hardware without simulation.
      </div>

      {/* 7 Per-Stage Cards List */}
      <div className="stages-list">
        {stages.map((stage) => {
          const isStageActive = stage.status === 'running';
          const isStageCompleted = stage.status === 'completed';
          const isStageError = stage.status === 'error';
          const isStagePending = stage.status === 'pending';

          return (
            <div
              key={stage.id}
              className={`stage-card-v2 status-${stage.status} ${isStageActive ? 'is-active' : ''}`}
            >
              {/* Stage Top Bar */}
              <div className="stage-header-row">
                <div className="stage-left-meta">
                  <div className={`stage-index-pill status-${stage.status}`}>
                    {isStageCompleted ? (
                      '✓'
                    ) : isStageError ? (
                      '✕'
                    ) : (
                      stage.index
                    )}
                  </div>
                  <div className="stage-names-group">
                    <span className="stage-primary-name">{stage.name}</span>
                    <span className="stage-secondary-desc">{stage.description}</span>
                  </div>
                </div>

                <div className="stage-right-meta">
                  <span className={`status-pill status-${stage.status}`}>
                    {isStageCompleted
                      ? 'Completed'
                      : isStageActive
                      ? 'In progress'
                      : isStageError
                      ? 'Failed'
                      : 'Waiting'}
                  </span>
                  <span className={`stage-pct-label status-${stage.status}`}>
                    {stage.progress}%
                  </span>
                </div>
              </div>

              {/* Smooth Progress Bar */}
              <div className="stage-progress-track">
                <div
                  className={`stage-progress-fill status-${stage.status}`}
                  style={{ width: `${stage.progress}%` }}
                />
              </div>

              {/* Live Stage Message / Counter */}
              <div className="stage-footer-row">
                <span className={`stage-status-msg status-${stage.status}`}>
                  {isStageError && stage.error
                    ? `Failed: ${stage.error}`
                    : stage.message}
                </span>
                {isStageActive && (
                  <span className="stage-live-pulse-dot" title="Active"></span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
