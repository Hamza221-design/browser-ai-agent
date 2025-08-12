import React from 'react';

const SessionInfo = ({ sessionState }) => {
  if (!sessionState) {
    return null;
  }

  const formatTime = (timestamp) => {
    if (!timestamp) return 'N/A';
    return new Date(timestamp).toLocaleString();
  };

  return (
    <div className="session-info">
      <h3>Session Information</h3>
      <div className="session-details">
        <div className="session-row">
          <span className="session-label">Session ID:</span>
          <span className="session-value">{sessionState.session_id}</span>
        </div>
        
        {sessionState.current_url && (
          <div className="session-row">
            <span className="session-label">Current URL:</span>
            <span className="session-value">
              <a href={sessionState.current_url} target="_blank" rel="noopener noreferrer">
                {sessionState.current_url}
              </a>
            </span>
          </div>
        )}
        
        <div className="session-row">
          <span className="session-label">Test Cases:</span>
          <span className="session-value">{sessionState.test_cases_count}</span>
        </div>
        
        <div className="session-row">
          <span className="session-label">Generated Code:</span>
          <span className={`session-value ${sessionState.has_generated_code ? 'success' : 'none'}`}>
            {sessionState.has_generated_code ? 'Yes' : 'No'}
          </span>
        </div>
        
        <div className="session-row">
          <span className="session-label">Execution Results:</span>
          <span className={`session-value ${sessionState.has_execution_results ? 'success' : 'none'}`}>
            {sessionState.has_execution_results ? 'Available' : 'None'}
          </span>
        </div>
        
        {sessionState.last_action && (
          <div className="session-row">
            <span className="session-label">Last Action:</span>
            <span className="session-value">{sessionState.last_action}</span>
          </div>
        )}
        
        {sessionState.context && (
          <div className="session-row">
            <span className="session-label">Context:</span>
            <span className="session-value">{sessionState.context}</span>
          </div>
        )}
        
        <div className="session-row">
          <span className="session-label">Messages:</span>
          <span className="session-value">{sessionState.message_count}</span>
        </div>
        
        <div className="session-row">
          <span className="session-label">Created:</span>
          <span className="session-value">{formatTime(sessionState.created_at)}</span>
        </div>
        
        <div className="session-row">
          <span className="session-label">Last Active:</span>
          <span className="session-value">{formatTime(sessionState.last_active)}</span>
        </div>
      </div>
    </div>
  );
};

export default SessionInfo; 