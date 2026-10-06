import React, { useState } from 'react';
import VideoPlayer from '../components/VideoPlayer';

export default function App() {
  const [topic, setTopic] = useState('');
  const [loading, setLoading] = useState(false);

  return (
    <div style={{ fontFamily: 'Inter, sans-serif', padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
      <h1>SmartCampus AI Video Generator</h1>
      <p>Generate educational videos with LTX-Video, IndicF5 TTS, and Manim animations.</p>
      
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
        <input 
          type="text" 
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="Enter educational topic..."
          style={{ flex: 1, padding: '0.75rem', borderRadius: '4px', border: '1px solid #ccc' }}
        />
        <button 
          disabled={loading}
          style={{ padding: '0.75rem 1.5rem', background: '#0284c7', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
        >
          {loading ? 'Synthesizing...' : 'Generate Video'}
        </button>
      </div>

      <VideoPlayer src="" />
    </div>
  );
}
