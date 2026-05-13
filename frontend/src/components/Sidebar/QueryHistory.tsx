import React from "react";
import { useChatStore } from "@/store/chatStore";
import { useChat } from "@/hooks/useChat";
import { useLocalStorage } from "@/hooks/useLocalStorage";
import type { ChatMessage, Message } from "@/types/chat";
import { Clock, Trash2 } from "lucide-react";
import { ClientRelativeTime } from "@/components/Common/ClientRelativeTime";

type ChatQueryHistoryEntry = {
  id: string;
  query: string;
  response: string;
  timestamp: string;
  rowCount: number;
};

export const QueryHistory: React.FC = () => {
  const { messages, removeTurnByUserMessageId } = useChatStore();
  const { handleSendMessage } = useChat();
  const [, setChatQueryHistory] = useLocalStorage<ChatQueryHistoryEntry[]>(
    "chat_query_history",
    [],
  );

  const userQueries = React.useMemo(() => {
    const isUserMessage = (message: Message): message is ChatMessage =>
      "role" in message && message.role === "user";

    return messages
      .map((m, index) => ({ m, index }))
      .filter((item): item is { m: ChatMessage; index: number } =>
        isUserMessage(item.m),
      )
      .map(({ m, index }) => {
        const nextMessage = messages[index + 1];
        const rowCount =
          nextMessage &&
          "role" in nextMessage &&
          nextMessage.role === "assistant"
            ? nextMessage.metadata?.row_count
            : undefined;

        return {
          id: m.id,
          query: m.content,
          timestamp: new Date(m.timestamp),
          rowCount,
        };
      })
      .reverse()
      .slice(0, 5);
  }, [messages]);

  const handleDeleteQuery = (userMessageId: string, queryText: string) => {
    removeTurnByUserMessageId(userMessageId);

    const { conversationId, messages: nextMessages } = useChatStore.getState();
    try {
      if (typeof window !== "undefined") {
        window.localStorage.setItem(
          `conversation_${conversationId}`,
          JSON.stringify(nextMessages),
        );
      }
    } catch {
      /* ignore quota / private mode */
    }

    setChatQueryHistory((prev) => {
      const i = prev.findIndex((q) => q.query === queryText);
      if (i === -1) return prev;
      return [...prev.slice(0, i), ...prev.slice(i + 1)];
    });
  };

  const handleRunQuery = (query: string) => {
    handleSendMessage(query);
  };

  if (userQueries.length === 0) {
    return (
      <div className="text-center py-6">
        <Clock size={32} className="mx-auto text-gray-300 mb-2" />
        <p className="text-sm text-gray-500">No recent queries</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold text-gray-700 uppercase">
        Recent Queries
      </p>

      <div className="space-y-1">
        {userQueries.map((query) => (
          <div
            key={query.id}
            className="group px-2 py-2 bg-gray-50 hover:bg-blue-50 rounded border border-gray-200 hover:border-blue-300 transition"
          >
            <button
              type="button"
              onClick={() => handleRunQuery(query.query)}
              className="w-full text-left"
            >
              <p className="text-xs text-gray-900 line-clamp-2 group-hover:text-blue-600 transition">
                {query.query}
              </p>
              <div className="flex items-center justify-between mt-1">
                <ClientRelativeTime
                  date={query.timestamp}
                  className="text-xs text-gray-500"
                />
                {query.rowCount !== undefined && (
                  <p className="text-xs text-gray-500">{query.rowCount} rows</p>
                )}
              </div>
            </button>

            <button
              type="button"
              title="Delete this query and its reply from the chat"
              onClick={(e) => {
                e.stopPropagation();
                handleDeleteQuery(query.id, query.query);
              }}
              className="opacity-0 group-hover:opacity-100 mt-1 p-1 text-red-500 hover:bg-red-100 rounded transition"
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};
