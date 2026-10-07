import React, { useRef, useEffect } from 'react';

export default function VideoPlayer({ videoUrl, topic, duration }) {
  const videoRef = useRef(null);

  useEffect(() => {
    if (videoRef.current && videoUrl) {
      videoRef.current.load();
    }
  }, [videoUrl]);

  return (
    <div className="video-section">
      <div className="video-header">
        <h3 className="video-title">
          {topic ? `Video: ${topic}` : 'Generated Video'}
        </h3>
        {duration && (
          <span className="badge badge-blue">
            {duration.toFixed(1)}s Runtime
          </span>
        )}
      </div>

      <div className="video-player-container">
        {videoUrl ? (
          <video
            ref={videoRef}
            controls
            playsInline
            className="video-element"
            key={videoUrl}
          >
            <source src={videoUrl} type="video/mp4" />
            Your browser does not support HTML5 video playback.
          </video>
        ) : (
          <div className="video-placeholder">
            <svg
              className="video-placeholder-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
            >
              <rect x="2" y="2" width="20" height="20" rx="5" ry="5"></rect>
              <polygon points="10 8 16 12 10 16 10 8" fill="currentColor"></polygon>
            </svg>
            <p>Generated MP4 video will appear and play here</p>
          </div>
        )}
      </div>
    </div>
  );
}
