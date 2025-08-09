import React, { useState } from 'react';

const ChatInput = ({ onSendMessage, disabled, contextItems = [], onRemoveFromContext, onClearContext }) => {
  const [message, setMessage] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSendMessage(message.trim());
      setMessage('');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="chat-input-section">
      {contextItems.length > 0 && (
        <div className="context-preview">
          <div className="context-header">
            <span className="context-title">Context ({contextItems.length} test case{contextItems.length > 1 ? 's' : ''})</span>
            <button 
              onClick={onClearContext}
              className="clear-context-btn"
              type="button"
            >
              Clear All
            </button>
          </div>
          <div className="context-items">
            {contextItems.map((item) => (
              <div key={item.id} className="context-item">
                <span className="context-item-title">{item.testCase.title}</span>
                {item.generatedCode && <span className="context-has-code">📝</span>}
                <button 
                  onClick={() => onRemoveFromContext(item.id)}
                  className="remove-context-item-btn"
                  type="button"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
      
      <form onSubmit={handleSubmit} className="chat-input-form">
        <div className="chat-input-container">
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={contextItems.length > 0 
              ? "Ask a follow-up question about the test cases above..." 
              : "Describe what you want to test and include the URL (e.g., 'Test login form on https://example.com/login')"
            }
            disabled={disabled}
            className="chat-input"
            rows="3"
          />
          <button 
            type="submit" 
            disabled={disabled || !message.trim()}
            className="chat-send-btn"
          >
            {disabled ? 'Processing...' : 'Send'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default ChatInput;
