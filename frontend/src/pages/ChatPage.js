import React from 'react';
import ChatInterface from '../components/chat/ChatInterface';

const ChatPage = () => {
  return (
    <div className="chat-page">
      <header className="page-header">
        <h1>AI Test Generator Chat</h1>
        <p>Describe your testing needs in natural language</p>
      </header>
      
      <main className="page-main">
        <ChatInterface />
      </main>
    </div>
  );
};

export default ChatPage;
