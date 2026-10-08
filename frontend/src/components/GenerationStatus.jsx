import React from 'react';

const ALL_STAGES = [
  { id: 1, name: "Understanding topic", desc: "Analyzing academic scope and requirements" },
  { id: 2, name: "Creating lesson", desc: "Structuring pedagogical video plan via Qwen2.5 3B" },
  { id: 3, name: "Rendering educational visuals", desc: "Generating programmatic animation with Manim" },
  { id: 4, name: "Generating narration", desc: "Synthesizing spoken audio with IndicF5 TTS" },
  { id: 5, name: "Creating subtitles", desc: "Transcribing and aligning timestamps via faster-whisper" },
  { id: 6, name: "Creating AI teacher", desc: "Preparing transparent 3D educator presenter layer", requiresCharacter: true },
  { id: 7, name: "Composing final video", desc: "Multiplexing video, audio, subtitles, and avatar via FFmpeg" },
];

export default function GenerationStatus({ topic, characterEnabled = false }) {
  const activeStages = ALL_STAGES.filter((s) => !s.requiresCharacter || characterEnabled);

  return (
    <div className="status-card">
      <div className="spinner-wrapper">
        <div className="spinner"></div>
      </div>
      <h3 className="status-title">
        Generating Educational Video Pipeline
      </h3>
      <p className="status-subtitle">
        Topic: <span className="status-topic-name">"{topic}"</span>
      </p>

      <div className="pipeline-notice">
        <span>⚡ Real-Time Pipeline:</span> Each stage executes sequentially on local AI hardware without simulation.
      </div>

      <div className="stages-list">
        {activeStages.map((stage, idx) => (
          <div key={stage.id} className="stage-item in-progress">
            <span className="stage-num">{idx + 1}</span>
            <div className="stage-content">
              <span className="stage-text">{stage.name}</span>
              <span className="stage-desc">{stage.desc}</span>
            </div>
            <span className="stage-pulse"></span>
          </div>
        ))}
      </div>
    </div>
  );
}
