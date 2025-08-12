import React, { useState } from 'react';

const ExecutionResultsDisplay = ({ executionResults }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!executionResults || executionResults.length === 0) {
    return null;
  }

  const result = executionResults[0]; // Take the first result for now

  return (
    <div className="execution-results-display">
      <div className="results-header">
        <h4>▶️ Test Execution Results</h4>
        <button 
          onClick={() => setIsExpanded(!isExpanded)}
          className="expand-results-btn"
        >
          {isExpanded ? '▼' : '▶'}
        </button>
      </div>
      
      <div className="results-summary">
        <span className={`status-badge ${result.status}`}>
          {result.status.toUpperCase()}
        </span>
        <span className="execution-time">
          {result.execution_time}s
        </span>
      </div>
      
      {isExpanded && (
        <div className="results-details">
          {result.title && (
            <div className="result-field">
              <strong>Test:</strong> {result.title}
            </div>
          )}
          
          {result.output && (
            <div className="result-field">
              <strong>Output:</strong>
              <pre className="test-output">{result.output}</pre>
            </div>
          )}
          
          {result.error && (
            <div className="result-field">
              <strong>Error:</strong>
              <pre className="test-error">{result.error}</pre>
            </div>
          )}
          
          {result.gpt_analysis && (
            <div className="gpt-analysis-section">
              <h5>🤖 AI Analysis</h5>
              
              {result.gpt_analysis.error ? (
                <div className="analysis-error">
                  <strong>Analysis Error:</strong> {result.gpt_analysis.error}
                </div>
              ) : (
                <>
                  {result.gpt_analysis.explanation && (
                    <div className="analysis-field">
                      <strong>Explanation:</strong>
                      <p>{result.gpt_analysis.explanation}</p>
                    </div>
                  )}
                  
                  {result.gpt_analysis.suggestions && result.gpt_analysis.suggestions.length > 0 && (
                    <div className="analysis-field">
                      <strong>Suggestions:</strong>
                      <ul>
                        {result.gpt_analysis.suggestions.map((suggestion, idx) => (
                          <li key={idx}>{suggestion}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  
                  {result.gpt_analysis.fix_priority && (
                    <div className="analysis-field">
                      <strong>Priority:</strong>
                      <span className={`priority-${result.gpt_analysis.fix_priority}`}>
                        {result.gpt_analysis.fix_priority.toUpperCase()}
                      </span>
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ExecutionResultsDisplay; 