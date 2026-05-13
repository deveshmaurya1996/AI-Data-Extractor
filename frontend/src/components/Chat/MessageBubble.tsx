
import React from "react";
import { Message } from "@/types/chat";
import { ConfidenceBadge } from "../Common/ConfidenceBadge";
import { CopyButton } from "../Common/CopyButton";
import { ClientRelativeTime } from "../Common/ClientRelativeTime";

interface MessageBubbleProps {
  message: Message;
  onFollowUpClick?: (query: string) => void;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  onFollowUpClick,
}) => {
  const isUser = "role" in message && message.role === "user";

  if ("type" in message && message.type === "error") {
    return (
      <div className="flex justify-center mb-4">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 max-w-3xl w-full text-left">
          <p className="text-red-900 font-semibold mb-2">Could not run that query</p>
          <p className="text-red-800 text-sm whitespace-pre-wrap leading-relaxed">
            {message.message}
          </p>
          {message.suggestions && message.suggestions.length > 0 && (
            <div className="mt-4 text-sm border-t border-red-200 pt-3">
              <p className="text-red-800 font-medium mb-2">Example questions you can try:</p>
              <ul className="space-y-1.5 list-disc list-inside text-red-700">
                {message.suggestions.map((sugg, i) => (
                  <li key={i}>{sugg}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    );
  }

  if ("type" in message && message.type === "clarification") {
    return (
      <div className="flex justify-center mb-4">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 max-w-md">
          <p className="text-blue-900 font-medium mb-3">{message.message}</p>
          <div className="space-y-2">
            {message.suggestions.map((sugg) => (
              <button
                key={sugg.id}
                className="w-full text-left p-2 bg-white hover:bg-blue-100 border border-blue-200 rounded transition"
              >
                <div className="font-medium text-gray-900">{sugg.name}</div>
                <div className="text-sm text-gray-500">{sugg.schema}</div>
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex mb-4 ${isUser ? "justify-end" : "justify-start"} animate-slide-up`}>
      <div
        className={`max-w-lg rounded-lg p-4 ${
          isUser
            ? "bg-blue-500 text-white"
            : "bg-gray-100 text-gray-900 border border-gray-200"
        }`}
      >
        <p className="text-sm">{message.content}</p>

        {!isUser &&
          message.metadata?.follow_up_suggestions &&
          message.metadata.follow_up_suggestions.length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-200">
              <p className="text-xs font-medium text-gray-700 mb-2">Try this</p>
              <div className="flex flex-col gap-2">
                {message.metadata.follow_up_suggestions.map((sugg, i) => (
                  <button
                    key={i}
                    type="button"
                    disabled={!onFollowUpClick}
                    onClick={() => onFollowUpClick?.(sugg)}
                    className="text-left text-xs px-3 py-2 rounded-md border border-gray-300 bg-white
                      hover:bg-gray-50 hover:border-gray-400 text-gray-800 transition
                      disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {sugg.length > 220 ? `${sugg.slice(0, 217)}…` : sugg}
                  </button>
                ))}
              </div>
            </div>
          )}

        {!isUser && message.metadata && (
          <div className="mt-3 pt-3 border-t border-gray-300 space-y-2">
            <ConfidenceBadge
              level={message.metadata.confidence_label ?? "medium"}
              showLabel={true}
            />

            {message.metadata.skip_sql ? (
              <p className="text-xs text-gray-600 whitespace-pre-wrap">
                {message.metadata.explanation}
              </p>
            ) : (
              <details className="text-xs">
                <summary className="cursor-pointer font-medium hover:underline">
                  Why this answer?
                </summary>
                <div className="mt-2 space-y-2">
                  <p>{message.metadata.explanation}</p>
                  <div>
                    <div className="font-medium mb-1">Generated SQL:</div>
                    <div className="bg-gray-800 text-gray-100 p-2 rounded font-mono text-xs overflow-x-auto max-h-40">
                      {message.metadata.sql ?? "No SQL available"}
                    </div>
                    <CopyButton
                      text={message.metadata.sql ?? ""}
                      label="Copy SQL"
                    />
                  </div>
                </div>
              </details>
            )}
          </div>
        )}

        <ClientRelativeTime
          date={new Date(message.timestamp)}
          className={`text-xs mt-2 block ${
            isUser ? "text-blue-100" : "text-gray-500"
          }`}
        />
      </div>
    </div>
  );
};

export default MessageBubble;