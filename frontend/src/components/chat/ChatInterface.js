import React, { useState } from 'react';
import ChatInput from './ChatInput';
import ChatMessages from './ChatMessages';
import TestCasesList from './TestCasesList';
import apiService from '../../services/apiService';

const ChatInterface = () => {
  const [messages, setMessages] = useState([]);
  const [testCases, setTestCases] = useState([]);
  const [currentUrl, setCurrentUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [contextItems, setContextItems] = useState([]);

  const handleSendMessage = async (message) => {
    // Build the complete message with context
    let completeMessage = message;
    if (contextItems.length > 0) {
      completeMessage = `${message}\n\n--- Context ---\n`;
      contextItems.forEach((item, index) => {
        completeMessage += `\nTest Case ${index + 1}:\n`;
        completeMessage += `Title: ${item.testCase.title}\n`;
        completeMessage += `Description: ${item.testCase.description}\n`;
        completeMessage += `Test Type: ${item.testCase.test_type}\n`;
        completeMessage += `Element Type: ${item.testCase.element_type}\n`;
        if (item.testCase.test_steps && item.testCase.test_steps.length > 0) {
          completeMessage += `Steps:\n${item.testCase.test_steps.map((step, i) => `${i + 1}. ${step}`).join('\n')}\n`;
        }
        completeMessage += `Expected Behavior: ${item.testCase.expected_behavior}\n`;
        
        if (item.generatedCode) {
          completeMessage += `\nGenerated Code:\n\`\`\`python\n${item.generatedCode.test_code}\n\`\`\`\n`;
        }
        completeMessage += '\n---\n';
      });
    }

    // Add user message (show original message, not the one with context)
    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: message,
      timestamp: new Date(),
      hasContext: contextItems.length > 0,
      contextCount: contextItems.length
    };
    setMessages(prev => [...prev, userMessage]);
    
    // Clear context after sending
    setContextItems([]);
    setLoading(true);

    try {
      // Send to chat analyze API with complete message including context
      const response = await apiService.chatAnalyze(completeMessage);
      
      // Add AI response
      const aiMessage = {
        id: Date.now() + 1,
        type: 'ai',
        content: response.message,
        timestamp: new Date(),
        data: response
      };
      setMessages(prev => [...prev, aiMessage]);

      // Update test cases if successful
      if (response.test_cases) {
        setTestCases(response.test_cases);
        setCurrentUrl(response.url);
      }
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        type: 'ai',
        content: `Error: ${error.response?.data?.message || error.message}`,
        timestamp: new Date(),
        isError: true
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateCode = async (testCase) => {
    try {
      const testCaseWithUrl = { ...testCase, url: currentUrl };
      const response = await apiService.generateTestCode(testCaseWithUrl);
      return response;
    } catch (error) {
      console.error('Error generating code:', error);
      throw error;
    }
  };

  const handleGenerateAllCodes = async () => {
    try {
      const testCasesWithUrl = testCases.map(tc => ({ ...tc, url: currentUrl }));
      const response = await apiService.generateMultipleTestCodes(testCasesWithUrl);
      return response;
    } catch (error) {
      console.error('Error generating all codes:', error);
      throw error;
    }
  };

  const handleEditTestCase = (index, editedTestCase) => {
    const updatedTestCases = [...testCases];
    updatedTestCases[index] = editedTestCase;
    setTestCases(updatedTestCases);
  };

  const handleRemoveTestCase = (index) => {
    const updatedTestCases = testCases.filter((_, i) => i !== index);
    setTestCases(updatedTestCases);
  };

  const handleAddToContext = (testCase, generatedCode = null) => {
    const contextItem = {
      id: Date.now(),
      testCase: testCase,
      generatedCode: generatedCode
    };
    
    // Check if this test case is already in context (by title)
    const existingIndex = contextItems.findIndex(item => item.testCase.title === testCase.title);
    if (existingIndex >= 0) {
      // Update existing context item
      const updatedContextItems = [...contextItems];
      updatedContextItems[existingIndex] = contextItem;
      setContextItems(updatedContextItems);
    } else {
      // Add new context item
      setContextItems(prev => [...prev, contextItem]);
    }
  };

  const handleRemoveFromContext = (contextId) => {
    setContextItems(prev => prev.filter(item => item.id !== contextId));
  };

  const handleClearContext = () => {
    setContextItems([]);
  };

  return (
    <div className="chat-interface">
      <div className="chat-container">
        <div className="chat-messages-section">
          <ChatMessages messages={messages} loading={loading} />
          <ChatInput 
            onSendMessage={handleSendMessage} 
            disabled={loading}
            contextItems={contextItems}
            onRemoveFromContext={handleRemoveFromContext}
            onClearContext={handleClearContext}
          />
        </div>
        
        {testCases.length > 0 && (
          <div className="test-cases-section">
            <TestCasesList 
              testCases={testCases}
              onGenerateCode={handleGenerateCode}
              onGenerateAllCodes={handleGenerateAllCodes}
              currentUrl={currentUrl}
              onEditTestCase={handleEditTestCase}
              onRemoveTestCase={handleRemoveTestCase}
              onAddToContext={handleAddToContext}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatInterface;
