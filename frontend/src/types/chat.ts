export type MessageRole = 'user' | 'assistant';

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
}

export interface ChatState {
  messages: Message[];
  isLoading: boolean;
  error: string | null;
}

export interface SyncResponse {
  synced_rows: number;
}

export interface AskResponse {
  answer: string;
  matches: {
    row: number;
    text: string;
    score: number;
  }[];
}
