
import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { ChatState, Message } from "@/types/chat";
import { v4 as uuidv4 } from "uuid";

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      messages: [],
      currentQuery: "",
      conversationId: uuidv4(),
      loading: false,
      error: null,

      addMessage: (message: Message) =>
        set((state) => ({
          messages: [...state.messages, message],
        })),

      setCurrentQuery: (query: string) =>
        set({ currentQuery: query }),

      setConversationId: (id: string) =>
        set({ conversationId: id }),

      setLoading: (loading: boolean) =>
        set({ loading }),

      setError: (error: string | null) =>
        set({ error }),

      clearMessages: () =>
        set({
          messages: [],
          conversationId: uuidv4(),
        }),

      removeTurnByUserMessageId: (userMessageId: string) =>
        set((state) => {
          const { messages } = state;
          const idx = messages.findIndex(
            (m) =>
              "role" in m &&
              m.role === "user" &&
              m.id === userMessageId
          );
          if (idx === -1) return state;
          let end = idx + 1;
          while (end < messages.length) {
            const m = messages[end];
            if ("role" in m && m.role === "user") break;
            end += 1;
          }
          return {
            messages: [...messages.slice(0, idx), ...messages.slice(end)],
          };
        }),

      removeClarificationMessages: () =>
        set((state) => ({
          messages: state.messages.filter(
            (m) => !("type" in m && m.type === "clarification"),
          ),
        })),

      clearError: () =>
        set({ error: null }),
    }),
    {
      name: "chat-store",
      version: 1,
      skipHydration: true,
    }
  )
);