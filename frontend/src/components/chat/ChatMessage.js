import React from 'react';

const ChatMessage = ({ message }) => {
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
      </div>
      <div className="message-timestamp">
        {formatTimestamp(message.timestamp)}
      </div>
    </div>
  );
};

export default ChatMessage;
