import React from 'react';
import StreamingChatInterface from '../components/unified-chat/StreamingChatInterface';

const StreamingChatPage = () => {
  return (
    <div className="streaming-chat-page">
      <header className="page-header">
        <h1>🔄 AI Testing Assistant (Streaming)</h1>
        <p>Real-time test execution with live progress updates and analysis</p>
      </header>
      
      <main className="page-main">
        <StreamingChatInterface />
      </main>
    </div>
  );
};

export default StreamingChatPage; 