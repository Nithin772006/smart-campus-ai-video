import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import VideoStudio from './components/VideoStudio';
import ExampleTopics from './components/ExampleTopics';
import GenerationStatus from './components/GenerationStatus';
import VideoPlayer from './components/VideoPlayer';
import GenerationDetails from './components/GenerationDetails';
import {
  generateVideoFromTopic,
  generateFullVideo,
  streamFullVideo,
  getVideoUrl,
  checkBackendHealth,
} from './api';

export default function App() {
  const [topic, setTopic] = useState('');
  const [quality, setQuality] = useState('medium_quality');
  const [targetDuration, setTargetDuration] = useState(30);
  const [voice, setVoice] = useState('indicf5');
  const [language, setLanguage] = useState('en');
  const [voiceId, setVoiceId] = useState('');
  const [character, setCharacter] = useState(false); // DEFAULT: No Character
  const [characterPosition, setCharacterPosition] = useState('auto');
  const [visualStyle, setVisualStyle] = useState('auto');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [videoUrl, setVideoUrl] = useState('');
  const [progressData, setProgressData] = useState(null);
  const [backendConnected, setBackendConnected] = useState(true);

  // Probe backend connection on mount
  useEffect(() => {
    checkBackendHealth().then((res) => {
      setBackendConnected(Boolean(res));
    });
  }, []);

  const handleGenerateVisual = async () => {
    const targetTopic = topic.trim();
    if (!targetTopic) {
      setError('Please enter an academic topic before generating.');
      return;
    }

    setLoading(true);
    setError(null);
    setProgressData(null);

    try {
      const data = await generateVideoFromTopic(targetTopic, quality, targetDuration);
      setResult(data);
      const resolvedUrl = getVideoUrl(data.video_path);
      setVideoUrl(resolvedUrl);
      setBackendConnected(true);
    } catch (err) {
      setError(err.message || 'An error occurred during video generation.');
      checkBackendHealth().then((res) => setBackendConnected(Boolean(res)));
    } finally {
      setLoading(false);
    }
  };

  const handleFullGenerate = () => {
    const targetTopic = topic.trim();
    if (!targetTopic) {
      setError('Please enter an academic topic before generating.');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);
    setVideoUrl('');
    setProgressData({
      overall_progress: 0,
      stage: 'understanding_topic',
      stage_index: 1,
      stages: [],
    });

    // Stream generation with real-time SSE progress
    streamFullVideo(
      targetTopic,
      {
        quality,
        burnSubtitles: true,
        targetDuration,
        character,
        characterPosition,
        visualStyle,
        voiceProvider: voice,
        voiceId: voiceId || null,
        language,
      },
      (progressEvent) => {
        // Real-time stage progress updates from backend
        setProgressData(progressEvent);
      },
      (completeEvent) => {
        // Video finished successfully!
        const data = completeEvent.result || completeEvent;
        setProgressData({
          overall_progress: 100,
          stages: completeEvent.stages,
        });
        setResult(data);
        if (data.video_path) {
          const resolvedUrl = getVideoUrl(data.video_path);
          setVideoUrl(resolvedUrl);
        }
        setBackendConnected(true);
        setLoading(false);
      },
      (err) => {
        // Error occurred
        setError(err.message || 'An error occurred during video generation.');
        setLoading(false);
        checkBackendHealth().then((res) => setBackendConnected(Boolean(res)));
      }
    );
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

      {/* Video Studio Section */}
      <div className="glass-card">
        <VideoStudio
          topic={topic}
          setTopic={setTopic}
          quality={quality}
          setQuality={setQuality}
          targetDuration={targetDuration}
          setTargetDuration={setTargetDuration}
          voice={voice}
          setVoice={setVoice}
          language={language}
          setLanguage={setLanguage}
          voiceId={voiceId}
          setVoiceId={setVoiceId}
          character={character}
          setCharacter={setCharacter}
          characterPosition={characterPosition}
          setCharacterPosition={setCharacterPosition}
          visualStyle={visualStyle}
          setVisualStyle={setVisualStyle}
          loading={loading}
          onGenerateVisual={handleGenerateVisual}
          onGenerateFull={handleFullGenerate}
        />
        <ExampleTopics
          onSelect={handleSelectExample}
          disabled={loading}
        />
      </div>

      {/* Real-Time Generation Progress Pipeline */}
      {(loading || progressData) && (
        <GenerationStatus
          topic={topic}
          characterEnabled={character}
          progressData={progressData}
          error={error}
        />
      )}

      {/* Video Player */}
      <VideoPlayer
        videoUrl={videoUrl}
        topic={result?.topic}
        duration={result?.duration_seconds}
      />

      {/* Generation Metadata Details */}
      {result && (
        <GenerationDetails
          result={result}
          targetDuration={targetDuration}
          onFinalVideoComposed={(url) => setVideoUrl(url)}
        />
      )}

      <footer className="app-footer">
        <p>
          SmartCampus AI Video • Powered by <span>Qwen2.5 3B</span>, <span>Manim</span>, <span>IndicF5</span>, <span>faster-whisper</span>, & <span>FFmpeg</span>
        </p>
      </footer>
    </div>
  );
}
