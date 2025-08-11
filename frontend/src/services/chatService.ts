import type { AskResponse, SyncResponse } from '../types/chat';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export class ChatService {
  private static instance: ChatService;
  
  private constructor() {}

  static getInstance(): ChatService {
    if (!ChatService.instance) {
      ChatService.instance = new ChatService();
    }
    return ChatService.instance;
  }

  async syncData(): Promise<SyncResponse> {
    try {
      const response = await fetch(`${API_URL}/api/sync`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      
      if (!response.ok) {
        throw new Error('Failed to sync data');
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error syncing data:', error);
      throw error;
    }
  }

  async askQuestion(question: string): Promise<AskResponse> {
    try {
      const response = await fetch(`${API_URL}/api/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to get answer');
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error asking question:', error);
      throw error;
    }
  }
}
