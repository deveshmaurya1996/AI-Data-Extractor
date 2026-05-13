import React from "react";
import { useHealth } from "@/api/hooks";
import { Menu } from "lucide-react";
import clsx from "clsx";

interface HeaderProps {
  onMenuClick: () => void;
  sidebarOpen: boolean;
}

export const Header: React.FC<HeaderProps> = ({ onMenuClick, sidebarOpen }) => {
  const { data: healthData, isLoading } = useHealth();

  const isHealthy = healthData?.status === "healthy";

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
      <div className="flex items-center justify-between px-4 py-3 lg:px-6">
        <div className="flex items-center gap-4">
          <button
            onClick={onMenuClick}
            className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition lg:hidden"
            title={sidebarOpen ? "Close sidebar" : "Open sidebar"}
            aria-label={sidebarOpen ? "Close sidebar" : "Open sidebar"}
            aria-expanded={sidebarOpen}
          >
            <Menu size={24} />
          </button>

          <div>
            <h1 className="text-xl font-bold text-gray-900">
              AI Data Assistant
            </h1>
            <p className="text-xs text-gray-500">
              Query your business data with natural language
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div
              className={clsx(
                "w-2 h-2 rounded-full",
                isHealthy ? "bg-green-500" : "bg-red-500",
              )}
            />
            <span className="text-xs text-gray-600 hidden sm:inline">
              {isLoading
                ? "Checking..."
                : isHealthy
                  ? "Connected"
                  : "Disconnected"}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
