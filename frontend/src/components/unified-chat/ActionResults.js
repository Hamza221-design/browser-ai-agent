import React, { useState } from 'react';
import TestCasesDisplay from './TestCasesDisplay';
import GeneratedCodeDisplay from './GeneratedCodeDisplay';
import ExecutionResultsDisplay from './ExecutionResultsDisplay';

const ActionResults = ({ results, actions }) => {
  const [expandedActions, setExpandedActions] = useState({});
  const [showCode, setShowCode] = useState({});

  const toggleAction = (index) => {
    setExpandedActions(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  const toggleCode = (index) => {
    setShowCode(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  // Helper function to get test code from actions
  const getTestCodeFromActions = (index) => {
    if (actions && actions[index] && actions[index].parameters) {
      return actions[index].parameters.python_code;
    }
    return null;
  };

  // Helper function to add line numbers to code
  const addLineNumbers = (code) => {
    if (!code) return '';
    const lines = code.split('\n');
    return lines.map((line, index) => 
      `${(index + 1).toString().padStart(2, ' ')} ${line}`
    ).join('\n');
  };

  const getActionIcon = (result) => {
    // Determine action type based on result content
    if (result.test_name) return '🧪';
    if (result.url) return '🔗';
    if (result.test_cases_generated) return '🧪';
    if (result.code_generated) return '💻';
    if (result.execution_completed) return '▶️';
    if (result.analysis_completed) return '🔍';
    if (result.embeddings_created) return '📊';
    if (result.session_cleared) return '🗑️';
    if (result.action) {
      const icons = {
        'extract_url': '🔗',
        'create_embeddings': '📊',
        'generate_test_cases': '🧪',
        'generate_test_code': '💻',
        'execute_test': '▶️',
        'execute_tests': '▶️',
        'analyze_failure': '🔍',
        'modify_test': '✏️',
        'show_results': '📋',
        'clear_session': '🗑️',
        'no_action': '💭'
      };
      return icons[result.action] || '⚡';
    }
    return '⚡';
  };

  const getActionName = (result) => {
    // Determine action name based on result content
    if (result.test_name) return result.test_name;
    if (result.url) return 'URL Extraction';
    if (result.test_cases_generated) return 'Test Case Generation';
    if (result.code_generated) return 'Code Generation';
    if (result.execution_completed) return 'Test Execution';
    if (result.analysis_completed) return 'Failure Analysis';
    if (result.embeddings_created) return 'Creating Embeddings';
    if (result.session_cleared) return 'Session Clear';
    if (result.action) {
      const names = {
        'extract_url': 'URL Extraction',
        'create_embeddings': 'Creating Embeddings',
        'generate_test_cases': 'Test Case Generation',
        'generate_test_code': 'Code Generation',
        'execute_test': 'Test Execution',
        'execute_tests': 'Test Execution',
        'analyze_failure': 'Failure Analysis',
        'modify_test': 'Test Modification',
        'show_results': 'Showing Results',
        'clear_session': 'Session Clear',
        'no_action': 'No Action Required'
      };
      return names[result.action] || result.action;
    }
    return 'Action Completed';
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'success':
        return 'success';
      case 'error':
        return 'error';
      case 'no_action_needed':
        return 'info';
      default:
        return 'warning';
    }
  };

  if (!results || results.length === 0) {
    return null;
  }



  return (
    <div className="action-results">
      <h4>Actions Taken:</h4>
      <div className="actions-list">
        {results.map((result, index) => (
          <div key={index} className={`action-item ${getStatusColor(result.status)}`}>
            <div 
              className="action-header"
              onClick={() => toggleAction(index)}
            >
              <span className="action-icon">
                {getActionIcon(result)}
              </span>
              <span className="action-name">
                {getActionName(result)}
              </span>
              <span className={`action-status ${getStatusColor(result.status)}`}>
                {result.status === 'success' && result.test_name ? '✅ PASSED' : result.status}
              </span>
              <span className="action-toggle">
                {expandedActions[index] ? '▼' : '▶'}
              </span>
            </div>
            
            {expandedActions[index] && (
              <div className="action-details">
                {result.error && (
                  <div className="action-error">
                    <strong>Error:</strong> {result.error}
                  </div>
                )}
                
                {/* Test execution summary for test results */}
                {result.test_name && (
                  <div className="test-execution-summary success">
                    <span className="test-icon">🧪</span>
                    <div className="test-summary-info">
                      <div className="test-name">{result.test_name}</div>
                      <div className="test-stats">
                        {result.execution_time && <span>⏱️ {result.execution_time}s</span>}
                        {result.attempts && <span>🔄 {result.attempts} attempts</span>}
                        {result.auto_fixed && <span>🔧 Auto-fixed</span>}
                      </div>
                    </div>
                  </div>
                )}
                
                {result.url && (
                  <div className="action-detail">
                    <strong>URL:</strong> {result.url}
                  </div>
                )}
                
                {result.test_name && (
                  <div className="action-detail">
                    <strong>Test Name:</strong> {result.test_name}
                  </div>
                )}
                
                {result.execution_time && (
                  <div className="action-detail">
                    <strong>Execution Time:</strong> {result.execution_time}s
                  </div>
                )}
                
                {result.attempts && (
                  <div className="action-detail">
                    <strong>Attempts:</strong> {result.attempts} {result.auto_fixed && '(Auto-fixed)'}
                  </div>
                )}
                
                {result.message && (
                  <div className="action-detail success-message">
                    <strong>✅ Result:</strong> {result.message}
                  </div>
                )}
                
                {result.output && (
                  <div className="action-detail">
                    <strong>Output:</strong>
                    <pre className="test-output">{result.output}</pre>
                  </div>
                )}
                
                {result.embeddings_created && (
                  <div className="action-detail">
                    <strong>Embeddings:</strong> Created successfully
                  </div>
                )}
                
                {result.session_cleared && (
                  <div className="action-detail">
                    <strong>Session:</strong> Cleared successfully
                  </div>
                )}
                
                {/* Display test cases if available */}
                {result.test_cases && (
                  <TestCasesDisplay testCases={result.test_cases} />
                )}
                
                {/* Display generated code if available */}
                {result.generated_code && (
                  <GeneratedCodeDisplay generatedCode={result.generated_code} />
                )}
                

                
                {/* Display test code from action parameters if available */}
                {(result.python_code || getTestCodeFromActions(index) || result.test_code) && (
                  <div className="action-detail">
                    <div className="code-toggle-header">
                      <strong>Test Code:</strong>
                      <div className="code-toggle-buttons">
                        <button 
                          onClick={() => toggleCode(index)}
                          className="toggle-code-btn"
                          title={showCode[index] ? "Hide code" : "Show code"}
                        >
                          {showCode[index] ? '👁️ Hide Code' : '👁️ Show Code'}
                        </button>
                        <button 
                          onClick={() => navigator.clipboard.writeText(result.python_code || getTestCodeFromActions(index) || result.test_code || '')}
                          className="copy-code-btn"
                          title="Copy to clipboard"
                        >
                          📋 Copy
                        </button>
                      </div>
                    </div>
                    {showCode[index] && (
                      <div className="code-block">
                        <div className="code-header-bar">
                          <span>Python Test Code</span>
                          <span className="code-info">Click to copy</span>
                        </div>
                        <pre className="code-snippet">
                          <code>{addLineNumbers(result.python_code || getTestCodeFromActions(index) || result.test_code || '')}</code>
                        </pre>
                      </div>
                    )}
                  </div>
                )}
                
                {/* Display execution results if available */}
                {result.execution_results && (
                  <ExecutionResultsDisplay executionResults={result.execution_results} />
                )}
                
                {/* Display other details */}
                {Object.keys(result).filter(key => 
                  !['status', 'action', 'error', 'test_cases', 'generated_code', 'execution_results', 'test_name', 'execution_time', 'attempts', 'message', 'output', 'url'].includes(key)
                ).map(key => (
                  <div key={key} className="action-detail">
                    <strong>{key.replace(/_/g, ' ').toUpperCase()}:</strong> {String(result[key])}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default ActionResults; 