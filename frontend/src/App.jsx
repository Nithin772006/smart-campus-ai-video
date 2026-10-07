import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import TopicInput from './components/TopicInput';
import ExampleTopics from './components/ExampleTopics';
import GenerationStatus from './components/GenerationStatus';
import VideoPlayer from './components/VideoPlayer';
import GenerationDetails from './components/GenerationDetails';
import { generateVideoFromTopic, getVideoUrl, checkBackendHealth } from './api';

export default function App() {
  const [topic, setTopic] = useState('');
  const [quality, setQuality] = useState('medium_quality');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [videoUrl, setVideoUrl] = useState('');
  const [backendConnected, setBackendConnected] = useState(true);

  // Probe backend connection on mount
  useEffect(() => {
    checkBackendHealth().then((res) => {
      setBackendConnected(Boolean(res));
    });
  }, []);

  const handleGenerate = async (customTopic) => {
    const targetTopic = (customTopic || topic).trim();
    if (!targetTopic) {
      setError('Please enter an academic topic before generating.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await generateVideoFromTopic(targetTopic, quality);
      setResult(data);
      const resolvedUrl = getVideoUrl(data.video_path);
      setVideoUrl(resolvedUrl);
      setBackendConnected(true);
    } catch (err) {
      setError(err.message || 'An error occurred during video generation.');
      // Re-probe health on failure
      checkBackendHealth().then((res) => setBackendConnected(Boolean(res)));
    } finally {
      setLoading(false);
    }
  };

  const handleSelectExample = (exampleTopic) => {
    setTopic(exampleTopic);
    setError(null);
  };

  return (
    <div className="app-container">
      <Header backendConnected={backendConnected} />

      {/* Error Alert */}
      {error && (
        <div className="error-banner">
          <div>
            <strong>Error: </strong>
            <span>{error}</span>
          </div>
          <button
            type="button"
            className="error-close-btn"
            onClick={() => setError(null)}
            title="Dismiss error"
          >
            ×
          </button>
        </div>
      )}

      {/* Main Input Card */}
      <div className="glass-card">
        <TopicInput
          topic={topic}
          setTopic={setTopic}
          quality={quality}
          setQuality={setQuality}
          loading={loading}
          onGenerate={() => handleGenerate(topic)}
        />
        <ExampleTopics
          onSelect={handleSelectExample}
          disabled={loading}
        />
      </div>

      {/* Loading Progress State */}
      {loading && <GenerationStatus topic={topic} />}

      {/* Video Player */}
      <VideoPlayer
        videoUrl={videoUrl}
        topic={result?.topic}
        duration={result?.duration_seconds}
      />

      {/* Generation Metadata Details */}
      {result && <GenerationDetails result={result} />}

      <footer className="app-footer">
        <p>
          SmartCampus AI Video • Powered by <span>Qwen2.5 3B via Ollama</span> & <span>Manim</span> (100% Local)
        </p>
      </footer>
    </div>
  );
}
