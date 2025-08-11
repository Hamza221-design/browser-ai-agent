import React, { useEffect, useRef } from 'react';
import ChatMessage from './ChatMessage';
import TestCasesList from './TestCasesList';

const ChatMessages = ({ 
  messages, 
  loading, 
  testCases,
  onGenerateCode,
  onGenerateAllCodes,
  currentUrl,
  onEditTestCase,
  onRemoveTestCase,
  onAddToContext
}) => {
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  return (
    <div className="chat-messages">
      {messages.length === 0 && (
        <div className="chat-welcome">
          <h3>Welcome to AI Test Generator</h3>
          <p>Describe what you want to test and provide a URL. For example:</p>
          <ul>
            <li>"Test login form on https://example.com/login"</li>
            <li>"Check form validation on https://example.com/signup"</li>
            <li>"Test navigation links on https://example.com"</li>
          </ul>
        </div>
      )}
      
      {messages.map((message) => (
        <ChatMessage 
          key={message.id} 
          message={message}
          testCases={message.data?.test_cases || []}
          currentUrl={message.data?.url || currentUrl}
          onGenerateCode={onGenerateCode}
          onGenerateAllCodes={onGenerateAllCodes}
          onEditTestCase={onEditTestCase}
          onRemoveTestCase={onRemoveTestCase}
          onAddToContext={onAddToContext}
        />
      ))}
      
      {loading && (
        <div className="chat-message ai-message">
          <div className="message-content">
            <div className="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <p>Analyzing your request...</p>
          </div>
        </div>
      )}
      
      <div ref={messagesEndRef} />
    </div>
  );
};

export default ChatMessages;
