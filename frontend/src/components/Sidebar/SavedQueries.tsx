"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Bookmark, Play, Trash2 } from "lucide-react";
import { useChat } from "@/hooks/useChat";
import { useChatStore } from "@/store/chatStore";
import type { Message } from "@/types/chat";

const STORAGE_KEY = "saved_queries_v1";

export type SavedQuery = {
  id: string;
  label: string;
  query: string;
  savedAt: string;
};

function loadSaved(): SavedQuery[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as SavedQuery[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveAll(items: SavedQuery[]) {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
}

function getLastUserQueryText(messages: Message[]): string {
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const m = messages[i];
    if ("role" in m && m.role === "user" && m.content.trim()) {
      return m.content.trim();
    }
  }
  return "";
}

export const SavedQueries: React.FC = () => {
  const { handleSendMessage } = useChat();
  const messages = useChatStore((s) => s.messages);
  const [items, setItems] = useState<SavedQuery[]>([]);
  const [label, setLabel] = useState("");

  useEffect(() => {
    queueMicrotask(() => {
      setItems(loadSaved());
    });
  }, []);

  const persist = useCallback((next: SavedQuery[]) => {
    setItems(next);
    saveAll(next);
  }, []);

  const lastUserQuery = getLastUserQueryText(messages);

  const bookmarkLast = () => {
    const q = lastUserQuery;
    if (!q) return;
    const lab = label.trim() || q.slice(0, 48);
    const row: SavedQuery = {
      id: crypto.randomUUID(),
      label: lab,
      query: q,
      savedAt: new Date().toISOString(),
    };
    persist([row, ...items.filter((x) => x.query !== q)].slice(0, 30));
    setLabel("");
  };

  const remove = (id: string) => {
    persist(items.filter((x) => x.id !== id));
  };

  return (
    <div className="border-t border-gray-200 pt-4 space-y-2">
      <p className="text-xs font-semibold text-gray-700 uppercase">
        Saved queries
      </p>
      <div className="flex gap-1">
        <input
          type="text"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="Label (optional)"
          className="grow min-w-0 text-xs border border-gray-200 rounded px-2 py-1"
        />
        <button
          type="button"
          onClick={bookmarkLast}
          disabled={!lastUserQuery}
          className="shrink-0 px-2 py-1 text-xs bg-blue-600 text-white rounded disabled:bg-gray-300 flex items-center gap-1"
          title="Save last user question"
        >
          <Bookmark size={14} />
          Save
        </button>
      </div>
      {items.length === 0 ? (
        <p className="text-xs text-gray-500">No bookmarks yet.</p>
      ) : (
        <ul className="space-y-1 max-h-40 overflow-y-auto">
          {items.map((s) => (
            <li
              key={s.id}
              className="flex items-start gap-1 text-xs bg-gray-50 rounded border border-gray-200 p-1.5"
            >
              <button
                type="button"
                className="grow text-left text-gray-800 line-clamp-2 hover:text-blue-600"
                onClick={() => handleSendMessage(s.query)}
                title={s.query}
              >
                <span className="font-medium">{s.label}</span>
              </button>
              <button
                type="button"
                aria-label="Run query"
                className="p-0.5 text-blue-600 hover:bg-blue-100 rounded"
                onClick={() => handleSendMessage(s.query)}
              >
                <Play size={14} />
              </button>
              <button
                type="button"
                aria-label="Remove"
                className="p-0.5 text-red-500 hover:bg-red-50 rounded"
                onClick={() => remove(s.id)}
              >
                <Trash2 size={14} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};
