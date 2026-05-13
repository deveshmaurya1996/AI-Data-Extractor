import React from "react";

/** Compact assistant “thinking” row for chat (not a full-width spinner). */
export const LoadingSpinner: React.FC = () => {
  return (
    <div
      className="flex justify-start mb-2 animate-fade-in"
      aria-live="polite"
      aria-busy="true"
    >
      <div
        className="inline-flex items-center gap-1.5 rounded-md border border-gray-200 bg-gray-50 px-2 py-1"
        role="status"
      >
        <span className="sr-only">Assistant is thinking</span>
        <span className="flex items-center gap-0.5 px-0.5" aria-hidden>
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="thinking-dot h-1 w-1 shrink-0 rounded-full bg-gray-400"
              style={{ animationDelay: `${i * 140}ms` }}
            />
          ))}
        </span>
        <span className="text-[11px] font-medium text-gray-500 leading-none">
          Thinking
        </span>
      </div>
    </div>
  );
};
