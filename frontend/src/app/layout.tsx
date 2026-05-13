import type { Metadata } from "next";
import "./globals.css";
import Providers from "./providers";

export const metadata: Metadata = {
  title: "AI Data Extraction Chatbot",
  description: "Natural language querying across ecommerce and support data",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full bg-gray-100 antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
