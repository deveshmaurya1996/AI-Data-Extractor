
export const API_ENDPOINTS = {
  CHAT: "/api/chat",
  CHAT_UPLOAD: "/api/chat/upload",
  HEALTH: "/api/health",
  SCHEMA: "/api/schema",
  SUGGESTED_QUERIES: "/api/suggested-queries",
} as const;

export type ApiEndpoint = (typeof API_ENDPOINTS)[keyof typeof API_ENDPOINTS];