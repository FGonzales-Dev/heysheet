import { type FC, useEffect, useRef, useState } from 'react';
import { useChatStore } from '../store/chatStore';
import { Message } from './Message';
import { ChatInput } from './ChatInput';
import { pingServer } from '../api';

const RefreshIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
  </svg>
);

const LoadingSpinner = () => (
  <svg className="animate-spin h-8 w-8" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
  </svg>
);

export const Chat: FC = () => {
  const { messages, isLoading, error, sendMessage, syncData } = useChatStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [isInitialLoad, setIsInitialLoad] = useState(true);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    const initialSync = async () => {
      await syncData();
      setIsInitialLoad(false);
      
      // Test ping endpoint
      try {
        const response = await pingServer();
        console.log('Ping response:', response);
      } catch (error) {
        console.error('Ping error:', error);
      }
    };
    initialSync();
  }, [syncData]);

  return (
    <div className="flex flex-col h-screen max-w-3xl mx-auto px-4 relative">
      {(isInitialLoad || (!isInitialLoad && isLoading)) && (
        <div className="absolute inset-0 bg-white bg-opacity-60 z-50 flex items-center justify-center">
          <LoadingSpinner />
        </div>
      )}
      
      <div className="flex justify-between items-center py-4 border-b">
        <h1 className="text-2xl font-bold text-gray-900">Google Sheet Chat</h1>
        <button
          onClick={async () => {
            console.log('Pinging server...');
            await syncData();
            try {
              const response = await pingServer();
              console.log('Ping response:', response);
            } catch (error) {
              console.error('Ping error:', error);
            }
          }}
          disabled={isLoading}
          className="flex items-center gap-2 px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
        >
          <RefreshIcon />
          Refresh Data
        </button>
      </div>

      {error && (
        <div className="bg-red-50 text-red-600 px-4 py-2 rounded-lg mt-4">
          {error}
        </div>
      )}

      <div className="flex-1 overflow-y-auto py-4">
        {messages.map((message) => (
          <Message key={message.id} message={message} />
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="py-4 border-t">
        <ChatInput onSend={sendMessage} isLoading={isLoading} />
      </div>
    </div>
  );
};
