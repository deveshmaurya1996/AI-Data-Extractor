import React, { useState } from "react";
import { ChatMutationProvider } from "@/context/ChatMutationContext";
import { useUIStore } from "@/store/uiStore";
import { Header } from "./Header";
import { Sidebar } from "../Sidebar/Sidebar";

interface MainLayoutProps {
  children: React.ReactNode;
}

export const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const { sidebarOpen, toggleSidebar } = useUIStore();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleMenuClick = () => {
    setMobileMenuOpen(!mobileMenuOpen);
    toggleSidebar();
  };

  return (
    <ChatMutationProvider>
      <div className="flex h-screen overflow-hidden bg-gray-100">
        <Sidebar />

        <div className="grow flex flex-col overflow-hidden">
          <Header onMenuClick={handleMenuClick} sidebarOpen={sidebarOpen} />

          <main className="grow overflow-y-auto">{children}</main>
        </div>

        {mobileMenuOpen && (
          <div
            className="fixed inset-0 bg-black bg-opacity-50 lg:hidden z-30"
            onClick={() => setMobileMenuOpen(false)}
          />
        )}
      </div>
    </ChatMutationProvider>
  );
};
