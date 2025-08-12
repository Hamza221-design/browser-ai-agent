import React, { useState } from 'react';

const GeneratedCodeDisplay = ({ generatedCode }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!generatedCode) {
    return null;
  }

  return (
    <div className="generated-code-display">
      <div className="code-header">
        <h4>💻 Generated Test Code</h4>
        <button 
          onClick={() => setIsExpanded(!isExpanded)}
          className="expand-code-btn"
        >
          {isExpanded ? '▼' : '▶'}
        </button>
      </div>
      
      {isExpanded && (
        <div className="code-content">
          <div className="code-info">
            <strong>Filename:</strong> {generatedCode.filename || 'test_generated.py'}
            <br />
            <strong>Status:</strong> 
            <span className={`status-${generatedCode.status}`}>
              {generatedCode.status}
            </span>
          </div>
          
          {generatedCode.test_code && (
            <div className="code-block">
              <div className="code-header-bar">
                <span>Python Test Code</span>
                <button 
                  onClick={() => navigator.clipboard.writeText(generatedCode.test_code)}
                  className="copy-code-btn"
                  title="Copy to clipboard"
                >
                  📋 Copy
                </button>
              </div>
              <pre className="code-snippet">
                <code>{generatedCode.test_code}</code>
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default GeneratedCodeDisplay; 