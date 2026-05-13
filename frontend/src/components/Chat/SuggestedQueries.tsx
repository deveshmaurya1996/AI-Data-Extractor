
import React from "react";
import { useChat } from "@/hooks/useChat";
import { Sparkles } from "lucide-react";

interface SuggestedQueriesProps {
  queries: string[];
}

export const SuggestedQueries: React.FC<SuggestedQueriesProps> = ({ queries }) => {
  const { handleSendMessage } = useChat();

  return (
    <div className="px-4 py-4 bg-gray-50 border-t border-gray-200">
      <div className="flex items-center gap-2 mb-3">
        <Sparkles size={18} className="text-yellow-500" />
        <p className="text-sm font-semibold text-gray-700">Try asking:</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
        {queries.map((query, idx) => (
          <button
            key={idx}
            onClick={() => handleSendMessage(query)}
            className="text-left p-3 text-sm text-blue-600 hover:bg-blue-50 border border-blue-200 rounded-lg transition hover:border-blue-300"
          >
            &quot;{query}&quot;
          </button>
        ))}
      </div>
    </div>
  );
};