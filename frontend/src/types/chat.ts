export interface ChatMetadata {
  confidence?: number;
  source?: string;
  confidence_label?: "high" | "medium" | "low";
  explanation?: string;
  sql?: string;
  strategy?: string;
  row_count?: number;
  data_preview?: Record<string, unknown>[];
  response_mode?: "conversational" | "tabular" | "plain_followup";
  skip_sql?: boolean;
  follow_up_suggestions?: string[];
  conversation_id?: string;
}

export interface ClarificationSuggestion {
  id: number;
  name: string;
  schema: string;
  email?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  data?: Record<string, unknown>[];
  metadata?: ChatMetadata;
}

export interface ClarificationMessage {
  id: string;
  type: "clarification";
  message: string;
  suggestions: ClarificationSuggestion[];
  timestamp: Date;
}

export interface ErrorMessage {
  id: string;
  type: "error";
  message: string;
  error_type?: string;
  suggestions?: string[];
  metadata?: Record<string, unknown>;
  timestamp: Date;
}

export type Message = ChatMessage | ClarificationMessage | ErrorMessage;

export interface ChatState {
  messages: Message[];
  currentQuery: string;
  conversationId: string;
  loading: boolean;
  error: string | null;

  addMessage: (message: Message) => void;
  setCurrentQuery: (query: string) => void;
  setConversationId: (id: string) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearMessages: () => void;
  clearError: () => void;
  removeTurnByUserMessageId: (userMessageId: string) => void;
  removeClarificationMessages: () => void;
}

export interface UIState {
  sidebarOpen: boolean;
  showMetadata: boolean;
  theme: "light" | "dark";

  toggleSidebar: () => void;
  toggleMetadata: () => void;
  setTheme: (theme: "light" | "dark") => void;
}