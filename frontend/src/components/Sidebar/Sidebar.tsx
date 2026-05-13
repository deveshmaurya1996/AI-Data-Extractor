import React from "react";
import { useUIStore } from "@/store/uiStore";
import { useChatStore } from "@/store/chatStore";
import type { ChatMessage, Message } from "@/types/chat";
import { QueryHistory } from "./QueryHistory";
import { SavedQueries } from "./SavedQueries";
import { InsightCard } from "./InsightCard";
import { BarChart3, Clock } from "lucide-react";

export const Sidebar: React.FC = () => {
  const { sidebarOpen } = useUIStore();
  const { messages } = useChatStore();

  const { totalQueriesToday, averageResponseSeconds } = React.useMemo(() => {
      const now = new Date();
      const startOfToday = new Date(
        now.getFullYear(),
        now.getMonth(),
        now.getDate(),
      );

      const isUserMessage = (message: Message): message is ChatMessage =>
        "role" in message && message.role === "user";
      const isAssistantMessage = (message: Message): message is ChatMessage =>
        "role" in message && message.role === "assistant";

      let queriesToday = 0;
      let responseTimeTotalMs = 0;
      let responseSamples = 0;

      for (let i = 0; i < messages.length; i += 1) {
        const message = messages[i];
        const messageTime = new Date(message.timestamp).getTime();

        if (isUserMessage(message) && messageTime >= startOfToday.getTime()) {
          queriesToday += 1;
        }

        if (!isUserMessage(message)) continue;

        const nextMessage = messages[i + 1];
        if (!nextMessage || !isAssistantMessage(nextMessage)) continue;

        const nextTime = new Date(nextMessage.timestamp).getTime();
        if (nextTime >= messageTime) {
          responseTimeTotalMs += nextTime - messageTime;
          responseSamples += 1;
        }
      }

      const averageSeconds =
        responseSamples > 0
          ? Number((responseTimeTotalMs / responseSamples / 1000).toFixed(1))
          : 0;

      return {
        totalQueriesToday: queriesToday,
        averageResponseSeconds: averageSeconds,
      };
    }, [messages]);

  return (
    <aside
      className={`${
        sidebarOpen ? "w-64" : "w-0"
      } bg-white border-r border-gray-200 transition-all duration-300 overflow-hidden flex flex-col h-full`}
    >
      <div className="px-4 py-4 border-b border-gray-200">
        <h2 className="font-bold text-gray-900 text-lg">Insights</h2>
        <p className="text-xs text-gray-500 mt-1">
          Query history & suggestions
        </p>
      </div>

      <div className="grow overflow-y-auto space-y-4 p-4">
        <InsightCard
          icon={<BarChart3 size={20} />}
          title="Total Queries"
          value={totalQueriesToday}
          subtitle="Today"
          color="blue"
        />

        <InsightCard
          icon={<Clock size={20} />}
          title="Avg Response Time"
          value={`${averageResponseSeconds}s`}
          subtitle="Last 24h"
          color="green"
        />

        <div className="border-t border-gray-200 pt-4">
          <QueryHistory />
        </div>

        <SavedQueries />
      </div>

      <div className="border-t border-gray-200 px-4 py-3 text-xs text-gray-500">
        <p>v1.0.0 • Running on PostgreSQL</p>
      </div>
    </aside>
  );
};
