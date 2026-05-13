import apiClient from "@/lib/axios";
import { API_ENDPOINTS } from "./endpoints";
import type {
  ChatRequestPayload,
  ChatResponse,
  SchemaInfo,
  SuggestedQueries,
  HealthCheck,
} from "../types/api";

export type SendMessageOptions = {
  signal?: AbortSignal;
};

export async function sendChatPayload(
  payload: ChatRequestPayload,
  options?: SendMessageOptions,
): Promise<ChatResponse> {
  const signal = options?.signal;

  if (payload.files && payload.files.length > 0) {
    const formData = new FormData();
    formData.append("query", payload.query);

    if (payload.conversation_id) {
      formData.append("conversation_id", payload.conversation_id);
    }

    if (payload.clarification_selection) {
      formData.append(
        "clarification_selection",
        JSON.stringify(payload.clarification_selection),
      );
    }

    payload.files.forEach((file) => {
      formData.append("files", file);
    });

    const response = await apiClient.post<ChatResponse>(
      API_ENDPOINTS.CHAT_UPLOAD,
      formData,
      { signal },
    );
    return response.data;
  }

  const response = await apiClient.post<ChatResponse>(
    API_ENDPOINTS.CHAT,
    payload,
    { signal },
  );
  return response.data;
}

class ChatAPI {
  async sendMessage(
    payload: ChatRequestPayload,
    options?: SendMessageOptions,
  ): Promise<ChatResponse> {
    return sendChatPayload(payload, options);
  }

  async getHealth(): Promise<HealthCheck> {
    const response = await apiClient.get<HealthCheck>(API_ENDPOINTS.HEALTH);
    return response.data;
  }

  async getSchema(): Promise<SchemaInfo> {
    const response = await apiClient.get<SchemaInfo>(API_ENDPOINTS.SCHEMA);
    return response.data;
  }

  async getSuggestedQueries(): Promise<SuggestedQueries> {
    const response = await apiClient.get<SuggestedQueries>(
      API_ENDPOINTS.SUGGESTED_QUERIES,
    );
    return response.data;
  }
}

export const chatAPI = new ChatAPI();

export async function sendChatMessage(message: string): Promise<ChatResponse> {
  return sendChatPayload({ query: message });
}
