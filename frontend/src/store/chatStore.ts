import { create } from 'zustand';
import { v4 as uuidv4 } from 'uuid';
import { ChatService } from '../services/chatService';
import { ChatState, Message } from '../types/chat';

const chatService = ChatService.getInstance();

interface ChatStore extends ChatState {
  addMessage: (content: string, role: Message['role']) => void;
  sendMessage: (content: string) => Promise<void>;
  syncData: () => Promise<void>;
  clearMessages: () => void;
  setError: (error: string | null) => void;
}

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [],
  isLoading: false,
  error: null,

  addMessage: (content, role) => {
    const message: Message = {
      id: uuidv4(),
      content,
      role,
      timestamp: new Date(),
    };
    set((state) => ({
      messages: [...state.messages, message],
    }));
  },

  sendMessage: async (content) => {
    const { addMessage } = get();
    set({ isLoading: true, error: null });
    
    try {
      // Add user message
      addMessage(content, 'user');
      
      // Get response from API
      const response = await chatService.askQuestion(content);
      
      // Add assistant message
      addMessage(response.answer, 'assistant');
    } catch (error) {
      set({ error: 'Failed to send message. Please try again.' });
      console.error('Error sending message:', error);
    } finally {
      set({ isLoading: false });
    }
  },

  syncData: async () => {
    set({ isLoading: true, error: null });
    try {
      await chatService.syncData();
      set({ error: null });
    } catch (error) {
      set({ error: 'Failed to sync data. Please try again.' });
      console.error('Error syncing data:', error);
    } finally {
      set({ isLoading: false });
    }
  },

  clearMessages: () => {
    set({ messages: [], error: null });
  },

  setError: (error) => {
    set({ error });
  },
}));
