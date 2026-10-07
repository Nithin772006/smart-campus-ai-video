import React from 'react';

export default function Header({ backendConnected }) {
  return (
    <header className="app-header">
      <div className="brand-badge">
        <span className="dot" style={{ background: backendConnected ? '#34d399' : '#f87171', boxShadow: backendConnected ? '0 0 8px #34d399' : '0 0 8px #f87171' }}></span>
        <span>{backendConnected ? 'Local Pipeline Online' : 'Backend Offline'}</span>
      </div>
      <h1 className="app-title">
        SmartCampus <span>AI Video</span>
      </h1>
      <p className="app-subtitle">
        Local AI-powered educational video generator. Converts academic topics into structured Manim animations via Qwen2.5 3B.
      </p>
    </header>
  );
}
