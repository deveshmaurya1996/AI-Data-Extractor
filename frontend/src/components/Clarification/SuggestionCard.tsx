import React from "react";
import type { ClarificationSuggestion } from "@/types/chat";
import { Check } from "lucide-react";
import clsx from "clsx";

interface SuggestionCardProps {
  suggestion: ClarificationSuggestion;
  selected: boolean;
  onSelect: () => void;
  disabled?: boolean;
}

export const SuggestionCard: React.FC<SuggestionCardProps> = ({
  suggestion,
  selected,
  onSelect,
  disabled = false,
}) => {
  return (
    <button
      onClick={onSelect}
      disabled={disabled}
      className={clsx(
        "w-full text-left p-4 border-2 rounded-lg transition",
        selected
          ? "border-blue-500 bg-blue-50"
          : "border-gray-200 bg-white hover:border-blue-300",
        disabled && "opacity-50 cursor-not-allowed",
      )}
    >
      <div className="flex items-start gap-3">
        <div
          className={clsx(
            "shrink-0 w-5 h-5 rounded border-2 flex items-center justify-center mt-0.5",
            selected ? "border-blue-500 bg-blue-500" : "border-gray-300",
          )}
        >
          {selected && <Check size={16} className="text-white" />}
        </div>

        <div className="grow">
          <div className="font-semibold text-gray-900">{suggestion.name}</div>
          <div className="text-sm text-gray-500 mt-1">{suggestion.schema}</div>
          {suggestion.email ? (
            <div className="text-xs text-gray-500 mt-0.5 font-mono">
              {suggestion.email}
            </div>
          ) : null}
        </div>
      </div>
    </button>
  );
};
