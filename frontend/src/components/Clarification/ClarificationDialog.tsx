import React, { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { ClarificationMessage, ClarificationSuggestion } from "@/types/chat";
import { SuggestionCard } from "./SuggestionCard";
import { X } from "lucide-react";

export interface ClarificationDialogProps {
  message: ClarificationMessage;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelectClarification: (
    selection: ClarificationSuggestion,
  ) => void | Promise<void>;
  isPending: boolean;
}

export const ClarificationDialog: React.FC<ClarificationDialogProps> = ({
  message,
  open,
  onOpenChange,
  onSelectClarification,
  isPending,
}) => {
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const handleSelect = async (suggestionId: number) => {
    const suggestion = message.suggestions.find((s) => s.id === suggestionId);
    if (!suggestion) return;

    setSelectedId(suggestion.id);
    await onSelectClarification(suggestion);
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/50" />
        <Dialog.Content
          className="fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white p-0 shadow-xl outline-none focus:outline-none"
        >
          <Dialog.Description id="clarification-dialog-desc" className="sr-only">
            Choose the record that best matches your question.
          </Dialog.Description>
          <div className="border-b border-gray-200 px-6 py-4 flex items-center justify-between">
            <Dialog.Title className="text-lg font-semibold text-gray-900">
              Clarification needed
            </Dialog.Title>
            <Dialog.Close asChild>
              <button
                type="button"
                className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 focus-visible:ring-2 focus-visible:ring-blue-500 focus:outline-none"
                aria-label="Dismiss"
              >
                <X size={20} />
              </button>
            </Dialog.Close>
          </div>

          <div className="p-6">
            <p className="text-gray-700 mb-6">{message.message}</p>

            <div className="space-y-3">
              {message.suggestions.map((suggestion) => (
                <SuggestionCard
                  key={suggestion.id}
                  suggestion={suggestion}
                  selected={selectedId === suggestion.id}
                  onSelect={() => {
                    void handleSelect(suggestion.id);
                  }}
                  disabled={isPending}
                />
              ))}
            </div>

            {isPending && (
              <div className="mt-4 text-center">
                <div className="inline-block animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500" />
                <p className="text-sm text-gray-600 mt-2">Processing…</p>
              </div>
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};
