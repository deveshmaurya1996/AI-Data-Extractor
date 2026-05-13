"use client";

import { MainLayout } from "@/components/Layout/MainLayout";
import { ChatInterface } from "@/components/Chat/ChatInterface";

export default function Home() {
  return (
    <MainLayout>
      <div className="h-full w-full">
        <ChatInterface />
      </div>
    </MainLayout>
  );
}
