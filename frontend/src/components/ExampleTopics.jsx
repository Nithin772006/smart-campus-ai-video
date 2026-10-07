import React from 'react';

const EXAMPLES = [
  "Explain Newton's Second Law",
  "How does photosynthesis work?",
  "Explain binary search",
  "Explain gradient descent",
  "Explain TCP three-way handshake",
  "Explain the OSI model",
  "Explain recursion",
  "Explain sorting algorithms",
];

export default function ExampleTopics({ onSelect, disabled }) {
  return (
    <div className="examples-container">
      <div className="examples-label">Example academic topics:</div>
      <div className="examples-list">
        {EXAMPLES.map((example, idx) => (
          <button
            key={idx}
            type="button"
            className="example-chip"
            onClick={() => onSelect(example)}
            disabled={disabled}
          >
            {example.replace(/^(Explain |How does )/i, '').replace(/ work\?$/i, '')}
          </button>
        ))}
      </div>
    </div>
  );
}
