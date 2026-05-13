import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { UIState } from "@/types/chat";

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      sidebarOpen: true,
      showMetadata: false,
      theme: "light",

      toggleSidebar: () =>
        set((state) => ({
          sidebarOpen: !state.sidebarOpen,
        })),

      toggleMetadata: () =>
        set((state) => ({
          showMetadata: !state.showMetadata,
        })),

      setTheme: (theme: "light" | "dark") =>
        set({ theme }),
    }),
    {
      name: "ui-store",
      version: 1,
      skipHydration: true,
    }
  )
);