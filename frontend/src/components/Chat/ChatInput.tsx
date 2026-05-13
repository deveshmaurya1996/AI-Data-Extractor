"use client";

import React, { useState, useRef, useEffect } from "react";
import { Paperclip, Send, X } from "lucide-react";

interface ChatInputProps {
  onSubmit: (query: string, files?: File[]) => void;
  disabled?: boolean;
  placeholder?: string;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSubmit,
  disabled = false,
  placeholder = "Ask me...",
}) => {
  const [query, setQuery] = useState("");
  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const canSend =
    !disabled && (query.trim().length > 0 || attachedFiles.length > 0);

  const handleSubmit = () => {
    if (query.trim() || attachedFiles.length > 0) {
      onSubmit(query, attachedFiles);
      setQuery("");
      setAttachedFiles([]);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 120)}px`;
    }
  }, [query]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;
    setAttachedFiles((prev) => [...prev, ...files]);
  };

  const removeAttachedFile = (index: number) => {
    setAttachedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="border-t bg-white p-4 rounded-b-lg">
      {attachedFiles.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-2">
          {attachedFiles.map((file, index) => (
            <div
              key={`${file.name}-${index}`}
              className="flex items-center gap-2 px-2 py-1 bg-blue-50 border border-blue-200 rounded text-xs text-blue-700"
            >
              <span className="max-w-48 truncate">{file.name}</span>
              <button
                type="button"
                onClick={() => removeAttachedFile(index)}
                className="text-blue-500 hover:text-blue-700"
                aria-label={`Remove ${file.name}`}
              >
                <X size={14} />
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-3">
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          onChange={handleFileSelect}
          multiple
          accept=".csv,.xlsx,.xls,.json,.txt"
        />

        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled}
          className="px-3 py-2 border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-100 disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed transition flex items-center justify-center"
          aria-label="Attach files"
          title="Attach files"
        >
          <Paperclip size={18} />
        </button>

        <textarea
          ref={inputRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          className="grow px-4 py-2 border border-gray-200 rounded-lg appearance-none overflow-hidden focus:outline-none focus:ring-1 focus:ring-blue-400 focus:border-blue-400 resize-none"
        />
        <button
          onClick={handleSubmit}
          disabled={!canSend}
          aria-label="Send message"
          title="Send message"
          className="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 disabled:bg-gray-200 disabled:text-gray-500 disabled:cursor-not-allowed transition flex items-center justify-center min-w-11"
        >
          <Send
            size={22}
            strokeWidth={2.25}
            className="shrink-0"
            aria-hidden="true"
          />
        </button>
      </div>
    </div>
  );
};

export default ChatInput;
