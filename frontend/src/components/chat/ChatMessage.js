import React from 'react';
import TestCasesList from './TestCasesList';

const ChatMessage = ({ 
  message, 
  testCases = [], 
  currentUrl,
  onGenerateCode,
  onGenerateAllCodes,
  onEditTestCase,
  onRemoveTestCase,
  onAddToContext
}) => {
  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  return (
    <div className={`chat-message ${message.type}-message ${message.isError ? 'error' : ''}`}>
      <div className="message-content">
        <p>{message.content}</p>
        {message.hasContext && (
          <div className="message-context-info">
            <small>📎 Sent with {message.contextCount} test case{message.contextCount > 1 ? 's' : ''} as context</small>
          </div>
        )}
        {message.data && message.data.test_cases && (
          <div className="message-summary">
            <small>
              Generated {message.data.total_cases} test cases for {message.data.url}
            </small>
          </div>
        )}
        
        {/* Display test cases if they exist in this message */}
        {testCases.length > 0 && (
          <TestCasesList 
            testCases={testCases}
            onGenerateCode={onGenerateCode}
            onGenerateAllCodes={onGenerateAllCodes}
            currentUrl={currentUrl}
            onEditTestCase={onEditTestCase}
            onRemoveTestCase={onRemoveTestCase}
            onAddToContext={onAddToContext}
          />
        )}
      </div>
      <div className="message-timestamp">
        {formatTimestamp(message.timestamp)}
      </div>
    </div>
  );
};

export default ChatMessage;
