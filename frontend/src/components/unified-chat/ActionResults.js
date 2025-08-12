import React, { useState } from 'react';

const ActionResults = ({ results }) => {
  const [expandedActions, setExpandedActions] = useState({});

  const toggleAction = (index) => {
    setExpandedActions(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  const getActionIcon = (action) => {
    const icons = {
      'extract_url': '🔗',
      'create_embeddings': '📊',
      'generate_test_cases': '🧪',
      'generate_test_code': '💻',
      'execute_tests': '▶️',
      'analyze_failure': '🔍',
      'modify_test': '✏️',
      'show_results': '📋',
      'clear_session': '🗑️',
      'no_action': '💭'
    };
    return icons[action] || '⚡';
  };

  const getActionName = (action) => {
    const names = {
      'extract_url': 'URL Extraction',
      'create_embeddings': 'Creating Embeddings',
      'generate_test_cases': 'Test Case Generation',
      'generate_test_code': 'Code Generation',
      'execute_tests': 'Test Execution',
      'analyze_failure': 'Failure Analysis',
      'modify_test': 'Test Modification',
      'show_results': 'Showing Results',
      'clear_session': 'Session Clear',
      'no_action': 'No Action Required'
    };
    return names[action] || action;
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
                {getActionIcon(result.action || 'unknown')}
              </span>
              <span className="action-name">
                {getActionName(result.action || 'unknown')}
              </span>
              <span className={`action-status ${getStatusColor(result.status)}`}>
                {result.status}
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
                
                {result.url && (
                  <div className="action-detail">
                    <strong>URL:</strong> {result.url}
                  </div>
                )}
                
                {result.embeddings_created && (
                  <div className="action-detail">
                    <strong>Embeddings:</strong> Created successfully
                  </div>
                )}
                
                {result.test_cases_generated && (
                  <div className="action-detail">
                    <strong>Test Cases:</strong> {result.test_cases_generated} generated
                  </div>
                )}
                
                {result.code_generated && (
                  <div className="action-detail">
                    <strong>Code:</strong> Generated successfully
                  </div>
                )}
                
                {result.execution_completed && (
                  <div className="action-detail">
                    <strong>Execution:</strong> Completed
                  </div>
                )}
                
                {result.analysis_completed && (
                  <div className="action-detail">
                    <strong>Analysis:</strong> Completed
                  </div>
                )}
                
                {result.session_cleared && (
                  <div className="action-detail">
                    <strong>Session:</strong> Cleared successfully
                  </div>
                )}
                
                {Object.keys(result).filter(key => 
                  !['status', 'action', 'error'].includes(key)
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