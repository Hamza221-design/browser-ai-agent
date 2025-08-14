import React from 'react';

const ChatMessage = ({ message }) => {
  const { role, content, timestamp, type } = message;

  const getMessageIcon = () => {
    switch (type) {
      case 'status':
        return '🔄';
      case 'test_result':
        return '🧪';
      case 'analysis':
        return '🔍';
      case 'code_update':
        return '💻';
      case 'success':
        return '✅';
      case 'final_failure':
        return '❌';
      case 'error':
        return '⚠️';
      default:
        return role === 'user' ? '👤' : '🤖';
    }
  };

  const getMessageClass = () => {
    const baseClass = 'chat-message';
    const roleClass = `chat-message-${role}`;
    const typeClass = type ? `chat-message-${type}` : '';
    return `${baseClass} ${roleClass} ${typeClass}`.trim();
  };

  return (
    <div className={getMessageClass()}>
      <div className="message-header">
        <span className="message-icon">{getMessageIcon()}</span>
        <span className="message-role">
          {role === 'user' ? 'You' : 'AI Assistant'}
        </span>
        {timestamp && (
          <span className="message-time">
            {new Date(timestamp).toLocaleTimeString()}
          </span>
        )}
      </div>
      <div className="message-content">
        {content}
      </div>
    </div>
  );
};

export default ChatMessage; 