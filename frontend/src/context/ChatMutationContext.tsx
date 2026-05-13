"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
} from "react";
import { useMutation } from "@tanstack/react-query";
import axios from "axios";
import { toast } from "sonner";
import { v4 as uuidv4 } from "uuid";

import { sendChatPayload } from "@/api/services";
import type { ChatRequestPayload, ChatResponse } from "@/types/api";
import type { ChatMessage, ClarificationMessage, ErrorMessage, ClarificationSuggestion } from "@/types/chat";
import { useChatStore } from "@/store/chatStore";
import { useLocalStorage } from "@/hooks/useLocalStorage";

function showChatError(message: string) {
  const text = message.trim() || "Something went wrong. Please try again.";
  toast.error(text, { duration: 4500, id: "chat-error" });
}

interface QueryHistoryItem {
  id: string;
  query: string;
  response: string;
  timestamp: Date;
  rowCount: number;
}

type ChatMutationContextValue = {
  handleSendMessage: (query: string, files?: File[]) => Promise<void>;
  handleClarificationSelection: (
    query: string,
    selection: ClarificationSuggestion,
  ) => Promise<void>;
  isChatPending: boolean;
};

const ChatMutationContext = createContext<ChatMutationContextValue | null>(null);

export function useChatMutation(): ChatMutationContextValue {
  const ctx = useContext(ChatMutationContext);
  if (!ctx) {
    throw new Error("useChatMutation must be used within ChatMutationProvider");
  }
  return ctx;
}

export function ChatMutationProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const {
    conversationId,
    addMessage,
    setCurrentQuery,
    setLoading,
    clearError,
    removeClarificationMessages,
    setConversationId,
  } = useChatStore();

  const [, setQueryHistory] = useLocalStorage<QueryHistoryItem[]>(
    "chat_query_history",
    [],
  );

  const [, setSavedConversation] = useLocalStorage(
    `conversation_${conversationId}`,
    [] as unknown[],
  );

  const abortRef = useRef<AbortController | null>(null);

  const mutation = useMutation({
    retry: 0,
    mutationFn: async (payload: ChatRequestPayload) => {
      abortRef.current?.abort();
      const ac = new AbortController();
      abortRef.current = ac;
      return sendChatPayload(payload, { signal: ac.signal });
    },
  });

  useEffect(() => {
    setLoading(mutation.isPending);
  }, [mutation.isPending, setLoading]);

  const persistConversation = useCallback(() => {
    const updated = useChatStore.getState().messages;
    setSavedConversation(updated);
  }, [setSavedConversation]);

  const applyResponse = useCallback(
    (query: string, response: ChatResponse) => {
      const syncConv = (meta?: Record<string, unknown>) => {
        const cid = meta?.conversation_id;
        if (typeof cid === "string" && cid.trim()) {
          setConversationId(cid.trim());
        }
      };

      if (response.type === "success") {
        syncConv(response.metadata as Record<string, unknown> | undefined);
        removeClarificationMessages();
        const assistantMessage: ChatMessage = {
          id: uuidv4(),
          role: "assistant",
          content: response.message,
          timestamp: new Date(),
          data: response.data,
          metadata: response.metadata,
        };
        addMessage(assistantMessage);
        setQueryHistory((prev) => [
          {
            id: assistantMessage.id,
            query,
            response: response.message,
            timestamp: new Date(),
            rowCount: response.data?.length || 0,
          },
          ...prev.slice(0, 49),
        ]);
      } else if (response.type === "clarification") {
        syncConv(response.metadata);
        removeClarificationMessages();
        const clarificationMessage: ClarificationMessage = {
          id: uuidv4(),
          type: "clarification",
          message: response.message,
          suggestions: response.suggestions || [],
          timestamp: new Date(),
        };
        addMessage(clarificationMessage);
      } else if (response.type === "error") {
        const errMsg: ErrorMessage = {
          id: uuidv4(),
          type: "error",
          message: response.message,
          suggestions: response.suggestions,
          metadata: response.metadata,
          timestamp: new Date(),
        };
        addMessage(errMsg);
        const toastText =
          response.message.split("\n").find((l) => l.trim())?.trim() ??
          "Something went wrong.";
        showChatError(toastText.slice(0, 200));
      }
      persistConversation();
    },
    [
      addMessage,
      removeClarificationMessages,
      setQueryHistory,
      persistConversation,
      setConversationId,
    ],
  );

  const handleSendMessage = useCallback(
    async (query: string, files: File[] = []) => {
      if (!query.trim() && files.length === 0) return;
      clearError();
      try {
        const userMessage: ChatMessage = {
          id: uuidv4(),
          role: "user",
          content: query,
          timestamp: new Date(),
        };
        addMessage(userMessage);
        setCurrentQuery("");
        const payload: ChatRequestPayload = {
          query,
          conversation_id: conversationId,
          files,
        };
        const response = await mutation.mutateAsync(payload);
        applyResponse(query, response);
      } catch (err: unknown) {
        if (axios.isCancel(err)) {
          return;
        }
        const { getApiErrorMessage } = await import("@/lib/apiErrorMessage");
        showChatError(getApiErrorMessage(err));
      }
    },
    [
      applyResponse,
      addMessage,
      clearError,
      conversationId,
      mutation,
      setCurrentQuery,
    ],
  );

  const handleClarificationSelection = useCallback(
    async (query: string, selection: ClarificationSuggestion) => {
      try {
        const payload: ChatRequestPayload = {
          query,
          conversation_id: conversationId,
          clarification_selection: selection,
        };
        const response = await mutation.mutateAsync(payload);
        applyResponse(query, response);
      } catch (err: unknown) {
        if (axios.isCancel(err)) {
          return;
        }
        const { getApiErrorMessage } = await import("@/lib/apiErrorMessage");
        showChatError(getApiErrorMessage(err));
      }
    },
    [applyResponse, conversationId, mutation],
  );

  const value = useMemo(
    () => ({
      handleSendMessage,
      handleClarificationSelection,
      isChatPending: mutation.isPending,
    }),
    [handleSendMessage, handleClarificationSelection, mutation.isPending],
  );

  return (
    <ChatMutationContext.Provider value={value}>
      {children}
    </ChatMutationContext.Provider>
  );
}
