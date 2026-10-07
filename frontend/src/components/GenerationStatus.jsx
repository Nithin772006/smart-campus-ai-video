import React, { useState, useEffect } from 'react';

const STAGES = [
  "Understanding topic",
  "Creating educational plan",
  "Rendering animation",
  "Preparing video",
];

export default function GenerationStatus({ topic }) {
  const [currentStage, setCurrentStage] = useState(0);

  useEffect(() => {
    // Stage 0: 0s
    // Stage 1: ~2.5s
    // Stage 2: ~6.0s
    // Stage 3: ~14.0s
    const t1 = setTimeout(() => setCurrentStage(1), 2500);
    const t2 = setTimeout(() => setCurrentStage(2), 6500);
    const t3 = setTimeout(() => setCurrentStage(3), 14000);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
    };
  }, []);

  return (
    <div className="status-card">
      <div className="spinner-wrapper">
        <div className="spinner"></div>
      </div>
      <h3 className="status-title">
        Generating your educational video...
      </h3>
      <p className="status-subtitle">
        Topic: <span className="status-topic-name">"{topic}"</span>
      </p>

      <div className="stages-list">
        {STAGES.map((stageName, idx) => {
          let statusClass = '';
          let icon = '○';

          if (idx < currentStage) {
            statusClass = 'completed';
            icon = '✓';
          } else if (idx === currentStage) {
            statusClass = 'active';
            icon = '●';
          } else {
            statusClass = '';
            icon = '○';
          }

          return (
            <div key={idx} className={`stage-item ${statusClass}`}>
              <span className="stage-icon">{icon}</span>
              <span className="stage-text">{stageName}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
