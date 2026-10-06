import React from 'react';

export default function VideoPlayer({ src }) {
  return (
    <div style={{ background: '#111', borderRadius: '8px', padding: '1rem', color: '#fff' }}>
      {src ? (
        <video controls src={src} style={{ width: '100%', borderRadius: '4px' }} />
      ) : (
        <div style={{ height: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#888' }}>
          Video preview will appear here
        </div>
      )}
    </div>
  );
}
