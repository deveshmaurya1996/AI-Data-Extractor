"use client";

import React, { useEffect } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import queryClient from "@/lib/queryClient";
import { useChatStore } from "@/store/chatStore";
import { useUIStore } from "@/store/uiStore";

interface ProvidersProps {
  children: React.ReactNode;
}

export default function Providers({ children }: ProvidersProps) {
  useEffect(() => {
    void useChatStore.persist.rehydrate();
    void useUIStore.persist.rehydrate();
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <Toaster
        position="bottom-right"
        richColors
        closeButton
        duration={4500}
        toastOptions={{ classNames: { toast: "text-sm" } }}
      />
    </QueryClientProvider>
  );
}
