import React, { useEffect, useRef } from "react";
import { useChat } from "@/hooks/useChat";
import { useChatMutation } from "@/context/ChatMutationContext";
import { useChatStore } from "@/store/chatStore";
import { useSuggestedQueries } from "@/api/hooks";
import { ChatInput } from "./ChatInput";
import { MessageBubble } from "./MessageBubble";
import { ResultsContainer } from "../Results/ResultsContainer";
import { ClarificationDialog } from "../Clarification/ClarificationDialog";
import { SuggestedQueries } from "./SuggestedQueries";
import { LoadingSpinner } from "../Common/LoadingSpinner";
import type { ChatMessage, ClarificationMessage } from "@/types/chat";

export const ChatInterface: React.FC = () => {
  const { messages, loading, handleSendMessage, handleClarificationSelection } =
    useChat();
  const { isChatPending } = useChatMutation();
  const removeClarificationMessages = useChatStore(
    (s) => s.removeClarificationMessages,
  );

  const { data: suggestedQueriesData } = useSuggestedQueries();
  const messagesScrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = messagesScrollRef.current;
    if (!el) return;
    const id = requestAnimationFrame(() => {
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    });
    return () => cancelAnimationFrame(id);
  }, [messages, loading]);

  const clarificationMessage = messages.find(
    (m) => "type" in m && m.type === "clarification",
  ) as ClarificationMessage | undefined;

  const lastUserMessage = [...messages]
    .reverse()
    .find((m) => "role" in m && m.role === "user") as ChatMessage | undefined;

  return (
    <div className="flex flex-col h-full w-full bg-white overflow-hidden">
      <div
        ref={messagesScrollRef}
        className="grow overflow-y-auto overflow-x-hidden p-4 sm:p-6 space-y-4"
      >
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-500">
            <div className="text-6xl mb-4">💬</div>
            <p className="text-lg font-medium">Start a conversation</p>
            <p className="text-sm mt-1">Ask me about your data</p>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <div key={message.id}>
                <MessageBubble
                  message={message}
                  onFollowUpClick={handleSendMessage}
                />

                {"role" in message &&
                  message.role === "assistant" &&
                  Array.isArray(message.data) &&
                  message.data.length > 0 &&
                  message.metadata?.response_mode !== "conversational" &&
                  message.metadata?.response_mode !== "plain_followup" && (
                    <ResultsContainer message={message} />
                  )}
              </div>
            ))}

            {loading && <LoadingSpinner />}
          </>
        )}
      </div>

      {messages.length === 0 && suggestedQueriesData && (
        <SuggestedQueries queries={suggestedQueriesData.queries} />
      )}

      <ChatInput onSubmit={handleSendMessage} disabled={loading} />

      {clarificationMessage && lastUserMessage && (
        <ClarificationDialog
          message={clarificationMessage}
          open
          onOpenChange={(next) => {
            if (!next) removeClarificationMessages();
          }}
          onSelectClarification={(selection) =>
            handleClarificationSelection(lastUserMessage.content, selection)
          }
          isPending={isChatPending}
        />
      )}
    </div>
  );
};
