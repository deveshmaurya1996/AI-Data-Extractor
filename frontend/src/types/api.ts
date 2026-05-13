export interface ChatRequestPayload {
  query: string;
  conversation_id?: string;
  files?: File[];
  clarification_selection?: {
    id: number;
    name: string;
    schema: string;
    email?: string;
  };
}

export interface ChatMetadata {
  confidence?: number;
  source?: string;
  confidence_label?: "high" | "medium" | "low";
  explanation?: string;
  sql?: string;
  strategy?: string;
  row_count?: number;
  data_preview?: Record<string, unknown>[];
  execution_time_ms?: number;
  cache_hit?: boolean;
  data_sources?: string[];
  used_uploads?: boolean;
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

export interface ChatSuccessResponse {
  type: "success";
  message: string;
  data?: Record<string, unknown>[];
  metadata?: ChatMetadata;
}

export interface ChatClarificationResponse {
  type: "clarification";
  message: string;
  suggestions: ClarificationSuggestion[];
  metadata?: Record<string, unknown>;
}

export interface ChatErrorResponse {
  type: "error";
  message: string;
  error_type?: string;
  suggestions?: string[];
  metadata?: Record<string, unknown>;
}

export type ChatResponse =
  | ChatSuccessResponse
  | ChatClarificationResponse
  | ChatErrorResponse;

export interface HealthCheck {
  status: string;
  service: string;
}

export interface SchemaInfo {
  ecommerce: Record<string, string[]>;
  support: Record<string, string[]>;
  uploads?: Record<string, string[]>;
}

export interface SuggestedQueries {
  queries: string[];
}
