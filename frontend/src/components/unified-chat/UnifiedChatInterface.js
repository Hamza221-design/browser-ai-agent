import React, { useState, useRef, useEffect } from 'react';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import ActionResults from './ActionResults';
import SessionInfo from './SessionInfo';
import { sendChatMessage } from '../../services/unifiedChatService';

const UnifiedChatInterface = () => {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionState, setSessionState] = useState(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (message) => {
    if (!message.trim()) return;

    // Add user message to chat
    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: message,
      timestamp: new Date(),
      type: 'message'
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await sendChatMessage(message);
      
      // Add assistant response to chat
      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: response.user_response,
        timestamp: new Date(),
        type: 'message',
        actionResults: response.action_results,
        sessionState: response.session_state
      };

      setMessages(prev => [...prev, assistantMessage]);
      setSessionState(response.session_state);

    } catch (error) {
      console.error('Error sending message:', error);
      
      // Add error message
      const errorMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date(),
        type: 'error'
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const clearChat = () => {
    setMessages([]);
    setSessionState(null);
  };

  return (
    <div className="unified-chat-interface">
      <div className="chat-container">
        <div className="chat-header">
          <h2>AI Testing Assistant</h2>
          <button onClick={clearChat} className="clear-chat-btn">
            Clear Chat
          </button>
        </div>

        <div className="chat-messages">
          {messages.length === 0 && (
            <div className="welcome-message">
              <h3>Welcome to AI Testing Assistant! 🤖</h3>
              <p>You can ask me to:</p>
              <ul>
                <li>Analyze websites and create test cases</li>
                <li>Generate Playwright test code</li>
                <li>Execute tests and show results</li>
                <li>Analyze test failures and suggest fixes</li>
                <li>Modify existing tests</li>
              </ul>
              <p>Try saying: "Analyze https://example.com and create login tests"</p>
            </div>
          )}

          {messages.map((message) => (
            <div key={message.id} className="message-container">
              <ChatMessage message={message} />
              {message.actionResults && message.actionResults.length > 0 && (
                <ActionResults results={message.actionResults} />
              )}
            </div>
          ))}

          {isLoading && (
            <div className="loading-message">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
              <p>AI is thinking...</p>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <ChatInput onSendMessage={handleSendMessage} isLoading={isLoading} />
      </div>

      {sessionState && (
        <SessionInfo sessionState={sessionState} />
      )}
    </div>
  );
};

export default UnifiedChatInterface; 