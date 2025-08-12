import React, { useState } from 'react';

const TestCasesDisplay = ({ testCases }) => {
  const [expandedCases, setExpandedCases] = useState({});

  const toggleCase = (index) => {
    setExpandedCases(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  if (!testCases || testCases.length === 0) {
    return null;
  }

  return (
    <div className="test-cases-display">
      <h4>🧪 Generated Test Cases ({testCases.length})</h4>
      <div className="test-cases-list">
        {testCases.map((testCase, index) => (
          <div key={index} className="test-case-item">
            <div 
              className="test-case-header"
              onClick={() => toggleCase(index)}
            >
              <span className="test-case-title">
                {testCase.title || `Test Case ${index + 1}`}
              </span>
              <span className="test-case-type">
                {testCase.test_type || 'functional'}
              </span>
              <span className="test-case-toggle">
                {expandedCases[index] ? '▼' : '▶'}
              </span>
            </div>
            
            {expandedCases[index] && (
              <div className="test-case-details">
                {testCase.description && (
                  <div className="test-case-field">
                    <strong>Description:</strong>
                    <p>{testCase.description}</p>
                  </div>
                )}
                
                {testCase.expected_behavior && (
                  <div className="test-case-field">
                    <strong>Expected Behavior:</strong>
                    <p>{testCase.expected_behavior}</p>
                  </div>
                )}
                
                {testCase.test_steps && testCase.test_steps.length > 0 && (
                  <div className="test-case-field">
                    <strong>Test Steps:</strong>
                    <ol>
                      {testCase.test_steps.map((step, stepIndex) => (
                        <li key={stepIndex}>{step}</li>
                      ))}
                    </ol>
                  </div>
                )}
                
                {testCase.element_type && (
                  <div className="test-case-field">
                    <strong>Element Type:</strong>
                    <span>{testCase.element_type}</span>
                  </div>
                )}
                
                {testCase.html_code && (
                  <div className="test-case-field">
                    <strong>HTML Code:</strong>
                    <pre className="html-code">
                      {testCase.html_code}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default TestCasesDisplay; 