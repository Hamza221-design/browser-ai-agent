import React, { useState, useRef, useEffect } from 'react';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import ActionResults from './ActionResults';

const StreamingChatInterface = () => {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [streamingData, setStreamingData] = useState(null);
  const [websocket, setWebsocket] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingData]);

  useEffect(() => {
    // Initialize WebSocket connection
    const ws = new WebSocket('ws://localhost:8000/ws/chat');
    
    ws.onopen = () => {
      console.log('WebSocket connected');
      setConnectionStatus('connected');
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('Received WebSocket message:', data);
      
      if (data.type === 'connection') {
        console.log('WebSocket connected successfully');
        return;
      }
      
      handleStreamingUpdate(data);
    };
    
    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setConnectionStatus('disconnected');
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setConnectionStatus('error');
    };
    
    setWebsocket(ws);
    
    return () => {
      ws.close();
    };
  }, []);

  const handleStreamingUpdate = (data) => {
    const { type, step, data: updateData, timestamp, context } = data;
    
    setStreamingData(prev => ({
      ...prev,
      [step]: { type, data: updateData, timestamp, context }
    }));
    
    // Handle different update types
    switch (type) {
      case 'status':
        handleStatusUpdate(step, updateData, context);
        break;
      case 'test_result':
        handleTestResultUpdate(step, updateData, context);
        break;
      case 'analysis':
        handleAnalysisUpdate(step, updateData, context);
        break;
      case 'code_update':
        handleCodeUpdate(step, updateData, context);
        break;
      case 'analysis_complete':
        handleAnalysisCompleteUpdate(step, updateData, context);
        break;
      case 'success':
        handleSuccessUpdate(step, updateData, context);
        break;
      case 'final_failure':
        handleFinalFailureUpdate(step, updateData, context);
        break;
      case 'final_response':
        handleFinalResponse(step, updateData, context);
        break;
      default:
        console.log('Unknown update type:', type, updateData);
    }
  };

  const handleStatusUpdate = (step, data, context) => {
    const message = {
      id: Date.now(),
      role: 'assistant',
      content: data.message,
      timestamp: new Date(),
      type: 'status',
      step: step,
      context: context
    };
    
    setMessages(prev => [...prev, message]);
  };

  const handleTestResultUpdate = (step, data, context) => {
    const statusIcon = data.status === 'success' ? '✅' : '❌';
    const message = {
      id: Date.now(),
      role: 'assistant',
      content: `${statusIcon} Test attempt ${data.attempt} ${data.status} (${data.execution_time}s)`,
      timestamp: new Date(),
      type: 'test_result',
      step: step,
      testData: data,
      context: context
    };
    
    setMessages(prev => [...prev, message]);
  };

  const handleAnalysisUpdate = (step, data, context) => {
    const message = {
      id: Date.now(),
      role: 'assistant',
      content: `🔍 ${data.message}`,
      timestamp: new Date(),
      type: 'analysis',
      step: step,
      analysisData: data,
      context: context
    };
    
    setMessages(prev => [...prev, message]);
  };

  const handleCodeUpdate = (step, data, context) => {
    const message = {
      id: Date.now(),
      role: 'assistant',
      content: `💻 ${data.message}`,
      timestamp: new Date(),
      type: 'code_update',
      step: step,
      codeData: data,
      context: context
    };
    
    setMessages(prev => [...prev, message]);
  };

  const handleAnalysisCompleteUpdate = (step, data, context) => {
    const message = {
      id: Date.now(),
      role: 'assistant',
      content: `✅ ${data.message} (${data.gpt_model_used})`,
      timestamp: new Date(),
      type: 'analysis_complete',
      step: step,
      analysisCompleteData: data,
      context: context
    };
    
    setMessages(prev => [...prev, message]);
  };

  const handleSuccessUpdate = (step, data, context) => {
    const message = {
      id: Date.now(),
      role: 'assistant',
      content: data.message,
      timestamp: new Date(),
      type: 'success',
      step: step,
      successData: data,
      context: context
    };
    
    setMessages(prev => [...prev, message]);
    setIsLoading(false);
  };

  const handleFinalFailureUpdate = (step, data, context) => {
    const message = {
      id: Date.now(),
      role: 'assistant',
      content: data.message,
      timestamp: new Date(),
      type: 'final_failure',
      step: step,
      failureData: data,
      context: context
    };
    
    setMessages(prev => [...prev, message]);
    setIsLoading(false);
  };

  const handleFinalResponse = (step, data, context) => {
    const message = {
      id: Date.now(),
      role: 'assistant',
      content: data.user_response,
      timestamp: new Date(),
      type: 'final_response',
      step: step,
      actionResults: data.action_results,
      actions: data.actions,
      context: context
    };
    
    setMessages(prev => [...prev, message]);
    setIsLoading(false);
  };

  const handleSendMessage = async (message) => {
    if (!message.trim() || !websocket) return;

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
    setStreamingData({}); // Reset streaming data

    try {
      // Send message via WebSocket
      websocket.send(JSON.stringify({
        type: 'chat',
        message: message
      }));
    } catch (error) {
      console.error('Error sending message:', error);
      
      const errorMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date(),
        type: 'error'
      };

      setMessages(prev => [...prev, errorMessage]);
      setIsLoading(false);
    }
  };

  const clearChat = () => {
    setMessages([]);
    setStreamingData(null);
  };

  const renderStreamingProgress = () => {
    if (!streamingData || Object.keys(streamingData).length === 0) return null;

    const steps = Object.keys(streamingData).sort();
    
    return (
      <div className="streaming-progress">
        <h4>🔄 Execution Progress</h4>
        <div className="progress-steps">
          {steps.map((step, index) => {
            const stepData = streamingData[step];
            const isActive = index === steps.length - 1;
            
            return (
              <div key={step} className={`progress-step ${isActive ? 'active' : 'completed'}`}>
                <div className="step-indicator">
                  {isActive ? '⏳' : '✅'}
                </div>
                <div className="step-content">
                  <div className="step-title">{stepData.data.message}</div>
                  <div className="step-time">
                    {new Date(stepData.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className="streaming-chat-interface">
      <div className="chat-container">
        <div className="chat-header">
          <h2>AI Testing Assistant (Streaming)</h2>
          <div className="header-controls">
            <div className={`connection-status ${connectionStatus}`}>
              {connectionStatus === 'connected' ? '🟢 Connected' : 
               connectionStatus === 'error' ? '🔴 Error' : '🟡 Connecting...'}
            </div>
            <button onClick={clearChat} className="clear-chat-btn">
              Clear Chat
            </button>
          </div>
        </div>

        <div className="chat-messages">
          {messages.length === 0 && (
            <div className="welcome-message">
              <h3>Welcome to AI Testing Assistant! 🤖</h3>
              <p>This is the streaming version that shows real-time updates during test execution.</p>
              <p>You can ask me to:</p>
              <ul>
                <li>Analyze websites and create test cases</li>
                <li>Generate Playwright test code</li>
                <li>Execute tests with real-time progress</li>
                <li>See test analysis and fixes in real-time</li>
              </ul>
              <p>Try saying: "Test login functionality for https://example.com"</p>
            </div>
          )}

          {messages.map((message) => (
            <div key={message.id} className="message-container">
              <ChatMessage message={message} />
              
              {/* Show detailed context information */}
              {message.context && (
                <div className="message-context">
                  {message.context.test_code && (
                    <div className="context-section">
                      <h5>Test Code Used:</h5>
                      <pre className="code-snippet small">
                        <code>{message.context.test_code.substring(0, 200)}...</code>
                      </pre>
                    </div>
                  )}
                  
                  {message.context.actions_performed && (
                    <div className="context-section">
                      <h5>Actions Performed:</h5>
                      <ul>
                        {message.context.actions_performed.map((action, index) => (
                          <li key={index}>
                            <strong>{action.action}</strong> - {action.status || 'executed'}
                            {action.execution_time && ` (${action.execution_time}s)`}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  
                  {message.context.gpt_generated_code && (
                    <div className="context-section">
                      <h5>GPT Analysis & Code Generation:</h5>
                      <div className="gpt-analysis">
                        <p><strong>Analysis Summary:</strong> {message.context.gpt_generated_code.analysis_summary}</p>
                        <div className="improvements">
                          <strong>Improvements Made:</strong>
                          <ul>
                            {message.context.gpt_generated_code.changes_made.map((change, index) => (
                              <li key={index}>{change}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    </div>
                  )}
                  
                  {message.context.gpt_analysis_results && (
                    <div className="context-section">
                      <h5>GPT Analysis Results:</h5>
                      <div className="analysis-results">
                        <p><strong>Model:</strong> {message.context.gpt_analysis_results.model_used}</p>
                        <p><strong>Duration:</strong> {message.context.gpt_analysis_results.analysis_duration}</p>
                        <p><strong>Confidence:</strong> {message.context.gpt_analysis_results.confidence_score}</p>
                        <div className="issues-identified">
                          <strong>Issues Identified:</strong>
                          <ul>
                            {message.context.gpt_analysis_results.issues_identified.map((issue, index) => (
                              <li key={index}>{issue}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    </div>
                  )}
                  
                  {message.context.test_execution_summary && (
                    <div className="context-section">
                      <h5>Test Execution Summary:</h5>
                      <div className="execution-summary">
                        <p><strong>Total Attempts:</strong> {message.context.test_execution_summary.total_attempts}</p>
                        <p><strong>Auto-fixed:</strong> {message.context.test_execution_summary.auto_fixed ? 'Yes' : 'No'}</p>
                        <p><strong>Total Time:</strong> {message.context.test_execution_summary.total_execution_time}s</p>
                        <p><strong>Test Name:</strong> {message.context.test_execution_summary.test_name}</p>
                        <p><strong>URL:</strong> {message.context.test_execution_summary.url}</p>
                      </div>
                    </div>
                  )}
                </div>
              )}
              
              {message.actionResults && message.actionResults.length > 0 && (
                <ActionResults results={message.actionResults} actions={message.actions} />
              )}
              
              {message.codeData && (
                <div className="code-update">
                  <h4>Updated Test Code:</h4>
                  <pre className="code-snippet">
                    <code>{message.codeData.new_code}</code>
                  </pre>
                </div>
              )}
            </div>
          ))}

          {renderStreamingProgress()}

          {isLoading && (
            <div className="loading-message">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
              <p>Processing your request...</p>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <ChatInput onSendMessage={handleSendMessage} isLoading={isLoading} />
      </div>
    </div>
  );
};

export default StreamingChatInterface; 