import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";

export const metadata: Metadata = {
  title: "AwaazAI - Generative Indian Speech AI (Hindi & Hinglish)",
  description: "ElevenLabs-style text-to-speech platform focused strictly on Indian voices, Hindi, and Hinglish.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen flex flex-col bg-white text-gray-900 antialiased">
        <Navbar />
        <main className="flex-1">{children}</main>
        <footer className="border-t border-gray-100 bg-white py-10 px-4">
          <div className="max-w-7xl mx-auto flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-center gap-2">
              <span className="font-bold text-gray-900">AwaazAI</span>
              <span className="text-gray-400 text-xs">• Indian Voice Synthesis Platform</span>
            </div>
            <p className="text-gray-400 text-xs">
              Strict ethical voice policy · Consented voice actors only · No deepfakes.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
