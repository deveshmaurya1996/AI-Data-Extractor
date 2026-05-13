import { useChatMutation } from "@/context/ChatMutationContext";
import { useChatStore } from "@/store/chatStore";
import { useLocalStorage } from "./useLocalStorage";

interface QueryHistoryItem {
  id: string;
  query: string;
  response: string;
  timestamp: Date;
  rowCount: number;
}

export const useChat = () => {
  const {
    messages,
    currentQuery,
    conversationId,
    loading,
    setCurrentQuery,
    clearMessages,
    clearError,
  } = useChatStore();

  const { handleSendMessage, handleClarificationSelection, isChatPending } =
    useChatMutation();

  const [queryHistory, setQueryHistory] = useLocalStorage<QueryHistoryItem[]>(
    "chat_query_history",
    [],
  );

  const deleteQueryFromHistory = (id: string) => {
    setQueryHistory((prev) => prev.filter((q) => q.id !== id));
  };

  return {
    messages,
    currentQuery,
    conversationId,
    loading: loading || isChatPending,

    handleSendMessage,
    handleClarificationSelection,
    setCurrentQuery,
    clearMessages,
    clearError,

    queryHistory,
    deleteQueryFromHistory,
  };
};
